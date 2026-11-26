from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.services import cash_flow
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


def test_cash_flow_historical_native_balance_uses_account_currency_snapshot(
    client: TestClient, monkeypatch
) -> None:
    register(client, "cashflow-multi-currency@example.com")
    foreign = client.post(
        "/api/v1/accounts",
        json={
            "name": "USD account",
            "type": "bank",
            "currency": "USD",
            "current_balance": "100.00",
        },
    )
    assert foreign.status_code == 201, foreign.text
    account = foreign.json()
    today = date.today()
    past = today - timedelta(days=2)
    transaction = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "20.00",
            "type": "expense",
            "date": today.isoformat(),
        },
    )
    assert transaction.status_code == 201, transaction.text

    def fake_conversion(db, household_obj, amount, currency, on_date):
        assert currency == "USD"
        assert on_date == past - timedelta(days=1)
        return (Decimal(str(amount)) * Decimal("0.75")).quantize(Decimal("0.01"))

    monkeypatch.setattr(cash_flow, "amount_in_base_currency", fake_conversion)
    response = client.get(
        f"/api/v1/cash-flow?period_start={past.isoformat()}&period_end={past.isoformat()}"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # Future expense is reversed in native USD before valuing the reconstructed
    # $100 historical balance at the historical rate of 0.75.
    assert body["closing_cash"] == "75.00"


def test_cash_flow_reverses_foreign_transfer_using_destination_native_amount(
    client: TestClient, monkeypatch
) -> None:
    register(client, "cashflow-cross-transfer@example.com")
    usd = client.post(
        "/api/v1/accounts",
        json={"name": "USD", "type": "bank", "currency": "USD", "current_balance": "200.00"},
    )
    eur = client.post(
        "/api/v1/accounts",
        json={"name": "EUR", "type": "bank", "currency": "EUR", "current_balance": "0.00"},
    )
    assert usd.status_code == 201, usd.text
    assert eur.status_code == 201, eur.text
    today = date.today()
    past = today - timedelta(days=1)
    transfer = client.post(
        "/api/v1/transactions",
        json={
            "account_id": usd.json()["id"],
            "counterparty_account_id": eur.json()["id"],
            "amount": "100.00",
            "type": "transfer",
            "date": today.isoformat(),
        },
    )
    assert transfer.status_code == 201, transfer.text
    transfer_body = transfer.json()
    assert Decimal(transfer_body["counterparty_amount"]) > Decimal("0")

    def convert(db, household, amount, currency, on_date):
        assert on_date == past - timedelta(days=1)
        rates = {"USD": Decimal("0.80"), "EUR": Decimal("0.90")}
        return (Decimal(str(amount)) * rates[currency]).quantize(Decimal("0.01"))

    monkeypatch.setattr(cash_flow, "amount_in_base_currency", convert)
    response = client.get(
        f"/api/v1/cash-flow?period_start={past.isoformat()}&period_end={past.isoformat()}"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    expected = (
        Decimal("200.00") * Decimal("0.80")
        + Decimal("0.00") * Decimal("0.90")
    )
    assert Decimal(body["closing_cash"]) == expected
