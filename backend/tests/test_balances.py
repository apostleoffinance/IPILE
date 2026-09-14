from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.services.balances import account_delta, counterparty_delta
from tests.conftest import register


def test_account_delta_never_uses_float() -> None:
    delta = account_delta("income", Decimal("2000000.00"))
    assert delta == Decimal("2000000.00")
    assert isinstance(delta, Decimal)
    assert counterparty_delta("transfer", Decimal("100.00")) == Decimal("100.00")
    assert account_delta("expense", Decimal("50.00")) == Decimal("-50.00")


def _create_account(client: TestClient, name: str = "Current", opening: str = "0.00") -> dict:
    response = client.post(
        "/api/v1/accounts",
        json={"name": name, "type": "bank", "current_balance": opening},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert isinstance(body["current_balance"], str)
    return body


def test_income_expense_and_void_update_balances(client: TestClient) -> None:
    register(client, "owner@example.com")
    account = _create_account(client)
    income = client.post(
        "/api/v1/income",
        json={
            "account_id": account["id"],
            "amount": "2000000.00",
            "date": date.today().isoformat(),
            "description": "September income",
        },
    )
    assert income.status_code == 201
    assert isinstance(income.json()["amount"], str)
    after_income = client.get(f"/api/v1/accounts/{account['id']}").json()
    assert after_income["current_balance"] == "2000000.00"

    expense = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "150000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "description": "Food",
        },
    )
    assert expense.status_code == 201
    after_spend = client.get(f"/api/v1/accounts/{account['id']}").json()
    assert after_spend["current_balance"] == "1850000.00"

    voided = client.post(f"/api/v1/transactions/{expense.json()['id']}/void")
    assert voided.status_code == 200
    restored = client.get(f"/api/v1/accounts/{account['id']}").json()
    assert restored["current_balance"] == "2000000.00"


def test_transfer_does_not_change_household_net_cash(client: TestClient) -> None:
    register(client, "owner@example.com")
    current = _create_account(client, "Current", "1000000.00")
    savings = _create_account(client, "Savings", "500000.00")
    transfer = client.post(
        "/api/v1/transactions",
        json={
            "account_id": current["id"],
            "counterparty_account_id": savings["id"],
            "amount": "200000.00",
            "type": "transfer",
            "date": date.today().isoformat(),
        },
    )
    assert transfer.status_code == 201, transfer.text
    after_current = client.get(f"/api/v1/accounts/{current['id']}").json()
    after_savings = client.get(f"/api/v1/accounts/{savings['id']}").json()
    assert after_current["current_balance"] == "800000.00"
    assert after_savings["current_balance"] == "700000.00"
    net = Decimal(after_current["current_balance"]) + Decimal(after_savings["current_balance"])
    assert net == Decimal("1500000.00")


def test_rejects_negative_amount(client: TestClient) -> None:
    register(client, "owner@example.com")
    account = _create_account(client)
    response = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "-10.00",
            "type": "expense",
            "date": date.today().isoformat(),
        },
    )
    assert response.status_code == 422
