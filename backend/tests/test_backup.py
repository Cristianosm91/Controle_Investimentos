import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from alembic import command
from app.config import settings
from app.services import backup, jobs


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
    return destino


def test_gerar_listar_e_limpar_automaticos(banco):
    manual = backup.gerar(banco, "manual")
    assert manual.parent == backup.pasta_backups(banco)
    assert _nomes(manual) == ["Ana"]
    for _ in range(3):
        backup.gerar(banco, "automatico")
    assert backup.limpar_automaticos(banco, manter=1) == 2
    tipos = [i.tipo for i in backup.listar(banco)]
    assert sorted(tipos) == ["automatico", "manual"]
    assert backup.automatico_recente(banco)
    assert not list(backup.pasta_backups(banco).glob("*.parcial"))


def test_caminho_nao_sai_da_pasta(banco):
    backup.gerar(banco)
    for nome in ("../investhub.db", "..\\investhub.db", "outro.db", "investhub-x-manual.txt"):
        with pytest.raises(FileNotFoundError):
            backup.caminho(banco, nome)


def test_validar_rejeita_arquivos_invalidos(tmp_path):
    texto = tmp_path / "texto.db"
    texto.write_text("não sou banco")
    with pytest.raises(backup.BackupInvalido, match="SQLite"):
        backup.validar(texto)

    alheio = tmp_path / "alheio.db"
    with closing(sqlite3.connect(alheio)) as con:
        con.execute("CREATE TABLE x (a)")
    with pytest.raises(backup.BackupInvalido, match="InvestHub"):
        backup.validar(alheio)


def test_validar_rejeita_versao_desconhecida(tmp_path, modelo):
    futuro = tmp_path / "futuro.db"
    futuro.write_bytes(modelo.read_bytes())
    with closing(sqlite3.connect(futuro)) as con:
        con.execute("UPDATE alembic_version SET version_num = 'ffffffffffff'")
        con.commit()
    with pytest.raises(backup.BackupInvalido, match="versão"):
        backup.validar(futuro)


def test_restaurar_guarda_copia_do_atual(banco, tmp_path):
    antigo = backup.gerar(banco)
    with closing(sqlite3.connect(banco)) as con:
        con.execute("INSERT INTO investidor (nome, cor, ativo) VALUES ('Bia', '#000000', 1)")
        con.commit()
    seguranca, revisao = backup.restaurar(antigo, banco)
    assert revisao == backup.revisao_atual()
    assert _nomes(banco) == ["Ana"]
    assert _nomes(seguranca) == ["Ana", "Bia"]


def test_restaurar_migra_backup_antigo(banco, tmp_path):
    antigo = tmp_path / "antigo.db"
    command.upgrade(backup._alembic(f"sqlite:///{antigo.as_posix()}"), "848b5d144b5f")
    with closing(sqlite3.connect(antigo)) as con:
        con.execute("INSERT INTO investidor (nome, cor, ativo) VALUES ('Caio', '#000000', 1)")
        con.commit()
    backup.restaurar(antigo, banco)
    with closing(sqlite3.connect(banco)) as con:
        assert con.execute("SELECT version_num FROM alembic_version").fetchone()[0] == backup.revisao_atual()
    assert _nomes(banco) == ["Caio"]


def test_api_backup_completo(cliente, banco):
    assert cliente.get("/api/backups").json()["itens"] == []
    criado = cliente.post("/api/backups").json()
    assert criado["tipo"] == "manual"

    baixado = cliente.get(f"/api/backups/{criado['nome']}")
    assert baixado.status_code == 200 and baixado.content.startswith(backup.CABECALHO_SQLITE)
    assert cliente.get("/api/backups/..%2Finvesthub.db").status_code == 404

    with closing(sqlite3.connect(banco)) as con:
        con.execute("INSERT INTO investidor (nome, cor, ativo) VALUES ('Bia', '#000000', 1)")
        con.commit()
    r = cliente.post(f"/api/backups/{criado['nome']}/restaurar")
    assert r.status_code == 200, r.text
    assert _nomes(banco) == ["Ana"]
    assert r.json()["copia_anterior"].endswith("-antes-restauracao.db")

    r = cliente.post(
        "/api/backups/restaurar-arquivo", content=b"lixo",
        headers={"content-type": "application/octet-stream", "x-nome-arquivo": "lixo.db"},
    )
    assert r.status_code == 422
    r = cliente.post(
        "/api/backups/restaurar-arquivo", content=baixado.content,
        headers={"content-type": "application/octet-stream", "x-nome-arquivo": "c%C3%B3pia.db"},
    )
    assert r.status_code == 200 and r.json()["restaurado"] == "cópia.db"
    assert not list(backup.pasta_backups(banco).glob("*.parcial"))

    assert cliente.delete(f"/api/backups/{criado['nome']}").status_code == 204
    assert cliente.delete(f"/api/backups/{criado['nome']}").status_code == 404


def test_api_bloqueia_restauracao_com_tarefa_em_execucao(cliente, banco):
    nome = backup.gerar(banco).name
    trava = jobs.TAREFAS["cotacoes"].trava
    trava.acquire()
    try:
        r = cliente.post(f"/api/backups/{nome}/restaurar")
    finally:
        trava.release()
    assert r.status_code == 409
    assert all(t.trava.acquire(blocking=False) for t in jobs.TAREFAS.values())
    for t in jobs.TAREFAS.values():
        t.trava.release()


def test_api_sem_sqlite(cliente, monkeypatch):
    monkeypatch.setattr(settings, "database_url", "postgresql://x")
    assert cliente.get("/api/backups").json()["disponivel"] is False
    assert cliente.post("/api/backups").status_code == 409
