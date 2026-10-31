import warnings
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

warnings.filterwarnings("ignore", message=".*does \\*not\\* support Decimal objects natively.*", category=SAWarning)


class Base(DeclarativeBase):
    pass


def criar_engine(url: str | None = None) -> Engine:
    url = url or settings.db_url
    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    eng = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _ativar_fk(conexao, _registro) -> None:
        conexao.execute("PRAGMA foreign_keys=ON")

    return eng


engine = criar_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as sessao:
        yield sessao
