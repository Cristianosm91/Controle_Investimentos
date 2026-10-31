import os
from pathlib import Path

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
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path.as_posix()}"


settings = Settings()
