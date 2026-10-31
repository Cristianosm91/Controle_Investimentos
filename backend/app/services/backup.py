"""Backup e restauração do banco SQLite local.

Cópias usam a API de backup do SQLite (consistente mesmo com o app gravando). A restauração valida o arquivo,
guarda uma cópia do banco atual e substitui o conteúdo pela mesma API, sem trocar o arquivo aberto.
"""

import logging
import sqlite3
from contextlib import ExitStack, closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command

from ..config import RAIZ_PROJETO

log = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")
CABECALHO_SQLITE = b"SQLite format 3\x00"
TAMANHO_MAXIMO = 200 * 1024 * 1024
MANTER_AUTOMATICOS = 10
# Cópias feitas a cada restauração; backups manuais nunca são apagados automaticamente.
MANTER_ANTES_RESTAURACAO = 10
PREFIXO = "investhub-"
TIPOS = ("manual", "automatico", "antes-restauracao")
_PASTA_ALEMBIC = RAIZ_PROJETO / "backend" / "alembic"


class BackupInvalido(Exception):
    pass


@dataclass(frozen=True)
class InfoBackup:
    nome: str
    tipo: str
    tamanho: int
    criado_em: datetime


def pasta_backups(banco: Path) -> Path:
    return banco.parent / "backups"


def _alembic(url: str | None = None) -> Config:
    # Sem o .ini: o env.py chamaria fileConfig e desligaria os loggers do app em execução.
    cfg = Config()
    cfg.set_main_option("script_location", str(_PASTA_ALEMBIC))
    if url:
        cfg.attributes["url"] = url
    return cfg


def revisoes_conhecidas() -> set[str]:
    return {r.revision for r in ScriptDirectory.from_config(_alembic()).walk_revisions()}


def revisao_atual() -> str | None:
    return ScriptDirectory.from_config(_alembic()).get_current_head()


def _tipo(nome: str) -> str | None:
    if not (nome.startswith(PREFIXO) and nome.endswith(".db")):
        return None
    sufixo = nome.removeprefix(PREFIXO).removesuffix(".db")
    return next((t for t in TIPOS if sufixo.endswith("-" + t)), None)


def _copiar(origem: sqlite3.Connection, destino: Path) -> None:
    with closing(sqlite3.connect(destino)) as alvo:
        origem.backup(alvo)


def gerar(banco: Path, tipo: str = "manual", agora: datetime | None = None) -> Path:
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de backup inválido: {tipo}")
    if not banco.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {banco}")
    pasta = pasta_backups(banco)
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = (agora or datetime.now(FUSO)).strftime("%Y%m%d-%H%M%S")
    destino = pasta / f"{PREFIXO}{carimbo}-{tipo}.db"
    contador = 1
    while destino.exists():
        contador += 1
        destino = pasta / f"{PREFIXO}{carimbo}-{contador}-{tipo}.db"
    temporario = destino.with_suffix(".parcial")
    temporario.unlink(missing_ok=True)
    try:
        with closing(sqlite3.connect(f"{banco.as_uri()}?mode=ro", uri=True)) as fonte:
            _copiar(fonte, temporario)
        temporario.rename(destino)
    finally:
        temporario.unlink(missing_ok=True)
    log.info("Backup %s gerado em %s", tipo, destino)
    return destino


def listar(banco: Path) -> list[InfoBackup]:
    pasta = pasta_backups(banco)
    if not pasta.is_dir():
        return []
    itens = []
    for arquivo in pasta.iterdir():
        tipo = _tipo(arquivo.name)
        if tipo and arquivo.is_file():
            estado = arquivo.stat()
            itens.append(InfoBackup(arquivo.name, tipo, estado.st_size, datetime.fromtimestamp(estado.st_mtime, FUSO)))
    return sorted(itens, key=lambda i: i.criado_em, reverse=True)


def caminho(banco: Path, nome: str) -> Path:
    """Resolve o nome de um backup existente, sem permitir sair da pasta de backups."""
    pasta = pasta_backups(banco).resolve()
    arquivo = (pasta / nome).resolve()
    if _tipo(nome) is None or arquivo.parent != pasta or not arquivo.is_file():
        raise FileNotFoundError(nome)
    return arquivo


