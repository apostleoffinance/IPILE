import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "database_url": "postgresql+psycopg://app:strong-password@db.example.com/ipile",
        "cookie_secure": True,
        "cookie_samesite": "lax",
        "seed_on_start": False,
        "cors_origins": "https://ipile-two.vercel.app",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_production_configuration_accepts_secure_settings() -> None:
    settings = production_settings()
    assert settings.resolved_cookie_samesite == "lax"


@pytest.mark.parametrize(
    ("override", "expected"),
    [
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
