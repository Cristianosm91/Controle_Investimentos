import uuid
from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from ..config import settings
from ..db import engine
from ..schemas import BackupOut, BackupsOut, RestauracaoOut
from ..services import backup, jobs
from .deps import exigir_binario

router = APIRouter(tags=["backup"])


def _banco() -> Path:
    if not jobs.usa_sqlite():
        raise HTTPException(409, "O banco está em um servidor: use o backup do próprio serviço (ex.: pg_dump).")
    return settings.db_path


def _arquivo(nome: str) -> Path:
    try:
        return backup.caminho(_banco(), nome)
    except FileNotFoundError as erro:
        raise HTTPException(404, "Backup não encontrado") from erro


def _restaurar(arquivo: Path) -> RestauracaoOut:
    banco = _banco()
    try:
        with jobs.exclusivo():
            seguranca, revisao = backup.restaurar(arquivo, banco)
    except jobs.TarefaOcupada as erro:
        raise HTTPException(409, str(erro)) from erro
    except backup.BackupInvalido as erro:
        raise HTTPException(422, str(erro)) from erro
    finally:
        # Conexões abertas antes da troca não podem reaproveitar cache/estado do banco antigo.
        engine.dispose()
    return RestauracaoOut(restaurado=arquivo.name, revisao=revisao, copia_anterior=seguranca.name)


@router.get("/backups", response_model=BackupsOut)
def listar_backups():
    if not jobs.usa_sqlite():
        return BackupsOut(disponivel=False, motivo="O banco está em um servidor: use o backup do próprio serviço.")
    banco = settings.db_path
    return BackupsOut(
        disponivel=True,
        pasta=str(backup.pasta_backups(banco)),
        itens=[BackupOut(**asdict(i)) for i in backup.listar(banco)],
    )


@router.post("/backups", response_model=BackupOut, status_code=201)
def gerar_backup():
    banco = _banco()
    try:
        destino = backup.gerar(banco, "manual")
    except FileNotFoundError as erro:
        raise HTTPException(404, str(erro)) from erro
    return next(BackupOut(**asdict(i)) for i in backup.listar(banco) if i.nome == destino.name)


@router.get("/backups/{nome}")
def baixar_backup(nome: str):
    return FileResponse(_arquivo(nome), media_type="application/vnd.sqlite3", filename=nome)


@router.delete("/backups/{nome}", status_code=204)
def excluir_backup(nome: str):
    _arquivo(nome).unlink()


@router.post("/backups/{nome}/restaurar", response_model=RestauracaoOut)
def restaurar_backup(nome: str):
    return _restaurar(_arquivo(nome))


@router.post("/backups/restaurar-arquivo", response_model=RestauracaoOut)
async def restaurar_arquivo(request: Request):
    banco = _banco()
    exigir_binario(request)
    declarado = request.headers.get("content-length")
    if declarado and declarado.isdigit() and int(declarado) > backup.TAMANHO_MAXIMO:
        raise HTTPException(413, "Arquivo maior que 200 MB")
    pasta = backup.pasta_backups(banco)
    pasta.mkdir(parents=True, exist_ok=True)
    temporario = pasta / f"envio-{uuid.uuid4().hex}.parcial"
    try:
        recebido = 0
        with temporario.open("wb") as destino:
            async for bloco in request.stream():
                recebido += len(bloco)
                if recebido > backup.TAMANHO_MAXIMO:
                    raise HTTPException(413, "Arquivo maior que 200 MB")
                await run_in_threadpool(destino.write, bloco)
        if not recebido:
            raise HTTPException(422, "Arquivo vazio")
        resultado = await run_in_threadpool(_restaurar, temporario)
        nome = unquote(request.headers.get("x-nome-arquivo", ""))[:200] or "arquivo enviado"
        return resultado.model_copy(update={"restaurado": nome})
    finally:
        temporario.unlink(missing_ok=True)
