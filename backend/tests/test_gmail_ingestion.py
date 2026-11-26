"""Tests for provider-independent bank alert parsing and automation."""
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register

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


def test_alert_preferences_default_to_review_and_can_be_changed(client: TestClient) -> None:

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



def test_auto_trusted_posts_only_exact_bank_and_currency_match(
    client: TestClient, monkeypatch
) -> None:
    from app.api.v1 import imports as imports_api
    from app.core.config import Settings

    register(client, "automatic-alert@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={
            "name": "GTBank Current",
            "type": "bank",
            "currency": "NGN",
            "institution": "GTBank",
            "current_balance": "5000.00",
        },
    ).json()
    saved = client.put(
        "/api/v1/imports/preferences",
        json={"automation_mode": "auto_trusted"},
    )
    assert saved.status_code == 200
    monkeypatch.setattr(
        imports_api,
        "get_settings",
        lambda: Settings(
            inbound_email_domain="imports.example.test",
            inbound_email_webhook_secret="test-secret",
        ),
    )
    mailbox = client.post("/api/v1/imports/mailbox").json()
    response = client.post(
        "/api/v1/imports/inbound-email",
        headers={"X-Inbound-Email-Secret": "test-secret"},
        json={
            "To": mailbox["address"],
            "From": "alerts@gtbank.com",
            "Subject": "Credit Alert",
            "TextBody": "Your account was credited NGN 1,000.00 on 26/11/2026. Ref: GTB123456",
            "MessageID": "gmail-like-delivery-001",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    transactions = client.get("/api/v1/transactions").json()
    assert len(transactions) == 1
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert balance == Decimal("6000.00")
