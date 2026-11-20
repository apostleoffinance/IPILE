import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "secret_key": "test-only-production-secret-key-32chars",
        "database_url": "postgresql+psycopg://app:strong-password@db.example.com/ipile",
        "cookie_secure": True,
        "cookie_samesite": "lax",
        "seed_on_start": False,
        "cors_origins": "https://ipile-web.ipile-71a.workers.dev",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_configuration_accepts_secure_settings() -> None:
    settings = production_settings()
    assert settings.resolved_cookie_samesite == "lax"


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"secret_key": "dev-only-change-me"}, "SECRET_KEY must be a unique value"),
        ({"cookie_secure": False}, "COOKIE_SECURE must be true"),
        ({"database_url": "postgresql://app:pass@localhost/ipile"}, "must not point to localhost"),
        ({"seed_on_start": True}, "SEED_ON_START must be false"),
        ({"cors_origins": "*"}, "wildcard origins"),
        ({"cookie_samesite": "invalid"}, "COOKIE_SAMESITE must be lax"),
    ],
)
def test_production_configuration_fails_closed(override: dict, expected: str) -> None:
    with pytest.raises(ValidationError, match=expected):
        production_settings(**override)


def test_samesite_none_is_rejected_without_secure_cookie() -> None:
    with pytest.raises(ValidationError, match="SameSite=None requires secure cookies"):
        production_settings(cookie_secure=False, cookie_samesite="none")


def test_production_configuration_accepts_separate_migration_database_url() -> None:
    settings = production_settings(
        database_migration_url="postgresql+psycopg://migrator:strong-password@db.example.com/ipile"
    )
    assert settings.database_migration_url.startswith("postgresql+psycopg://")


@pytest.mark.parametrize(
    "migration_url",
    [
        "sqlite:///tmp/ipile.db",
        "postgresql://migrator:pass@localhost/ipile",
    ],
)
def test_production_migration_database_url_fails_closed(migration_url: str) -> None:
    with pytest.raises(ValidationError, match="DATABASE_MIGRATION_URL"):
        production_settings(database_migration_url=migration_url)
