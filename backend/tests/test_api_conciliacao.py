import pytest


@pytest.fixture
def ids(cliente):
    investidor = cliente.post("/api/investidores", json={"nome": "Conta teste"}).json()["id"]
    ativo = cliente.post("/api/ativos", json={"ticker": "ATIVO3"}).json()["id"]
    corretora = cliente.post("/api/corretoras", json={"nome": "Corretora teste"}).json()["id"]
    return {"investidor_id": investidor, "ativo_id": ativo, "corretora_id": corretora}


def test_conciliar_posicao_usa_saldo_historico_e_explica_diferencas(cliente, ids):
    cliente.post(
        "/api/operacoes",
        json={
            **ids,
            "data": "2026-01-05",
            "evento": "C",
            "quantidade": 10,
            "preco": 20,
            "taxas": 2,
        },
    )
    cliente.post(
        "/api/operacoes",
        json={
            **ids,
            "data": "2026-02-05",
            "evento": "V",
            "quantidade": -2,
            "preco": 25,
        },
    )

    resposta = cliente.post(
        "/api/conciliacao/posicao",
        json={
            "investidor_id": ids["investidor_id"],
            "ativo_id": ids["ativo_id"],
            "data_referencia": "2026-02-28",
            "quantidade_informada": 9,
            "custo_informado": 180,
        },
    )

    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["quantidade_calculada"] == 8
    assert dados["custo_calculado"] == pytest.approx(161.6)
    assert dados["preco_medio_calculado"] == pytest.approx(20.2)
    assert dados["preco_medio_informado"] == 20
    assert dados["diferenca_quantidade"] == -1
    assert dados["diferenca_custo"] == pytest.approx(-18.4)
    assert dados["diferenca_preco_medio"] == pytest.approx(0.2)
    assert [op["evento"] for op in dados["operacoes"]] == ["V", "C"]


def test_conciliar_posicao_respeita_data_referencia(cliente, ids):
    cliente.post(
        "/api/operacoes",
        json={**ids, "data": "2026-01-05", "evento": "C", "quantidade": 10, "preco": 20},
    )
    cliente.post(
        "/api/operacoes",
        json={**ids, "data": "2026-02-05", "evento": "V", "quantidade": -2, "preco": 25},
    )

    resposta = cliente.post(
        "/api/conciliacao/posicao",
        json={
            "investidor_id": ids["investidor_id"],
            "ativo_id": ids["ativo_id"],
            "data_referencia": "2026-01-31",
            "quantidade_informada": 10,
            "custo_informado": 200,
        },
    )

    assert resposta.status_code == 200, resposta.text
    dados = resposta.json()
    assert dados["quantidade_calculada"] == 10
    assert dados["custo_calculado"] == 200
    assert dados["operacoes_total"] == 1
