"""Concilia a rentabilidade calculada pelo app com a aba `dashboard.` da planilha.

Uso (dentro de backend/):
    ..\\.venv\\Scripts\\python.exe -m scripts.conciliar_rentabilidade "..\\Ref\\planilha.xlsx" --investidor "Nome"
"""

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal

import openpyxl
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Investidor
from app.services import rentabilidade as r

# Colunas da aba dashboard. (linha 6 = cabeçalho; dados a partir da linha 7)
COLUNAS = {"data": 0, "investido": 1, "mercado": 2, "proventos": 3, "trades": 4, "daytrade": 5, "twr": 11, "twr_acc": 12}


def ler_dashboard(caminho: str) -> dict[date, dict[str, float]]:
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    resultado = {}
    for linha in wb["dashboard."].iter_rows(min_row=7, values_only=True):
        dia = linha[COLUNAS["data"]]
        if not isinstance(dia, datetime):
            continue
        valores = {}
        for nome, i in COLUNAS.items():
            if nome != "data":
                v = linha[i]
                valores[nome] = float(v) if isinstance(v, (int, float)) else 0.0
        resultado[dia.date()] = valores
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("planilha")
    parser.add_argument("--investidor", required=True)
    parser.add_argument("--tolerancia-pp", type=float, default=0.05, help="Tolerância do TWR mensal em p.p.")
    parser.add_argument("--detalhar", action="store_true", help="Mostra todos os meses")
    args = parser.parse_args(argv)

    esperado = ler_dashboard(args.planilha)
    with SessionLocal() as sessao:
        inv = sessao.scalar(select(Investidor).where(Investidor.nome == args.investidor))
        if inv is None:
            print(f"Investidor {args.investidor!r} não encontrado", file=sys.stderr)
            return 1
        dados = r.carregar_dados(sessao, [inv.id])
    serie = r.serie_mensal(dados.movimentos, [(d, v) for _, _, d, v in dados.proventos], dados.precificacao, max(esperado))

    divergentes = 0
    print(f"{'mês':<8} {'investido':>22} {'mercado':>22} {'proventos':>18} {'trades':>18} {'TWR % (planilha|app)':>22}")
    for m in serie:
        e = esperado.get(m.data)
        if e is None:
            continue
        twr_dif = abs(float(m.twr) - e["twr"]) * 100
        ok = twr_dif <= args.tolerancia_pp
        divergentes += not ok
        if args.detalhar or not ok:
            print(
                f"{m.data:%Y-%m} {e['investido']:>11.2f}|{float(m.investido):>10.2f} "
                f"{e['mercado']:>11.2f}|{float(m.mercado):>10.2f} {e['proventos']:>9.2f}|{float(m.proventos):>8.2f} "
                f"{e['trades']:>9.2f}|{float(m.lucro_trades):>8.2f} {e['twr']*100:>9.3f}|{float(m.twr)*100:>8.3f}"
                f"{'' if ok else '  <--'}"
            )
    ultimo = next((m for m in reversed(serie) if m.data in esperado), None)
    if ultimo:
        print(f"\nTWR acumulado em {ultimo.data:%m/%Y}: planilha {esperado[ultimo.data]['twr_acc']*100:.2f}% | app {float(ultimo.twr_acumulado)*100:.2f}%")
    print(f"Meses comparados: {sum(m.data in esperado for m in serie)} · divergentes: {divergentes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
