from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_extrato_b3 import NEGOCIACAO, enviar

from app.api.rentabilidade import real
from app.db import Base
from app.models import Ativo, AtivoRadar, Corretora, Cotacao, Investidor, Operacao, Provento
from app.services import agenda_proventos, alertas, exposicao, metas, qualidade
from app.services import renda_fixa_liquida as rfl


@pytest.fixture
def sessao():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def _op(inv, ativo, dia, qtd, preco, evento="C", corretora=None, taxas=D(0)):
    return Operacao(
        investidor_id=inv.id, ativo_id=ativo.id, data=dia, evento=evento, quantidade=D(qtd), preco=D(preco),
        taxas=taxas, corretora_id=corretora.id if corretora else None,
    )


# ---------- Renda fixa ----------

def test_aliquotas_ir_regressivo_e_iof():
    assert [rfl.aliquota_ir(d) for d in (1, 180, 181, 360, 361, 720, 721)] == [
        D("0.225"), D("0.225"), D("0.20"), D("0.20"), D("0.175"), D("0.175"), D("0.15"),
    ]
    assert rfl.aliquota_iof(0) == D("0.96") and rfl.aliquota_iof(1) == D("0.96")
    assert rfl.aliquota_iof(29) == D("0.03") and rfl.aliquota_iof(30) == 0


def test_resgate_consome_aplicacoes_mais_antigas():
    movs = [
        (date(2024, 1, 1), "C", D(100), D(1), D(0), D(1)),
        (date(2025, 1, 1), "C", D(100), D("1.1"), D(0), D(1)),
        (date(2025, 6, 1), "V", D(-150), D("1.2"), D(0), D(1)),
    ]
    abertas = rfl.aplicacoes_abertas(movs)
    assert len(abertas) == 1
    assert abertas[0].data == date(2025, 1, 1) and abertas[0].quantidade == 50 and abertas[0].custo == D(55)


def test_impostos_por_aplicacao():
    hoje = date(2026, 1, 1)
    aplicacoes = [rfl.Aplicacao(date(2023, 1, 1), D(100), D(100)), rfl.Aplicacao(date(2025, 10, 1), D(100), D(100))]
    r = rfl.calcular_impostos(aplicacoes, D("1.2"), hoje, isento=False)
    assert r.bruto == D(240) and r.iof == 0
    assert r.ir == D(20) * D("0.15") + D(20) * D("0.225")
    assert rfl.calcular_impostos(aplicacoes, D("1.2"), hoje, isento=True).ir == 0
    curto = rfl.calcular_impostos([rfl.Aplicacao(date(2025, 12, 22), D(100), D(100))], D("1.01"), hoje, False)
    assert curto.iof == D(1) * D("0.66") and curto.ir == (D(1) - curto.iof) * D("0.225")  # 10 dias


def test_listar_renda_fixa_com_projecao_no_vencimento(sessao):
    hoje = date(2026, 1, 1)
    inv = Investidor(nome="Ana")
    cdb = Ativo(
        ticker="CDB-X", classe="R.FIXA", cotacao_automatica=False, indexador="PRE", taxa_aa=D("0.10"),
        data_base=date(2025, 1, 1), data_vencimento=date(2027, 1, 1),
    )
    sessao.add_all([inv, cdb])
    sessao.flush()
    sessao.add(_op(inv, cdb, date(2025, 1, 1), 1000, 1))
    sessao.commit()

    [item] = rfl.listar(sessao, None, hoje)
    assert item.descricao == "Prefixado 10,00% a.a."
    assert item.dias_para_vencer == 365
    assert abs(item.atual.bruto - D(1100)) < D("0.01")
    assert abs(item.atual.ir - D(100) * D("0.175")) < D("0.01")
    assert item.vencimento is not None and item.vencimento.bruto > item.atual.bruto
    assert abs(item.vencimento.ir - (item.vencimento.bruto - 1000) * D("0.15")) < D("0.01")
    assert item.aliquota_ir == D("0.175")


