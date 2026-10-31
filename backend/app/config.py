import logging
import os
import sqlite3
from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
ARQUIVO_ENV = RAIZ_PROJETO / ".env"
PREFIXO_ENV = "INVESTHUB_"
_PREFIXO_ENV_LEGADO = "CONTROLEINV_"

log = logging.getLogger(__name__)


def _pasta_dados() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home()))


def db_padrao() -> Path:
    # Fora do OneDrive: sincronização de arquivo SQLite aberto corrompe o banco.
    return _pasta_dados() / "InvestHub" / "investhub.db"


def _db_legado() -> Path:
    return _pasta_dados() / "ControleInv" / "controleinv.db"


def _aceitar_prefixo_legado() -> None:
    """Mantém válidas as variáveis CONTROLEINV_* (ambiente ou .env) do nome anterior do app; INVESTHUB_* prevalece."""
    legado = {k.upper(): v for k, v in os.environ.items() if k.upper().startswith(_PREFIXO_ENV_LEGADO)}
    novas_no_arquivo: set[str] = set()
    if ARQUIVO_ENV.is_file():
        for chave, valor in dotenv_values(ARQUIVO_ENV).items():
            chave = chave.upper()
            if chave.startswith(PREFIXO_ENV):
                novas_no_arquivo.add(chave)
            elif chave.startswith(_PREFIXO_ENV_LEGADO) and valor is not None:
                legado.setdefault(chave, valor)
    for chave, valor in legado.items():
        nova = PREFIXO_ENV + chave.removeprefix(_PREFIXO_ENV_LEGADO)
        if nova not in novas_no_arquivo and nova not in {k.upper() for k in os.environ}:
            os.environ[nova] = valor


def migrar_banco_legado(destino: Path) -> None:
    """Copia o banco do nome anterior (ControleInv) para o caminho padrão novo, se este ainda não existir."""
    origem = _db_legado()
    if destino.exists() or not origem.is_file():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".migrando")
    temporario.unlink(missing_ok=True)
    # API de backup do SQLite: cópia consistente mesmo com o WAL ou o app antigo ainda aberto.
    fonte, alvo = sqlite3.connect(origem), sqlite3.connect(temporario)
    try:
        fonte.backup(alvo)
    finally:
        alvo.close()
        fonte.close()
    temporario.rename(destino)
    log.info("Banco migrado de %s para %s (o original foi mantido).", origem, destino)


_aceitar_prefixo_legado()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=PREFIXO_ENV,
        env_file=ARQUIVO_ENV,
        extra="ignore",
    )

    db_path: Path = db_padrao()
    # Quando definida (ex.: PostgreSQL), tem precedência sobre db_path.
    database_url: str | None = None
    host: str = "127.0.0.1"
    port: int = 8000
    # Valores aceitos no cabeçalho Host e na origem de requisições de escrita (proteção contra CSRF/DNS rebinding).
    hosts_permitidos: list[str] = ["127.0.0.1", "localhost"]

    # Lei 14.754/2023 art. 15: PTAX de venda da data do fato gerador (0 = a própria data).
    ptax_dias_uteis_antes: int = Field(default=0, ge=0, le=5)

    jobs_ativos: bool = True
    cotacoes_intervalo_min: int = Field(default=15, ge=5)
    # Arquivo diário da B3 sai à noite; o job tenta a partir deste horário.
    cotahist_hora: int = Field(default=21, ge=0, le=23)

    @property
    def db_url(self) -> str:
        if self.database_url:
            return normalizar_url(self.database_url)
        return f"sqlite:///{self.db_path.as_posix()}"


def normalizar_url(url: str) -> str:
    """Usa o driver psycopg (v3) nas URLs copiadas de Neon/Supabase/Aiven (`postgres://` ou `postgresql://`)."""
    url = url.strip()
    for prefixo in ("postgres://", "postgresql://"):
        if url.startswith(prefixo):
            return "postgresql+psycopg://" + url.removeprefix(prefixo)
    return url


settings = Settings()
