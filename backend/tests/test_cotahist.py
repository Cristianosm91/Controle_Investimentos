import zipfile
from datetime import date
from decimal import Decimal as D

from app.services.cotahist import interpretar_linha, ler_arquivo

PETR4 = (
    "012026102902PETR4       010PETROBRAS   PN      N2   R$  000000000520500000000053030000000005175000000000522800"
    "000000052200000000005220000000000522670737000000000051969000000000271710199700000000000000009999123100000010"
    "000000000000BRPETRACNPR6230"
)
HGLG11 = (
    "012026102912HGLG11      010FII HGLG PAXCI           R$  000000001477000000000148000000000014673000000001470500"
    "000000147000000000014700000000001471415019000000000000104025000000001529771640000000000000009999123100000010"
    "000000000000BRHGLGCTF004302"
)
HEADER = "00COTAHIST.2026BOVESPA 20261029" + " " * 214


def _com_mercado(linha: str, tpmerc: str) -> str:
    return linha[:24] + tpmerc + linha[27:]


def _com_fator(linha: str, fator: int) -> str:
    return linha[:210] + f"{fator:07d}" + linha[217:]


def test_interpreta_fechamento_do_mercado_a_vista():
    f = interpretar_linha(PETR4)
    assert f.ticker == "PETR4"
    assert f.data == date(2026, 10, 29)
    assert f.preco == D("52.20")


def test_ignora_header_e_outros_mercados():
    assert interpretar_linha(HEADER) is None
    assert interpretar_linha(_com_mercado(PETR4, "070")) is None  # opção de compra


def test_preco_dividido_pelo_fator_de_cotacao():
    assert interpretar_linha(_com_fator(PETR4, 1000)).preco == D("0.0522")


def test_le_zip_filtrando_tickers(tmp_path):
    arquivo = tmp_path / "COTAHIST_D29102026.ZIP"
    with zipfile.ZipFile(arquivo, "w") as z:
        z.writestr("COTAHIST_D29102026.TXT", "\n".join([HEADER, PETR4, HGLG11]).encode("latin-1"))
    resultado = ler_arquivo(arquivo, {"HGLG11"})
    assert list(resultado) == [("HGLG11", date(2026, 10, 29))]
    assert resultado[("HGLG11", date(2026, 10, 29))].preco == D("147.00")
