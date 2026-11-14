"""Gera um extrato de Negociação da B3 FICTÍCIO (.xlsx) para o teste E2E de importação.

Uso: python gerar_extrato.py <destino.xlsx> <TICKER>
Duas compras do mesmo ticker, corretora e valores inventados; nenhum dado real.
"""

import sys

from openpyxl import Workbook

CABECALHO = (
    "Data do Negócio", "Tipo de Movimentação", "Mercado", "Prazo/Vencimento", "Instituição",
    "Código de Negociação", "Quantidade", "Preço", "Valor",
)


def main() -> None:
    destino, ticker = sys.argv[1], sys.argv[2].upper()
    livro = Workbook()
    planilha = livro.active
    planilha.title = "Negociação"
    planilha.append(CABECALHO)
    planilha.append(("05/02/2026", "Compra", "Mercado à Vista", "-", "CORRETORA FICTICIA E2E S.A.", ticker, 10, 12.5, 125))
    planilha.append(("06/02/2026", "Compra", "Mercado à Vista", "-", "CORRETORA FICTICIA E2E S.A.", ticker, 20, 13.0, 260))
    livro.save(destino)


if __name__ == "__main__":
    main()
