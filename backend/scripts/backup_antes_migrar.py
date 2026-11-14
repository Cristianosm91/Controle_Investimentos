"""Gera um backup verificado do banco SQLite antes de `alembic upgrade head`, só se houver migração pendente.

Uso (dentro de backend/, chamado pelo iniciar.bat):
    ..\\.venv\\Scripts\\python.exe -m scripts.backup_antes_migrar

Sai com código 1 se o backup falhar, para que a atualização do banco não rode sem cópia de segurança.
"""

import sys

from app.config import settings
from app.services import backup

MOTIVO = "antes-migracao"


def main() -> int:
    if settings.database_url:
        print("Banco em servidor: backup antes da atualização não se aplica; use o backup do serviço (ex.: pg_dump).")
        return 0
    banco = settings.db_path
    if not banco.is_file():
        print(f"Banco ainda não existe em {banco}; nada a copiar antes da atualização.")
        return 0
    avisos: list[str] = []
    try:
        if not backup.migracoes_pendentes(banco):
            return 0
        destino = backup.gerar(banco, "manual", motivo=MOTIVO, avisos=avisos)
    except Exception as erro:
        print(f"ERRO: não foi possível gerar o backup antes de atualizar o banco: {erro}", file=sys.stderr)
        print("A atualização foi cancelada para proteger seus dados; o banco não foi alterado.", file=sys.stderr)
        return 1
    print(f"Backup verificado antes da atualização do banco: {destino}")
    for aviso in avisos:
        print(f"Aviso: {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
