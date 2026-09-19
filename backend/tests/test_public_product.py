from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.models.household import Household
from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, SEED_SLUG, seed_household
from tests.conftest import TestingSessionLocal, login, register


def _logout(client: TestClient) -> None:
    client.post("/api/v1/auth/logout")


def test_new_family_onboards_without_seed(client: TestClient) -> None:
    register(client, "fresh-family@example.com", "Fresh Owner")
    households = client.get("/api/v1/households").json()
    assert len(households) == 1
    assert households[0]["slug"] != SEED_SLUG
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Main", "type": "bank", "current_balance": "100000.00"},
    )
    assert account.status_code == 201
    income = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account.json()["id"],
            "amount": "50000.00",
            "type": "income",
            "date": "2026-09-14",
            "description": "First paycheck",
        },
    )
    assert income.status_code == 201, income.text


def test_onboarding_after_household_delete(client: TestClient) -> None:
    register(client, "rejoin@example.com", "Rejoin")
    assert client.delete("/api/v1/households/current").status_code == 204
    assert client.get("/api/v1/households").json() == []
    created = client.post(
        "/api/v1/onboarding/household",
        json={"name": "Second Chance Household", "minimum_buffer_amount": "50000.00"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Second Chance Household"
    assert client.get("/api/v1/households/current").json()["id"] == created.json()["id"]


def test_deleted_seed_is_not_resurrected(client: TestClient) -> None:
    db = TestingSessionLocal()
    try:
        household = seed_household(db)
        assert household is not None
        db.commit()
        household.deleted_at = datetime.now(UTC)
        db.add(household)
        db.commit()
        assert seed_household(db) is None
        still = db.query(Household).filter(Household.slug == SEED_SLUG).first()
        assert still is not None
        assert still.deleted_at is not None
    finally:
        db.close()


def test_invite_accept_flow(client: TestClient) -> None:
    register(client, "invite-owner@example.com", "Owner")
    _logout(client)
    register(client, "invite-partner@example.com", "Partner")
    _logout(client)
    login(client, "invite-owner@example.com")
    invited = client.post(
        "/api/v1/invites",
        json={"email": "invite-partner@example.com", "role": "partner"},
    )
    assert invited.status_code == 201, invited.text
    token = invited.json()["token"]
    household_id = invited.json()["household_id"]
    _logout(client)
    login(client, "invite-partner@example.com")
    accepted = client.post("/api/v1/invites/accept", json={"token": token})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["role"] == "partner"
    memberships = client.get("/api/v1/households").json()
    assert any(row["id"] == household_id for row in memberships)


def test_billing_and_support(client: TestClient) -> None:
    register(client, "billing@example.com", "Biller")
    billing = client.get("/api/v1/billing")
    assert billing.status_code == 200, billing.text
    assert billing.json()["plan"] == "pilot"
    upgraded = client.post("/api/v1/billing/plan", json={"plan": "family"})
    assert upgraded.status_code == 200, upgraded.text
    assert upgraded.json()["plan"] == "family"
    ticket = client.post(
        "/api/v1/support/tickets",
        json={"subject": "Need help", "body": "How do I invite my partner?"},
    )
    assert ticket.status_code == 201, ticket.text
    tickets = client.get("/api/v1/support/tickets")
    assert tickets.status_code == 200
    assert len(tickets.json()) == 1


def test_seed_login_still_works_when_present(client: TestClient) -> None:
    db = TestingSessionLocal()
    try:
        seed_household(db)
        db.commit()
    finally:
        db.close()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": SEED_OWNER_EMAIL, "password": SEED_OWNER_PASSWORD},
    )
    assert response.status_code == 200, response.text


def test_billing_webhook_requires_secret(client: TestClient, monkeypatch) -> None:
    from app.core.config import get_settings

    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", "")
    get_settings.cache_clear()
    try:
        empty = client.post("/api/v1/billing/webhook", json={"event": "charge.success"})
        assert empty.status_code == 503

        monkeypatch.setenv("BILLING_WEBHOOK_SECRET", "psp-shared-secret")
        get_settings.cache_clear()
        denied = client.post("/api/v1/billing/webhook", json={"event": "charge.success"})
        assert denied.status_code == 401
        accepted = client.post(
            "/api/v1/billing/webhook",
            headers={"X-Billing-Secret": "psp-shared-secret"},
            json={"event": "charge.success", "provider": "paystack", "id": "evt_1"},
        )
        assert accepted.status_code == 202, accepted.text
        assert accepted.json()["status"] == "accepted"
    finally:
        monkeypatch.delenv("BILLING_WEBHOOK_SECRET", raising=False)
        get_settings.cache_clear()
