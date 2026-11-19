from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "IPÌLẸ̀"
    environment: str = "development"
    secret_key: str = "dev-only-change-me"
    database_url: str = "postgresql+psycopg://familyos:familyos_dev_only@localhost:5432/familyos"
    cors_origins: str = "http://localhost:3000"
    session_cookie_name: str = "ffos_session"
    csrf_cookie_name: str = "ffos_csrf"
    session_idle_hours: int = 12
    session_absolute_days: int = 7
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    seed_on_start: bool = True
    billing_webhook_secret: str = ""
    inbound_email_domain: str = ""
    inbound_email_webhook_secret: str = ""
    max_import_upload_bytes: int = 10 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def resolved_cookie_samesite(self) -> str:
        value = self.cookie_samesite.lower().strip()
        if value not in {"lax", "strict", "none"}:
            return "lax"
        if value == "none" and not self.cookie_secure:
            return "lax"
        return value

    @model_validator(mode="after")
    def validate_production_configuration(self) -> "Settings":
        if self.environment.lower().strip() not in {"production", "prod"}:
            return self

        problems: list[str] = []
        database_url = self.database_url.lower()
        if not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            problems.append("DATABASE_URL must use PostgreSQL in production")
        if "localhost" in database_url or "127.0.0.1" in database_url:
            problems.append("DATABASE_URL must not point to localhost in production")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true in production")
        if self.cookie_samesite.lower().strip() not in {"lax", "strict", "none"}:
            problems.append("COOKIE_SAMESITE must be lax, strict, or none")
        if self.cookie_samesite.lower().strip() == "none" and not self.cookie_secure:
            problems.append("SameSite=None requires secure cookies")
        if self.seed_on_start:
            problems.append("SEED_ON_START must be false in production")
        if "*" in self.cors_origin_list:
            problems.append("CORS_ORIGINS must not contain wildcard origins with credentials")
        if self.session_idle_hours < 1 or self.session_absolute_days < 1:
            problems.append("Session expiry settings must be positive")
        if self.session_idle_hours > self.session_absolute_days * 24:
            problems.append("Session idle expiry cannot exceed absolute expiry")

        if problems:
            raise ValueError("Invalid production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
