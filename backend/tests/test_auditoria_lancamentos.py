from decimal import Decimal


def test_historico_registra_criacao_edicao_e_exclusao_com_valores(cliente):
    investidor = cliente.post("/api/investidores", json={"nome": "Teste"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={"ticker": "TEST3"}).json()["id"]
    corpo = {
        "investidor_id": investidor,
        "ativo_id": ativo,
        "data": "2026-01-05",
        "evento": "C",
        "quantidade": 10,
        "preco": 20,
    }

    criada = cliente.post("/api/operacoes", json=corpo)
    assert criada.status_code == 201, criada.text
    id_ = criada.json()["id"]

    alterada = cliente.put(f"/api/operacoes/{id_}", json={**corpo, "quantidade": 5, "preco": 25})
    assert alterada.status_code == 200, alterada.text
    assert cliente.delete(f"/api/operacoes/{id_}").status_code == 204

    resposta = cliente.get("/api/historico-lancamentos", params={"investidores": investidor})
    assert resposta.status_code == 200, resposta.text
    historico = resposta.json()
    assert [item["acao"] for item in historico] == ["excluido", "alterado", "criado"]
    assert all(item["registro_id"] == id_ and item["entidade"] == "operacao" for item in historico)
    assert Decimal(historico[1]["anterior"]["quantidade"]) == 10
    assert Decimal(historico[1]["novo"]["quantidade"]) == 5
    assert Decimal(historico[2]["novo"]["preco"]) == 20
    assert Decimal(historico[0]["anterior"]["preco"]) == 25


def test_historico_registra_importacao_e_desfazer_lote(cliente):
    from test_extrato_b3 import NEGOCIACAO, investidor

    id_investidor = investidor(cliente)
    importada = cliente.post(
        "/api/extratos/b3/importar",
        params={"investidor_id": id_investidor},
        content=NEGOCIACAO,
        headers={"content-type": "application/octet-stream"},
    )
    assert importada.status_code == 200, importada.text
    lote_id = importada.json()["lote_id"]

    criados = cliente.get("/api/historico-lancamentos", params={"investidores": id_investidor}).json()
    assert len(criados) == importada.json()["operacoes"] + importada.json()["proventos"]
    assert all(item["acao"] == "criado" for item in criados)

    desfeito = cliente.post(f"/api/lotes/{lote_id}/desfazer")
    assert desfeito.status_code == 200, desfeito.text
    historico = cliente.get("/api/historico-lancamentos", params={"investidores": id_investidor}).json()
    assert sum(item["acao"] == "excluido" for item in historico) == len(criados)
