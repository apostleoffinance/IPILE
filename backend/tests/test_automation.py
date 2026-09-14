from datetime import date

from fastapi.testclient import TestClient

from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register


def test_duplicate_ticks_do_not_double_allocate(client: TestClient) -> None:
    register(client, "auto-tick@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "0.00"},
    ).json()
    client.post(
        "/api/v1/allocation-rules",
        json={
            "name": "Buffer",
            "type": "fixed",
            "amount": "100000.00",
            "priority": 0,
            "destination_type": "account",
            "destination_id": account["id"],
        },
    )
    income = client.post(
        "/api/v1/income",
        json={
            "account_id": account["id"],
            "amount": "500000.00",
            "date": date.today().isoformat(),
        },
    )
    assert income.status_code == 201, income.text
    first = client.post("/api/v1/automation/tick", json={"tick_type": "income_recognized"})
    assert first.status_code == 200, first.text
    # income path already ran income_recognized; explicit retick must skip
    assert first.json()["skipped"] is True
    second = client.post("/api/v1/automation/tick", json={"tick_type": "income_recognized"})
    assert second.status_code == 200
    assert second.json()["skipped"] is True
    assert second.json()["id"] == first.json()["id"]
    latest = client.get("/api/v1/allocations/latest").json()
    assert latest["recognized_income"] == "500000.00"


def test_budget_threshold_and_overspend_alerts(client: TestClient) -> None:
    register(client, "auto-budget@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "1000000.00"},
    ).json()
    food = {row["name"]: row for row in client.get("/api/v1/categories").json()}["Food"]
    budget = client.post(
        "/api/v1/budget",
        json={
            "name": "Lifestyle",
            "categories": [{"category_id": food["id"], "allocated_amount": "100000.00"}],
        },
    )
    assert budget.status_code == 201, budget.text
    warn = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "80000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": food["id"],
        },
    )
    assert warn.status_code == 201, warn.text
    alerts = client.get("/api/v1/alerts").json()
    assert any(row["type"] == "budget_threshold" for row in alerts)
    over = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "30000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": food["id"],
        },
    )
    assert over.status_code == 201, over.text
    tick = client.post("/api/v1/automation/tick", json={"tick_type": "daily"})
    assert tick.status_code == 200, tick.text
    alerts = client.get("/api/v1/alerts").json()
    assert any(row["type"] == "budget_overspend" for row in alerts)
    inbox = client.get("/api/v1/notifications").json()
    assert len(inbox) >= 1
    assert inbox[0]["channel"] == "in_app"
    read = client.post(f"/api/v1/notifications/{inbox[0]['id']}/read")
    assert read.status_code == 200
    assert read.json()["status"] == "read"


def test_underfunded_obligation_alert_and_seed_inbox(client: TestClient) -> None:
    db = TestingSessionLocal()
    try:
        seed_household(db)
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": SEED_OWNER_EMAIL, "password": SEED_OWNER_PASSWORD},
    )
    assert login.status_code == 200
    tick = client.post("/api/v1/automation/tick", json={"tick_type": "daily"})
    assert tick.status_code == 200, tick.text
    assert tick.json()["skipped"] is False
    again = client.post("/api/v1/automation/tick", json={"tick_type": "daily"})
    assert again.json()["skipped"] is True
    alerts = client.get("/api/v1/alerts").json()
    assert any(row["type"] == "obligation_underfunded" for row in alerts)
    inbox = client.get("/api/v1/notifications").json()
    assert len(inbox) >= 1
    assert any(row["severity"] in {"warning", "critical"} for row in inbox)
