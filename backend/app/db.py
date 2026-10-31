import warnings
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event, func
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import normalizar_url, settings

warnings.filterwarnings("ignore", message=".*does \\*not\\* support Decimal objects natively.*", category=SAWarning)


class Base(DeclarativeBase):
    pass


def criar_engine(url: str | None = None) -> Engine:
    url = normalizar_url(url or settings.db_url)
    if not url.startswith("sqlite"):
        # pre_ping/recycle: serviços gerenciados (ex.: Neon) encerram conexões ociosas.
        return create_engine(url, pool_pre_ping=True, pool_recycle=300)

    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    # timeout: jobs em segundo plano e API gravam no mesmo arquivo.
    eng = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(eng, "connect")
    def _ativar_fk(conexao, _registro) -> None:
        conexao.execute("PRAGMA foreign_keys=ON")

    return eng


def _dialeto(sessao: Session) -> str:
    return sessao.get_bind().dialect.name


def insert_upsert(sessao: Session, modelo):
    """INSERT do dialeto em uso, com suporte a `on_conflict_do_update` (SQLite e PostgreSQL)."""
    modulo = postgresql if _dialeto(sessao) == "postgresql" else sqlite
    return modulo.insert(modelo)


def ano_mes(sessao: Session, coluna):
    """Expressão 'AAAA-MM' de uma coluna de data."""
    if _dialeto(sessao) == "postgresql":
        return func.to_char(coluna, "YYYY-MM")
    return func.strftime("%Y-%m", coluna)


engine = criar_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with SessionLocal() as sessao:
        yield sessao
