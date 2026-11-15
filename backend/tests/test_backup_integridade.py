"""Backups verificados após a cópia, rollback de restauração e pasta secundária (BKP-001/002/003/004)."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from alembic import command
from app import config
from app.config import Settings, settings
from app.services import backup


def _banco(caminho: Path, nome: str = "Ana") -> Path:
    command.upgrade(backup._alembic(f"sqlite:///{caminho.as_posix()}"), "head")
    with closing(sqlite3.connect(caminho)) as con:
        con.execute("INSERT INTO investidor (nome, cor, ativo) VALUES (?, '#000000', 1)", (nome,))
        con.commit()
    return caminho


def _nomes(caminho: Path) -> list[str]:
    with closing(sqlite3.connect(caminho)) as con:
        return [r[0] for r in con.execute("SELECT nome FROM investidor ORDER BY id")]


@pytest.fixture(scope="module")
def modelo(tmp_path_factory) -> Path:
    return _banco(tmp_path_factory.mktemp("modelo") / "modelo.db")


@pytest.fixture
def banco(tmp_path, modelo, monkeypatch) -> Path:
    destino = tmp_path / "dados" / "investhub.db"
    destino.parent.mkdir()
    destino.write_bytes(modelo.read_bytes())
    monkeypatch.setattr(settings, "db_path", destino)
    monkeypatch.setattr(settings, "database_url", None)
    monkeypatch.setattr(settings, "backup_copia_dir", "", raising=False)
    return destino


def _copiar_corrompendo(original):
    def copiar(origem, destino):
        original(origem, destino)
        with open(destino, "r+b") as f:
            f.seek(4096)
            f.write(b"\xff" * 4096 * 4)

    return copiar


def _arquivos(pasta: Path) -> list[str]:
    return sorted(p.name for p in pasta.iterdir()) if pasta.is_dir() else []


def test_gerar_rejeita_copia_corrompida_e_apaga_o_arquivo(banco, monkeypatch):
    monkeypatch.setattr(backup, "_copiar", _copiar_corrompendo(backup._copiar))
    with pytest.raises(backup.BackupInvalido):
        backup.gerar(banco, "manual")
    assert _arquivos(backup.pasta_backups(banco)) == []


def test_retencao_nao_apaga_ultimo_valido_por_causa_de_backup_invalido(banco, monkeypatch):
    valido = backup.gerar_automatico(banco)
    monkeypatch.setattr(backup, "_copiar", _copiar_corrompendo(backup._copiar))
    monkeypatch.setattr(backup, "MANTER_AUTOMATICOS", 1)
    with pytest.raises(backup.BackupInvalido):
        backup.gerar_automatico(banco)
    assert _arquivos(backup.pasta_backups(banco)) == [valido.name]
    backup.validar(valido)


def test_gerar_com_motivo_mantem_tipo_manual(banco):
    destino = backup.gerar(banco, "manual", motivo="antes-migracao")
    assert destino.name.endswith("-antes-migracao-manual.db")
    [item] = backup.listar(banco)
    assert (item.nome, item.tipo) == (destino.name, "manual")
    with pytest.raises(ValueError):
        backup.gerar(banco, "manual", motivo="../fora")


def test_restaurar_reverte_quando_migracao_falha(banco, tmp_path, monkeypatch):
    antigo = tmp_path / "antigo.db"
    command.upgrade(backup._alembic(f"sqlite:///{antigo.as_posix()}"), "848b5d144b5f")
    with closing(sqlite3.connect(antigo)) as con:
        con.execute("INSERT INTO investidor (nome, cor, ativo) VALUES ('Caio', '#000000', 1)")
        con.commit()

    def falhar(*_args, **_kwargs):
        raise RuntimeError("migração quebrada")

    monkeypatch.setattr(backup.command, "upgrade", falhar)
    with pytest.raises(backup.BackupInvalido, match="anterior foi mantido"):
        backup.restaurar(antigo, banco)
    assert _nomes(banco) == ["Ana"]
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("SELECT version_num FROM alembic_version").fetchone()[0] == backup.revisao_atual()
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_api_restauracao_com_migracao_falha_retorna_erro_claro(cliente, banco, tmp_path, monkeypatch):
    antigo = tmp_path / "antigo.db"
    command.upgrade(backup._alembic(f"sqlite:///{antigo.as_posix()}"), "848b5d144b5f")
    pasta = backup.pasta_backups(banco)
    pasta.mkdir(exist_ok=True)
    nome = "investhub-20200101-000000-manual.db"
    (pasta / nome).write_bytes(antigo.read_bytes())

    def falhar(*_args, **_kwargs):
        raise RuntimeError("migração quebrada")

    monkeypatch.setattr(backup.command, "upgrade", falhar)
    r = cliente.post(f"/api/backups/{nome}/restaurar")
    assert r.status_code == 422
    assert "anterior foi mantido" in r.json()["detail"]
    assert _nomes(banco) == ["Ana"]


def test_copia_secundaria_desligada_por_padrao(banco):
    assert Settings.model_fields["backup_copia_dir"].default == ""
    avisos: list[str] = []
    backup.gerar(banco, "manual", avisos=avisos)
    assert avisos == [] and backup.pasta_copia() is None


def test_copia_secundaria_aceita_prefixo_legado(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ARQUIVO_ENV", tmp_path / ".env")
    monkeypatch.setenv("CONTROLEINV_BACKUP_COPIA_DIR", r"D:\Copias")
    monkeypatch.setenv("INVESTHUB_BACKUP_COPIA_DIR", "")  # registra o estado original para o teardown restaurar
    monkeypatch.delenv("INVESTHUB_BACKUP_COPIA_DIR")
    config._aceitar_prefixo_legado()
    assert Settings(_env_file=None).backup_copia_dir == r"D:\Copias"


def test_copia_secundaria_verificada(banco, tmp_path, monkeypatch):
    secundaria = tmp_path / "copia"
    monkeypatch.setattr(settings, "backup_copia_dir", str(secundaria))
    avisos: list[str] = []
    destino = backup.gerar(banco, "manual", avisos=avisos)
    assert avisos == []
    assert _arquivos(secundaria) == [destino.name]
    assert _nomes(secundaria / destino.name) == ["Ana"]


def test_falha_na_copia_secundaria_nao_derruba_backup(banco, tmp_path, monkeypatch):
    bloqueio = tmp_path / "nao-e-pasta"
    bloqueio.write_text("arquivo no lugar da pasta")
    monkeypatch.setattr(settings, "backup_copia_dir", str(bloqueio))
    avisos: list[str] = []
    destino = backup.gerar(banco, "manual", avisos=avisos)
    assert destino.is_file()
    assert len(avisos) == 1 and "cópia" in avisos[0].lower()


def test_retencao_tambem_limpa_pasta_secundaria(banco, tmp_path, monkeypatch):
    secundaria = tmp_path / "copia"
    monkeypatch.setattr(settings, "backup_copia_dir", str(secundaria))
    for _ in range(3):
        backup.gerar(banco, "automatico")
    assert backup.limpar_automaticos(banco, manter=1) == 2
    assert _arquivos(secundaria) == _arquivos(backup.pasta_backups(banco))


def test_api_gerar_backup_informa_falha_na_copia(cliente, banco, tmp_path, monkeypatch):
    bloqueio = tmp_path / "nao-e-pasta"
    bloqueio.write_text("x")
    monkeypatch.setattr(settings, "backup_copia_dir", str(bloqueio))
    r = cliente.post("/api/backups")
    assert r.status_code == 201, r.text
    assert r.json()["tipo"] == "manual"
    assert "cópia" in r.json()["aviso_copia"].lower()


def test_api_gerar_backup_corrompido_retorna_erro(cliente, banco, monkeypatch):
    monkeypatch.setattr(backup, "_copiar", _copiar_corrompendo(backup._copiar))
    r = cliente.post("/api/backups")
    assert r.status_code == 500
    assert "integridade" in r.json()["detail"].lower()
    assert _arquivos(backup.pasta_backups(banco)) == []