def test_api_renda_fixa(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={
        "ticker": "LCI-1", "classe": "R.FIXA", "cotacao_automatica": False, "mercado": None, "indexador": "PRE",
        "taxa_aa": 0.1, "data_base": "2024-01-01", "data_vencimento": "2030-01-01", "isento_ir": True,
    }).json()
    assert ativo["isento_ir"] is True and ativo["data_vencimento"] == "2030-01-01"
    cliente.post("/api/operacoes", json={
        "investidor_id": inv, "ativo_id": ativo["id"], "data": "2024-01-01", "evento": "C", "quantidade": 500, "preco": 1,
    })
    r = cliente.get("/api/renda-fixa").json()
    assert len(r["itens"]) == 1 and r["itens"][0]["ir"] == 0 and r["impostos"] == 0
    assert r["liquido"] == r["bruto"] > 500 and r["liquido_vencimento"] > r["liquido"]

    # Edição sem os campos novos (outras telas) não apaga vencimento nem isenção.
    cliente.put(f"/api/ativos/{ativo['id']}", json={
        "ticker": "LCI-1", "classe": "R.FIXA", "cotacao_automatica": False, "mercado": None, "indexador": "PRE",
        "taxa_aa": 0.1, "data_base": "2024-01-01",
    })
    atual = next(a for a in cliente.get("/api/ativos").json() if a["id"] == ativo["id"])
    assert atual["isento_ir"] is True and atual["data_vencimento"] == "2030-01-01"


# ---------- Retorno real ----------

def test_retorno_real_desconta_ipca():
    assert real(D("0.10"), D("0.05")) == D("1.10") / D("1.05") - 1
    assert real(None, D("0.05")) is None and real(D("0.1"), None) is None


# ---------- Agenda e projeção de proventos ----------

def test_projecao_ajusta_pela_quantidade_atual(sessao):
    hoje = date(2026, 10, 31)
    inv = Investidor(nome="Ana")
    petr = Ativo(ticker="PETR4")
    sessao.add_all([inv, petr])
    sessao.flush()
    sessao.add_all([
        _op(inv, petr, date(2025, 1, 10), 100, 30),
        _op(inv, petr, date(2026, 6, 1), 100, 35),
        Provento(investidor_id=inv.id, ativo_id=petr.id, data_com=date(2026, 3, 1), data_pagamento=date(2026, 3, 20),
                 evento="DIVIDENDO", valor=D(50)),
        Provento(investidor_id=inv.id, ativo_id=petr.id, data_pagamento=date(2026, 3, 25), evento="AMORTIZACAO",
                 valor=D(999)),
        Provento(investidor_id=inv.id, ativo_id=petr.id, data_com=date(2026, 7, 1), data_pagamento=date(2026, 8, 20),
                 evento="JSCP", valor=D(40), irrf=D(6)),
        # Já anunciado para agosto/2027: substitui a estimativa daquele mês.
        Provento(investidor_id=inv.id, ativo_id=petr.id, data_pagamento=date(2027, 8, 15), evento="JSCP", valor=D(70)),
        Provento(investidor_id=inv.id, ativo_id=petr.id, data_pagamento=date(2026, 11, 10), evento="DIVIDENDO", valor=D(30)),
    ])
    sessao.commit()

    a = agenda_proventos.calcular(sessao, None, hoje)
    assert [i.data_pagamento for i in a.a_receber] == [date(2026, 11, 10), date(2027, 8, 15)]
    assert a.total_a_receber == D(100)
    meses = {m: (c, e) for m, c, e in a.meses}
    assert len(meses) == 12 and min(meses) == date(2026, 11, 1) and max(meses) == date(2027, 10, 1)
    assert meses[date(2027, 3, 1)] == (0, D(100))  # 50 ÷ 100 cotas na data-com x 200 cotas hoje
    assert meses[date(2027, 8, 1)] == (D(70), 0)
    assert meses[date(2026, 11, 1)] == (D(30), 0)
    assert a.total_12m == D(200)
    [p] = a.por_ativo
    assert p.ticker == "PETR4" and p.estimado == D(100) and p.confirmado == D(100)


