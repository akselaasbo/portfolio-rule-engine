from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfigurasjon lest fra miljovariabler, med fornuftige standardverdier."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: str = "data"
    log_level: str = "INFO"
    weight_tolerance: float = 0.01


settings = Settings()