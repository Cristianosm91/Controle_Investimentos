import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import __version__
from .api import (
    alocacao,
    aluguel,
    ativos,
    atualizacoes,
    backup,
    cadastros,
    carteira,
    conciliacao,
    configuracoes,
    cripto,
    exportacao,
    extratos,
    fundamentos,
    ir,
    lancamentos,
    modelos,
    monitoramento,
    planejamento,
    radar,
    rentabilidade,
    status,
    valuation,
)
from .config import RAIZ_PROJETO, settings
from .seguranca import CabecalhosSegurancaMiddleware, OrigemLocalMiddleware
from .services import jobs

LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUPS = 5
_FORMATO_LOG = "%(asctime)s %(levelname)s %(name)s [%(request_id)s]: %(message)s"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_PASTA_USUARIO = re.compile(r"(?i)\b([a-z]:[\\/]+users[\\/]+)[^\\/\s'\"]+")
_REQUEST_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

log = logging.getLogger(__name__)


class _ContextoRequisicao(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class _FormatadorSemDadosPessoais(logging.Formatter):
    """Mascara o usuário do Windows em caminhos (C:\\Users\\<nome>\\...), inclusive em tracebacks."""

    def format(self, record: logging.LogRecord) -> str:
        return _PASTA_USUARIO.sub(r"\1***", super().format(record))


def pasta_logs() -> Path:
    """Mesma base do banco (padrão %LOCALAPPDATA%\\InvestHub, fora do OneDrive); INVESTHUB_LOG_DIR sobrepõe."""
    return Path(os.environ["INVESTHUB_LOG_DIR"]) if os.environ.get("INVESTHUB_LOG_DIR") else settings.db_path.parent / "logs"


def _novo_handler(handler: logging.Handler) -> logging.Handler:
    handler._investhub = True  # type: ignore[attr-defined]
    handler.addFilter(_ContextoRequisicao())
    handler.setFormatter(_FormatadorSemDadosPessoais(_FORMATO_LOG))
    return handler


def configurar_logs(pasta: Path | None = None) -> Path | None:
    """Console + arquivo com rotação. Idempotente: substitui os handlers criados por chamadas anteriores."""
    raiz = logging.getLogger()
    for handler in [h for h in raiz.handlers if getattr(h, "_investhub", False)]:
        raiz.removeHandler(handler)
        handler.close()
    nivel = os.environ.get("INVESTHUB_LOG_LEVEL", "INFO").upper()
    raiz.setLevel(nivel if nivel in logging.getLevelNamesMapping() else "INFO")
    if not raiz.handlers:  # como o basicConfig: não duplica o console quando outro já configurou (ex.: pytest)
        raiz.addHandler(_novo_handler(logging.StreamHandler()))
    arquivo = (pasta or pasta_logs()) / "investhub.log"
    try:
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(arquivo, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8")
    except OSError:
        log.warning("Pasta de logs não gravável; mantendo só o console", exc_info=True)
        return None
    raiz.addHandler(_novo_handler(handler))
    return arquivo


configurar_logs()


class RequestIdMiddleware:
    """Gera (ou reaproveita, se seguro) o X-Request-ID, disponibiliza aos logs e devolve no cabeçalho."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        recebido = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1")
        request_id = recebido if _REQUEST_ID_VALIDO.match(recebido) else uuid.uuid4().hex[:16]
        scope.setdefault("state", {})["request_id"] = request_id
        token = _request_id.set(request_id)

        async def enviar(mensagem: Message) -> None:
            if mensagem["type"] == "http.response.start":
                mensagem.setdefault("headers", [])
                mensagem["headers"] = [*mensagem["headers"], (b"x-request-id", request_id.encode())]
            await send(mensagem)

        try:
            await self.app(scope, receive, enviar)
        finally:
            _request_id.reset(token)


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    if settings.jobs_ativos:
        jobs.iniciar()
    yield
    jobs.parar()


app = FastAPI(title="InvestHub+", version=__version__, lifespan=ciclo_de_vida)
# O último adicionado roda primeiro: Host é validado antes da origem; os cabeçalhos valem para todas as respostas.
app.add_middleware(OrigemLocalMiddleware, hosts_permitidos=settings.hosts_permitidos)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts_permitidos)
app.add_middleware(CabecalhosSegurancaMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, erro: Exception) -> JSONResponse:
    """Só exceções não tratadas: HTTPException e validação mantêm as respostas padrão do FastAPI."""
    erro_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex[:16]
    log.error("Erro inesperado [erro_id=%s] em %s %s", erro_id, request.method, request.url.path, exc_info=erro)
    return JSONResponse(
        {"detail": "Erro inesperado no servidor. Tente novamente; se persistir, informe o código ao suporte.",
         "erro_id": erro_id},
        status_code=500,
        headers={"X-Request-ID": erro_id},
    )

for modulo in (
    cadastros, ativos, lancamentos, carteira, conciliacao, atualizacoes, rentabilidade, configuracoes, alocacao, ir,
    fundamentos, radar, status, valuation, cripto, backup, exportacao, extratos, aluguel, modelos, planejamento,
    monitoramento,
):
    app.include_router(modulo.router, prefix="/api")


@app.get("/api/saude", tags=["infra"])
def saude():
    return {"status": "ok", "versao": __version__}


_DIST = RAIZ_PROJETO / "frontend" / "dist"

if (_DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        if caminho.startswith("api/"):
            raise HTTPException(404)
        arquivo = (_DIST / caminho).resolve()
        if caminho and arquivo.is_file() and arquivo.is_relative_to(_DIST.resolve()):
            return FileResponse(arquivo)
        return FileResponse(_DIST / "index.html")
