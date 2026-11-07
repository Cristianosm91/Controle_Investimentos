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


def test_operacoes_filtradas_por_classe(cliente, ids):
    fii = cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"]
    cripto = cliente.post("/api/ativos", json={"ticker": "BTC", "classe": "CRIPTO"}).json()["id"]
    for ativo_id in (ids["ativo_id"], fii, cripto):
        resposta = cliente.post(
            "/api/operacoes",
            json={
                "investidor_id": ids["investidor_id"],
                "ativo_id": ativo_id,
                "data": "2026-01-05",
                "evento": "C",
                "quantidade": 1,
                "preco": 10,
            },
        )
        assert resposta.status_code == 201

    resultado = cliente.get("/api/operacoes", params={"classe": "FII"}).json()
    assert resultado["total"] == 1
    assert resultado["itens"][0]["ticker"] == "HGLG11"


def test_alterar_classe_do_ativo_reflete_nos_lancamentos_existentes(cliente, ids):
    operacao = cliente.post(
        "/api/operacoes",
        json={**ids, "data": "2026-01-05", "evento": "C", "quantidade": 1, "preco": 10},
    ).json()
    provento = cliente.post(
        "/api/proventos",
        json={**ids, "data_pagamento": "2026-02-10", "evento": "DIVIDENDO", "valor": 5},
    ).json()
    resposta = cliente.patch(f"/api/ativos/{ids['ativo_id']}/classe", json={"classe": "REIT"})
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["classe"] == "REIT"

    ops = cliente.get("/api/operacoes", params={"classe": "REIT"}).json()["itens"]
    proventos = cliente.get("/api/proventos", params={"classe": "REIT"}).json()["itens"]
    assert [item["id"] for item in ops] == [operacao["id"]]
    assert [item["id"] for item in proventos] == [provento["id"]]


def test_editar_bolsa_preserva_classe_e_corrige_simbolo_yahoo(cliente):
    from app.providers.base import AtivoRef
    from app.providers.yahoo import simbolo_yahoo

    ativo = cliente.post("/api/ativos", json={
        "ticker": "MSFT", "classe": "STOCK", "moeda": "USD", "mercado": "BVMF",
        "setor": "Tecnologia", "cnpj": "12345678000199",
    }).json()
    assert simbolo_yahoo(AtivoRef(ativo["ticker"], ativo["mercado"], ativo["moeda"])) == "MSFT.SA"
    resposta = cliente.patch(f"/api/ativos/{ativo['id']}/classe", json={"mercado": "NASDAQ"})
    assert resposta.status_code == 200, resposta.text
    atualizado = resposta.json()
    assert atualizado == {**ativo, "mercado": "NASDAQ"}
    assert simbolo_yahoo(AtivoRef(atualizado["ticker"], atualizado["mercado"], atualizado["moeda"])) == "MSFT"
    classe = cliente.patch(f"/api/ativos/{ativo['id']}/classe", json={"classe": "ETF_US"})
    assert classe.status_code == 200
    assert classe.json()["mercado"] == "NASDAQ"
    sem_bolsa = cliente.patch(f"/api/ativos/{ativo['id']}/classe", json={"mercado": None})
    assert sem_bolsa.status_code == 200
    assert sem_bolsa.json()["mercado"] is None


@pytest.mark.parametrize("corpo", [{}, {"classe": None}, {"classe": " "}, {"mercado": "INVALIDA"}])
def test_edicao_classe_bolsa_rejeita_entrada_invalida(cliente, ids, corpo):
    resposta = cliente.patch(f"/api/ativos/{ids['ativo_id']}/classe", json=corpo)
    assert resposta.status_code == 422


def test_edicao_bolsa_preserva_protecao_de_cripto_vinculada(cliente):
    ativo = cliente.post("/api/ativos", json={
        "ticker": "BTC", "classe": "CRIPTO", "moeda": "USD",
        "mercado": None, "coingecko_id": "bitcoin",
    }).json()
    rota = f"/api/ativos/{ativo['id']}/classe"
    assert cliente.patch(rota, json={"mercado": "NASDAQ"}).status_code == 409
    assert cliente.patch(rota, json={"classe": "STOCK", "mercado": "NASDAQ"}).status_code == 409
    resposta = cliente.patch(rota, json={"mercado": None})
    assert resposta.status_code == 200
    assert resposta.json() == ativo


