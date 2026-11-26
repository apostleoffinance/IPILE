"""Tests for provider-independent bank alert parsing and automation."""

from fastapi.testclient import TestClient
from decimal import Decimal

from app.services.email_imports import parse_bank_alert
from tests.conftest import register


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
    client.post(
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



def test_gmail_oauth_flow_encrypts_refresh_token_and_consumes_state(
    client: TestClient, monkeypatch
) -> None:
    from urllib.parse import parse_qs, urlsplit

    from cryptography.fernet import Fernet

    from app.api.v1 import gmail as gmail_api
    from app.core.config import Settings
    from app.models.gmail import GmailConnection
    from app.services import gmail as gmail_service
    from tests.conftest import TestingSessionLocal

    register(client, "gmail-oauth@example.com")
    settings = Settings(
        gmail_oauth_client_id="google-client",
        gmail_oauth_client_secret="google-secret",
        gmail_oauth_redirect_uri="https://api.ipile.app/api/v1/imports/gmail/callback",
        gmail_sync_secret="sync-secret",
        gmail_token_encryption_key=Fernet.generate_key().decode("ascii"),
        gmail_allowed_sender_domains="bank.example",
        cors_origins="https://ipile.app",
    )
    monkeypatch.setattr(gmail_api, "get_settings", lambda: settings)
    monkeypatch.setattr(gmail_service, "get_settings", lambda: settings)

    started = client.post("/api/v1/imports/gmail/connect")
    assert started.status_code == 200, started.text
    authorization = started.json()["authorization_url"]
    query = parse_qs(urlsplit(authorization).query)
    assert query["scope"] == [gmail_service.GMAIL_SCOPE]
    assert query["access_type"] == ["offline"]
    state = query["state"][0]

    monkeypatch.setattr(
        gmail_api,
        "exchange_code",
        lambda _code: {"access_token": "access-token", "refresh_token": "refresh-token"},
    )
    monkeypatch.setattr(
        gmail_api,
        "gmail_get",
        lambda _token, _path: {"emailAddress": "bank-alerts@gmail.com"},
    )
    callback = client.get(
        "/api/v1/imports/gmail/callback",
        params={"code": "one-time-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert "gmail=connected" in callback.headers["location"]

    with TestingSessionLocal() as db:
        connection = db.query(GmailConnection).one()
        assert connection.enabled is True
        assert connection.email_address == "bank-alerts@gmail.com"
        assert connection.refresh_token_encrypted != "refresh-token"
        assert connection.state_hash is None

    replay = client.get(
        "/api/v1/imports/gmail/callback",
        params={"code": "one-time-code", "state": state},
        follow_redirects=False,
    )
    assert "gmail=expired" in replay.headers["location"]



def test_gmail_search_is_restricted_to_allowlisted_sender_domains(monkeypatch) -> None:
    from app.services import gmail as gmail_service

    captured: list[dict] = []

    def fake_gmail_get(_token: str, _path: str, params: dict | None = None) -> dict:
        captured.append(params or {})
        return {"messages": []}

    monkeypatch.setattr(gmail_service, "gmail_get", fake_gmail_get)
    assert gmail_service.list_recent_messages("access-token", None, []) == []
    assert captured == []
    gmail_service.list_recent_messages(
        "access-token",
        None,
        ["gtbank.com", "kuda.com"],
    )
    assert "from:gtbank.com" in captured[0]["q"]
    assert "from:kuda.com" in captured[0]["q"]



def test_gmail_sender_authentication_requires_aligned_dmarc() -> None:
    from app.api.v1.gmail import _gmail_dmarc_passes_for_sender

    passed = "mx.google.com; dmarc=pass header.from=gtbank.com"
    mismatched = "mx.google.com; dmarc=pass header.from=attacker.example"
    failed = "mx.google.com; dmarc=fail header.from=gtbank.com"
    assert _gmail_dmarc_passes_for_sender("GTBank <alerts@gtbank.com>", passed)
    assert not _gmail_dmarc_passes_for_sender("alerts@gtbank.com", mismatched)
    assert not _gmail_dmarc_passes_for_sender("alerts@gtbank.com", failed)



def test_provider_neutral_intelligence_enriches_forwarded_alert_review(
    client: TestClient, monkeypatch
) -> None:
    from app.api.v1 import imports as imports_api
    from app.core.config import Settings

    register(client, "intelligence-review@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={
            "name": "OPay Wallet",
            "type": "bank",
            "currency": "NGN",
            "institution": "OPay",
            "current_balance": "25000.00",
        },
    ).json()
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
            "From": "no-reply@opayweb.com",
            "Subject": "Debit Alert",
            "TextBody": "Your wallet was debited NGN 2,500.00 for fuel on 26/11/2026. Ref: OPY123456",
            "MessageID": "forwarding-event-001",
        },
    )
    assert response.status_code == 200, response.text
    queue = client.get("/api/v1/imports/review")
    assert queue.status_code == 200
    item = queue.json()[0]
    assert item["result"]["account_match"] == "exact_institution"
    assert item["result"]["suggested_account_id"] == account["id"]
    intelligence = item["result"]["intelligence"]
    assert intelligence["normalized_event"]["provider"] == "cloudflare_forwarding"
    assert intelligence["normalized_event"]["external_id"].startswith("bankref:opayweb.com:")
    assert intelligence["sender_verified"] is True
    assert intelligence["confidence_band"] == "high"
    assert "category_name" in item["result"]["rows"][0]


def test_same_bank_event_has_same_identity_across_ingestion_providers() -> None:
    forwarded = parse_bank_alert(
        sender="alerts@gtbank.com",
        subject="Debit Alert",
        body="Your account was debited NGN 5,000.00 on 26/11/2026. Ref: CROSS12345",
        email_date="Thu, 26 Nov 2026 09:00:00 +0100",
        message_id="cloudflare-message-id",
    )
    gmail = parse_bank_alert(
        sender="alerts@gtbank.com",
        subject="Debit Alert",
        body="Your account was debited NGN 5,000.00 on 26/11/2026. Ref: CROSS12345",
        email_date="Thu, 26 Nov 2026 09:00:00 +0100",
        message_id="gmail-message-id",
    )
    assert forwarded.external_id == gmail.external_id
