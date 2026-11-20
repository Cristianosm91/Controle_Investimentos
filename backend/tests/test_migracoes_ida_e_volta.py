"""Schema das migrações × modelos (MIG-005) e ida e volta upgrade/downgrade (MIG-006)."""

import inspect
import sqlite3
from contextlib import closing
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from alembic import command
from app import models  # noqa: F401  (registra as tabelas no metadata)
from app.config import RAIZ_PROJETO
from app.db import Base

IRREVERSIVEL = "Downgrade indisponível"


def _alembic(banco: Path) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(RAIZ_PROJETO / "backend" / "alembic"))
    cfg.attributes["url"] = f"sqlite:///{banco.as_posix()}"
    return cfg


def _schema(banco: Path) -> list[tuple]:
    """Tabelas e índices; linhas do CREATE ordenadas (a ordem das FKs recriadas pelo batch varia entre execuções)."""
    with closing(sqlite3.connect(banco)) as con:
        linhas = con.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
        return sorted(
            (tipo, nome, tabela, tuple(sorted(l.strip().rstrip(",").strip() for l in (sql or "").splitlines())))
            for tipo, nome, tabela, sql in linhas
        )


def test_migracoes_produzem_o_schema_dos_modelos(tmp_path):
    banco = tmp_path / "drift.db"
    command.upgrade(_alembic(banco), "head")
    engine = create_engine(f"sqlite:///{banco.as_posix()}")
    try:
        with engine.connect() as con:
            contexto = MigrationContext.configure(con, opts={"compare_type": True, "render_as_batch": True})
            diferencas = compare_metadata(contexto, Base.metadata)
    finally:
        engine.dispose()
    assert diferencas == [], "Modelos e migrações divergem; gere uma migração (alembic revision --autogenerate)."


def _ultima_irreversivel(script: ScriptDirectory):
    """Migração mais recente cujo downgrade é sempre bloqueado (evita perda de dados)."""
    for revisao in script.walk_revisions():  # da head para a base
        fonte = inspect.getsource(revisao.module.downgrade)
        if IRREVERSIVEL in fonte and "if count:" not in fonte:
            return revisao
    return None


def test_ida_e_volta_upgrade_downgrade_upgrade(tmp_path):
    script = ScriptDirectory.from_config(_alembic(tmp_path / "x.db"))
    irreversivel = _ultima_irreversivel(script)
    # Downgrade só é exercitado até a última migração irreversível; dali para cima o caminho é só de ida.
    alvo = "head" if irreversivel is None else irreversivel.down_revision
    assert isinstance(alvo, str), "Migração irreversível que é merge: ajuste o teste."

    referencia = tmp_path / "referencia.db"
    command.upgrade(_alembic(referencia), "head")

    banco = tmp_path / "ida-e-volta.db"
    cfg = _alembic(banco)
    command.upgrade(cfg, alvo)
    command.downgrade(cfg, "base")
    with closing(sqlite3.connect(banco)) as con:
        restantes = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert restantes <= {"alembic_version"}
        assert con.execute("SELECT count(*) FROM alembic_version").fetchone()[0] == 0
    command.upgrade(cfg, "head")

    assert _schema(banco) == _schema(referencia)
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
