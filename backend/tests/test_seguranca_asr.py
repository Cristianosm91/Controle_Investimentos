"""Regressão das correções da revisão de segurança (security-report/05-achados.md, ASR-001 a ASR-007)."""

import io
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path

import pytest
from openpyxl import Workbook

from alembic import command
from app.config import settings
from app.seguranca import CABECALHOS_SEGURANCA, tamanho_descompactado_excedido
from app.services import aluguel, backup, extrato_b3

BINARIO = {"content-type": "application/octet-stream"}


def _investidor(cliente) -> int:
    return cliente.post("/api/investidores", json={"nome": "Ana"}).json()["id"]


def _xlsx(linhas: int) -> bytes:
    livro = Workbook()
    planilha = livro.active
    for i in range(linhas):
        planilha.append([f"linha {i}", i])
    saida = io.BytesIO()
    livro.save(saida)
    return saida.getvalue()


# ---------- ASR-001: uploads só como application/octet-stream ----------

@pytest.mark.parametrize("rota", ["/api/extratos/b3/previa", "/api/aluguel/extrato/previa"])
@pytest.mark.parametrize("tipo", [None, "text/plain", "application/x-www-form-urlencoded", "multipart/form-data"])
def test_upload_sem_tipo_binario_e_recusado(cliente, rota, tipo):
    inv = _investidor(cliente)
    cabecalhos = {"content-type": tipo} if tipo else {}
    r = cliente.post(rota, params={"investidor_id": inv}, content=b"x", headers=cabecalhos)
    assert r.status_code == 415


def test_upload_binario_continua_aceito(cliente):
    inv = _investidor(cliente)
    r = cliente.post(
        "/api/extratos/b3/previa", params={"investidor_id": inv}, content=b"x",
        headers={"content-type": "application/octet-stream; charset=binary"},
    )
    assert r.status_code == 422  # passou do tipo; recusado só por não ser uma planilha


@pytest.fixture
def banco(tmp_path, monkeypatch) -> Path:
    (tmp_path / "dados").mkdir()
    destino = tmp_path / "dados" / "investhub.db"
    command.upgrade(backup._alembic(f"sqlite:///{destino.as_posix()}"), "head")
    monkeypatch.setattr(settings, "db_path", destino)
    monkeypatch.setattr(settings, "database_url", None)
    return destino


def test_restaurar_arquivo_exige_tipo_binario(cliente, banco):
    r = cliente.post("/api/backups/restaurar-arquivo", content=b"x", headers={"content-type": "text/plain"})
    assert r.status_code == 415
    assert not list(backup.pasta_backups(banco).glob("*.parcial"))


# ---------- ASR-007: cabeçalhos de segurança ----------

@pytest.mark.parametrize("requisicao", [
    lambda c: c.get("/api/saude"),
    lambda c: c.get("/api/investidores"),
    lambda c: c.post("/api/investidores", json={"nome": "X"}, headers={"Origin": "https://malicioso.example"}),
    lambda c: c.get("/api/saude", headers={"Host": "rebind.attacker.example"}),
])
def test_respostas_trazem_cabecalhos_de_seguranca(cliente, requisicao):
    r = requisicao(cliente)
    for nome, valor in CABECALHOS_SEGURANCA.items():
        assert r.headers.get(nome) == valor
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


# ---------- ASR-005: bomba de descompressão e excesso de linhas ----------

def test_tamanho_descompactado_excedido_soma_as_entradas():
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("a.xml", b"0" * 4000)
        z.writestr("b.xml", b"0" * 4000)
    conteudo = saida.getvalue()
    assert len(conteudo) < 1000
    assert tamanho_descompactado_excedido(conteudo, limite=7999)
    assert not tamanho_descompactado_excedido(conteudo, limite=8000)


@pytest.mark.parametrize("modulo, leitor", [(extrato_b3, "_ler_planilha"), (aluguel, "_ler_tabela")])
def test_planilha_que_expande_demais_e_recusada(monkeypatch, modulo, leitor):
    monkeypatch.setattr(modulo, "tamanho_descompactado_excedido", lambda _c: True)
    with pytest.raises(modulo.ExtratoInvalido, match="descompactada"):
        getattr(modulo, leitor)(_xlsx(2))


@pytest.mark.parametrize("modulo, leitor", [(extrato_b3, "_ler_planilha"), (aluguel, "_ler_tabela")])
def test_planilha_com_linhas_demais_e_recusada(monkeypatch, modulo, leitor):
    monkeypatch.setattr(modulo, "LINHAS_MAXIMAS", 3)
    assert len(getattr(modulo, leitor)(_xlsx(3))) == 3
    with pytest.raises(modulo.ExtratoInvalido, match="mais de 3 linhas"):
        getattr(modulo, leitor)(_xlsx(4))


@pytest.mark.parametrize("modulo, leitor", [(extrato_b3, "_ler_planilha"), (aluguel, "_ler_tabela")])
def test_zip_corrompido_vira_erro_de_validacao(monkeypatch, modulo, leitor):
    def corrompido(_c):
        raise zipfile.BadZipFile("diretório central inválido")

    monkeypatch.setattr(modulo, "tamanho_descompactado_excedido", corrompido)
    with pytest.raises(modulo.ExtratoInvalido, match="corrompida"):
        getattr(modulo, leitor)(_xlsx(1))


# ---------- ASR-006: backup com triggers/views ----------

@pytest.mark.parametrize("ddl", [
    "CREATE TRIGGER t AFTER INSERT ON operacao BEGIN DELETE FROM investidor; END",
    "CREATE VIEW v AS SELECT * FROM investidor",
])
def test_backup_com_trigger_ou_view_e_recusado(banco, ddl):
    with closing(sqlite3.connect(banco)) as con:
        con.execute(ddl)
        con.commit()
    with pytest.raises(backup.BackupInvalido, match="triggers ou views"):
        backup.validar(banco)


def test_backup_legitimo_continua_valido(banco):
    assert backup.validar(banco) == backup.revisao_atual()
