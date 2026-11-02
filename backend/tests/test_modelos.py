import io
from decimal import Decimal as D

import openpyxl
import pytest

from app.services import aluguel, extrato_b3, modelos


def _preenchido(nome: str) -> bytes:
    """Modelo baixado e preenchido com o próprio exemplo da aba de instruções."""
    _, conteudo = modelos.gerar(nome)
    livro = openpyxl.load_workbook(io.BytesIO(conteudo))
    dados = livro.worksheets[0]
    for linha in modelos.MODELOS[nome].exemplo:
        dados.append(list(linha))
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


@pytest.mark.parametrize(
    ("nome", "relatorio", "esperado"),
    [
        ("planilha-operacoes", "PLANILHA_OPERACOES", [("OPERACAO", "C", "PETR4", D(100)), ("OPERACAO", "V", "PETR4", D(-10))]),
        ("b3-negociacao", "NEGOCIACAO", [("OPERACAO", "C", "PETR4", D(100)), ("OPERACAO", "V", "PETR4", D(-10))]),
        ("b3-movimentacao", "MOVIMENTACAO", [("PROVENTO", "DIVIDENDO", "ITSA4", D(0)),
                                             ("PROVENTO", "RENDIMENTO", "HGLG11", D(0))]),
        ("b3-proventos", "PROVENTOS", [("PROVENTO", "JSCP", "ITSA4", D(0))]),
    ],
)
def test_modelos_b3_sao_lidos_pelo_importador(nome, relatorio, esperado):
    lido, linhas = extrato_b3.ler(_preenchido(nome))
    assert lido == relatorio
    assert [(l.tipo, l.evento, l.ticker, l.quantidade) for l in linhas] == esperado


@pytest.mark.parametrize("nome", ["planilha-operacoes", "b3-negociacao", "b3-movimentacao", "b3-proventos"])
def test_modelo_b3_vazio_tem_cabecalho_reconhecido(nome):
    _, conteudo = modelos.gerar(nome)
    with pytest.raises(extrato_b3.ExtratoInvalido, match="não tem lançamentos"):
        extrato_b3.ler(conteudo)


def test_modelo_aluguel_e_lido_pelo_importador():
    (grupo,) = aluguel.ler_extrato(_preenchido("aluguel"))
    assert (grupo.raiz, grupo.ticker, grupo.valor, grupo.irrf, grupo.taxas) == (
        "MGLU", "MGLU3", D("23.24"), D("5.22"), D("11.99"),
    )


def test_modelo_traz_instrucoes_e_listas():
    _, conteudo = modelos.gerar("b3-negociacao")
    livro = openpyxl.load_workbook(io.BytesIO(conteudo))
    assert livro.sheetnames == ["Negociação", "Instruções"]
    assert {str(v.sqref) for v in livro.worksheets[0].data_validations.dataValidation} == {"B2:B1001", "C2:C1001"}


def test_api_baixa_modelo(cliente):
    resposta = cliente.get("/api/modelos/aluguel")
    assert resposta.status_code == 200
    assert resposta.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert "modelo-aluguel-btc.xlsx" in resposta.headers["content-disposition"]
    assert cliente.get("/api/modelos/inexistente").status_code == 404


@pytest.mark.parametrize(
    ("nome", "arquivo", "relatorio"),
    [
        ("planilha-operacoes", "modelo-planilha-operacoes.xlsx", "PLANILHA_OPERACOES"),
        ("b3-negociacao", "modelo-b3-negociacao.xlsx", "NEGOCIACAO"),
        ("b3-movimentacao", "modelo-b3-movimentacao.xlsx", "MOVIMENTACAO"),
        ("b3-proventos", "modelo-b3-proventos.xlsx", "PROVENTOS"),
    ],
)
def test_modelos_baixados_continuam_importaveis(cliente, nome, arquivo, relatorio):
    resposta = cliente.get(f"/api/modelos/{nome}")
    assert resposta.status_code == 200
    assert arquivo in resposta.headers["content-disposition"]

    livro = openpyxl.load_workbook(io.BytesIO(resposta.content))
    for linha in modelos.MODELOS[nome].exemplo:
        livro.worksheets[0].append(list(linha))
    saida = io.BytesIO()
    livro.save(saida)
    assert extrato_b3.ler(saida.getvalue())[0] == relatorio

    investidor_id = cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]
    arquivo = saida.getvalue()
    previa = cliente.post(
        "/api/extratos/b3/previa", params={"investidor_id": investidor_id}, content=arquivo,
        headers={"content-type": "application/octet-stream"},
    )
    assert previa.status_code == 200 and previa.json()["relatorio"] == relatorio

    if nome == "planilha-operacoes":
        importacao = cliente.post(
            "/api/extratos/b3/importar", params={"investidor_id": investidor_id}, content=arquivo,
            headers={"content-type": "application/octet-stream"},
        )
        assert importacao.status_code == 200 and importacao.json()["operacoes"] == 2
        operacoes = cliente.get("/api/operacoes", params={"investidores": investidor_id}).json()["itens"]
        assert {(op["evento"], op["taxas"], op["irrf"]) for op in operacoes} == {
            ("C", 12.34, 0), ("V", 2.5, 0.01),
        }
