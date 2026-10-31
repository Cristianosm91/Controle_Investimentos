import io
from datetime import datetime

from openpyxl import Workbook

CABECALHO = ["Movimentação", "Liquidação", "Lançamento", "Valor (R$)"]
DIA = datetime(2026, 8, 5)


def xlsx(linhas, cabecalho=CABECALHO) -> bytes:
    livro = Workbook()
    planilha = livro.active
    planilha.append(["Extrato de conta corrente"])
    planilha.append(cabecalho)
    for linha in linhas:
        planilha.append(linha)
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


EXTRATO = xlsx([
    [DIA, DIA, "Crédito Ref. Taxa de Remuneração BTC MGLU", "R$ 23,24"],
    [DIA, DIA, "DEBITO CBLC IRRF S/ RENDIMENTO DE BTC MGLU", "-R$ 5,22"],
    [DIA, DIA, "Taxa de intermediação doador MGLU3 2026072301087022250001-2", "-R$ 11,99"],
    [DIA, DIA, "Crédito Ref. Taxa de Remuneração BTC WEGE", 0.14],
    [DIA, DIA, "Taxa de intermediação doador ABCD3 2026072301087022250001-2", -1],
    [DIA, DIA, "TED RECEBIDA", "R$ 100,00"],
])


def preparar(cliente):
    inv = cliente.post("/api/investidores", json={"nome": "Ana", "cor": "#000000", "ativo": True}).json()["id"]
    for ticker in ("MGLU3", "WEGE3"):
        cliente.post("/api/ativos", json={"ticker": ticker, "classe": "AÇÃO"})
    return inv


def enviar(cliente, rota, conteudo, **params):
    return cliente.post(
        f"/api/aluguel/extrato/{rota}", params=params, content=conteudo,
        headers={"content-type": "application/octet-stream"},
    )


def test_previa_e_importacao_idempotente(cliente):
    inv = preparar(cliente)
    r = enviar(cliente, "previa", EXTRATO, investidor_id=inv)
    assert r.status_code == 200, r.text
    itens = {i["raiz"]: i for i in r.json()}
    assert set(itens) == {"ABCD", "MGLU", "WEGE"}
    mglu = itens["MGLU"]
    assert (mglu["ticker"], mglu["valor"], mglu["irrf"], mglu["taxas"], mglu["status"]) == ("MGLU3", 23.24, 5.22, 11.99, "novo")
    assert mglu["linhas"] == [3, 4, 5]
    assert itens["WEGE"]["ticker"] == "WEGE3" and itens["WEGE"]["status"] == "novo"
    assert itens["ABCD"]["status"] == "sem_ativo"

    assert enviar(cliente, "importar", EXTRATO, investidor_id=inv).json() == {"gravados": 2}
    assert enviar(cliente, "importar", EXTRATO, investidor_id=inv).json() == {"gravados": 0}
    status = {i["raiz"]: i["status"] for i in enviar(cliente, "previa", EXTRATO, investidor_id=inv).json()}
    assert status == {"ABCD": "sem_ativo", "MGLU": "duplicado", "WEGE": "duplicado"}

    lista = cliente.get("/api/proventos", params={"evento": "ALUGUEL", "investidores": inv}).json()
    assert lista["total"] == 2
    assert cliente.get("/api/proventos", params={"evento": "DIVIDENDO"}).json()["total"] == 0


def test_existente_com_outro_valor_vai_para_verificar(cliente):
    inv = preparar(cliente)
    mglu = next(a for a in cliente.get("/api/ativos").json() if a["ticker"] == "MGLU3")
    cliente.post("/api/proventos", json={
        "investidor_id": inv, "ativo_id": mglu["id"], "data_pagamento": "2026-08-05", "evento": "ALUGUEL", "valor": 20,
    })
    itens = {i["raiz"]: i for i in enviar(cliente, "previa", EXTRATO, investidor_id=inv).json()}
    assert itens["MGLU"]["status"] == "verificar"
    r = enviar(cliente, "importar", EXTRATO, investidor_id=inv, incluir=itens["MGLU"]["hash"])
    assert r.json() == {"gravados": 2}


def test_resumo(cliente):
    inv = preparar(cliente)
    enviar(cliente, "importar", EXTRATO, investidor_id=inv)
    r = cliente.get("/api/aluguel").json()
    assert r["anos"] == [2026] and r["lancamentos"] == 2
    assert r["totais"] == {"bruto": 23.38, "taxas": 11.99, "irrf": 5.22, "liquido": 6.17}
    assert [a["ticker"] for a in r["por_ativo"]] == ["MGLU3", "WEGE3"]
    assert r["por_ativo"][0]["liquido"] == 6.03 and r["por_ativo"][0]["ultimo"] == "2026-08-05"
    assert r["por_mes"] == [{"mes": "2026-08", "bruto": 23.38, "taxas": 11.99, "irrf": 5.22, "liquido": 6.17}]
    assert cliente.get("/api/aluguel", params={"ano": 2025}).json()["lancamentos"] == 0


def test_csv_e_erros(cliente):
    inv = preparar(cliente)
    csv = "Data;Histórico;Valor\n05/08/2026;Crédito Ref. Taxa de Remuneração BTC MGLU;23,24\n".encode("cp1252")
    itens = enviar(cliente, "previa", csv, investidor_id=inv).json()
    assert itens[0]["valor"] == 23.24 and itens[0]["ticker"] == "MGLU3"
    r = enviar(cliente, "previa", xlsx([[DIA, DIA, "TED", 1]]), investidor_id=inv)
    assert r.status_code == 422 and "BTC" in r.json()["detail"]
    r = enviar(cliente, "previa", xlsx([], ["A", "B"]), investidor_id=inv)
    assert r.status_code == 422 and "Cabeçalho" in r.json()["detail"]
    assert enviar(cliente, "previa", EXTRATO, investidor_id=99).status_code == 404