def test_filtro_por_corretora_em_operacoes_e_proventos(cliente, ids):
    outra_corretora = cliente.post("/api/corretoras", json={"nome": "Inter"}).json()["id"]
    for corretora_id in (ids["corretora_id"], outra_corretora):
        corpo = {
            **ids,
            "corretora_id": corretora_id,
            "data": "2026-01-05",
            "evento": "C",
            "quantidade": 1,
            "preco": 10,
        }
        assert cliente.post("/api/operacoes", json=corpo).status_code == 201
        provento = {
            **ids,
            "corretora_id": corretora_id,
            "data_pagamento": "2026-02-10",
            "evento": "DIVIDENDO",
            "valor": 10,
        }
        assert cliente.post("/api/proventos", json=provento).status_code == 201

    operacoes = cliente.get("/api/operacoes", params={"corretora_id": ids["corretora_id"]}).json()
    proventos = cliente.get("/api/proventos", params={"corretora_id": ids["corretora_id"]}).json()
    assert operacoes["total"] == proventos["total"] == 1
    assert operacoes["itens"][0]["corretora"] == proventos["itens"][0]["corretora"] == "XP"


def test_filtro_de_operacoes_aceita_varios_tickers(cliente, ids):
    vale = cliente.post("/api/ativos", json={"ticker": "VALE3"}).json()["id"]
    for ativo_id in (ids["ativo_id"], vale):
        assert cliente.post(
            "/api/operacoes",
            json={
                "investidor_id": ids["investidor_id"],
                "ativo_id": ativo_id,
                "data": "2026-01-05",
                "evento": "C",
                "quantidade": 1,
                "preco": 10,
            },
        ).status_code == 201

    resultado = cliente.get("/api/operacoes", params={"ticker": "petr4, VALE3"}).json()
    assert resultado["total"] == 2
    assert {item["ticker"] for item in resultado["itens"]} == {"PETR4", "VALE3"}


def test_filtro_de_operacoes_aplicado_antes_da_paginacao(cliente, ids):
    fii = cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"]
    acoes = cliente.post("/api/ativos", json={"ticker": "VALE3", "classe": "AÇÃO"}).json()["id"]
    for ativo_id in (fii, acoes, fii):
        assert cliente.post(
            "/api/operacoes",
            json={
                "investidor_id": ids["investidor_id"],
                "ativo_id": ativo_id,
                "data": "2026-01-05",
                "evento": "C",
                "quantidade": 1,
                "preco": 10,
            },
        ).status_code == 201

    resultado = cliente.get("/api/operacoes", params={"classe": "FII", "limite": 1, "deslocamento": 1}).json()
    assert resultado["total"] == 2
    assert len(resultado["itens"]) == 1
    assert resultado["itens"][0]["ticker"] == "HGLG11"


def test_proventos_filtrados_por_classe(cliente, ids):
    fii = cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"]
    for ativo_id in (ids["ativo_id"], fii):
        assert cliente.post(
            "/api/proventos",
            json={
                "investidor_id": ids["investidor_id"],
                "ativo_id": ativo_id,
                "data_pagamento": "2026-02-10",
                "evento": "DIVIDENDO",
                "valor": 10,
            },
        ).status_code == 201

    resultado = cliente.get("/api/proventos", params={"classe": "FII"}).json()
    assert resultado["total"] == 1
    assert resultado["itens"][0]["ticker"] == "HGLG11"


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


def test_carga_historica_dispara_em_sequencia(cliente, monkeypatch):
    from app.services import jobs

    chamadas = []
    monkeypatch.setattr(jobs, "_executar_agendado", chamadas.append)
    falso_threading = type("FalsoThreading", (), {
        "Thread": staticmethod(lambda target, **_: type("T", (), {"start": staticmethod(target)})()),
    })
    monkeypatch.setattr(jobs, "threading", falso_threading)
    assert cliente.post("/api/atualizacoes/carga-historica").status_code == 202
    assert chamadas == ["cotahist_historico", "historico_complementar"]

    monkeypatch.setattr(jobs.TAREFAS["cotahist_historico"], "em_execucao", True)
    assert cliente.post("/api/atualizacoes/carga-historica").status_code == 409