def test_api_agenda(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={"ticker": "ITSA4"}).json()["id"]
    hoje = date.today()
    cliente.post("/api/operacoes", json={
        "investidor_id": inv, "ativo_id": ativo, "data": str(hoje - timedelta(days=200)), "evento": "C",
        "quantidade": 10, "preco": 10,
    })
    cliente.post("/api/proventos", json={
        "investidor_id": inv, "ativo_id": ativo, "data_pagamento": str(hoje - timedelta(days=10)),
        "evento": "DIVIDENDO", "valor": 20,
    })
    cliente.post("/api/proventos", json={
        "investidor_id": inv, "ativo_id": ativo, "data_pagamento": str(hoje + timedelta(days=3)), "evento": "DIVIDENDO",
        "valor": 5,
    })
    r = cliente.get("/api/proventos/agenda").json()
    assert r["total_a_receber"] == 5 and r["a_receber"][0]["ticker"] == "ITSA4"
    assert r["total_recebido_12m"] == 20
    assert r["media_mensal"] == 20 / 12
    assert r["yoc_atual"] == 0.2
    assert r["yoc_projetado"] == r["total_12m"] / 100
    assert len(r["meses"]) == 12
    assert any(a["codigo"] == "proventos" for a in cliente.get("/api/alertas").json())


# ---------- Lotes de importação ----------

