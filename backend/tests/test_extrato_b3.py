import io
import json
import re
import zipfile
from datetime import datetime
from decimal import Decimal

from openpyxl import Workbook

CAB_NEGOCIACAO = [
    "Data do Negócio", "Tipo de Movimentação", "Mercado", "Prazo/Vencimento", "Instituição",
    "Código de Negociação", "Quantidade", "Preço", "Valor",
]
CAB_MOVIMENTACAO = [
    "Entrada/Saída", "Data", "Movimentação", "Produto", "Instituição", "Quantidade", "Preço unitário",
    "Valor da Operação",
]
CAB_PLANILHA_OPERACOES = ["ativo", "date", "evento", "qtd", "preco", "taxas", "corretora", "irrf", "moeda"]
XP = "XP INVESTIMENTOS CCTVM S/A"
INTER = "BANCO INTER S.A."


def xlsx(cabecalho, linhas) -> bytes:
    livro = Workbook()
    planilha = livro.active
    planilha.append(cabecalho)
    for linha in linhas:
        planilha.append(linha)
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


def tsv(cabecalho, linhas) -> bytes:
    return ("\n".join(["\t".join(cabecalho), *("\t".join(linha) for linha in linhas)]) + "\n").encode("utf-8")


NEGOCIACAO = xlsx(CAB_NEGOCIACAO, [
    ["02/01/2025", "Compra", "Mercado Fracionário", "-", XP, "PETR4F", 7, 38.5, 269.5],
    ["02/01/2025", "Compra", "Mercado à Vista", "-", XP, "PETR4", 100, "38,40", "3.840,00"],
    ["03/01/2025", "Compra", "Mercado à Vista", "-", INTER, "HGLG11", 10, 160, 1600],
    ["06/01/2025", "Compra", "Mercado à Vista", "-", XP, "VALE3", 100, 60, 6000],
    ["06/01/2025", "Venda", "Mercado à Vista", "-", XP, "VALE3", 100, 61, 6100],
    ["07/01/2025", "Compra", "Mercado à Vista", "-", XP, "ITUB4", 200, 30, 6000],
    ["07/01/2025", "Venda", "Mercado à Vista", "-", XP, "ITUB4", 100, 31, 3100],
    ["08/01/2025", "Compra", "Opção de Compra", "17/01/2025", XP, "PETRA400", 1000, 0.5, 500],
    ["09/01/2025", "Compra", "Mercado a Termo", "-", XP, "BBAS3", 10, 25, 250],
])

