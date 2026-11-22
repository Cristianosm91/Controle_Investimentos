from datetime import date, timedelta

import pytest


@pytest.fixture
def carteira_multimercado(cliente):
    investidor = cliente.post("/api/investidores", json={"nome": "Investidora filtros"}).json()["id"]
    hoje = date.today()
    inicio = hoje - timedelta(days=40)
    cadastros = [
        {
            "ticker": "PETR4",
            "classe": "AÇÃO",
            "mercado": "BVMF",
            "moeda": "USD",
        },
        {
            "ticker": "AAPL",
            "classe": "AÇÃO",
            "mercado": "NASDAQ",
            "moeda": "BRL",
        },
        {
            "ticker": "BTC",
            "nome": "Bitcoin",
            "classe": "CRIPTO",
            "mercado": None,
            "moeda": "EUR",
            "coingecko_id": "bitcoin",
        },
    ]
    ativos = {}
    for cadastro in cadastros:
        ativo_id = cliente.post("/api/ativos", json=cadastro).json()["id"]
        ativos[cadastro["ticker"]] = ativo_id
        moeda = cadastro["moeda"]
        cliente.post(
            "/api/operacoes",
            json={
                "investidor_id": investidor,
                "ativo_id": ativo_id,
                "data": inicio.isoformat(),
                "evento": "C",
                "quantidade": 2,
                "preco": 100,
                "moeda": moeda,
                "cambio": 1 if moeda == "BRL" else 1.1,
            },
        )
        cliente.post(
            "/api/proventos",
            json={
                "investidor_id": investidor,
                "ativo_id": ativo_id,
                "data_pagamento": (hoje - timedelta(days=5)).isoformat(),
                "evento": "DIVIDENDO",
                "valor": 10,
                "moeda": moeda,
                "cambio": 1 if moeda == "BRL" else 1.1,
            },
        )

    return {"investidor": investidor, "ativos": ativos}


@pytest.mark.parametrize(
    ("mercados", "esperados"),
    [
        ("BRASIL", {"PETR4"}),
        ("EUA", {"AAPL"}),
        ("CRIPTO", {"BTC"}),
        ("BRASIL,EUA", {"PETR4", "AAPL"}),
        ("BRASIL,CRIPTO", {"PETR4", "BTC"}),
        ("EUA,CRIPTO", {"AAPL", "BTC"}),
        ("BRASIL,EUA,CRIPTO", {"PETR4", "AAPL", "BTC"}),
    ],
)
def test_filtro_de_mercado_usa_classificacao_do_ativo(cliente, carteira_multimercado, mercados, esperados):
    params = {"investidores": carteira_multimercado["investidor"], "mercados": mercados}
    operacoes = cliente.get("/api/operacoes", params=params).json()["itens"]
    assert {op["ticker"] for op in operacoes} == esperados


def test_filtros_combinam_mercado_classe_e_multiplos_ativos(cliente, carteira_multimercado):
    ativos = carteira_multimercado["ativos"]
    base = {"investidores": carteira_multimercado["investidor"]}

    for tickers in (["PETR4"], ["PETR4", "AAPL"], ["PETR4", "AAPL", "BTC"]):
        resultado = cliente.get(
            "/api/operacoes",
            params={**base, "ativo_ids": ",".join(str(ativos[t]) for t in tickers)},
        ).json()
        assert {op["ticker"] for op in resultado["itens"]} == set(tickers)

    resultado = cliente.get(
        "/api/operacoes",
        params={
            **base,
            "mercados": "BRASIL,EUA",
            "classes": "AÇÃO",
            "ativo_ids": f"{ativos['PETR4']},{ativos['AAPL']},{ativos['BTC']}",
        },
    ).json()
    assert {op["ticker"] for op in resultado["itens"]} == {"PETR4", "AAPL"}

    sem_resultados = cliente.get(
        "/api/operacoes",
        params={**base, "mercados": "BRASIL", "ativo_ids": str(ativos["BTC"])},
    ).json()
    assert sem_resultados["total"] == 0


def test_classificacao_nao_depende_da_moeda_e_opcoes_respeitam_investidor(cliente, carteira_multimercado):
    parametros = {"investidores": carteira_multimercado["investidor"]}
    opcoes = cliente.get("/api/ativos/disponiveis", params=parametros).json()
    tipos = {ativo["ticker"]: ativo["mercado_tipo"] for ativo in opcoes}
    assert tipos == {"AAPL": "EUA", "BTC": "CRIPTO", "PETR4": "BRASIL"}

    outro = cliente.post("/api/investidores", json={"nome": "Outro investidor"}).json()["id"]
    ativos_outro = cliente.get("/api/ativos/disponiveis", params={"investidores": outro}).json()
    assert ativos_outro == []