def test_desfazer_lote_de_importacao(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    manual = cliente.post("/api/ativos", json={"ticker": "WEGE3"}).json()["id"]
    cliente.post("/api/operacoes", json={
        "investidor_id": inv, "ativo_id": manual, "data": "2025-01-02", "evento": "C", "quantidade": 1, "preco": 40,
    })
    r = cliente.post(
        "/api/extratos/b3/importar", params={"investidor_id": inv}, content=NEGOCIACAO,
        headers={"content-type": "application/octet-stream", "x-nome-arquivo": "negocia%C3%A7%C3%A3o.xlsx"},
    ).json()
    lote = r["lote_id"]
    [registro] = cliente.get("/api/lotes").json()
    assert registro["id"] == lote and registro["arquivo"] == "negociação.xlsx" and registro["operacoes"] == r["operacoes"]

    desfeito = cliente.post(f"/api/lotes/{lote}/desfazer")
    assert desfeito.json() == {"operacoes": r["operacoes"], "proventos": 0, "caixa": 0}
    ops = cliente.get("/api/operacoes").json()
    assert ops["total"] == 1 and ops["itens"][0]["ticker"] == "WEGE3"
    assert cliente.get("/api/lotes").json()[0]["desfeito_em"] is not None
    assert cliente.post(f"/api/lotes/{lote}/desfazer").status_code == 409
    assert cliente.post("/api/lotes/999/desfazer").status_code == 404

    # Reimportar depois de desfazer grava de novo.
    assert enviar(cliente, "importar", NEGOCIACAO, investidor_id=inv).json()["operacoes"] == r["operacoes"]


# ---------- Qualidade dos dados ----------

def test_qualidade_aponta_posicao_negativa_e_cambio(sessao):
    hoje = date(2026, 10, 31)
    inv = Investidor(nome="Ana")
    petr = Ativo(ticker="PETR4", classe="AÇÃO")
    aapl = Ativo(ticker="AAPL", classe="STOCK", moeda="USD", mercado="NASDAQ")
    sessao.add_all([inv, petr, aapl])
    sessao.flush()
    venda = _op(inv, petr, date(2026, 1, 5), -10, 30, evento="V")
    compra = _op(inv, aapl, date(2026, 1, 5), 1, 200)
    compra.moeda = "USD"
    sessao.add_all([venda, compra, Cotacao(ativo_id=aapl.id, data=date(2026, 9, 1), preco=D(210), fonte="Yahoo")])
    sessao.commit()

    v = {x.codigo: x for x in qualidade.verificar(sessao, None, hoje)}
    assert v["posicao_negativa"].severidade == "erro" and v["posicao_negativa"].itens[0].startswith("PETR4")
    assert v["cambio_ausente"].itens == ["AAPL em 05/01/2026"]
    assert v["cotacao_antiga"].itens == ["AAPL · 01/09/2026"]
    assert "sem_corretora" in v and "indices_antigos" in v
    assert list(v)[:2] == ["posicao_negativa", "cambio_ausente"]
    assert any(a.codigo == "qualidade" for a in alertas.listar(sessao, None, hoje))


# ---------- Exposição por corretora ----------

def test_exposicao_por_corretora(sessao):
    inv = Investidor(nome="Ana")
    petr = Ativo(ticker="PETR4")
    xp, inter = Corretora(nome="XP"), Corretora(nome="INTER")
    sessao.add_all([inv, petr, xp, inter])
    sessao.flush()
    sessao.add_all([
        _op(inv, petr, date(2025, 1, 2), 100, 30, corretora=xp),
        _op(inv, petr, date(2025, 1, 3), 50, 30, corretora=inter),
        _op(inv, petr, date(2025, 1, 4), 10, 30),
        Cotacao(ativo_id=petr.id, data=date(2025, 2, 1), preco=D(40), fonte="Yahoo"),
    ])
    sessao.commit()
    r = {e.corretora: (e.valor, e.ativos) for e in exposicao.por_corretora(sessao, None)}
    assert r == {"XP": (D(4000), 1), "INTER": (D(2000), 1), exposicao.SEM_CORRETORA: (D(400), 1)}


# ---------- Alertas ----------

def test_alertas_preco_alvo_vencimento_e_desvio(sessao):
    hoje = date(2026, 10, 31)
    inv = Investidor(nome="Ana")
    petr = Ativo(ticker="PETR4", mercado="BVMF")
    cdb = Ativo(
        ticker="CDB-Y", classe="R.FIXA", cotacao_automatica=False, indexador="PRE", taxa_aa=D("0.1"),
        data_base=date(2025, 1, 1), data_vencimento=hoje + timedelta(days=5),
    )
    sessao.add_all([inv, petr, cdb])
    sessao.flush()
    sessao.add_all([
        AtivoRadar(ativo_id=petr.id, preco_alvo=D(35)),
        Cotacao(ativo_id=petr.id, data=hoje, preco=D("34.5"), fonte="Yahoo"),
        _op(inv, cdb, date(2025, 1, 1), 100, 1),
    ])
    sessao.commit()
    codigos = {a.codigo: a for a in alertas.listar(sessao, None, hoje)}
    assert codigos["preco_alvo:PETR4"].severidade == "media"
    assert codigos["vencimento:CDB-Y"].severidade == "alta"


def test_alerta_de_alocacao_consolida_books(monkeypatch):
    from types import SimpleNamespace as NS

    books = [NS(nome="Ações", peso_alvo=D("0.3"), peso_atual=D("0.5")), NS(nome="FII", peso_alvo=D("0.2"), peso_atual=D("0.22")),
             NS(nome="RF", peso_alvo=D("0.5"), peso_atual=D("0.28"))]
    monkeypatch.setattr(alertas.alocacao, "calcular", lambda *_: NS(books=books))
    [a] = alertas._alocacao(None, None, 5)
    assert a.titulo == "2 books fora do alvo"
    assert a.detalhe.startswith("RF: 28,0% × alvo 50,0%; Ações: 50,0% × alvo 30,0%")


def test_radar_preco_alvo_api(cliente):
    ativo = cliente.post("/api/ativos", json={"ticker": "VALE3"}).json()
    cliente.post(f"/api/radar/{ativo['id']}")
    assert cliente.put(f"/api/radar/{ativo['id']}/alvo", json={"preco_alvo": 55.5}).status_code == 204
    item = cliente.get("/api/radar").json()[0]
    assert item["preco_alvo"] == 55.5 and item["atingiu_alvo"] is False
    assert cliente.put("/api/radar/999/alvo", json={"preco_alvo": 1}).status_code == 404
    assert cliente.put(f"/api/radar/{ativo['id']}/alvo", json={"preco_alvo": None}).status_code == 204
    assert cliente.get("/api/radar").json()[0]["preco_alvo"] is None


# ---------- Metas ----------

def test_projecao_e_aporte_necessario_sao_coerentes():
    necessario = metas.aporte_necessario(10_000, 100_000, 0.06, 120)
    assert metas.projetar(10_000, necessario, 0.06, 120)[-1] == pytest.approx(100_000)
    assert metas.aporte_necessario(10_000, 20_000, 0.0, 10) == pytest.approx(1_000)
    assert metas.aporte_necessario(200_000, 100_000, 0.05, 12) == 0
    assert metas.meses_ate_atingir(0, 1_000, 0.0, 12_000) == 12
    assert metas.meses_ate_atingir(0, 0, 0.0, 1) is None


def test_meta_de_renda_usa_rendimento():
    hoje = date(2026, 1, 15)
    from app.models import Meta

    meta = Meta(
        nome="Renda", tipo="RENDA", valor_alvo=D(1000), data_alvo=date(2036, 1, 1), aporte_mensal=D(0),
        rentabilidade_aa=D(0), rendimento_aa=D("0.06"), investidores=None,
    )
    p = metas.calcular(meta, metas.Situacao(patrimonio=200_000, renda_mensal=800), hoje)
    assert p.valor_atual == 800 and p.progresso == pytest.approx(0.8)
    assert p.projetado[1] == pytest.approx(1000)  # 200 mil x 6% ÷ 12
    assert p.atinge and p.data_estimada == date(2026, 1, 1)
    assert p.serie[0][0] == date(2026, 1, 1) and p.serie[-1][0] == date(2036, 1, 1)


def test_api_metas(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    alvo = str(date.today().replace(day=1) + timedelta(days=800))
    r = cliente.post("/api/metas", json={
        "nome": "Independência", "valor_alvo": 50_000, "data_alvo": alvo, "aporte_mensal": 1000,
        "rentabilidade_aa": 0.05, "investidores": [inv],
    })
    assert r.status_code == 201, r.text
    meta = r.json()
    assert meta["investidores"] == [inv] and meta["valor_atual"] == 0 and meta["projetado_base"] > 25_000
    assert meta["projetado_pessimista"] < meta["projetado_base"] < meta["projetado_otimista"]
    assert meta["aporte_necessario"] > 0 and len(meta["serie"]) > 2

    passado = cliente.post("/api/metas", json={"nome": "X", "valor_alvo": 1, "data_alvo": "2020-01-01"})
    assert passado.status_code == 422
    alterada = cliente.put(f"/api/metas/{meta['id']}", json={**{k: meta[k] for k in (
        "nome", "valor_alvo", "data_alvo", "aporte_mensal", "rentabilidade_aa")}, "tipo": "PATRIMONIO", "investidores": None})
    assert alterada.json()["investidores"] is None
    assert len(cliente.get("/api/metas").json()) == 1
    assert cliente.delete(f"/api/metas/{meta['id']}").status_code == 204
    assert cliente.get("/api/metas").json() == []


def test_api_exposicao_e_qualidade_vazias(cliente):
    assert cliente.get("/api/exposicao/corretoras").json() == []
    assert cliente.get("/api/qualidade-dados").json() == []
    assert cliente.get("/api/alertas").json() == []
    assert cliente.get("/api/renda-fixa").json()["itens"] == []
