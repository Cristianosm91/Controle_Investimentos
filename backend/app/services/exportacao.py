"""Gera CSV (padrão Excel pt-BR) e XLSX a partir de tabelas já calculadas pela interface."""

import csv
import io
import re
from datetime import date
from decimal import Decimal

from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from ..schemas import AbaExportacao, CelulaData, CelulaNumero

# Texto iniciado por estes caracteres vira fórmula no Excel/LibreOffice (CSV/formula injection).
_INICIO_FORMULA = ("=", "+", "-", "@", "\t", "\r")
_INVALIDOS_ABA = re.compile(r"[\[\]:*?/\\]")
_FORMATO_MOEDA = {simbolo: f'"{simbolo}" #,##0.00;-"{simbolo}" #,##0.00' for simbolo in ("R$", "US$", "€")}


def _texto_seguro(texto: str) -> str:
    return "'" + texto if texto.startswith(_INICIO_FORMULA) else texto


def _decimal_br(valor: float, casas: int | None = None) -> str:
    texto = f"{valor:.{casas}f}" if casas is not None else format(Decimal(repr(valor)).normalize(), "f")
    return texto.replace(".", ",")


def _celula_csv(celula) -> str:
    if celula is None:
        return ""
    if isinstance(celula, CelulaData):
        return celula.d.strftime("%d/%m/%Y")
    if isinstance(celula, CelulaNumero):
        if celula.f == "percentual":
            return _decimal_br(celula.n * 100, 2) + "%"
        return _decimal_br(celula.n, 2 if celula.f == "moeda" else None)
    if isinstance(celula, int | float):
        return _decimal_br(float(celula))
    return _texto_seguro(str(celula))


def gerar_csv(abas: list[AbaExportacao]) -> bytes:
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    for indice, aba in enumerate(abas):
        if len(abas) > 1:
            if indice:
                escritor.writerow([])
            escritor.writerow([_texto_seguro(aba.titulo)])
        escritor.writerow([_texto_seguro(c) for c in aba.colunas])
        for linha in aba.linhas:
            escritor.writerow([_celula_csv(c) for c in linha])
    # BOM: o Excel só reconhece UTF-8 (acentos) com ele.
    return "\ufeff".encode() + saida.getvalue().encode()


def _titulo_aba(titulo: str, usados: set[str]) -> str:
    base = _INVALIDOS_ABA.sub(" ", titulo).strip().strip("'")[:31] or "Tabela"
    nome, n = base, 1
    while nome.lower() in usados:
        n += 1
        sufixo = f" ({n})"
        nome = base[: 31 - len(sufixo)] + sufixo
    usados.add(nome.lower())
    return nome


def _preencher(cell: Cell, celula) -> None:
    if celula is None:
        return
    if isinstance(celula, CelulaData):
        cell.value = celula.d
        cell.number_format = "DD/MM/YYYY"
    elif isinstance(celula, CelulaNumero):
        cell.value = celula.n
        if celula.f == "percentual":
            cell.number_format = "0.00%"
        elif celula.f == "moeda":
            cell.number_format = _FORMATO_MOEDA.get(celula.moeda or "R$", "#,##0.00")
        else:
            cell.number_format = "#,##0" if float(celula.n).is_integer() else "#,##0.00######"
    elif isinstance(celula, int | float):
        cell.value = celula
    else:
        cell.value = str(celula)
        cell.data_type = "s"  # nunca interpretar como fórmula


def _largura(celula) -> int:
    if celula is None:
        return 0
    if isinstance(celula, CelulaData | date):
        return 10
    if isinstance(celula, CelulaNumero):
        return len(_decimal_br(celula.n, 2)) + 4
    return len(str(celula))


def gerar_xlsx(abas: list[AbaExportacao]) -> bytes:
    livro = Workbook()
    livro.remove(livro.active)
    usados: set[str] = set()
    negrito = Font(bold=True)
    for aba in abas:
        planilha = livro.create_sheet(_titulo_aba(aba.titulo, usados))
        larguras = [len(c) for c in aba.colunas]
        for coluna, titulo in enumerate(aba.colunas, start=1):
            cell = planilha.cell(row=1, column=coluna)
            _preencher(cell, titulo)
            cell.font = negrito
        for linha_idx, linha in enumerate(aba.linhas, start=2):
            for coluna, celula in enumerate(linha, start=1):
                _preencher(planilha.cell(row=linha_idx, column=coluna), celula)
                if coluna <= len(larguras):
                    larguras[coluna - 1] = max(larguras[coluna - 1], _largura(celula))
                else:
                    larguras.append(_largura(celula))
        for coluna, largura in enumerate(larguras, start=1):
            planilha.column_dimensions[get_column_letter(coluna)].width = min(max(largura + 2, 8), 60)
        planilha.freeze_panes = "A2"
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()
