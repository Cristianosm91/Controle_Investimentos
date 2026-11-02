from datetime import date, timedelta

import pytest


@pytest.fixture
def carteira(cliente):
    """Compra há ~2 meses, cotação de hoje e um provento no mês passado."""
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={"ticker": "ABCD3"}).json()["id"]
    hoje = date.today()
    inicio = (hoje.replace(day=1) - timedelta(days=40)).replace(day=10)
    cliente.post("/api/operacoes", json={
        "investidor_id": inv, "ativo_id": ativo, "data": inicio.isoformat(), "evento": "C", "quantidade": 100, "preco": 10,
    })
    cliente.post("/api/proventos", json={
        "investidor_id": inv, "ativo_id": ativo, "data_pagamento": (inicio + timedelta(days=5)).isoformat(),
        "evento": "DIVIDENDO", "valor": 20,
    })
    return {"investidor": inv, "ativo": ativo, "inicio": inicio}


def test_rentabilidade_mensal_sem_cotacao_usa_custo(cliente, carteira):
    meses = cliente.get("/api/rentabilidade/mensal").json()
    assert len(meses) >= 2
    primeiro = meses[0]
    assert primeiro["investido"] == 1000 and primeiro["mercado"] == 1000
    assert primeiro["sem_cotacao"] == 1
    assert primeiro["proventos"] == 20
    assert primeiro["ibov"] is None  # sem índices carregados


def test_resumo(cliente, carteira):
    r = cliente.get("/api/rentabilidade/resumo").json()
    assert r["investido"] == 1000
    assert r["proventos_total"] == 20
    assert {j["nome"] for j in r["janelas"]} >= {"Mês", "Ano", "12 meses", "Desde o início"}


def test_resumo_separa_aluguel_btc_e_filtra_por_classe(cliente, carteira):
    fii = cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"]
    cliente.post("/api/operacoes", json={
        "investidor_id": carteira["investidor"], "ativo_id": fii, "data": carteira["inicio"].isoformat(),
        "evento": "C", "quantidade": 10, "preco": 50,
    })
    cliente.post("/api/proventos", json={
        "investidor_id": carteira["investidor"], "ativo_id": fii,
        "data_pagamento": (carteira["inicio"] + timedelta(days=5)).isoformat(),
        "evento": "ALUGUEL", "valor": 100, "taxas": 10, "irrf": 5,
    })

    r = cliente.get("/api/rentabilidade/resumo", params={"classe": "FII"}).json()
    assert r["investido"] == 500
    assert r["proventos_total"] == 0
    assert r["aluguel_total"] == 85
    mensal = cliente.get("/api/rentabilidade/mensal", params={"classe": "FII"}).json()
    assert mensal[-1]["investido"] == 500


def test_resumo_vazio(cliente):
    r = cliente.get("/api/rentabilidade/resumo").json()
    assert r["patrimonio"] == 0 and r["janelas"] == []


def test_matriz_de_proventos(cliente, carteira):
    ano = carteira["inicio"].year
    por_ano = cliente.get("/api/proventos/matriz").json()
    assert por_ano["titulo_linhas"] == "Ano" and por_ano["linhas"] == [str(ano)]
    assert por_ano["total"] == 20

    por_ativo = cliente.get("/api/proventos/matriz", params={"ano": ano}).json()
    assert por_ativo["linhas"] == ["ABCD3"]
    mes = (carteira["inicio"] + timedelta(days=5)).month
    assert por_ativo["valores"][0][mes - 1] == 20


def test_matriz_e_agenda_filtradas_por_classe(cliente, carteira):
    fii = cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"]
    hoje = date.today()
    cliente.post("/api/proventos", json={
        "investidor_id": carteira["investidor"], "ativo_id": fii, "data_pagamento": hoje.isoformat(),
        "evento": "DIVIDENDO", "valor": 10,
    })
    cliente.post("/api/proventos", json={
        "investidor_id": carteira["investidor"], "ativo_id": fii,
        "data_pagamento": (hoje + timedelta(days=30)).isoformat(),
        "evento": "DIVIDENDO", "valor": 15,
    })

    matriz = cliente.get("/api/proventos/matriz", params={"ano": hoje.year, "classe": "FII"}).json()
    assert matriz["linhas"] == ["HGLG11"]
    agenda = cliente.get("/api/proventos/agenda", params={"classe": "FII"}).json()
    assert [item["ticker"] for item in agenda["a_receber"]] == ["HGLG11"]


def test_posicoes_trazem_yoc_e_tir(cliente, carteira):
    (p,) = cliente.get("/api/posicoes").json()
    assert p["proventos_12m"] == 20
    assert p["yoc_12m"] == pytest.approx(0.02)
    assert p["tir_aa"] is None  # sem cotação não há valor final
