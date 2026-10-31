"""Concilia a apuração de IR do app com a aba `apuração IR` da planilha.

Uso (dentro de backend/):
    ..\\.venv\\Scripts\\python.exe -m scripts.conciliar_ir "..\\Ref\\planilha.xlsx" --investidor "Nome"

Compara, mês a mês, vendas e lucro por categoria e o DARF. Divergências de DARF esperadas: a planilha mantém
prejuízo separado por classe (ações × BDR × opções); o app segue a RFB e compensa dentro das operações comuns.
"""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal

import openpyxl
from sqlalchemy import select

from app.db import SessionLocal
from app.dominio import DARF_MINIMO
from app.models import Investidor
from app.services import ir

MESES_ABREV = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]

# Colunas da aba (linha 7 = cabeçalho): mês, vendas e lucro das ações, lucro de BDR/opções/DT/ETF/FII e DARF.
COLUNAS = {"mes": 1, "vendas_acao": 2, "ACAO": 3, "BDR": 7, "OPCAO": 9, "DAYTRADE": 11, "ETF": 14, "FII": 16, "darf": 29}
CATEGORIAS = ("ACAO", "BDR", "OPCAO", "DAYTRADE", "ETF", "FII")


def _competencia(valor) -> date | None:
    if isinstance(valor, datetime):
        return valor.date().replace(day=1)
    if isinstance(valor, str) and "/" in valor:
        abrev, _, ano = valor.strip().partition("/")
        if abrev in MESES_ABREV and ano.isdigit():
            return date(int(ano), MESES_ABREV.index(abrev) + 1, 1)
    return None


def _num(valor) -> Decimal:
    return Decimal(str(valor)) if isinstance(valor, (int, float)) else Decimal(0)


def ler_apuracao(caminho: str) -> dict[date, dict[str, Decimal]]:
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    aba = next(n for n in wb.sheetnames if n.lower().startswith("apura"))
    resultado = {}
    for linha in wb[aba].iter_rows(min_row=8, values_only=True):
        if len(linha) <= COLUNAS["darf"]:
            continue
        comp = _competencia(linha[COLUNAS["mes"]])
        if comp:
            resultado[comp] = {k: _num(linha[i]) for k, i in COLUNAS.items() if k != "mes"}
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("planilha")
    parser.add_argument("--investidor", required=True)
    parser.add_argument("--tolerancia", type=Decimal, default=Decimal("0.01"), help="Tolerância em R$")
    args = parser.parse_args(argv)

    esperado = ler_apuracao(args.planilha)
    with SessionLocal() as sessao:
        inv = sessao.scalar(select(Investidor).where(Investidor.nome == args.investidor))
        if inv is None:
            print(f"Investidor {args.investidor!r} não encontrado", file=sys.stderr)
            return 1
        apuracao = ir.apurar(sessao, inv.id)

    lucros_divergentes = darf_divergentes = comparados = 0
    for m in apuracao.meses:
        e = esperado.get(m.competencia)
        if e is None:
            continue
        comparados += 1
        cat = {r.categoria: r for r in m.categorias}
        difs = []
        if abs(abs(e["vendas_acao"]) - cat["ACAO"].vendas) > args.tolerancia:
            difs.append(f"vendas ações {abs(e['vendas_acao']):.2f}|{cat['ACAO'].vendas:.2f}")
        for c in CATEGORIAS:
            if abs(e[c] - cat[c].lucro) > args.tolerancia:
                difs.append(f"lucro {c} {e[c]:.2f}|{cat[c].lucro:.2f}")
        lucros_divergentes += bool(difs)
        darf_app = m.darf if m.darf else Decimal(0)
        # A planilha mostra o DARF do mês mesmo abaixo do mínimo; o app transporta para o mês seguinte.
        darf_planilha = e["darf"] if e["darf"] >= DARF_MINIMO else Decimal(0)
        if abs(darf_planilha - darf_app) > args.tolerancia:
            difs.append(f"DARF {darf_planilha:.2f}|{darf_app:.2f}")
            darf_divergentes += 1
        if difs:
            print(f"{m.competencia:%Y-%m}  " + " · ".join(difs) + "   (planilha|app)")

    print(
        f"\nMeses comparados: {comparados} · lucro/vendas divergentes: {lucros_divergentes}"
        f" · DARF divergentes: {darf_divergentes}"
    )
    if apuracao.nao_apurados:
        print("Fora da apuração de renda variável:", ", ".join(apuracao.nao_apurados))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
