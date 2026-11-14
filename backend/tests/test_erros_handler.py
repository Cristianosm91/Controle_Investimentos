"""OBS-004: erro inesperado devolve JSON com erro_id; HTTPException e validação ficam como estavam."""

import logging

import pytest
from fastapi.testclient import TestClient

from app.api import atualizacoes
from app.main import app


@pytest.fixture
def cliente_500(cliente, monkeypatch):
    def falhar(_nome):
        raise RuntimeError("[SQL: SELECT segredo FROM tabela] C:\\Users\\fulano\\x")

    monkeypatch.setattr(atualizacoes.jobs, "proxima_execucao", falhar)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_erro_inesperado_devolve_json_com_erro_id(cliente_500, caplog):
    with caplog.at_level(logging.ERROR):
        resposta = cliente_500.get("/api/atualizacoes")
    assert resposta.status_code == 500
    corpo = resposta.json()
    assert set(corpo) == {"detail", "erro_id"}
    assert corpo["erro_id"] == resposta.headers["X-Request-ID"]
    assert "segredo" not in resposta.text and "fulano" not in resposta.text
    registros = [r for r in caplog.records if corpo["erro_id"] in r.getMessage()]
    assert registros and registros[0].exc_info is not None


def test_http_exception_mantem_formato_e_ganha_request_id(cliente):
    resposta = cliente.post("/api/atualizacoes/nao_existe")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Tarefa nao_existe não existe"}
    assert resposta.headers["X-Request-ID"]


def test_validacao_mantem_formato(cliente):
    resposta = cliente.get("/api/cambio/ptax")
    assert resposta.status_code == 422
    assert isinstance(resposta.json()["detail"], list)
    assert resposta.headers["X-Request-ID"]


def test_request_id_do_cliente_e_reaproveitado_quando_seguro(cliente):
    assert cliente.get("/api/saude", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"
    gerado = cliente.get("/api/saude", headers={"X-Request-ID": "x" * 200 + "<>"}).headers["X-Request-ID"]
    assert gerado and len(gerado) <= 64 and "<" not in gerado
