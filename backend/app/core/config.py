"""Configuration de l'application, lue depuis les variables d'environnement et le fichier .env."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Paramètres de l'outil. Chaque champ correspond à une variable du fichier .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = Path("./data")
    # Valeurs prudentes provisoires, à ajuster après les tests sur le compte secondaire.
    # Unlikes tentés par jour (date locale), tous nettoyages confondus.
    daily_limit: int = Field(default=150, ge=1)
    # Pause tirée au hasard entre deux lots, en secondes.
    delay_min: float = Field(default=4.0, ge=0)
    delay_max: float = Field(default=12.0, ge=0)
    # Likes retirés par lot, c'est-à-dire par clic sur « Je n’aime plus ».
    batch_size: int = Field(default=20, ge=1)
    log_level: LogLevel = "INFO"

    @field_validator("log_level", mode="before")
    @classmethod
    def _uppercase_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _check_delays(self) -> Self:
        if self.delay_min > self.delay_max:
            raise ValueError("DELAY_MIN doit être inférieur ou égal à DELAY_MAX")
        return self

    @property
    def browser_profile_dir(self) -> Path:
        return self.data_dir / "browser-profile"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "iuc.db"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def diagnostics_dir(self) -> Path:
        return self.data_dir / "diagnostics"

    def ensure_dirs(self) -> None:
        """Crée le dossier de données et ses sous-dossiers s'ils n'existent pas."""
        for directory in (
            self.data_dir,
            self.browser_profile_dir,
            self.reports_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