def test_proventos_matriz_agenda_e_rentabilidade_respeitam_filtros(cliente, carteira_multimercado):
    ativos = carteira_multimercado["ativos"]
    investidor = carteira_multimercado["investidor"]
    hoje = date.today()
    params = {
        "investidores": investidor,
        "mercados": "BRASIL,CRIPTO",
        "classes": "AÇÃO,CRIPTO",
        "ativo_ids": f"{ativos['PETR4']},{ativos['AAPL']},{ativos['BTC']}",
    }

    proventos = cliente.get("/api/proventos", params=params).json()
    assert {item["ticker"] for item in proventos["itens"]} == {"PETR4", "BTC"}

    matriz = cliente.get(
        "/api/proventos/matriz",
        params={**params, "ano": hoje.year},
    ).json()
    assert set(matriz["linhas"]) == {"PETR4", "BTC"}
    assert matriz["total"] == pytest.approx(22)

    agenda = cliente.get("/api/proventos/agenda", params=params).json()
    assert agenda["total_recebido_12m"] == pytest.approx(22)
    assert {item["ticker"] for item in agenda["por_ativo"]} == {"PETR4", "BTC"}

    mensal = cliente.get("/api/rentabilidade/mensal", params=params).json()
    assert mensal
    assert mensal[-1]["investido"] == pytest.approx(440)

    resumo = cliente.get("/api/rentabilidade/resumo", params=params).json()
    assert resumo["investido"] == pytest.approx(440)
    assert resumo["proventos_total"] == pytest.approx(22)


@pytest.mark.parametrize(
    ("classes", "investido", "proventos"),
    [(None, 690, 33), ("AÇÃO", 420, 21), ("AÇÃO,CRIPTO", 640, 32), ("__NENHUM__", 0, 0)],
)
def test_filtro_de_classes_no_resumo_e_na_serie(cliente, carteira_multimercado, classes, investido, proventos):
    ativo = cliente.post("/api/ativos", json={"ticker": "TEST11", "classe": "FII"}).json()["id"]
    investidor = carteira_multimercado["investidor"]
    operacao = cliente.post("/api/operacoes", json={
        "investidor_id": investidor,
        "ativo_id": ativo,
        "data": (date.today() - timedelta(days=40)).isoformat(),
        "evento": "C",
        "quantidade": 1,
        "preco": 50,
    })
    provento = cliente.post("/api/proventos", json={
        "investidor_id": investidor,
        "ativo_id": ativo,
        "data_pagamento": (date.today() - timedelta(days=5)).isoformat(),
        "evento": "DIVIDENDO",
        "valor": 1,
    })
    assert operacao.status_code == provento.status_code == 201
    params = {"investidores": carteira_multimercado["investidor"]}
    if classes is not None:
        params["classes"] = classes

    resumo = cliente.get("/api/rentabilidade/resumo", params=params)
    mensal = cliente.get("/api/rentabilidade/mensal", params=params)
    assert resumo.status_code == mensal.status_code == 200
    assert resumo.json()["investido"] == pytest.approx(investido)
    assert resumo.json()["proventos_total"] == pytest.approx(proventos)
    meses = mensal.json()
    if classes == "__NENHUM__":
        assert meses == []
    else:
        assert meses[-1]["investido"] == pytest.approx(investido)


def test_filtro_vazio_e_mercado_invalido(cliente, carteira_multimercado):
    base = {"investidores": carteira_multimercado["investidor"]}
    vazio = cliente.get("/api/operacoes", params={**base, "mercados": "__NENHUM__"}).json()
    assert vazio["total"] == 0

    resposta = cliente.get("/api/operacoes", params={**base, "mercados": "LUA"})
    assert resposta.status_code == 422


def test_posicao_disponibiliza_setor_real_independente_do_subsetor(cliente):
    investidor = cliente.post("/api/investidores", json={"nome": "Investidora setor"}).json()["id"]
    ativo = cliente.post(
        "/api/ativos",
        json={"ticker": "SETR3", "setor": "Energia", "subsetor": "Petróleo"},
    ).json()["id"]
    cliente.post(
        "/api/operacoes",
        json={
            "investidor_id": investidor,
            "ativo_id": ativo,
            "data": date.today().isoformat(),
            "evento": "C",
            "quantidade": 1,
            "preco": 10,
        },
    )

    (posicao,) = cliente.get("/api/posicoes").json()
    assert posicao["setor"] == "Energia"
    assert posicao["subsetor"] == "Petróleo"
