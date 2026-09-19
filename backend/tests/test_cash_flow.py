from calendar import monthrange
from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import register


def _account(client: TestClient, name: str = "Current", opening: str = "1000000.00") -> dict:
    response = client.post(
        "/api/v1/accounts",
        json={"name": name, "type": "bank", "current_balance": opening},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cash_flow_defaults_to_current_month_and_tracks_activity(client: TestClient) -> None:
    register(client, "cashflow-owner@example.com")
    account = _account(client)
    today = date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])

    income = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "200000.00",
            "type": "income",
            "date": today.isoformat(),
        },
    )
    assert income.status_code == 201, income.text
    expense = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "50000.00",
            "type": "expense",
            "date": today.isoformat(),
        },
    )
    assert expense.status_code == 201, expense.text
    giving = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "20000.00",
            "type": "giving",
            "date": today.isoformat(),
        },
    )
    assert giving.status_code == 201, giving.text

    response = client.get("/api/v1/cash-flow")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["period_start"] == start.isoformat()
    assert body["period_end"] == end.isoformat()
    assert body["income"] == "200000.00"
    assert body["expenses"] == "50000.00"
    assert body["giving"] == "20000.00"
    assert body["surplus"] == "130000.00"
    assert body["opening_cash"] == "1000000.00"
    assert body["closing_cash"] == "1130000.00"
    assert len(body["daily"]) == (end - start).days + 1
    today_row = next(row for row in body["daily"] if row["date"] == today.isoformat())
    assert today_row["income"] == "200000.00"
    assert today_row["expenses"] == "50000.00"
    assert today_row["giving"] == "20000.00"
    assert today_row["net"] == "130000.00"


def test_cash_flow_transfers_net_excludes_cash_to_cash(client: TestClient) -> None:
    register(client, "cashflow-xfer@example.com")
    current = _account(client, "Current", "500000.00")
    savings = client.post(
        "/api/v1/accounts",
        json={"name": "Savings", "type": "savings", "current_balance": "100000.00"},
    ).json()
    investment = client.post(
        "/api/v1/accounts",
        json={"name": "Brokerage", "type": "investment", "current_balance": "0.00"},
    ).json()
    today = date.today()

    internal = client.post(
        "/api/v1/transactions",
        json={
            "account_id": current["id"],
            "counterparty_account_id": savings["id"],
            "amount": "50000.00",
            "type": "transfer",
            "date": today.isoformat(),
        },
    )
    assert internal.status_code == 201, internal.text
    outward = client.post(
        "/api/v1/transactions",
        json={
            "account_id": current["id"],
            "counterparty_account_id": investment["id"],
            "amount": "75000.00",
            "type": "transfer",
            "date": today.isoformat(),
        },
    )
    assert outward.status_code == 201, outward.text

    body = client.get(
        f"/api/v1/cash-flow?period_start={today.isoformat()}&period_end={today.isoformat()}"
    ).json()
    assert body["transfers_net"] == "-75000.00"
    assert body["opening_cash"] == "600000.00"
    assert body["closing_cash"] == "525000.00"


def test_cash_flow_rejects_inverted_range(client: TestClient) -> None:
    register(client, "cashflow-bad@example.com")
    today = date.today()
    earlier = today - timedelta(days=1)
    response = client.get(
        f"/api/v1/cash-flow?period_start={today.isoformat()}&period_end={earlier.isoformat()}"
    )
    assert response.status_code == 400
