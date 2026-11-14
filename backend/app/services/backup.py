"""Backup e restauração do banco SQLite local.

Cópias usam a API de backup do SQLite (consistente mesmo com o app gravando) e só são aceitas após
`PRAGMA integrity_check`. A restauração valida o arquivo, guarda uma cópia do banco atual e substitui o conteúdo
pela mesma API, sem trocar o arquivo aberto; se a migração do backup falhar, o conteúdo anterior volta.
"""

import logging
import re
import shutil
import sqlite3
from contextlib import ExitStack, closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from alembic import command

from ..config import RAIZ_PROJETO, settings

log = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")
CABECALHO_SQLITE = b"SQLite format 3\x00"
TAMANHO_MAXIMO = 200 * 1024 * 1024
MANTER_AUTOMATICOS = 10
# Cópias feitas a cada restauração; backups manuais nunca são apagados automaticamente.
MANTER_ANTES_RESTAURACAO = 10
PREFIXO = "investhub-"
TIPOS = ("manual", "automatico", "antes-restauracao")
# Motivo opcional no nome (ex.: investhub-…-antes-migracao-manual.db); o tipo continua sendo o sufixo.
_MOTIVO = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_PASTA_ALEMBIC = RAIZ_PROJETO / "backend" / "alembic"


class BackupInvalido(Exception):
    pass


class RestauracaoIncompleta(Exception):
    """A migração do backup falhou e o conteúdo anterior não pôde ser devolvido automaticamente."""


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


def migracoes_pendentes(banco: Path) -> bool:
    """True se a revisão gravada no banco difere da head das migrações do app."""
    engine = create_engine("sqlite://", creator=lambda: sqlite3.connect(f"{banco.as_uri()}?mode=ro", uri=True))
    try:
        with engine.connect() as con:
            atuais = set(MigrationContext.configure(con).get_current_heads())
    finally:
        engine.dispose()
    return atuais != set(ScriptDirectory.from_config(_alembic()).get_heads())


def pasta_copia() -> Path | None:
    valor = settings.backup_copia_dir.strip()
    return Path(valor).expanduser() if valor else None


def _tipo(nome: str) -> str | None:
    if not (nome.startswith(PREFIXO) and nome.endswith(".db")):
        return None
    sufixo = nome.removeprefix(PREFIXO).removesuffix(".db")
    return next((t for t in TIPOS if sufixo.endswith("-" + t)), None)


def _copiar(origem: sqlite3.Connection, destino: Path) -> None:
    with closing(sqlite3.connect(destino)) as alvo:
        origem.backup(alvo)


def verificar_integridade(arquivo: Path) -> None:
    """Exige `PRAGMA integrity_check = ok`; backup que não passa não pode ser contado como cópia válida."""
    try:
        with closing(sqlite3.connect(f"{arquivo.as_uri()}?mode=ro", uri=True)) as con:
            con.execute("PRAGMA trusted_schema = OFF")
            resultado = con.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.DatabaseError as erro:
        raise BackupInvalido(f"Backup reprovado na verificação de integridade: {erro}") from erro
    if resultado != "ok":
        raise BackupInvalido(f"Backup reprovado na verificação de integridade: {resultado}")


def _copiar_para_pasta_secundaria(arquivo: Path, avisos: list[str] | None) -> None:
    """Falha aqui só gera aviso: o backup principal já está salvo e verificado."""
    pasta = pasta_copia()
    if pasta is None:
        return
    temporario = pasta / (arquivo.name + ".parcial")
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(arquivo, temporario)
        verificar_integridade(temporario)
        temporario.replace(pasta / arquivo.name)
    except (OSError, BackupInvalido) as erro:
        mensagem = f"Backup salvo, mas a cópia para a pasta secundária {pasta} falhou: {erro}"
        log.warning(mensagem)
        if avisos is not None:
            avisos.append(mensagem)
    finally:
        try:
            temporario.unlink(missing_ok=True)
        except OSError:
            pass


