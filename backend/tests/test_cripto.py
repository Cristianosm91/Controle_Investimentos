from datetime import UTC, date, datetime
from decimal import Decimal as D

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Ativo, Cotacao, CriptoMercado, Investidor, Operacao
from app.providers import cripto as fonte
from app.providers.base import CotacaoAtual
from app.schemas import AtivoIn
from app.services import cotacoes, cripto


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
