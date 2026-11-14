"""Sobe o backend do InvestHub+ para os testes E2E com banco SQLite descartável.

Uso (o Playwright chama via `webServer`): ..\\.venv\\Scripts\\python.exe e2e\\servidor_e2e.py

- Cria uma pasta nova por execução em `frontend/.e2e-dados/` (ou em E2E_DADOS_DIR) e apaga as anteriores.
- Nunca aponta para o banco do usuário: aborta se a URL efetiva não for o SQLite da pasta da execução.
- Jobs em segundo plano desligados, sem cópia secundária de backup, logs na pasta da execução.
- Aplica `alembic upgrade head` (o banco nasce das migrações, como em produção).
- Serve uma cópia de `frontend/dist` feita na subida (imune a um `vite build` simultâneo).
- Bloqueia conexões de rede do processo para fora de 127.0.0.1/localhost: nenhuma API externa é chamada.
  Tentativas bloqueadas ficam em `<pasta da execução>/rede-bloqueada.log`.
"""

import os
import shutil
import socket
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BACKEND = RAIZ / "backend"
DIST = RAIZ / "frontend" / "dist" / "index.html"
PORTA = int(os.environ.get("E2E_PORTA", "8765"))
HOSTS_LOCAIS = {"127.0.0.1", "localhost", "::1", "", None}


def preparar_pasta() -> Path:
    base = Path(os.environ.get("E2E_DADOS_DIR") or RAIZ / "frontend" / ".e2e-dados")
    base.mkdir(parents=True, exist_ok=True)
    for antiga in base.glob("execucao-*"):
        shutil.rmtree(antiga, ignore_errors=True)
    pasta = base / f"execucao-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    (pasta / "logs").mkdir(parents=True)
    return pasta


def bloquear_rede(registro: Path) -> None:
    """Recusa conexões (e resolução de nomes) para hosts que não sejam a própria máquina."""
    conectar_original = socket.socket.connect
    conectar_ex_original = socket.socket.connect_ex
    resolver_original = socket.getaddrinfo

    def local(host) -> bool:
        if isinstance(host, bytes):
            host = host.decode(errors="replace")
        return host in HOSTS_LOCAIS or str(host).startswith("127.")

    def recusar(host) -> OSError:
        with registro.open("a", encoding="utf-8") as arquivo:
            arquivo.write(f"{time.strftime('%H:%M:%S')} bloqueado: {host}\n")
        return ConnectionRefusedError(f"E2E: rede externa bloqueada ({host})")

    def connect(self, endereco):
        host = endereco[0] if isinstance(endereco, tuple) else endereco
        if not local(host):
            raise recusar(host)
        return conectar_original(self, endereco)

    def connect_ex(self, endereco):
        host = endereco[0] if isinstance(endereco, tuple) else endereco
        if not local(host):
            raise recusar(host)
        return conectar_ex_original(self, endereco)

    def getaddrinfo(host, *args, **kwargs):
        if not local(host):
            raise recusar(host)
        return resolver_original(host, *args, **kwargs)

    socket.socket.connect = connect  # type: ignore[method-assign]
    socket.socket.connect_ex = connect_ex  # type: ignore[method-assign]
    socket.getaddrinfo = getaddrinfo  # type: ignore[assignment]


def main() -> None:
    if not DIST.is_file():
        sys.exit("E2E: frontend/dist não encontrado. Rode `npm --prefix frontend run build` antes dos testes.")
    pasta = preparar_pasta()
    banco = pasta / "investhub-e2e.db"
    os.environ.update(
        {
            "INVESTHUB_DB_PATH": str(banco),
            "INVESTHUB_JOBS_ATIVOS": "false",
            "INVESTHUB_BACKUP_COPIA_DIR": "",
            "INVESTHUB_LOG_DIR": str(pasta / "logs"),
            "INVESTHUB_HOSTS_PERMITIDOS": '["127.0.0.1","localhost"]',
        }
    )
    os.environ.pop("INVESTHUB_DATABASE_URL", None)
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    bloquear_rede(pasta / "rede-bloqueada.log")

    from app.config import settings

    # Um INVESTHUB_DATABASE_URL vindo do .env do usuário teria precedência sobre o db_path: anulado só neste processo.
    settings.database_url = None
    esperado = f"sqlite:///{banco.as_posix()}"
    if settings.db_url != esperado or settings.jobs_ativos or settings.backup_copia_dir.strip():
        sys.exit(f"E2E: configuração inesperada ({settings.db_url}, jobs={settings.jobs_ativos}); abortado.")

    from alembic.config import main as alembic

    alembic(argv=["-c", str(BACKEND / "alembic.ini"), "upgrade", "head"])

    preparar_cdi_ficticio()

    import uvicorn

    principal = servir_copia_do_build(pasta)
    print(f"E2E: banco descartável em {banco}", flush=True)
    uvicorn.run(principal.app, host="127.0.0.1", port=PORTA, log_level="warning")


def servir_copia_do_build(pasta: Path):
    """Serve uma cópia de frontend/dist feita na subida: um `vite build` simultâneo (ex.: lint.bat) esvazia a pasta
    original e derrubaria as páginas no meio da execução. Ajuste só deste processo; o app não é alterado."""
    copia = pasta / "dist"
    shutil.copytree(DIST.parent, copia)
    if not (copia / "index.html").is_file() or not any((copia / "assets").glob("*.js")):
        sys.exit("E2E: frontend/dist incompleto (build em andamento?). Rode o build e tente de novo.")

    from starlette.routing import Mount
    from starlette.staticfiles import StaticFiles

    import app.main as principal

    principal._DIST = copia
    montagens = [r for r in principal.app.routes if isinstance(r, Mount) and r.name == "assets"]
    if len(montagens) != 1:
        sys.exit("E2E: rota /assets do app não encontrada; revise servidor_e2e.py.")
    montagens[0].app = StaticFiles(directory=copia / "assets")
    return principal


def preparar_cdi_ficticio() -> None:
    """Fixture deterministica: taxas sinteticas, nunca dados de investidores ou consultas externas."""
    from datetime import date, timedelta
    from decimal import Decimal

    from app.db import SessionLocal
    from app.services.cdi import gravar

    inicio = date(2025, 1, 1)
    fim = date.today() - timedelta(days=1)
    taxas = {}
    dia = inicio
    while dia <= fim:
        if dia.weekday() < 5:
            taxas[dia] = Decimal("0.0001")
        dia += timedelta(days=1)
    with SessionLocal() as sessao:
        gravar(sessao, inicio, fim, taxas)


if __name__ == "__main__":
    main()
