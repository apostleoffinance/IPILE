from functools import lru_cache
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "IPÌLẸ̀"
    environment: str = "development"
    secret_key: str = "dev-only-change-me"
    database_url: str = "postgresql+psycopg://familyos:familyos_dev_only@localhost:5432/familyos"
    database_migration_url: str = ""
    cors_origins: str = "http://localhost:3000"
    session_cookie_name: str = "ffos_session"
    csrf_cookie_name: str = "ffos_csrf"
    session_idle_hours: int = 12
    session_absolute_days: int = 7
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    seed_on_start: bool = True
    billing_webhook_secret: str = ""
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0
    inbound_email_domain: str = ""
    inbound_email_webhook_secret: str = ""
    max_import_upload_bytes: int = 10 * 1024 * 1024
    mono_secret_key: str = ""
    mono_webhook_secret: str = ""
    mono_redirect_url: str = ""
    bank_data_encryption_key: str = ""
    gmail_oauth_client_id: str = ""
    gmail_oauth_client_secret: str = ""
    gmail_oauth_redirect_uri: str = ""
    gmail_sync_secret: str = ""
    gmail_token_encryption_key: str = ""
    gmail_allowed_sender_domains: str = ""

    @property
    def gmail_connect_configured(self) -> bool:
        return all(value.strip() for value in (
            self.gmail_oauth_client_id,
            self.gmail_oauth_client_secret,
            self.gmail_oauth_redirect_uri,
            self.gmail_sync_secret,
            self.gmail_token_encryption_key,
            self.gmail_allowed_sender_domains,
        ))

    @property
    def gmail_sender_domain_list(self) -> list[str]:
        return [
            part.strip().lower().lstrip("@")
            for part in self.gmail_allowed_sender_domains.split(",")
            if part.strip()
        ]

    @property
    def mono_connect_configured(self) -> bool:
        return all(value.strip() for value in (
            self.mono_secret_key, self.mono_webhook_secret,
            self.mono_redirect_url, self.bank_data_encryption_key,
        ))

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
        migration_url = self.database_migration_url.lower().strip()
        if migration_url and not migration_url.startswith(("postgresql://", "postgresql+psycopg://")):
            problems.append("DATABASE_MIGRATION_URL must use PostgreSQL in production")
        if migration_url and ("localhost" in migration_url or "127.0.0.1" in migration_url):
            problems.append("DATABASE_MIGRATION_URL must not point to localhost in production")
        if self.secret_key == "dev-only-change-me" or len(self.secret_key) < 32:
            problems.append("SECRET_KEY must be a unique value of at least 32 characters")
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
        mono_values = (
            self.mono_secret_key,
            self.mono_webhook_secret,
            self.mono_redirect_url,
            self.bank_data_encryption_key,
        )
        if (
            any(value.strip() for value in mono_values)
            and not all(value.strip() for value in mono_values)
        ):
            problems.append(
                "Mono requires MONO_SECRET_KEY, MONO_WEBHOOK_SECRET, MONO_REDIRECT_URL "
                "and BANK_DATA_ENCRYPTION_KEY together"
            )
        if self.mono_redirect_url:
            redirect = urlsplit(self.mono_redirect_url)
            if (
                redirect.scheme.lower() != "https"
                or not redirect.hostname
                or redirect.username
                or redirect.password
            ):
                problems.append(
                    "MONO_REDIRECT_URL must be an absolute HTTPS URL without embedded credentials"
                )
        if self.bank_data_encryption_key:
            try:
                Fernet(self.bank_data_encryption_key.encode("ascii"))
            except (ValueError, UnicodeEncodeError):
                problems.append(
                    "BANK_DATA_ENCRYPTION_KEY must be a valid URL-safe base64-encoded "
                    "32-byte Fernet key"
                )

        gmail_values = (
            self.gmail_oauth_client_id,
            self.gmail_oauth_client_secret,
            self.gmail_oauth_redirect_uri,
            self.gmail_sync_secret,
            self.gmail_token_encryption_key,
            self.gmail_allowed_sender_domains,
        )
        if any(value.strip() for value in gmail_values) and not all(
            value.strip() for value in gmail_values
        ):
            problems.append(
                "Gmail integration requires GMAIL_OAUTH_CLIENT_ID, "
                "GMAIL_OAUTH_CLIENT_SECRET, GMAIL_OAUTH_REDIRECT_URI, GMAIL_SYNC_SECRET, "
                "GMAIL_TOKEN_ENCRYPTION_KEY and GMAIL_ALLOWED_SENDER_DOMAINS"
            )
        if self.gmail_oauth_redirect_uri:
            gmail_redirect = urlsplit(self.gmail_oauth_redirect_uri)
            if (
                gmail_redirect.scheme.lower() != "https"
                or not gmail_redirect.hostname
                or gmail_redirect.username
                or gmail_redirect.password
            ):
                problems.append("GMAIL_OAUTH_REDIRECT_URI must be an absolute HTTPS URL")

        if self.gmail_token_encryption_key:
            try:
                Fernet(self.gmail_token_encryption_key.encode("ascii"))
            except (ValueError, UnicodeEncodeError):
                problems.append(
                    "GMAIL_TOKEN_ENCRYPTION_KEY must be a valid URL-safe base64-encoded "
                    "32-byte Fernet key"
                )

        if problems:
            raise ValueError("Invalid production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