def excluir(banco: Path, nome: str) -> None:
    caminho(banco, nome).unlink()


def limpar_automaticos(banco: Path, manter: int = MANTER_AUTOMATICOS) -> int:
    return _limpar(banco, "automatico", manter)


def _limpar(banco: Path, tipo: str, manter: int, preservar: Path | None = None) -> int:
    """Apaga os backups mais antigos do tipo além dos `manter` mais recentes (nunca o `preservar`)."""
    excedentes = [i for i in listar(banco) if i.tipo == tipo][manter:]
    pasta = pasta_backups(banco)
    removidos = 0
    for item in excedentes:
        arquivo = pasta / item.nome
        if preservar is not None and arquivo.resolve() == preservar.resolve():
            continue
        arquivo.unlink(missing_ok=True)
        removidos += 1
    return removidos


def limpar_parciais(banco: Path) -> int:
    """Remove restos (`*.parcial`) de backups/envios interrompidos pelo encerramento do app."""
    pasta = pasta_backups(banco)
    if not pasta.is_dir():
        return 0
    removidos = 0
    for arquivo in pasta.glob("*.parcial"):
        if arquivo.is_file():
            arquivo.unlink(missing_ok=True)
            removidos += 1
    if removidos:
        log.info("%d arquivo(s) .parcial removido(s) de %s", removidos, pasta)
    return removidos


def automatico_recente(banco: Path, horas: int = 20) -> bool:
    limite = datetime.now(FUSO) - timedelta(hours=horas)
    return any(i.tipo == "automatico" and i.criado_em >= limite for i in listar(banco))


def gerar_automatico(banco: Path) -> Path:
    destino = gerar(banco, "automatico")
    limpar_automaticos(banco)
    return destino


def validar(arquivo: Path) -> str:
    """Confere se é um banco do InvestHub+ íntegro e de versão conhecida; devolve a revisão do Alembic."""
    with arquivo.open("rb") as f:
        if f.read(len(CABECALHO_SQLITE)) != CABECALHO_SQLITE:
            raise BackupInvalido("O arquivo não é um banco SQLite.")
    try:
        with closing(sqlite3.connect(f"{arquivo.as_uri()}?mode=ro", uri=True)) as con:
            integridade = con.execute("PRAGMA integrity_check").fetchone()[0]
            if integridade != "ok":
                raise BackupInvalido(f"Banco corrompido: {integridade}")
            tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            if not {"alembic_version", "investidor", "ativo", "operacao"} <= tabelas:
                raise BackupInvalido("O arquivo não é um backup do InvestHub+.")
            linha = con.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.DatabaseError as erro:
        raise BackupInvalido(f"Não foi possível ler o banco: {erro}") from erro
    if not linha or linha[0] not in revisoes_conhecidas():
        raise BackupInvalido("O backup é de uma versão do app desconhecida (mais nova ou de outro sistema).")
    return linha[0]


def restaurar(arquivo: Path, banco: Path) -> tuple[Path, str]:
    """Substitui o conteúdo do banco pelo backup; devolve a cópia de segurança e a revisão restaurada.

    Quem chama deve garantir que nenhuma tarefa em segundo plano esteja gravando e descartar as conexões
    abertas (engine.dispose) depois.
    """
    revisao = validar(arquivo)
    seguranca = gerar(banco, "antes-restauracao")
    with ExitStack() as pilha:
        fonte = pilha.enter_context(closing(sqlite3.connect(f"{arquivo.as_uri()}?mode=ro", uri=True)))
        alvo = pilha.enter_context(closing(sqlite3.connect(banco, timeout=30)))
        fonte.backup(alvo)
    if revisao != revisao_atual():
        command.upgrade(_alembic(f"sqlite:///{banco.as_posix()}"), "head")
    _limpar(banco, "antes-restauracao", MANTER_ANTES_RESTAURACAO, preservar=arquivo)
    log.info("Banco restaurado a partir de %s (revisão %s); cópia anterior em %s", arquivo.name, revisao, seguranca)
    return seguranca, revisao
