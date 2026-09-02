from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Konfigurasjon lest fra miljovariabler, med fornuftige standardverdier."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: str = "data"
    log_level: str = "INFO"
    weight_tolerance: float = 0.01
    min_position_weight_pct: float = 2.0

    @property
    def data_path(self) -> Path:
        """Absolutt sti til datamappen, forankret i prosjektrota uansett arbeidsmappe."""
        return PROJECT_ROOT / self.data_dir


settings = Settings()