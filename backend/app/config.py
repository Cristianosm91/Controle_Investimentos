import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROJETO = Path(__file__).resolve().parents[2]


def _db_padrao() -> Path:
    # Fora do OneDrive: sincronização de arquivo SQLite aberto corrompe o banco.
    base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ControleInv"
    return base / "controleinv.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONTROLEINV_",
        env_file=RAIZ_PROJETO / ".env",
        extra="ignore",
    )

    db_path: Path = _db_padrao()
    # Quando definida (ex.: PostgreSQL), tem precedência sobre db_path.
    database_url: str | None = None
    host: str = "127.0.0.1"
    port: int = 8000

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
