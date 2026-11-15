"""Backup verificado antes de `alembic upgrade head` no iniciar.bat (MIG-004 / BKP-008)."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from alembic import command
from app.config import settings
from app.services import backup
from scripts import backup_antes_migrar


@pytest.fixture
def banco(tmp_path, monkeypatch) -> Path:
    destino = tmp_path / "dados" / "investhub.db"
    destino.parent.mkdir()
    monkeypatch.setattr(settings, "db_path", destino)
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "backup_copia_dir", "", raising=False)
    return destino


def _migrar(banco: Path, revisao: str) -> None:
    command.upgrade(backup._alembic(f"sqlite:///{banco.as_posix()}"), revisao)


def test_gera_backup_verificado_quando_ha_migracao_pendente(banco, capsys):
    _migrar(banco, "848b5d144b5f")
    with closing(sqlite3.connect(banco)) as con:
        con.execute("INSERT INTO investidor (nome, cor, ativo) VALUES ('Ana', '#000000', 1)")
        con.commit()

    assert backup_antes_migrar.main() == 0

    [item] = backup.listar(banco)
    assert item.tipo == "manual" and "-antes-migracao-" in item.nome
    copia = backup.pasta_backups(banco) / item.nome
    with closing(sqlite3.connect(copia)) as con:
        assert con.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "848b5d144b5f"
        assert con.execute("SELECT nome FROM investidor").fetchall() == [("Ana",)]
    assert item.nome in capsys.readouterr().out


def test_nao_gera_backup_sem_migracao_pendente(banco):
    _migrar(banco, "head")
    assert backup_antes_migrar.main() == 0
    assert backup.listar(banco) == []


def test_banco_inexistente_e_ignorado(banco, capsys):
    assert backup_antes_migrar.main() == 0
    assert not banco.exists()
    assert "ainda não existe" in capsys.readouterr().out


def test_postgresql_e_ignorado(banco, monkeypatch, capsys):
    monkeypatch.setattr(settings, "database_url", "postgresql://u:p@localhost/db")
    assert backup_antes_migrar.main() == 0
    assert "servidor" in capsys.readouterr().out


def test_falha_no_backup_aborta_inicializacao(banco, monkeypatch, capsys):
    _migrar(banco, "848b5d144b5f")

    def falhar(*_args, **_kwargs):
        raise backup.BackupInvalido("Backup corrompido: teste")

    monkeypatch.setattr(backup, "gerar", falhar)
    assert backup_antes_migrar.main() == 1
    assert "cancelada" in capsys.readouterr().err
    assert backup.listar(banco) == []
