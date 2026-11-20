import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal as D

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Ativo, Cotacao, CotacaoMoeda, CriptoMercado, HistoricoLancamento, Investidor, Operacao
from app.providers import cripto as fonte
from app.providers.base import AtivoRef, CotacaoAtual
from app.providers.yahoo import MERCADO_CRIPTO, ProvedorYahoo, simbolo_yahoo
from app.schemas import AtivoIn, CriptoOperacaoIn, CriptoTrocaTickerIn, OperacaoIn
from app.services import carteira as servico_carteira
from app.services import cotacoes, cripto, historico


def snapshot(id_="bitcoin", fonte_="CoinGecko", preco="100", **extras):
    return fonte.Mercado(
        id=id_, symbol="btc", name="Bitcoin", current_price=D(preco),
        last_updated=datetime.now(UTC), fonte=fonte_, **extras,
    )


@pytest.fixture
def sessao():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as sessao:
        yield sessao
    engine.dispose()


def cadastrar(sessao):
    inv1, inv2 = Investidor(nome="A"), Investidor(nome="B")
    ativo = Ativo(ticker="BTC", classe="CRIPTO", moeda="USD", mercado=None, coingecko_id="bitcoin")
    outro = Ativo(ticker="ETH", classe="CRIPTO", moeda="BRL", mercado=None, coingecko_id="ethereum")
    sessao.add_all([inv1, inv2, ativo, outro])
    sessao.commit()
    return inv1, inv2, ativo, outro


def operacao(sessao, inv, ativo, dia, q, p, cambio="1", taxas="0"):
    sessao.add(Operacao(
        investidor_id=inv.id, ativo_id=ativo.id, data=date.fromisoformat(dia),
        evento="C" if D(q) > 0 else "V", quantidade=D(q), preco=D(p),
        moeda=ativo.moeda, cambio=D(cambio), taxas=D(taxas),
    ))
    sessao.commit()


def ptax_fixa(monkeypatch, valores):
    def obter(moeda, dia, dias_uteis_antes=0):
        if moeda not in valores:
            raise cripto.bcb.ErroPtax(f"indisponível: {moeda}")
        taxa = D(valores[moeda])
        return cripto.bcb.Ptax(moeda, dia, taxa, taxa)

    monkeypatch.setattr(cripto.bcb, "ptax", obter)


def nova_operacao_cripto(sessao, investidor, ativo, dia, **campos):
    valores = {
        "investidor_id": investidor.id, "ativo_id": ativo.id, "data": dia, "evento": "C",
        "quantidade": D("1"), "moeda": "USD", "valor_original": D("100"),
    }
    valores.update(campos)
    return cripto.salvar_operacao(sessao, CriptoOperacaoIn(**valores))


