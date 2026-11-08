import pytest


@pytest.fixture
def base(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    corretora = cliente.post("/api/corretoras", json={"nome": "XP"}).json()["id"]
    petr = cliente.post("/api/ativos", json={"ticker": "PETR4", "classe": "AÇÃO"}).json()["id"]
    hglg = cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"]
    rv = cliente.post("/api/estrategias", json={"nome": "Renda Variável", "peso": 1}).json()["id"]
    acoes = cliente.post("/api/books", json={"estrategia_id": rv, "nome": "Ações", "peso": 0.6, "classes": ["ação"]}).json()
    fii = cliente.post("/api/books", json={"estrategia_id": rv, "nome": "FII", "peso": 0.4, "classes": ["FII"]}).json()
    return {"inv": inv, "corretora": corretora, "petr": petr, "hglg": hglg, "rv": rv, "acoes": acoes, "fii": fii}


def _compra(cliente, b, ativo, data="2026-01-05", qtd=100, preco=30, taxas=1):
    r = cliente.post("/api/operacoes", json={"investidor_id": b["inv"], "ativo_id": ativo, "corretora_id": b["corretora"],
                                             "data": data, "evento": "C", "quantidade": qtd, "preco": preco, "taxas": taxas})
    assert r.status_code == 201, r.text


def test_books_e_classes(cliente, base):
    assert base["acoes"]["classes"] == ["AÇÃO"]
    # Mover a classe para outro book retira do anterior.
    r = cliente.put(f"/api/books/{base['fii']['id']}", json={"estrategia_id": base["rv"], "nome": "FII", "peso": 0.4,
                                                              "classes": ["FII", "AÇÃO"]})
    assert r.json()["classes"] == ["AÇÃO", "FII"]
    livros = {b["nome"]: b["classes"] for b in cliente.get("/api/books").json()}
    assert livros["Ações"] == []
    assert cliente.post("/api/books", json={"estrategia_id": base["rv"], "nome": "FII", "peso": 0}).status_code == 409
    assert cliente.delete(f"/api/estrategias/{base['rv']}").status_code == 409
    assert {"AÇÃO", "FII"} <= set(cliente.get("/api/classes").json())


def test_excecao_de_book(cliente, base):
    url = f"/api/ativos/{base['petr']}/books"
    meio = [{"book_id": base["acoes"]["id"], "percentual": 0.5}, {"book_id": base["fii"]["id"], "percentual": 0.4}]
    assert cliente.put(url, json=meio).status_code == 422
    meio[1]["percentual"] = 0.5
    assert cliente.put(url, json=meio).status_code == 204
    assert cliente.get("/api/books/excecoes").json()[0]["ticker"] == "PETR4"
    assert cliente.put(url, json=[]).status_code == 204
    assert cliente.get("/api/books/excecoes").json() == []


def test_excluir_book_desfaz_excecao_incompleta(cliente, base):
    _compra(cliente, base, base["petr"])
    meio = [{"book_id": base["acoes"]["id"], "percentual": 0.5}, {"book_id": base["fii"]["id"], "percentual": 0.5}]
    cliente.put(f"/api/ativos/{base['petr']}/books", json=meio)
    outro = cliente.post("/api/books", json={"estrategia_id": base["rv"], "nome": "Novo", "peso": 0, "classes": ["AÇÃO"]}).json()
    assert cliente.delete(f"/api/books/{base['fii']['id']}").status_code == 204
    assert cliente.get("/api/books/excecoes").json() == []
    # Sem a exceção, o ativo volta ao book da classe com 100% do valor.
    assert cliente.get("/api/posicoes").json()[0]["book"] == outro["nome"]


def test_preco_teto_so_vale_quando_marcado(cliente, base):
    # Ativo de saldo manual: a cota (R$ 20) faz o papel da cotação acima do teto (R$ 15).
    ativo = cliente.post("/api/ativos", json={"ticker": "MANUAL3", "classe": "AÇÃO", "cotacao_automatica": False}).json()["id"]
    _compra(cliente, base, ativo, qtd=100, preco=10, taxas=0)
    cliente.post(f"/api/ativos/{ativo}/saldo", json={"data": "2026-01-10", "saldo": 2000})
    vinculo = {"ativo_id": ativo, "preco_teto": 15, "entra_preco_teto": True}
    cid = cliente.post("/api/carteiras", json={"nome": "C", "ativos": [vinculo]}).json()["id"]
    item = lambda: next(i for i in cliente.get("/api/alocacao").json()["ativos"] if i["ticker"] == "MANUAL3")  # noqa: E731
    assert item()["acima_teto"] is True
    cliente.put(f"/api/carteiras/{cid}", json={"nome": "C", "ativos": [{**vinculo, "entra_preco_teto": False}]})
    assert item()["acima_teto"] is False and item()["preco_teto"] is None


def test_carteiras_e_posicoes(cliente, base):
    _compra(cliente, base, base["petr"])
    c1 = cliente.post("/api/carteiras", json={"nome": "Dividendos", "categoria": "Renda Passiva",
                                              "ativos": [{"ativo_id": base["petr"], "peso": 0.5, "preco_teto": 35}]})
    assert c1.status_code == 201 and c1.json()["ativos"][0]["ticker"] == "PETR4"
    conflito = cliente.post("/api/carteiras", json={"nome": "Outra", "ativos": [{"ativo_id": base["petr"]}]})
    assert conflito.status_code == 409 and "Dividendos" in conflito.json()["detail"]
    assert cliente.post("/api/carteiras", json={"nome": "Outra"}).status_code == 201  # nada gravado no conflito

    pos = cliente.get("/api/posicoes").json()[0]
    assert (pos["book"], pos["estrategia"], pos["carteira"]) == ("Ações", "Renda Variável", "Dividendos")

    # Carteira inativa não classifica.
    cid = c1.json()["id"]
    cliente.put(f"/api/carteiras/{cid}", json={"nome": "Dividendos", "ativa": False, "ativos": [{"ativo_id": base["petr"]}]})
    assert cliente.get("/api/posicoes").json()[0]["carteira"] is None
    assert cliente.delete(f"/api/carteiras/{cid}").status_code == 204


def test_alocacao_inclui_ativo_de_carteira_sem_posicao(cliente, base):
    _compra(cliente, base, base["petr"], qtd=100, preco=10, taxas=0)  # R$ 1.000 sem cotação → usa o custo
    cliente.post("/api/carteiras", json={"nome": "FIIs", "ativos": [{"ativo_id": base["hglg"], "peso": 1}]})
    r = cliente.get("/api/alocacao", params={"aporte": 500})
    assert r.status_code == 200
    j = r.json()
    assert j["total_atual"] == 1000
    itens = {i["ticker"]: i for i in j["ativos"]}
    assert itens["HGLG11"]["peso_alvo"] == pytest.approx(0.4) and itens["HGLG11"]["valor_atual"] == 0
    # Sem cotação não há preço para comprar: o aporte sobra.
    assert itens["HGLG11"]["ajuste"] == 0 and j["sobra"] == 500
    assert cliente.get("/api/alocacao", params={"modo": "vender"}).status_code == 422


def test_parametros_e_saldo_de_caixa(cliente, base):
    assert cliente.get("/api/parametros").json() == {
        "caixa_data_inicio": None, "caixa_no_portfolio": False,
        "ir_ano_inicio": None, "ir_bdr_como_acao": False, "ir_daytrade_no_limite": False,
        "ir_opcoes_no_limite": False, "ir_outras_classes_no_limite": False, "ir_subscricao_fii_isenta": False,
        "alerta_desvio_pp": 5, "alerta_vencimento_dias": 30, "alerta_cotacao_dias": 5,
    }
    cliente.post("/api/caixa", json={"investidor_id": base["inv"], "corretora_id": base["corretora"], "data": "2026-01-02",
                                     "evento": "APORTE", "valor": 10000})
    _compra(cliente, base, base["petr"], data="2025-12-01")  # antes do início: ignorada
    _compra(cliente, base, base["petr"], data="2026-01-05")
    ref = {"investidor_id": base["inv"], "ativo_id": base["petr"], "corretora_id": base["corretora"]}
    cliente.post("/api/operacoes", json={**ref, "data": "2026-02-05", "evento": "V", "quantidade": -50, "preco": 40, "taxas": 1,
                                         "irrf": 0.1})
    cliente.post("/api/proventos", json={**ref, "data_pagamento": "2026-03-01", "evento": "JSCP", "valor": 100, "irrf": 15})

    so_mov = cliente.get("/api/caixa/saldos").json()
    assert so_mov["integrado_desde"] is None and so_mov["total_brl"] == 10000

    r = cliente.put("/api/parametros", json={"caixa_data_inicio": "2026-01-01", "caixa_no_portfolio": True})
    assert r.json()["caixa_no_portfolio"] is True
    saldo = cliente.get("/api/caixa/saldos").json()
    linha = saldo["saldos"][0]
    assert linha["corretora"] == "XP"
    assert linha["operacoes"] == pytest.approx(-3001 + 1998.9)
    assert linha["proventos"] == 85
    assert saldo["total_brl"] == pytest.approx(10000 - 3001 + 1998.9 + 85)


def test_valor_investido_liquido_separa_custo_das_posicoes(cliente, base):
    def operar(data, evento, quantidade, preco, taxas=0, irrf=0, daytrade=False):
        resposta = cliente.post("/api/operacoes", json={
            "investidor_id": base["inv"], "ativo_id": base["petr"], "data": data, "evento": evento,
            "quantidade": quantidade, "preco": preco, "taxas": taxas, "irrf": irrf, "daytrade": daytrade,
        })
        assert resposta.status_code == 201, resposta.text

    operar("2026-01-05", "C", 10, 10, taxas=0.2)
    operar("2026-02-05", "V", -4, 15, taxas=0.2, irrf=0.1)
    operar("2026-02-10", "BONIFICACAO", 2, 5)
    operar("2026-03-05", "CISAO", 8, -1)
    operar("2026-04-05", "AMORTIZACAO", 8, -0.5, taxas=0.1, irrf=0.05)
    operar("2026-05-05", "C", 1, 20, taxas=0.2, daytrade=True)
    operar("2026-05-05", "V", -1, 21, taxas=0.2, irrf=0.1, daytrade=True)
    cliente.post("/api/proventos", json={
        "investidor_id": base["inv"], "ativo_id": base["petr"], "data_pagamento": "2026-04-10",
        "evento": "JSCP", "valor": 10, "irrf": 1, "taxas": 0.2,
    })

    resposta = cliente.get("/api/carteira/valor-investido")
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["valor_investido"] == pytest.approx(52.12)
    assert resposta.json()["valor_investido_posicoes_abertas"] == pytest.approx(52.12)

    (posicao,) = cliente.get("/api/posicoes", params={"somente_abertas": False}).json()
    assert posicao["custo"] == pytest.approx(58.12)
    assert posicao["valor_investido"] == pytest.approx(52.12)
    assert posicao["lucro_realizado"] == pytest.approx(19.62)
    assert posicao["lucro_daytrade"] == pytest.approx(0.5)


def test_valor_investido_inclui_operacoes_encerradas(cliente, base):
    _compra(cliente, base, base["petr"], qtd=10, preco=10, taxas=0.2)
    venda = cliente.post("/api/operacoes", json={
        "investidor_id": base["inv"], "ativo_id": base["petr"], "data": "2026-02-05", "evento": "V",
        "quantidade": -10, "preco": 8, "taxas": 0.2, "irrf": 0.1,
    })
    assert venda.status_code == 201, venda.text

    resposta = cliente.get("/api/carteira/valor-investido").json()
    assert resposta["valor_investido"] == 0
    assert resposta["valor_investido_posicoes_abertas"] == 0
    (posicao,) = cliente.get("/api/posicoes", params={"somente_abertas": False}).json()
    assert posicao["quantidade"] == 0
    assert posicao["custo"] == 0
    assert posicao["valor_investido"] == 0
    assert posicao["lucro_realizado"] == pytest.approx(-20.5)


def test_valor_investido_portfolio_com_posicoes_abertas_e_encerradas(cliente, base):
    _compra(cliente, base, base["petr"], qtd=10, preco=10, taxas=0.2)
    _compra(cliente, base, base["hglg"], qtd=5, preco=20, taxas=0)
    venda = cliente.post("/api/operacoes", json={
        "investidor_id": base["inv"], "ativo_id": base["hglg"], "data": "2026-02-05", "evento": "V",
        "quantidade": -5, "preco": 20,
    })
    assert venda.status_code == 201, venda.text

    resposta = cliente.get("/api/carteira/valor-investido").json()
    assert resposta["valor_investido"] == pytest.approx(100.2)
    assert resposta["valor_investido_posicoes_abertas"] == pytest.approx(100.2)
    posicoes = cliente.get("/api/posicoes", params={"somente_abertas": False}).json()
    por_ticker = {posicao["ticker"]: posicao for posicao in posicoes}
    assert por_ticker["PETR4"]["custo"] == pytest.approx(100.2)
    assert por_ticker["HGLG11"]["quantidade"] == 0
    assert por_ticker["HGLG11"]["custo"] == 0


def test_valor_investido_portfolio_somente_com_posicoes_abertas(cliente, base):
    _compra(cliente, base, base["petr"], qtd=10, preco=10, taxas=0.2)

    resposta = cliente.get("/api/carteira/valor-investido").json()
    assert resposta["valor_investido"] == pytest.approx(100.2)
    assert resposta["valor_investido_posicoes_abertas"] == pytest.approx(100.2)
    posicoes = cliente.get("/api/posicoes").json()
    assert len(posicoes) == 1 and posicoes[0]["custo"] == pytest.approx(100.2)


def test_valor_investido_ignora_fluxos_com_data_futura(cliente, base):
    operacao = cliente.post("/api/operacoes", json={
        "investidor_id": base["inv"], "ativo_id": base["petr"], "data": "2099-01-01", "evento": "C",
        "quantidade": 1, "preco": 100,
    })
    provento = cliente.post("/api/proventos", json={
        "investidor_id": base["inv"], "ativo_id": base["petr"], "data_pagamento": "2099-01-01",
        "evento": "DIVIDENDO", "valor": 50,
    })
    assert operacao.status_code == provento.status_code == 201

    resposta = cliente.get("/api/carteira/valor-investido").json()
    assert resposta["valor_investido"] == 0
    assert resposta["valor_investido_posicoes_abertas"] == 0


def test_valor_investido_respeita_classes_excluidas_no_portfolio(cliente, base):
    _compra(cliente, base, base["petr"], qtd=10, preco=10, taxas=0.2)
    cripto = cliente.post("/api/ativos", json={"ticker": "BTC", "classe": "CRIPTO"}).json()["id"]
    _compra(cliente, base, cripto, qtd=1, preco=50, taxas=0)

    todos = cliente.get("/api/carteira/valor-investido").json()
    sem_cripto = cliente.get("/api/carteira/valor-investido", params={"classes_excluidas": "CRIPTO"}).json()
    assert todos["valor_investido"] == pytest.approx(150.2)
    assert todos["valor_investido_posicoes_abertas"] == pytest.approx(150.2)
    assert sem_cripto["valor_investido"] == pytest.approx(100.2)
    assert sem_cripto["valor_investido_posicoes_abertas"] == pytest.approx(100.2)
