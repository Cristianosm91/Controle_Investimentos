import csv
import io
from datetime import date

from openpyxl import load_workbook

ABAS = [
    {
        "titulo": "Posições",
        "colunas": ["Ativo", "Data", "Valor", "Peso", "Qtd", "Obs"],
        "linhas": [
            ["PETR4", {"d": "2024-03-05"}, {"n": -1234.5, "f": "moeda", "moeda": "R$"}, {"n": 0.1234, "f": "percentual"},
             {"n": 100, "f": "numero"}, "=HYPERLINK(\"x\")"],
            ["AAPL", None, {"n": 10.5, "f": "moeda", "moeda": "US$"}, None, {"n": 0.123456, "f": "numero"}, "ok"],
        ],
    },
    {"titulo": "Posições", "colunas": ["A"], "linhas": [["x"]]},
    {"titulo": "a/b:c*d?[e]", "colunas": ["A"], "linhas": []},
]


def test_csv_pt_br_com_varias_tabelas(cliente):
    r = cliente.post("/api/exportacao/csv", json={"nome": "Portfólio", "abas": ABAS})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "filename*=UTF-8''Portf%C3%B3lio-" in r.headers["content-disposition"]
    assert r.content.startswith("\ufeff".encode())
    linhas = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig")), delimiter=";"))
    assert linhas[0] == ["Posições"]
    assert linhas[1] == ["Ativo", "Data", "Valor", "Peso", "Qtd", "Obs"]
    assert linhas[2] == ["PETR4", "05/03/2024", "-1234,50", "12,34%", "100", "'=HYPERLINK(\"x\")"]
    assert linhas[3] == ["AAPL", "", "10,50", "", "0,123456", "ok"]
    assert linhas[4] == []


def test_xlsx_tipado_e_seguro(cliente):
    r = cliente.post("/api/exportacao/xlsx", json={"nome": "portfolio", "abas": ABAS})
    assert r.status_code == 200
    livro = load_workbook(io.BytesIO(r.content))
    assert livro.sheetnames == ["Posições", "Posições (2)", "a b c d  e"]
    aba = livro["Posições"]
    assert [c.value for c in aba[1]] == ["Ativo", "Data", "Valor", "Peso", "Qtd", "Obs"]
    assert aba["B2"].value.date() == date(2024, 3, 5)
    assert aba["C2"].value == -1234.5 and "R$" in aba["C2"].number_format
    assert aba["D2"].value == 0.1234 and aba["D2"].number_format == "0.00%"
    assert aba["E2"].value == 100 and aba["E2"].number_format == "#,##0"
    assert aba["F2"].value == '=HYPERLINK("x")' and aba["F2"].data_type == "s"
    assert "US$" in aba["C3"].number_format
    assert aba.freeze_panes == "A2"


def test_validacao(cliente):
    assert cliente.post("/api/exportacao/pdf", json={"nome": "x", "abas": ABAS}).status_code == 422
    assert cliente.post("/api/exportacao/csv", json={"nome": "../x", "abas": ABAS}).status_code == 422
    assert cliente.post("/api/exportacao/csv", json={"nome": "x", "abas": []}).status_code == 422
    invalida = [{"titulo": "t", "colunas": ["a"], "linhas": [[{"n": 1, "f": "outro"}]]}]
    assert cliente.post("/api/exportacao/csv", json={"nome": "x", "abas": invalida}).status_code == 422
