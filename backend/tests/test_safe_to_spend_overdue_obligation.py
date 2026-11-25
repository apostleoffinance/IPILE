from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


def test_overdue_obligation_is_deducted_from_current_safe_to_spend(
    client: TestClient,
) -> None:
    register(client, "sts-overdue-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "2000000.00"},
    )
    assert account.status_code == 201, account.text
    obligation = client.post(
        "/api/v1/obligations",
        json={
            "name": "Overdue rent",
            "amount": "150000.00",
            "frequency": "one_time",
            "next_due_date": (date.today() - timedelta(days=10)).isoformat(),
            "priority": "critical",
        },
    )
    assert obligation.status_code == 201, obligation.text

    snapshot = client.get("/api/v1/safe-to-spend")
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert Decimal(body["current"]) == Decimal("1850000.00")
    assert Decimal(body["period"]) == Decimal("1850000.00")
