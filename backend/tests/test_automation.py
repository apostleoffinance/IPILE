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



def test_recurring_payment_generates_one_proactive_alert_and_notification(
    client: TestClient,
) -> None:
    from app.services.recurring import add_months

    register(client, "proactive-recurring@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    anchor = date.today().replace(day=5)
    for months_ago in (2, 1, 0):
        occurred_on = add_months(anchor, -months_ago)
        response = client.post(
            "/api/v1/transactions",
            json={
                "account_id": account["id"],
                "amount": "1000.00",
                "type": "expense",
                "date": occurred_on.isoformat(),
                "merchant": "Netflix",
                "description": "Monthly subscription",
                "status": "cleared",
            },
        )
        assert response.status_code == 201, response.text

    alerts = client.get("/api/v1/alerts").json()
    recurring = [row for row in alerts if row["type"] == "recurring_payment_upcoming"]
    assert len(recurring) == 1
    assert recurring[0]["related_entity_id"] == account["id"]

    inbox = client.get("/api/v1/notifications", params={"unread_only": "true"}).json()
    proactive = [row for row in inbox if row["title"] == "Expected recurring transaction"]
    assert len(proactive) == 1

    tick = client.post("/api/v1/automation/tick", json={"tick_type": "daily"})
    assert tick.status_code == 200, tick.text
    inbox_after_tick = client.get(
        "/api/v1/notifications", params={"unread_only": "true"}
    ).json()
    recurring_after_tick = [
        row for row in inbox_after_tick
        if row["title"] == "Expected recurring transaction"
    ]
    assert len(recurring_after_tick) == 1


def test_unusually_large_transaction_generates_proactive_alert(client: TestClient) -> None:
    register(client, "proactive-anomaly@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    history = [
        (date(2026, 7, 20), "100.00"),
        (date(2026, 8, 20), "110.00"),
        (date(2026, 9, 20), "90.00"),
        (date(2026, 10, 20), "100.00"),
    ]
    anomaly_transaction_id = None
    for occurred_on, amount in history + [(date(2026, 11, 20), "500.00")]:
        response = client.post(
            "/api/v1/transactions",
            json={
                "account_id": account["id"],
                "amount": amount,
                "type": "expense",
                "date": occurred_on.isoformat(),
                "merchant": "PowerCo",
                "description": "Utility payment",
                "status": "cleared",
            },
        )
        assert response.status_code == 201, response.text
        anomaly_transaction_id = response.json()["id"]

    alerts = client.get("/api/v1/alerts").json()
    anomaly = [row for row in alerts if row["type"] == "unusually_large_transaction"]
    assert len(anomaly) == 1
    assert anomaly[0]["severity"] == "warning"

    inbox = client.get("/api/v1/notifications", params={"unread_only": "true"}).json()
    assert any(row["title"] == "Transaction is larger than usual" for row in inbox)

    voided = client.post(f"/api/v1/transactions/{anomaly_transaction_id}/void")
    assert voided.status_code == 200, voided.text
    remaining = client.get("/api/v1/alerts").json()
    assert not any(row["type"] == "unusually_large_transaction" for row in remaining)
    unread_after_void = client.get(
        "/api/v1/notifications", params={"unread_only": "true"}
    ).json()
    assert not any(
        row["title"] == "Transaction is larger than usual" for row in unread_after_void
    )
