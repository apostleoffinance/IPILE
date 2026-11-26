"""Tests for provider-independent bank alert parsing and automation."""
from decimal import Decimal

from app.services.email_imports import parse_bank_alert


def test_bank_alert_parser_recognizes_iso_codes_and_symbols() -> None:
    base = {
        "sender": "alerts@bank.example",
        "subject": "Credit Alert",
        "email_date": "Thu, 26 Nov 2026 09:00:00 +0100",
    }
    usd = parse_bank_alert(**base, body="You received USD 125.50. Ref: USD123456")
    eur = parse_bank_alert(**base, body="You received € 80.00. Ref: EUR123456")
    ambiguous = parse_bank_alert(**base, body="You received $ 80.00. Ref: USD123457")
    assert usd.currency == "USD"
    assert eur.currency == "EUR"
    assert ambiguous.currency is None
    assert usd.amount == Decimal("125.50")


def test_alert_preferences_default_to_review_and_can_be_changed(client) -> None:
    from tests.conftest import register

    register(client, "gmail-preferences@example.com")
    initial = client.get("/api/v1/imports/preferences")
    assert initial.status_code == 200
    assert initial.json()["automation_mode"] == "review_everything"
    saved = client.put(
        "/api/v1/imports/preferences",
        json={"automation_mode": "auto_trusted"},
    )
    assert saved.status_code == 200
    assert saved.json()["automation_mode"] == "auto_trusted"
    invalid = client.put(
        "/api/v1/imports/preferences",
        json={"automation_mode": "auto_everything_without_review"},
    )
    assert invalid.status_code == 422
