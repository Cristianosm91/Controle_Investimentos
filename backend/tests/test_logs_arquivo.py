"""OBS-001/PP-009: log persistente com rotação, fora de pastas sincronizadas, sem dados pessoais."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from app import main
from app.config import db_padrao, settings


def _handlers_arquivo() -> list[RotatingFileHandler]:
    return [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]


@pytest.fixture
def restaurar_logs():
    yield
    main.configurar_logs()


def test_arquivo_com_rotacao_5mb_x5(tmp_path, restaurar_logs):
    arquivo = main.configurar_logs(tmp_path)
    assert arquivo == tmp_path / "investhub.log"
    [handler] = _handlers_arquivo()
    assert (handler.maxBytes, handler.backupCount) == (5 * 1024 * 1024, 5)
    assert Path(handler.baseFilename) == arquivo
    logging.getLogger("app.teste").warning("evento de diagnóstico")
    handler.flush()
    assert "evento de diagnóstico" in arquivo.read_text(encoding="utf-8")


def test_configurar_duas_vezes_nao_duplica_handlers(tmp_path, restaurar_logs):
    antes = len(logging.getLogger().handlers)
    main.configurar_logs(tmp_path)
    main.configurar_logs(tmp_path)
    assert len(_handlers_arquivo()) == 1
    assert len(logging.getLogger().handlers) == antes


def test_mascara_caminho_de_usuario_windows(tmp_path, restaurar_logs):
    arquivo = main.configurar_logs(tmp_path)
    log = logging.getLogger("app.teste")
    log.warning("Banco em %s", r"C:\Users\joao.silva\OneDrive - Empresa\investhub.db")
    try:
        raise OSError(r"sem acesso a c:/users/maria/AppData/Local/InvestHub")
    except OSError:
        log.exception("falhou")
    _handlers_arquivo()[0].flush()
    texto = arquivo.read_text(encoding="utf-8")
    assert "joao.silva" not in texto and "maria" not in texto
    assert r"C:\Users\***\OneDrive" in texto


def test_pasta_padrao_e_a_mesma_base_do_banco(monkeypatch):
    monkeypatch.delenv("INVESTHUB_LOG_DIR", raising=False)
    monkeypatch.setattr(settings, "db_path", db_padrao())
    assert main.pasta_logs() == db_padrao().parent / "logs"


def test_variavel_de_ambiente_define_pasta(monkeypatch, tmp_path):
    monkeypatch.setenv("INVESTHUB_LOG_DIR", str(tmp_path / "x"))
    assert main.pasta_logs() == tmp_path / "x"


def test_testes_nao_escrevem_na_pasta_real():
    real = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "InvestHub"
    for handler in _handlers_arquivo():
        assert not Path(handler.baseFilename).is_relative_to(real)


def test_pasta_nao_gravavel_mantem_console(tmp_path, restaurar_logs):
    bloqueio = tmp_path / "arquivo"
    bloqueio.write_text("x")
    assert main.configurar_logs(bloqueio / "logs") is None
    assert _handlers_arquivo() == []
