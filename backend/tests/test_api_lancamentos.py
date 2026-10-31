import pytest


@pytest.fixture
def ids(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={"ticker": "petr4"}).json()["id"]
    corretora = cliente.post("/api/corretoras", json={"nome": "XP"}).json()["id"]
    return {"investidor_id": inv, "ativo_id": ativo, "corretora_id": corretora}


def test_operacao_crud(cliente, ids):
    corpo = {**ids, "data": "2026-01-05", "evento": "C", "quantidade": 100, "preco": 30, "taxas": 1}
    criada = cliente.post("/api/operacoes", json=corpo)
    assert criada.status_code == 201
    op = criada.json()
    assert op["ticker"] == "PETR4" and op["corretora"] == "XP" and op["corretora_id"] == ids["corretora_id"]

    alterada = cliente.put(f"/api/operacoes/{op['id']}", json={**corpo, "quantidade": 50}).json()
    assert alterada["quantidade"] == 50

    assert cliente.get("/api/operacoes", params={"ticker": "petr4"}).json()["total"] == 1
    assert cliente.delete(f"/api/operacoes/{op['id']}").status_code == 204
    assert cliente.get("/api/operacoes").json()["total"] == 0


def test_operacao_rejeita_sinal_e_corretora_inexistente(cliente, ids):
    base = {**ids, "data": "2026-01-05", "evento": "V", "preco": 30}
    assert cliente.post("/api/operacoes", json={**base, "quantidade": 10}).status_code == 422
    assert cliente.post("/api/operacoes", json={**base, "quantidade": -10, "corretora_id": 999}).status_code == 404


def test_provento_alteracao(cliente, ids):
    corpo = {**ids, "data_pagamento": "2026-02-10", "evento": "DIVIDENDO", "valor": 12.5}
    p = cliente.post("/api/proventos", json=corpo).json()
    r = cliente.put(f"/api/proventos/{p['id']}", json={**corpo, "evento": "JSCP", "irrf": 1.88})
    assert r.status_code == 200
    assert r.json()["evento"] == "JSCP" and r.json()["irrf"] == 1.88


def test_provento_em_brl_exige_cambio_1(cliente, ids):
    corpo = {**ids, "data_pagamento": "2026-02-10", "evento": "DIVIDENDO", "valor": 10, "cambio": 5}
    assert cliente.post("/api/proventos", json=corpo).status_code == 422


def test_caixa_crud_e_sinal(cliente, ids):
    corpo = {"investidor_id": ids["investidor_id"], "data": "2026-03-01", "evento": "APORTE", "valor": 1000}
    m = cliente.post("/api/caixa", json=corpo)
    assert m.status_code == 201 and m.json()["corretora"] is None

    assert cliente.post("/api/caixa", json={**corpo, "evento": "SAQUE"}).status_code == 422
    assert cliente.post("/api/caixa", json={**corpo, "evento": "SAQUE", "valor": -200}).status_code == 201

    lista = cliente.get("/api/caixa", params={"investidores": str(ids["investidor_id"])}).json()
    assert lista["total"] == 2
    assert [i["valor"] for i in lista["itens"]] == [-200, 1000]

    mid = m.json()["id"]
    assert cliente.put(f"/api/caixa/{mid}", json={**corpo, "valor": 1500}).json()["valor"] == 1500
    assert cliente.delete(f"/api/caixa/{mid}").status_code == 204


def test_investidor_com_caixa_nao_pode_ser_excluido(cliente, ids):
    cliente.post("/api/caixa", json={"investidor_id": ids["investidor_id"], "data": "2026-03-01", "evento": "APORTE", "valor": 1})
    assert cliente.delete(f"/api/investidores/{ids['investidor_id']}").status_code == 409


def test_ativo_com_provento_nao_pode_ser_excluido(cliente, ids):
    cliente.post("/api/proventos", json={**ids, "data_pagamento": "2026-02-10", "evento": "DIVIDENDO", "valor": 1})
    assert cliente.delete(f"/api/ativos/{ids['ativo_id']}").status_code == 409


def test_status_das_tarefas(cliente):
    nomes = {t["nome"] for t in cliente.get("/api/atualizacoes").json()}
    assert {"cotacoes", "cotahist_diario", "cotahist_historico"} <= nomes
    assert cliente.post("/api/atualizacoes/inexistente").status_code == 404
