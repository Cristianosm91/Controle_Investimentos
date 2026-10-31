"""Regressão das correções da auditoria de QA (qa-report/06-falhas-encontradas.md, QA-002 a QA-006)."""

import logging
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from alembic import command
from app.config import settings
from app.services import backup, jobs

MALICIOSO = "https://site-malicioso.example"


# ---------- QA-002: Host e Origin ----------

def test_escrita_de_origem_externa_e_recusada(cliente):
    r = cliente.post("/api/investidores", json={"nome": "CSRF"}, headers={"Origin": MALICIOSO})
    assert r.status_code == 403
    assert cliente.get("/api/investidores").json() == []


@pytest.mark.parametrize("cabecalhos", [
    {"Origin": "null"},
    {"Sec-Fetch-Site": "cross-site"},
    {"Origin": "http://127.0.0.1.malicioso.example"},
])
def test_escrita_sem_origem_confiavel_e_recusada(cliente, cabecalhos):
    assert cliente.post("/api/investidores", json={"nome": "X"}, headers=cabecalhos).status_code == 403


def test_corpo_bruto_e_rotas_sem_corpo_de_origem_externa_sao_recusados(cliente):
    externo = {"Origin": MALICIOSO, "Content-Type": "text/plain"}
    assert cliente.post("/api/extratos/b3/previa?investidor_id=1", content=b"x", headers=externo).status_code == 403
    assert cliente.post("/api/lotes/1/desfazer", headers=externo).status_code == 403
    assert cliente.post("/api/backups/restaurar-arquivo", content=b"x", headers=externo).status_code == 403


@pytest.mark.parametrize("origem", [
    "http://127.0.0.1:8000", "http://localhost:5173", "http://127.0.0.1:8010",
])
def test_escrita_do_proprio_app_continua_funcionando(cliente, origem):
    r = cliente.post("/api/investidores", json={"nome": f"Ana {origem[-4:]}"}, headers={"Origin": origem})
    assert r.status_code == 201


def test_escrita_same_origin_sem_cabecalho_origin_e_aceita(cliente):
    r = cliente.post("/api/investidores", json={"nome": "Bia"}, headers={"Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 201


def test_leitura_de_origem_externa_nao_e_bloqueada(cliente):
    assert cliente.get("/api/investidores", headers={"Origin": MALICIOSO}).status_code == 200


def test_host_desconhecido_e_recusado(cliente):
    assert cliente.get("/api/saude", headers={"Host": "rebind.attacker.example"}).status_code == 400
    assert cliente.get("/api/saude", headers={"Host": "127.0.0.1:8000"}).status_code == 200


# ---------- QA-003: carga histórica disparada duas vezes ----------

class _ThreadAdiada:
    """Substitui threading.Thread: guarda o alvo para rodar depois, reproduzindo a janela da corrida."""

    criadas: list["_ThreadAdiada"] = []

    def __init__(self, target, args=(), **_kwargs):
        self.alvo, self.args = target, args
        _ThreadAdiada.criadas.append(self)

    def start(self):
        pass

    def rodar(self):
        self.alvo(*self.args)


@pytest.fixture
def carga_falsa(monkeypatch):
    executadas: list[str] = []
    for nome in jobs.CARGA_HISTORICA:
        tarefa = jobs.TAREFAS[nome]
        monkeypatch.setattr(tarefa, "funcao", lambda _s, n=nome: executadas.append(n))
        monkeypatch.setattr(tarefa, "resumir", lambda _r: "ok")
    _ThreadAdiada.criadas = []
    monkeypatch.setattr(jobs.threading, "Thread", _ThreadAdiada)
    return executadas


def test_carga_historica_nao_dispara_duas_vezes(carga_falsa):
    jobs.disparar_carga_historica()
    with pytest.raises(jobs.TarefaOcupada):
        jobs.disparar_carga_historica()
    assert len(_ThreadAdiada.criadas) == 1

    _ThreadAdiada.criadas[0].rodar()
    assert carga_falsa == list(jobs.CARGA_HISTORICA)

    jobs.disparar_carga_historica()  # trava liberada ao terminar
    assert len(_ThreadAdiada.criadas) == 2
    _ThreadAdiada.criadas[1].rodar()


def test_carga_historica_libera_trava_quando_tarefa_falha(carga_falsa, monkeypatch):
    def falhar(_s):
        raise RuntimeError("fonte fora do ar")

    monkeypatch.setattr(jobs.TAREFAS["cotahist_historico"], "funcao", falhar)
    jobs.disparar_carga_historica()
    _ThreadAdiada.criadas[0].rodar()
    jobs.disparar_carga_historica()
    _ThreadAdiada.criadas[1].rodar()


# ---------- QA-004: comportamento das rotas async preservado ----------

def test_rotas_de_upload_mantem_404_para_investidor_inexistente(cliente):
    cabecalho = {"content-type": "application/octet-stream"}
    for rota in ("/api/extratos/b3/previa", "/api/aluguel/extrato/previa"):
        assert cliente.post(f"{rota}?investidor_id=999", content=b"x", headers=cabecalho).status_code == 404


# ---------- QA-005 e QA-006: backups ----------

def _banco(caminho: Path) -> Path:
    command.upgrade(backup._alembic(f"sqlite:///{caminho.as_posix()}"), "head")
    with closing(sqlite3.connect(caminho)) as con:
        con.execute("INSERT INTO investidor (nome, cor, ativo) VALUES ('Ana', '#000000', 1)")
        con.commit()
    return caminho


@pytest.fixture
def banco(tmp_path, monkeypatch) -> Path:
    (tmp_path / "dados").mkdir()
    destino = _banco(tmp_path / "dados" / "investhub.db")
    monkeypatch.setattr(settings, "db_path", destino)
    monkeypatch.setattr(settings, "database_url", None)
    return destino


def _tipos(banco: Path) -> list[str]:
    return [i.tipo for i in backup.listar(banco)]


def test_copias_antes_de_restaurar_sao_limitadas(banco):
    origem = backup.gerar(banco, "manual")
    for _ in range(backup.MANTER_ANTES_RESTAURACAO + 2):
        backup.restaurar(origem, banco)
    assert _tipos(banco).count("antes-restauracao") == backup.MANTER_ANTES_RESTAURACAO
    assert _tipos(banco).count("manual") == 1
    assert origem.is_file()


def test_restaurar_da_copia_mais_antiga_nao_apaga_a_origem(banco):
    copias = []
    for i in range(backup.MANTER_ANTES_RESTAURACAO):
        copia = backup.gerar(banco, "antes-restauracao")
        os.utime(copia, (1_000_000 + i, 1_000_000 + i))
        copias.append(copia)
    mais_antiga = copias[0]
    backup.restaurar(mais_antiga, banco)
    assert mais_antiga.is_file()


def test_parar_registra_tarefas_interrompidas(monkeypatch, caplog):
    monkeypatch.setattr(jobs.TAREFAS["cotahist_historico"], "em_execucao", True)
    with caplog.at_level(logging.WARNING, logger=jobs.log.name):
        jobs.parar()
    assert "cotahist_historico" in caplog.text


def test_limpar_parciais_remove_restos_de_execucao_interrompida(banco):
    valido = backup.gerar(banco, "manual")
    pasta = backup.pasta_backups(banco)
    restos = [pasta / "envio-abc123.parcial", pasta / "investhub-20260101-000000-manual.parcial"]
    for resto in restos:
        resto.write_bytes(b"x")
    assert backup.limpar_parciais(banco) == 2
    assert not any(r.exists() for r in restos)
    assert valido.is_file()