def test_catalogo_cache_e_identidade(monkeypatch):
    chamadas = []
    fonte._buscar.cache_clear()
    monkeypatch.setattr(fonte, "_get", lambda url, params: chamadas.append(params) or {
        "coins": [{"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
                  {"id": "outro-btc", "symbol": "BTC", "name": "Outro BTC"}],
    })
    assert [m.id for m in fonte.buscar("BTC")] == ["bitcoin", "outro-btc"]
    assert fonte.buscar("btc")[0].symbol == "BTC"
    assert len(chamadas) == 1


def test_fallback_so_por_id_verificado_e_sem_metricas_inventadas(monkeypatch):
    chamadas = []

    def get(url, params):
        chamadas.append(params)
        if "coins/markets" in url:
            raise fonte.ErroCripto("CoinGecko offline")
        return {"error": [], "result": {"XXBTZUSD": {"c": ["100.000001", "1"]}}}

    monkeypatch.setattr(fonte, "_get", get)
    encontrados, avisos = fonte.mercados(["bitcoin", "outro-btc"])
    assert encontrados["bitcoin"].current_price == D("100.000001")
    assert encontrados["bitcoin"].fonte == "Kraken"
    assert encontrados["bitcoin"].market_cap is None
    assert encontrados["bitcoin"].price_change_percentage_24h_in_currency is None
    assert "outro-btc" not in encontrados
    assert chamadas[-1] == {"pair": "XBTUSD"}
    assert any("sem vínculo Kraken" in aviso for aviso in avisos)


def test_erro_kraken_e_snapshot_invalido_nao_sao_sucesso(monkeypatch):
    monkeypatch.setattr(fonte, "_get", lambda url, params: (
        [{"id": "bitcoin", "current_price": -1}] if "coins/markets" in url
        else {"error": ["EQuery:Unknown asset pair"], "result": {}}
    ))
    encontrados, avisos = fonte.mercados(["bitcoin"])
    assert encontrados == {}
    assert len(avisos) == 2


def test_consulta_retry_e_decimal(monkeypatch):
    chamadas = []
    monkeypatch.setattr(fonte.time, "sleep", lambda tempo: None)

    def get(url, **kwargs):
        chamadas.append(url)
        return httpx.Response(
            429 if len(chamadas) < 3 else 200,
            text='{"preco": 0.123456789123}', request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(fonte.httpx, "get", get)
    assert fonte._get("https://exemplo.test", {}) == {"preco": D("0.123456789123")}
    assert len(chamadas) == 3


def test_historico_cache_validacao(monkeypatch):
    fonte._historico.cache_clear()
    monkeypatch.setattr(fonte, "_get", lambda url, params: {"prices": [[1000, D("1.01")], [2000, D("2.02")]]})
    pontos = fonte.historico("bitcoin", 30)
    assert pontos[0] == (datetime.fromtimestamp(1, UTC), D("1.01"))
    fonte._historico.cache_clear()
    monkeypatch.setattr(fonte, "_get", lambda url, params: {"prices": []})
    with pytest.raises(fonte.ErroCripto):
        fonte.historico("bitcoin", 30)


def test_snapshot_cotacoes_idempotentes_e_conversao(sessao, monkeypatch):
    inv, _, ativo, outro = cadastrar(sessao)
    operacao(sessao, inv, ativo, "2026-01-01", "2", "50", cambio="4")
    monkeypatch.setattr(fonte, "mercados", lambda ids: (
        {"bitcoin": snapshot(price_change_percentage_24h_in_currency=D("2")),
         "ethereum": snapshot("ethereum", preco="20")}, [],
    ))
    monkeypatch.setattr(cripto.ProvedorBcb, "cambios", lambda self, moedas: {
        "USD": CotacaoAtual("USD", D("5"), None, date.today(), "BCB PTAX"),
    })
    assert len(cripto.atualizar(sessao).atualizados) == 2
    cripto.atualizar(sessao)
    assert len(list(sessao.scalars(select(CriptoMercado)))) == 2
    assert len(list(sessao.scalars(select(Cotacao)))) == 2
    assert sessao.scalar(select(Cotacao).where(Cotacao.ativo_id == outro.id)).preco == D("100")
    painel = cripto.painel(sessao, [inv.id])
    bitcoin = painel["itens"][0]
    assert bitcoin["preco_brl"] == D("500")
    assert bitcoin["mercado_brl"] == D("1000")
    assert bitcoin["investido_brl"] == D("400")
    assert bitcoin["variacao_24h"] == D("0.02")
    assert painel["cambio_data"] == date.today()


def test_sem_cambio_usd_nao_cria_preco_brl(sessao, monkeypatch):
    _, _, _, ativo_brl = cadastrar(sessao)
    monkeypatch.setattr(fonte, "mercados", lambda ids: ({"ethereum": snapshot("ethereum")}, []))
    monkeypatch.setattr(cripto.ProvedorBcb, "cambios", lambda self, moedas: {})
    resultado = cripto.atualizar(sessao)
    assert any("câmbio indisponível" in a for a in resultado.avisos)
    assert sessao.scalar(select(Cotacao).where(Cotacao.ativo_id == ativo_brl.id)) is None
    assert cripto.painel(sessao, None)["itens"][1]["preco_brl"] is None


def test_monitor_limite_exato_soma_ativos_e_nao_soma_cpfs(sessao):
    inv, inv2, btc, eth = cadastrar(sessao)
    for investidor in [inv, inv2]:
        operacao(sessao, investidor, btc, "2025-01-01", "10", "1000", cambio="5")
        operacao(sessao, investidor, eth, "2025-01-02", "10", "1000")
    operacao(sessao, inv, btc, "2026-03-01", "-2", "3000", cambio="5", taxas="10")
    operacao(sessao, inv, eth, "2026-03-02", "-1", "5000")
    operacao(sessao, inv2, eth, "2026-03-01", "-1", "35000.01")
    meses = cripto.monitor(sessao, None, 2026)["meses"]
    assert len(meses) == 2
    assert meses[0]["vendas_brl"] == D("35000")
    assert not meses[0]["acima_limite"]
    assert meses[0]["saldo_limite_brl"] == 0
    assert meses[0]["resultado_brl"] == D("23950")
    assert meses[1]["acima_limite"]
    assert len(cripto.monitor(sessao, [inv.id], 2026)["meses"]) == 1


def test_monitor_perda_separada_e_posicao_anterior_ao_ano(sessao):
    inv, _, btc, _ = cadastrar(sessao)
    operacao(sessao, inv, btc, "2025-01-01", "2", "100")
    operacao(sessao, inv, btc, "2026-02-01", "-1", "80", taxas="2")
    m = cripto.monitor(sessao, None, 2026)["meses"][0]
    assert m["vendas_brl"] == D("80")
    assert m["perdas_brl"] == D("22")
    assert m["ganhos_brl"] == 0
    assert m["resultado_brl"] == D("-22")


def test_monitor_venda_sem_posicao_exibe_incompletude(sessao):
    inv, _, btc, _ = cadastrar(sessao)
    operacao(sessao, inv, btc, "2026-02-01", "-1", "100")
    resultado = cripto.monitor(sessao, None, 2026)
    assert resultado["avisos"]
    assert resultado["meses"][0]["resultado_brl"] is None
    assert resultado["meses"][0]["vendas_brl"] == 100


def test_atualizador_generico_nao_envia_cripto_ao_yahoo(sessao):
    _, _, btc, _ = cadastrar(sessao)

    class Provedor:
        def cotacoes(self, ativos):
            assert not ativos
            return {}

        def cambios(self, moedas):
            return {}

    assert cotacoes.atualizar_cotacoes(sessao, [Provedor()], [btc]).atualizados == {}


def test_schema_retrocompativel_e_id_so_para_cripto():
    assert AtivoIn(ticker="PETR4").coingecko_id is None
    with pytest.raises(ValueError):
        AtivoIn(ticker="PETR4", coingecko_id="bitcoin")


def test_api_catalogo_cadastro_vinculo_e_preservacao_id(cliente, monkeypatch):
    monkeypatch.setattr(fonte, "mercados", lambda ids: ({"bitcoin": snapshot()}, []))
    monkeypatch.setattr(fonte, "buscar", lambda termo: [fonte.MoedaCatalogo(id="bitcoin", symbol="btc", name="Bitcoin")])
    assert cliente.get("/api/cripto/catalogo?busca=btc").json() == [
        {"id": "bitcoin", "ticker": "BTC", "nome": "Bitcoin"},
    ]
    ativo = cliente.post("/api/cripto/ativos", json={"coingecko_id": "bitcoin", "ticker": "BTC"}).json()
    assert ativo["classe"] == "CRIPTO" and ativo["moeda"] == "USD"
    assert cliente.post("/api/cripto/ativos", json={"coingecko_id": "bitcoin", "ticker": "OUTRO"}).status_code == 409
    dados = {"ticker": "BTC", "classe": "CRIPTO", "moeda": "USD", "mercado": None}
    editado = cliente.put(f"/api/ativos/{ativo['id']}", json=dados)
    assert editado.status_code == 200
    assert editado.json()["coingecko_id"] == "bitcoin"
    assert cliente.get("/api/cripto").json()["itens"][0]["coingecko_id"] == "bitcoin"
    assert cliente.get("/api/cripto/monitor?ano=2026").json() == {"meses": [], "avisos": []}
    assert cliente.get("/api/cripto/monitor?ano=2100").status_code == 422


def test_api_vincula_sem_alterar_moeda_ticker(cliente, monkeypatch):
    monkeypatch.setattr(fonte, "mercados", lambda ids: ({"bitcoin": snapshot()}, []))
    ativo = cliente.post("/api/ativos", json={"ticker": "BTC_LOCAL", "classe": "CRIPTO", "moeda": "BRL"}).json()
    r = cliente.post("/api/cripto/ativos", json={"coingecko_id": "bitcoin", "ticker": "BTC", "ativo_id": ativo["id"]})
    assert r.status_code == 201
    assert r.json()["ticker"] == "BTC_LOCAL"
    assert r.json()["moeda"] == "BRL"


def test_api_historico_erros_e_shape(cliente, monkeypatch):
    ativo = cliente.post("/api/ativos", json={"ticker": "BTC", "classe": "CRIPTO", "coingecko_id": "bitcoin"}).json()
    monkeypatch.setattr(fonte, "historico", lambda id_, dias: [(datetime(2026, 1, 1, tzinfo=UTC), D("1.2345"))])
    r = cliente.get(f"/api/cripto/{ativo['id']}/historico")
    assert r.json() == [{"instante": "2026-01-01T00:00:00Z", "preco_usd": 1.2345}]
    assert cliente.get(f"/api/cripto/{ativo['id']}/historico?dias=91").status_code == 422
    assert cliente.get("/api/cripto/99999/historico").status_code == 404


def test_precos_abaixo_da_precisao_nao_viram_zero(sessao, monkeypatch):
    cadastrar(sessao)
    monkeypatch.setattr(fonte, "mercados", lambda ids: ({"bitcoin": snapshot(preco="0.0000000001")}, []))
    monkeypatch.setattr(cripto.ProvedorBcb, "cambios", lambda self, moedas: {})
    resultado = cripto.atualizar(sessao)
    assert resultado.atualizados == []
    assert any("precisão" in aviso for aviso in resultado.avisos)
    assert sessao.scalar(select(CriptoMercado)) is None


def test_api_nao_troca_identidade_de_ativo_vinculado(cliente):
    ativo = cliente.post("/api/ativos", json={
        "ticker": "BTC", "classe": "CRIPTO", "coingecko_id": "bitcoin",
    }).json()
    resposta = cliente.put(f"/api/ativos/{ativo['id']}", json={
        "ticker": "BTC", "classe": "CRIPTO", "coingecko_id": "ethereum",
    })
    assert resposta.status_code == 409
    assert cliente.get("/api/ativos").json()[0]["coingecko_id"] == "bitcoin"


def test_fallback_nao_deixa_metricas_antigas_com_novo_preco(sessao, monkeypatch):
    cadastrar(sessao)
    monkeypatch.setattr(fonte, "mercados", lambda ids: ({
        "bitcoin": snapshot(market_cap=D("2000000000000"), price_change_percentage_7d_in_currency=D("10")),
    }, []))
    monkeypatch.setattr(cripto.ProvedorBcb, "cambios", lambda self, moedas: {})
    cripto.atualizar(sessao)
    monkeypatch.setattr(fonte, "mercados", lambda ids: ({"bitcoin": snapshot(fonte_="Kraken")}, []))
    cripto.atualizar(sessao)
    mercado = sessao.scalar(select(CriptoMercado))
    assert mercado.fonte == "Kraken"
    assert mercado.market_cap_usd is None and mercado.variacao_7d is None


def test_operacoes_mistas_preservam_originais_e_custo_historico(sessao, monkeypatch):
    investidor, _, btc, _ = cadastrar(sessao)
    ptax_fixa(monkeypatch, {"USD": "5", "EUR": "6", "GBP": "7"})
    dia = date.today() - timedelta(days=3)
    brl = CriptoOperacaoIn(
        investidor_id=investidor.id, ativo_id=btc.id, data=dia, evento="C",
        quantidade=D("0.01"), moeda="BRL", valor_original=D("5000"),
    )
    usd = CriptoOperacaoIn(
        investidor_id=investidor.id, ativo_id=btc.id, data=dia, evento="C",
        quantidade=D("0.01"), moeda="USD", valor_original=D("500"),
    )
    compra_brl = cripto.salvar_operacao(sessao, brl)
    compra_usd = cripto.salvar_operacao(sessao, usd)
    sessao.add(CriptoMercado(
        ativo_id=btc.id, preco_usd=D("100000"), market_cap_usd=None, variacao_24h=None,
        variacao_7d=None, variacao_30d=None, fonte="fixture", atualizado_em=datetime.now(UTC).replace(tzinfo=None),
    ))
    sessao.commit()

    painel_usd = cripto.painel(sessao, [investidor.id], "USD")
    item_usd = next(item for item in painel_usd["itens"] if item["ativo_id"] == btc.id)
    painel_brl = cripto.painel(sessao, [investidor.id], "BRL")
    item_brl = next(item for item in painel_brl["itens"] if item["ativo_id"] == btc.id)

    assert compra_brl.cripto_valor_original == D("5000")
    assert compra_brl.cripto_cambio_usd == D("0.2")
    assert compra_brl.cripto_valor_usd == D("1000")
    assert compra_usd.moeda == "USD" and compra_usd.cripto_valor_original == D("500")
    assert item_usd["investido_visualizacao"] == D("1500")
    assert item_usd["mercado_visualizacao"] == D("2000")
    assert item_usd["lucro_aberto_visualizacao"] == D("500")
    assert item_brl["investido_visualizacao"] == D("7500")
    assert item_brl["mercado_visualizacao"] == D("10000")
    assert compra_brl.moeda == "BRL" and compra_brl.cripto_valor_original == D("5000")


def test_operacoes_cripto_registram_auditoria(sessao, monkeypatch):
    investidor, _, btc, _ = cadastrar(sessao)
    ptax_fixa(monkeypatch, {"USD": "5", "EUR": "6", "GBP": "7"})
    dia = date.today() - timedelta(days=3)
    criada = nova_operacao_cripto(sessao, investidor, btc, dia, valor_original=D("100"), moeda="USD")

    alterada = CriptoOperacaoIn(
        investidor_id=investidor.id, ativo_id=btc.id, data=dia, evento="C",
        quantidade=D("2"), moeda="USD", valor_original=D("110"),
    )
    cripto.salvar_operacao(sessao, alterada, criada)
    historico = list(sessao.scalars(select(HistoricoLancamento).order_by(HistoricoLancamento.id)))

    assert [item.acao for item in historico] == ["criado", "alterado"]
    assert D(json.loads(historico[1].anterior_json)["quantidade"]) == D("1")
    assert D(json.loads(historico[1].novo_json)["quantidade"]) == D("2")


def test_troca_vinculada_cripto_preserva_custo_na_nova_posicao(sessao, monkeypatch):
    investidor, _, btc, eth = cadastrar(sessao)
    ptax_fixa(monkeypatch, {"USD": "5", "EUR": "6", "GBP": "7"})
    dia = date.today() - timedelta(days=3)
    nova_operacao_cripto(sessao, investidor, btc, dia, valor_original=D("100"), moeda="USD")
    saida, entrada = cripto.salvar_troca_ticker(sessao, CriptoTrocaTickerIn(
        investidor_id=investidor.id, ativo_origem_id=btc.id, ativo_destino_id=eth.id, data=dia,
        quantidade_origem=D("1"), quantidade_destino=D("2"), preco_origem=D("100"), moeda="USD",
    ))

    posicoes, incompletos = cripto._posicoes_em_moeda(
        sessao, [investidor.id], {btc.id, eth.id}, "USD",
    )
    linhas_brl = servico_carteira.montar_carteira(
        sessao, [investidor.id], consolidado=True, ativo_ids={btc.id, eth.id},
    )

    assert saida.transferencia_pareada_id == entrada.id
    assert entrada.transferencia_pareada_id == saida.id
    assert not incompletos
    assert posicoes[btc.id].quantidade == 0
    assert posicoes[eth.id].quantidade == 2 and posicoes[eth.id].custo == D("100")
    assert [(linha.ativo.id, linha.posicao.custo) for linha in linhas_brl] == [(eth.id, D("500"))]


def test_taxa_manual_taxas_em_outra_moeda_e_venda_parcial(sessao, monkeypatch):
    investidor, _, btc, _ = cadastrar(sessao)
    ptax_fixa(monkeypatch, {"USD": "5", "EUR": "6", "GBP": "7"})
    dia = date.today() - timedelta(days=3)

    compra_usd = nova_operacao_cripto(
        sessao, investidor, btc, dia, valor_original=D("100"), moeda="USD",
        taxas=D("2"), taxas_moeda="EUR",
    )
    compra_brl = nova_operacao_cripto(
        sessao, investidor, btc, dia, valor_original=D("500"), moeda="BRL",
        taxas=D("1"), taxas_moeda="GBP",
    )
    venda = CriptoOperacaoIn(
        investidor_id=investidor.id, ativo_id=btc.id, data=dia, evento="V",
        quantidade=D("-1"), moeda="USD", valor_original=D("150"), taxas=D("0.5"),
        taxas_moeda="EUR",
    )
    venda_salva = cripto.salvar_operacao(sessao, venda)
    pos_usd, incompletos = cripto._posicoes_em_moeda(sessao, [investidor.id], {btc.id}, "USD")
    linha_brl = servico_carteira.montar_carteira(
        sessao, [investidor.id], consolidado=True, ativo_ids={btc.id},
    )[0]
    posicao = pos_usd[btc.id]

    assert compra_usd.taxas_moeda == "EUR" and compra_usd.taxas_valor_usd == D("2.4")
    assert compra_usd.taxas_cambio_brl == D("6")
    assert compra_brl.taxas_cambio_brl == D("7")
    assert venda_salva.cripto_valor_usd == D("150")
    assert not incompletos
    assert posicao.quantidade == D("1")
    assert posicao.custo == D("101.9")
    assert posicao.lucro_realizado == D("47.5")
    assert linha_brl.posicao.custo == D("509.5")

    manual = CriptoOperacaoIn(
        investidor_id=investidor.id, ativo_id=btc.id, data=dia, evento="C",
        quantidade=D("1"), moeda="BRL", valor_original=D("1000"),
        cambio_usd=D("0.18"), cambio_usd_manual=True,
        taxas=D("2"), taxas_moeda="EUR", taxas_cambio_usd=D("1.5"),
        taxas_cambio_usd_manual=True,
    )
    manual_salva = cripto.salvar_operacao(sessao, manual)
    assert manual_salva.moeda == "BRL" and manual_salva.cripto_valor_original == D("1000")
    assert manual_salva.cripto_cambio_usd == D("0.18")
    assert manual_salva.cripto_valor_usd == D("180")
    assert manual_salva.cripto_cambio_usd_fonte == "Manual"
    assert manual_salva.cambio == D("0.90")
    assert manual_salva.taxas_valor_usd == D("3")
    assert manual_salva.taxas_cambio_brl == D("7.5")


def test_operacao_legada_nao_usa_cambio_atual_para_custo_usd(sessao):
    inv, _, btc, _ = cadastrar(sessao)
    dia_operacao = date.today() - timedelta(days=30)
    operacao(sessao, inv, btc, dia_operacao.isoformat(), "1", "100", cambio="5")
    sessao.add_all([
        CotacaoMoeda(moeda="USD", data=date.today(), valor=D("8"), fonte="fixture"),
        CriptoMercado(
            ativo_id=btc.id, preco_usd=D("200"), market_cap_usd=None, variacao_24h=None,
            variacao_7d=None, variacao_30d=None, fonte="fixture",
            atualizado_em=datetime.now(UTC).replace(tzinfo=None),
        ),
    ])
    sessao.commit()

    painel = cripto.painel(sessao, [inv.id], "USD")
    item = next(item for item in painel["itens"] if item["ativo_id"] == btc.id)
    painel_brl = cripto.painel(sessao, [inv.id], "BRL")
    item_brl = next(item for item in painel_brl["itens"] if item["ativo_id"] == btc.id)

    assert item["mercado_visualizacao"] == D("200")
    assert item["investido_visualizacao"] is None
    assert any("câmbio histórico ausente" in aviso for aviso in painel["avisos"])
    assert item_brl["investido_visualizacao"] == D("500")
    assert OperacaoIn(
        investidor_id=1, ativo_id=1, data=date.today(), evento="C", quantidade=D("1"),
        moeda="USD", cambio=D("5"), preco=D("1"),
    ).moeda == "USD"
    with pytest.raises(ValueError):
        OperacaoIn(
            investidor_id=1, ativo_id=1, data=date.today(), evento="C", quantidade=D("1"),
            moeda="GBP", cambio=D("5"), preco=D("1"),
        )


def test_api_operacao_cripto_e_consulta_de_cambios(cliente, monkeypatch):
    def ptax(moeda, dia, dias_uteis_antes=0):
        valores = {"USD": D("5"), "EUR": D("6"), "GBP": D("7")}
        taxa = valores[moeda]
        return cripto.bcb.Ptax(moeda, dia, taxa, taxa)

    monkeypatch.setattr(cripto.bcb, "ptax", ptax)
    investidor = cliente.post("/api/investidores", json={"nome": "Teste"}).json()
    ativo = cliente.post("/api/ativos", json={
        "ticker": "BTC", "classe": "CRIPTO", "moeda": "USD", "coingecko_id": "bitcoin",
    }).json()
    resposta_cambio = cliente.get("/api/cripto/cambios?data=2026-01-05")
    assert resposta_cambio.status_code == 200
    assert next(m for m in resposta_cambio.json()["moedas"] if m["moeda"] == "GBP")["cambio_usd"] == 1.4

    resposta = cliente.post("/api/cripto/operacoes", json={
        "investidor_id": investidor["id"], "ativo_id": ativo["id"], "data": "2026-01-05", "evento": "C",
        "quantidade": "0.01", "valor_original": "5000", "moeda": "BRL",
    })
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["cripto_valor_original"] == 5000
    assert resposta.json()["cripto_valor_usd"] == 1000
    assert cliente.get("/api/cripto?moeda_visualizacao=GBP").status_code == 200
    assert cliente.get("/api/cripto?moeda_visualizacao=JPY").status_code == 422


def test_troca_ticker_cripto_preserva_cambio_taxas_e_pareamento(cliente, monkeypatch):
    def ptax(moeda, dia, dias_uteis_antes=0):
        valores = {"USD": D("5"), "EUR": D("6"), "GBP": D("7")}
        taxa = valores[moeda]
        return cripto.bcb.Ptax(moeda, dia, taxa, taxa)

    monkeypatch.setattr(cripto.bcb, "ptax", ptax)
    investidor = cliente.post("/api/investidores", json={"nome": "Teste"}).json()
    origem = cliente.post("/api/ativos", json={
        "ticker": "BTC", "classe": "CRIPTO", "moeda": "USD",
    }).json()
    destino = cliente.post("/api/ativos", json={
        "ticker": "ETH", "classe": "CRIPTO", "moeda": "BRL",
    }).json()
    resposta = cliente.post("/api/cripto/troca-ticker", json={
        "investidor_id": investidor["id"], "ativo_origem_id": origem["id"],
        "ativo_destino_id": destino["id"], "data": "2026-01-05",
        "quantidade_origem": "2", "quantidade_destino": "4", "preco_origem": "10",
        "taxas": "1", "taxas_moeda": "GBP", "moeda": "EUR",
    })

    assert resposta.status_code == 201, resposta.text
    saida, entrada = resposta.json()
    assert (saida["quantidade"], saida["preco"], saida["moeda"]) == (-2, 10, "EUR")
    assert (entrada["quantidade"], entrada["preco"], entrada["moeda"]) == (4, 5, "EUR")
    assert saida["cripto_cambio_usd"] == entrada["cripto_cambio_usd"] == 1.2
    assert saida["taxas_valor_usd"] == 1.4 and entrada["taxas_valor_usd"] == 0
    assert saida["cripto_valor_original"] is None
    assert saida["transferencia_pareada_id"] == entrada["id"]
    assert entrada["transferencia_pareada_id"] == saida["id"]

    outro = cliente.post("/api/ativos", json={"ticker": "ABC"}).json()
    incompatível = cliente.post("/api/cripto/troca-ticker", json={
        "investidor_id": investidor["id"], "ativo_origem_id": origem["id"],
        "ativo_destino_id": outro["id"], "data": "2026-01-05",
        "quantidade_origem": 2, "quantidade_destino": 4, "preco_origem": 10, "moeda": "USD",
    })
    assert incompatível.status_code == 422
    assert cliente.get("/api/operacoes", params={"evento": "TRANSFERENCIA"}).json()["total"] == 2


def test_simbolo_yahoo_de_cripto():
    assert simbolo_yahoo(AtivoRef("BTC", MERCADO_CRIPTO, "USD")) == "BTC-USD"
    assert simbolo_yahoo(AtivoRef("NANO", MERCADO_CRIPTO, "USD")) == "XNO-USD"
    assert simbolo_yahoo(AtivoRef("SUI", MERCADO_CRIPTO, "USD")) == "SUI20947-USD"
    assert simbolo_yahoo(AtivoRef("BTC", None, "USD")) is None  # cotação atual segue no CoinGecko


def test_historico_complementar_inclui_criptos(sessao, monkeypatch):
    inv, _, btc, eth = cadastrar(sessao)
    operacao(sessao, inv, btc, "2026-01-05", "1", "90000")
    pedidos = []

    def falso_historico(self, ativos, inicio):
        pedidos.extend(ativos)
        return {"BTC": {date(2026, 1, 30): D("0.00001234"), date(2026, 2, 27): D("85000")}}

    monkeypatch.setattr(ProvedorYahoo, "historico", falso_historico)
    resultado = historico.carregar_historico_exterior(sessao)

    assert [(a.ticker, a.mercado) for a in pedidos] == [("BTC", MERCADO_CRIPTO)]  # ETH sem operação fica de fora
    assert resultado.gravados["cotações"] == 2 and not resultado.falhas
    precos = {c.data: c.preco for c in sessao.scalars(select(Cotacao).where(Cotacao.ativo_id == btc.id))}
    assert precos == {date(2026, 1, 30): D("0.00001234"), date(2026, 2, 27): D("85000")}
