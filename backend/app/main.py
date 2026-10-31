import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import (
    alocacao,
    aluguel,
    ativos,
    atualizacoes,
    backup,
    cadastros,
    carteira,
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
from .services import jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    if settings.jobs_ativos:
        jobs.iniciar()
    yield
    jobs.parar()


app = FastAPI(title="InvestHub+", version=__version__, lifespan=ciclo_de_vida)

for modulo in (
    cadastros, ativos, lancamentos, carteira, atualizacoes, rentabilidade, configuracoes, alocacao, ir, fundamentos, radar,
    status, valuation, cripto, backup, exportacao, extratos, aluguel, modelos, planejamento, monitoramento,
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