def gerar(
    banco: Path,
    tipo: str = "manual",
    agora: datetime | None = None,
    motivo: str | None = None,
    avisos: list[str] | None = None,
) -> Path:
    """Gera e verifica um backup; `avisos` recebe falhas não fatais (cópia para a pasta secundária)."""
    if tipo not in TIPOS:
        raise ValueError(f"Tipo de backup inválido: {tipo}")
    if motivo is not None and not _MOTIVO.fullmatch(motivo):
        raise ValueError(f"Motivo de backup inválido: {motivo}")
    if not banco.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {banco}")
    pasta = pasta_backups(banco)
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = (agora or datetime.now(FUSO)).strftime("%Y%m%d-%H%M%S")
    sufixo = f"{motivo}-{tipo}" if motivo else tipo
    destino = pasta / f"{PREFIXO}{carimbo}-{sufixo}.db"
    contador = 1
    while destino.exists():
        contador += 1
        destino = pasta / f"{PREFIXO}{carimbo}-{contador}-{sufixo}.db"
    temporario = destino.with_suffix(".parcial")
    temporario.unlink(missing_ok=True)
    try:
        with closing(sqlite3.connect(f"{banco.as_uri()}?mode=ro", uri=True)) as fonte:
            _copiar(fonte, temporario)
        verificar_integridade(temporario)
        temporario.rename(destino)
    finally:
        temporario.unlink(missing_ok=True)
    log.info("Backup %s gerado e verificado em %s", tipo, destino)
    _copiar_para_pasta_secundaria(destino, avisos)
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
    secundaria = pasta_copia()
    removidos = 0
    for item in excedentes:
        arquivo = pasta / item.nome
        if preservar is not None and arquivo.resolve() == preservar.resolve():
            continue
        arquivo.unlink(missing_ok=True)
        removidos += 1
        if secundaria is not None:
            # A pasta secundária espelha a retenção; falha nela não interrompe a limpeza principal.
            try:
                (secundaria / item.nome).unlink(missing_ok=True)
            except OSError as erro:
                log.warning("Não foi possível remover %s da pasta secundária: %s", item.nome, erro)
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
    # Só limpa depois que o backup novo passou na verificação (gerar levanta se falhar).
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
            # Arquivo não confiável: funções em views/triggers dele não podem rodar durante a validação.
            con.execute("PRAGMA trusted_schema = OFF")
            integridade = con.execute("PRAGMA integrity_check").fetchone()[0]
            if integridade != "ok":
                raise BackupInvalido(f"Banco corrompido: {integridade}")
            tabelas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            if not {"alembic_version", "investidor", "ativo", "operacao"} <= tabelas:
                raise BackupInvalido("O arquivo não é um backup do InvestHub+.")
            # O app não cria triggers nem views: num backup, só serviriam para alterar dados às escondidas.
            if con.execute("SELECT 1 FROM sqlite_master WHERE type IN ('trigger', 'view') LIMIT 1").fetchone():
                raise BackupInvalido("O backup contém triggers ou views que o InvestHub+ não cria.")
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
    _sobrescrever(arquivo, banco)
    if revisao != revisao_atual():
        try:
            command.upgrade(_alembic(f"sqlite:///{banco.as_posix()}"), "head")
        except Exception as erro:
            log.exception("Falha ao migrar o backup %s; devolvendo o conteúdo anterior", arquivo.name)
            try:
                _sobrescrever(seguranca, banco)
            except Exception as erro_volta:
                raise RestauracaoIncompleta(
                    f"Não foi possível atualizar o backup para a versão atual do app ({erro}) nem desfazer a "
                    f"restauração automaticamente ({erro_volta}). Restaure a cópia {seguranca.name}."
                ) from erro_volta
            raise BackupInvalido(
                f"Não foi possível atualizar o backup para a versão atual do app ({erro}). "
                "A restauração foi desfeita e o banco anterior foi mantido."
            ) from erro
    _limpar(banco, "antes-restauracao", MANTER_ANTES_RESTAURACAO, preservar=arquivo)
    log.info("Banco restaurado a partir de %s (revisão %s); cópia anterior em %s", arquivo.name, revisao, seguranca)
    return seguranca, revisao


def _sobrescrever(origem: Path, banco: Path) -> None:
    with ExitStack() as pilha:
        fonte = pilha.enter_context(closing(sqlite3.connect(f"{origem.as_uri()}?mode=ro", uri=True)))
        alvo = pilha.enter_context(closing(sqlite3.connect(banco, timeout=30)))
        fonte.backup(alvo)
