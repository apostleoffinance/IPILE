from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import register


def test_period_safe_to_spend_does_not_deduct_due_today_obligation_twice(
    client: TestClient,
) -> None:
    register(client, "sts-due-today-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "2000000.00"},
    )
    assert account.status_code == 201, account.text

    obligation = client.post(
        "/api/v1/obligations",
        json={
            "name": "Due today",
            "amount": "100000.00",
            "frequency": "one_time",
            "next_due_date": date.today().isoformat(),
            "priority": "critical",
        },
    )
    assert obligation.status_code == 201, obligation.text

    snapshot = client.get("/api/v1/safe-to-spend")
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert body["current"] == "1900000.00"
    assert body["period"] == body["current"]
