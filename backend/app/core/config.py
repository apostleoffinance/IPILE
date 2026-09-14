from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "IPÌLẸ̀"
    environment: str = "development"
    secret_key: str = "dev-only-change-me"
    database_url: str = "postgresql+psycopg://familyos:familyos_dev_only@localhost:5432/familyos"
    cors_origins: str = "http://localhost:3000"
    session_cookie_name: str = "ffos_session"
    session_idle_hours: int = 12
    session_absolute_days: int = 7
    cookie_secure: bool = False
    seed_on_start: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
