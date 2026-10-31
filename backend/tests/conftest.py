import os

import pytest

# Antes de importar o app: testes nunca tocam o banco real nem iniciam jobs.
os.environ["CONTROLEINV_JOBS_ATIVOS"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def cliente():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(conexao, _registro):
        conexao.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _sessao():
        with Sessao() as s:
            yield s

    app.dependency_overrides[get_session] = _sessao
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()