MOVIMENTACAO = xlsx(CAB_MOVIMENTACAO, [
    ["Credito", "15/01/2025", "Dividendo", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", XP, 107, 1.2, 128.4],
    ["Credito", "15/01/2025", "Juros Sobre Capital Próprio", "ITUB4 - ITAU UNIBANCO HOLDING S.A.", XP, 100, 0.1, 10],
    ["Credito", "14/01/2025", "Rendimento", "HGLG11 - CSHG LOGISTICA FUNDO DE INVESTIMENTO IMOBILIARIO", INTER, 10, 1.1, 11],
    ["Credito", "20/01/2025", "Amortização", "HGLG11 - CSHG LOGISTICA FUNDO DE INVESTIMENTO IMOBILIARIO", INTER, 10, 0.5, 5],
    [
        "Credito", "20/01/2025", "Restituição de Capital",
        "HGLG11 - CSHG LOGISTICA FUNDO DE INVESTIMENTO IMOBILIARIO", INTER, 0, "-", 12.69,
    ],
    ["Credito", "21/01/2025", "Desdobro", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", XP, 107, "-", "-"],
    ["Credito", "04/01/2025", "Transferência - Liquidação", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", XP, 100, 38.4, 3840],
    ["Credito", "22/01/2025", "Rendimento", "Tesouro Selic 2029", XP, 1, 10, 10],
    ["Debito", "23/01/2025", "Dividendo", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", XP, 1, 1, 1],
    ["Credito", "24/01/2025", "Empréstimo", "PETR4 - PETROLEO BRASILEIRO S.A. PETROBRAS", XP, 100, "-", "-"],
    [None, None, None, None, None, None, None, None],
])

PLANILHA_OPERACOES = xlsx(CAB_PLANILHA_OPERACOES, [
    ["PETR4", datetime(2025, 2, 3), "C", 100, 38.5, 12.34, "XP", 0, "BRL"],
    ["PETR4", datetime(2025, 2, 4), "V", 10, 40, 2.5, "XP", 0.01, "BRL"],
    ["AAPL", datetime(2025, 2, 5), "C", 1, 200, 0, "XP", 0, "USD"],
])


def investidor(cliente, nome="Ana") -> int:
    return cliente.post("/api/investidores", json={"nome": nome, "cor": "#000000", "ativo": True}).json()["id"]


def enviar(cliente, rota, conteudo, **params):
    return cliente.post(
        f"/api/extratos/b3/{rota}", params=params, content=conteudo,
        headers={"content-type": "application/octet-stream"},
    )


def por_numero(previa):
    return {linha["numero"]: linha for linha in previa["linhas"]}


def test_previa_negociacao(cliente):
    inv = investidor(cliente)
    r = enviar(cliente, "previa", NEGOCIACAO, investidor_id=inv)
    assert r.status_code == 200, r.text
    previa = r.json()
    assert previa["relatorio"] == "NEGOCIACAO"
    linhas = por_numero(previa)
    assert linhas[2]["ticker"] == "PETR4" and linhas[2]["quantidade"] == 7 and linhas[2]["status"] == "novo"
    assert linhas[3]["preco"] == 38.4 and linhas[3]["valor"] == 3840
    assert linhas[5]["daytrade"] and linhas[6]["daytrade"] and linhas[6]["quantidade"] == -100
    assert linhas[7]["status"] == linhas[8]["status"] == "verificar"
    assert linhas[9]["status"] == "novo"
    assert linhas[10]["status"] == "ignorado" and "Termo" in linhas[10]["motivo"]
    assert previa["ativos_novos"] == {"PETR4": "AÇÃO", "HGLG11": "FII", "VALE3": "AÇÃO", "ITUB4": "AÇÃO", "PETRA400": "OPÇÃO"}
    assert sorted(previa["corretoras_novas"]) == ["INTER", "XP"]


def test_previa_mostra_comparacao_de_quantidade_e_valor_sem_alterar_registros(cliente):
    inv = investidor(cliente)
    ativo = cliente.post("/api/ativos", json={"ticker": "PETR4"}).json()["id"]
    existente = cliente.post(
        "/api/operacoes",
        json={
            "investidor_id": inv,
            "ativo_id": ativo,
            "data": "2025-01-02",
            "evento": "C",
            "quantidade": 50,
            "preco": 38.4,
        },
    )
    assert existente.status_code == 201

    resposta = enviar(cliente, "previa", NEGOCIACAO, investidor_id=inv)
    assert resposta.status_code == 200, resposta.text
    previa = resposta.json()
    comparacao = next(item for item in previa["comparacoes"] if item["ticker"] == "PETR4")

    assert comparacao["status"] == "verificar"
    assert comparacao["quantidade_extrato"] == 107
    assert comparacao["quantidade_existente"] == 50
    assert comparacao["diferenca_quantidade"] == 57
    assert comparacao["valor_extrato"] == 4109.5
    assert comparacao["valor_existente"] == 1920
    assert cliente.get("/api/operacoes", params={"investidores": inv}).json()["total"] == 1


def test_planilha_operacoes_importa_taxas_e_irrf(cliente):
    inv = investidor(cliente)
    previa = enviar(cliente, "previa", PLANILHA_OPERACOES, investidor_id=inv).json()
    assert previa["relatorio"] == "PLANILHA_OPERACOES"
    linhas = por_numero(previa)
    assert (linhas[2]["evento"], linhas[2]["quantidade"], linhas[2]["valor"]) == ("C", 100, 3850)
    assert (linhas[3]["evento"], linhas[3]["quantidade"]) == ("V", -10)
    assert (linhas[4]["status"], linhas[4]["evento"], linhas[4]["moeda"]) == ("novo", "C", "USD")

    resultado = enviar(cliente, "importar", PLANILHA_OPERACOES, investidor_id=inv).json()
    assert resultado["operacoes"] == 3
    operacoes = cliente.get("/api/operacoes", params={"investidores": inv}).json()["itens"]
    assert {(op["evento"], op["taxas"], op["irrf"], op["moeda"]) for op in operacoes} == {
        ("C", 12.34, 0, "BRL"), ("V", 2.5, 0.01, "BRL"), ("C", 0, 0, "USD"),
    }
    assert enviar(cliente, "importar", PLANILHA_OPERACOES, investidor_id=inv).json()["operacoes"] == 0


def test_importa_operacoes_coladas_da_planilha_personalizada(cliente):
    inv = investidor(cliente)
    conteudo = tsv(
        CAB_PLANILHA_OPERACOES + ["observacao"],
        [["ABCP11", "03/02/2025", "C", "25", "13,20", "22,55", "XP", "0,00", "BRL", ""]]
    )

    previa = enviar(cliente, "previa", conteudo, investidor_id=inv)
    assert previa.status_code == 200, previa.text
    linha = previa.json()["linhas"][0]
    assert (previa.json()["relatorio"], linha["ticker"], linha["evento"], linha["quantidade"]) == (
        "PLANILHA_OPERACOES", "ABCP11", "C", 25,
    )

    resultado = enviar(cliente, "importar", conteudo, investidor_id=inv)
    assert resultado.status_code == 200, resultado.text
    assert resultado.json()["operacoes"] == 1
    operacao = cliente.get("/api/operacoes", params={"investidores": inv}).json()["itens"][0]
    assert (operacao["ticker"], operacao["preco"], operacao["taxas"], operacao["moeda"]) == (
        "ABCP11", 13.2, 22.55, "BRL",
    )


def test_importa_proventos_colados_da_planilha_personalizada(cliente):
    inv = investidor(cliente)
    conteudo = tsv(
        ["ativo", "date", "evento", "valor", "irrf", "taxas", "moeda", "corretora", "date_com", "observacao"],
        [["PETR4", "03/03/2025", "JSCP", "2,00", "0,30", "0,10", "BRL", "XP", "01/03/2025", "Colado"]],
    )

    previa = enviar(cliente, "previa", conteudo, investidor_id=inv)
    assert previa.status_code == 200, previa.text
    linha = previa.json()["linhas"][0]
    assert (previa.json()["relatorio"], linha["ticker"], linha["evento"], linha["valor"]) == (
        "PLANILHA_PROVENTOS", "PETR4", "JSCP", 2,
    )

    resultado = enviar(cliente, "importar", conteudo, investidor_id=inv)
    assert resultado.status_code == 200, resultado.text
    assert resultado.json()["proventos"] == 1
    provento = cliente.get("/api/proventos", params={"investidores": inv}).json()["itens"][0]
    assert (provento["evento"], provento["valor"], provento["irrf"], provento["taxas"], provento["data_com"]) == (
        "JSCP", 2, 0.3, 0.1, "2025-03-01",
    )


def test_planilha_personalizada_importa_classe_informada_e_aceita_layout_antigo(cliente):
    inv = investidor(cliente)
    cabecalho = CAB_PLANILHA_OPERACOES + ["classe"]
    planilha = xlsx(cabecalho, [
        ["O", datetime(2025, 2, 5), "C", 1, 200, 0, "XP", 0, "USD", "STOCK"],
        ["VNQ", datetime(2025, 2, 6), "C", 1, 80, 0, "XP", 0, "USD", "REIT"],
        ["SPY", datetime(2025, 2, 7), "C", 1, 500, 0, "XP", 0, "USD", "ETF_US"],
    ])
    previa = enviar(cliente, "previa", planilha, investidor_id=inv)
    assert previa.status_code == 200, previa.text
    assert previa.json()["ativos_novos"] == {"O": "STOCK", "VNQ": "REIT", "SPY": "ETF_US"}

    resultado = enviar(cliente, "importar", planilha, investidor_id=inv)
    assert resultado.status_code == 200, resultado.text
    ativos = {ativo["ticker"]: ativo["classe"] for ativo in cliente.get("/api/ativos").json()}
    assert {ticker: ativos[ticker] for ticker in ("O", "VNQ", "SPY")} == {
        "O": "STOCK", "VNQ": "REIT", "SPY": "ETF_US",
    }

    antiga = xlsx(CAB_PLANILHA_OPERACOES, [
        ["MSFT", datetime(2025, 2, 8), "C", 1, 200, 0, "XP", 0, "USD"],
    ])
    previa_antiga = enviar(cliente, "previa", antiga, investidor_id=inv)
    assert previa_antiga.status_code == 200, previa_antiga.text
    assert previa_antiga.json()["ativos_novos"]["MSFT"] == "AÇÃO"


def test_planilha_corrige_multiplas_linhas_na_previa_e_importa_sem_editar_arquivo(cliente):
    inv = investidor(cliente)
    planilha = xlsx(CAB_PLANILHA_OPERACOES, [
        ["PETR4", datetime(2025, 2, 5), "XX", "inválido", 200, 0, "XP", 0, "USD"],
        ["?", datetime(2025, 2, 6), "C", 1, 200, 0, "XP", 0, "EUR"],
    ])
    previa = enviar(cliente, "previa", planilha, investidor_id=inv).json()
    linha = previa["linhas"][0]
    assert linha["status"] == "ignorado"
    assert "qtd" in linha["motivo"]
    assert linha["campos"]["evento"] == "XX"
    assert previa["linhas"][1]["status"] == "ignorado"

    correcoes = {
        "2": {"ticker": "O", "evento": "C", "quantidade": "1"},
        "3": {"ticker": "A"},
    }
    parametros = {"investidor_id": inv, "correcoes": json.dumps(correcoes)}
    revalidada = enviar(cliente, "previa", planilha, **parametros).json()["linhas"]
    assert [(item["ticker"], item["status"], item["evento"]) for item in revalidada] == [
        ("O", "novo", "C"), ("A", "novo", "C"),
    ]

    resultado = enviar(cliente, "importar", planilha, **parametros).json()
    assert resultado["operacoes"] == 2
    operacoes = cliente.get("/api/operacoes", params={"investidores": inv}).json()["itens"]
    assert {(op["ticker"], op["moeda"], op["quantidade"]) for op in operacoes} == {
        ("O", "USD", 1), ("A", "EUR", 1),
    }


def test_s_i_importa_split_e_inplit_pelo_sinal_da_quantidade(cliente):
    inv = investidor(cliente)
    planilha = xlsx(CAB_PLANILHA_OPERACOES, [
        ["PETR4", datetime(2025, 2, 5), "S/I", 100, 0, 0, "XP", 0, "BRL"],
        ["PETR4", datetime(2025, 2, 6), "S/I", -100, 0, 0, "XP", 0, "BRL"],
    ])
    previa = enviar(cliente, "previa", planilha, investidor_id=inv).json()
    assert [(linha["evento"], linha["quantidade"], linha["status"]) for linha in previa["linhas"]] == [
        ("DESDOBRAMENTO", 100, "novo"), ("DESDOBRAMENTO", -100, "novo"),
    ]
    assert enviar(cliente, "importar", planilha, investidor_id=inv).json()["operacoes"] == 2


def test_importar_negociacao_e_reimportar(cliente):
    inv = investidor(cliente)
    r = enviar(cliente, "importar", NEGOCIACAO, investidor_id=inv, incluir="7")
    assert r.status_code == 200, r.text
    resultado = r.json()
    lote_id = resultado.pop("lote_id")
    assert resultado == {
        "operacoes": 7, "proventos": 0, "ativos_criados": ["PETR4", "HGLG11", "VALE3", "ITUB4", "PETRA400"],
        "corretoras_criadas": ["XP", "INTER"],
    }
    assert lote_id
    ops = cliente.get("/api/operacoes", params={"investidores": inv}).json()
    assert ops["total"] == 7
    vale = [o for o in ops["itens"] if o["ticker"] == "VALE3"]
    assert len(vale) == 2 and all(o["daytrade"] for o in vale)
    assert {o["corretora"] for o in ops["itens"]} == {"XP", "INTER"}

    previa = enviar(cliente, "previa", NEGOCIACAO, investidor_id=inv).json()
    status = {linha["numero"]: linha["status"] for linha in previa["linhas"]}
    assert status[7] == "duplicado" and status[8] == "verificar"
    assert all(s in ("duplicado", "ignorado", "verificar") for s in status.values())
    assert enviar(cliente, "importar", NEGOCIACAO, investidor_id=inv).json()["operacoes"] == 0


def test_movimentacao_proventos_e_eventos(cliente):
    inv = investidor(cliente)
    previa = enviar(cliente, "previa", MOVIMENTACAO, investidor_id=inv).json()
    assert previa["relatorio"] == "MOVIMENTACAO"
    linhas = por_numero(previa)
    assert (linhas[2]["tipo"], linhas[2]["evento"], linhas[2]["valor"]) == ("PROVENTO", "DIVIDENDO", 128.4)
    assert linhas[3]["evento"] == "JSCP" and linhas[4]["evento"] == "RENDIMENTO"
    assert (linhas[5]["evento"], linhas[5]["quantidade"], linhas[5]["preco"]) == ("AMORTIZACAO", 10, -0.5)
    assert (linhas[6]["evento"], linhas[6]["quantidade"], linhas[6]["preco"]) == ("R_CAP", 0, -12.69)
    assert (linhas[7]["evento"], linhas[7]["quantidade"]) == ("DESDOBRAMENTO", 107)
    assert "Negociação" in linhas[8]["motivo"]
    assert linhas[9]["status"] == linhas[10]["status"] == "ignorado"
    assert "Aluguel" in linhas[11]["motivo"]
    assert previa["ativos_novos"]["HGLG11"] == "FII"

    resultado = enviar(cliente, "importar", MOVIMENTACAO, investidor_id=inv).json()
    assert (resultado["operacoes"], resultado["proventos"]) == (3, 3)
    proventos = cliente.get("/api/proventos", params={"investidores": inv}).json()["itens"]
    assert {(p["ticker"], p["evento"], p["valor"], p["irrf"]) for p in proventos} == {
        ("PETR4", "DIVIDENDO", 128.4, 0), ("ITUB4", "JSCP", 10, 0), ("HGLG11", "RENDIMENTO", 11, 0),
    }


def test_compara_com_lancamentos_existentes(cliente):
    inv = investidor(cliente)
    petr = cliente.post("/api/ativos", json={"ticker": "PETR4", "classe": "AÇÃO"}).json()["id"]
    itub = cliente.post("/api/ativos", json={"ticker": "ITUB4", "classe": "AÇÃO"}).json()["id"]
    # Planilha guardou o dividendo em um lançamento e o JCP bruto com IRRF (líquido = valor do extrato).
    for ativo, evento, valor, irrf in ((petr, "DIVIDENDO", 128.40, 0), (itub, "JSCP", 11.76, 1.76)):
        r = cliente.post("/api/proventos", json={
            "investidor_id": inv, "ativo_id": ativo, "data_pagamento": "2025-01-15", "evento": evento,
            "valor": valor, "irrf": irrf,
        })
        assert r.status_code == 201, r.text
    # Compra agrupada em uma única operação (107 = 7 fracionário + 100).
    cliente.post("/api/operacoes", json={
        "investidor_id": inv, "ativo_id": petr, "data": "2025-01-02", "evento": "C", "quantidade": 107, "preco": 38.4,
    })
    cliente.post("/api/operacoes", json={
        "investidor_id": inv, "ativo_id": cliente.post("/api/ativos", json={"ticker": "HGLG11", "classe": "FII"}).json()["id"],
        "data": "2025-01-03", "evento": "C", "quantidade": 5, "preco": 160,
    })

    mov_previa = enviar(cliente, "previa", MOVIMENTACAO, investidor_id=inv).json()
    mov = por_numero(mov_previa)
    assert mov[2]["status"] == mov[3]["status"] == "novo"
    comparacao_jscp = next(item for item in mov_previa["comparacoes"] if item["ticker"] == "ITUB4")
    assert comparacao_jscp["status"] == "duplicado"
    assert comparacao_jscp["valor_extrato"] == comparacao_jscp["valor_existente"] == 10
    assert "líquido" in comparacao_jscp["observacao"]

    neg_previa = enviar(cliente, "previa", NEGOCIACAO, investidor_id=inv).json()
    neg = por_numero(neg_previa)
    assert neg[2]["status"] == neg[3]["status"] == neg[4]["status"] == "novo"
    comparacao_petr = next(item for item in neg_previa["comparacoes"] if item["ticker"] == "PETR4")
    assert comparacao_petr["status"] == "verificar"
    assert comparacao_petr["quantidade_extrato"] == comparacao_petr["quantidade_existente"] == 107
    assert comparacao_petr["diferenca_valor"] == 0.7


def test_erros(cliente):
    inv = investidor(cliente)
    assert enviar(cliente, "previa", b"nao e planilha", investidor_id=inv).status_code == 422
    r = enviar(cliente, "previa", xlsx(["A", "B"], [[1, 2]]), investidor_id=inv)
    assert r.status_code == 422 and "Formato" in r.json()["detail"]
    assert enviar(cliente, "previa", xlsx(CAB_NEGOCIACAO, []), investidor_id=inv).status_code == 422
    assert enviar(cliente, "previa", NEGOCIACAO, investidor_id=999).status_code == 404
    assert enviar(cliente, "previa", b"", investidor_id=inv).status_code == 422
    assert enviar(cliente, "importar", NEGOCIACAO, investidor_id=inv, incluir="x").status_code == 422


def test_datas_como_datetime(cliente):
    inv = investidor(cliente)
    conteudo = xlsx(CAB_NEGOCIACAO, [[datetime(2025, 2, 3), "Venda", "Mercado à Vista", "-", XP, "BOVA11", 5, 120.5, 602.5]])
    linha = enviar(cliente, "previa", conteudo, investidor_id=inv).json()["linhas"][0]
    assert (linha["data"], linha["evento"], linha["quantidade"]) == ("2025-02-03", "V", -5)


CAB_PROVENTOS = ["Produto", "Pagamento", "Tipo de Evento", "Instituição", "Quantidade", "Preço unitário", "Valor líquido"]
XP_PONTO = "XP INVESTIMENTOS CCTVM S/A."


def dimensao_a1(conteudo: bytes) -> bytes:
    """Reproduz o arquivo da B3, que declara a dimensão da planilha como "A1"."""
    entrada, saida = zipfile.ZipFile(io.BytesIO(conteudo)), io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as destino:
        for item in entrada.infolist():
            dados = entrada.read(item.filename)
            if item.filename.startswith("xl/worksheets/sheet"):
                dados = re.sub(rb'<dimension ref="[^"]+"', b'<dimension ref="A1"', dados)
            destino.writestr(item, dados)
    return saida.getvalue()


PROVENTOS_RECEBIDOS = dimensao_a1(xlsx(CAB_PROVENTOS, [
    ["HGBS11 - HEDGE BRASIL SHOPPING FDO INV IMOB", "15/10/2026", "Rendimento", XP_PONTO, "1.350", 0.17, 229.5],
    ["JHSF3 - JHSF PARTICIPACOES S/A", "09/10/2026", "Dividendo", XP_PONTO, "1.400", 0.07, 96.81],
    ["ABEV3 - AMBEV S.A.", "06/10/2026", "Reembolso", XP_PONTO, "-", "-", 30.22],
    ["ITUB4 - ITAU UNIBANCO HOLDING S.A", "01/10/2026", "Juros Sobre Capital Próprio", XP_PONTO, "370", 0.02, 5.55],
    ["", "", "", "", "", "", ""],
    ["", "", "", "", "", "", "Total"],
    ["", "", "", "", "", "", 362.08],
]))


def test_proventos_recebidos(cliente):
    inv = investidor(cliente)
    r = enviar(cliente, "previa", PROVENTOS_RECEBIDOS, investidor_id=inv)
    assert r.status_code == 200, r.text
    previa = r.json()
    assert previa["relatorio"] == "PROVENTOS"
    linhas = por_numero(previa)
    assert sorted(linhas) == [2, 3, 4, 5]
    assert (linhas[2]["evento"], linhas[2]["valor"]) == ("RENDIMENTO", 229.5)
    assert linhas[3]["evento"] == "DIVIDENDO" and linhas[5]["evento"] == "JSCP"
    assert linhas[4]["evento"] == "REEMBOLSO_JSCP" and "BTC" in linhas[4]["motivo"]
    assert all(lin["status"] == "novo" for lin in linhas.values())
    assert previa["ativos_novos"]["HGBS11"] == "FII"
    resultado = enviar(cliente, "importar", PROVENTOS_RECEBIDOS, investidor_id=inv).json()
    assert resultado["proventos"] == 4 and resultado["corretoras_criadas"] == ["XP"]
    assert enviar(cliente, "importar", PROVENTOS_RECEBIDOS, investidor_id=inv).json()["proventos"] == 0


def test_quantidade_em_texto_pt_br():
    from app.services.extrato_b3 import _decimal

    assert _decimal("1.350") == 1350
    assert _decimal("2.700") == 2700
    assert _decimal("1.234,56") == Decimal("1234.56")
    assert _decimal("38.4") == Decimal("38.4")
    assert _decimal("-") is None
