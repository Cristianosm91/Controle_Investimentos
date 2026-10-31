"""Carrega fechamentos oficiais da B3 (COTAHIST) para os ativos que já tiveram operação.

Uso (dentro de backend/):
    ..\\.venv\\Scripts\\python.exe -m scripts.carregar_cotahist            # anual, desde a 1ª operação
    ..\\.venv\\Scripts\\python.exe -m scripts.carregar_cotahist --desde 2024
    ..\\.venv\\Scripts\\python.exe -m scripts.carregar_cotahist --diario   # só dias pendentes
"""

import argparse
import logging

from app.db import SessionLocal
from app.services import cotahist


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--desde", type=int, help="Primeiro ano (padrão: ano da 1ª operação)")
    parser.add_argument("--ate", type=int, help="Último ano (padrão: ano corrente)")
    parser.add_argument("--diario", action="store_true", help="Carrega só os arquivos diários pendentes")
    args = parser.parse_args(argv)

    with SessionLocal() as sessao:
        if args.diario:
            r = cotahist.carregar_pendentes(sessao)
        else:
            r = cotahist.carregar_historico(sessao, args.desde, args.ate)
    print(f"Arquivos: {', '.join(r.arquivos) or '-'}")
    print(f"Não publicados: {', '.join(r.indisponiveis) or '-'}")
    print(f"Cotações gravadas: {r.cotacoes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
