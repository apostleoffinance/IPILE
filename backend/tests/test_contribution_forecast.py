from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


def test_contribution_forecast_is_separate_from_unverified_receipts(
    client: TestClient,
) -> None:
    register(client, "contribution-forecast-owner@example.com")
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Ada", "role": "member"},
    ).json()
    start = date.today()
    agreement = client.post(
        "/api/v1/contributions",
        json={
            "member_id": member["id"],
            "name": "Monthly household contribution",
            "amount": "50000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": start.day,
            "start_date": start.isoformat(),
        },
    )
    assert agreement.status_code == 201, agreement.text

    # A record without a linked ledger transaction is only a reported receipt.
    # It must not be treated as verified cash or reduce forecast outstanding.
    record = client.post(
        f"/api/v1/contributions/{agreement.json()['id']}/records",
        json={
            "amount": "20000.00",
            "contributed_on": start.isoformat(),
            "note": "Reported, not yet reconciled",
        },
    )
    assert record.status_code == 201, record.text

    forecast = client.get("/api/v1/contributions/forecast?horizon_days=90")
    assert forecast.status_code == 200, forecast.text
    body = forecast.json()
    assert body["currency"] == "NGN"
    assert Decimal(body["expected"]) >= Decimal("50000.00")
    assert Decimal(body["verified_received"]) == Decimal("0.00")
    assert Decimal(body["outstanding"]) == Decimal(body["expected"])


def test_contribution_forecast_counts_only_cleared_linked_income(
    client: TestClient,
) -> None:
    register(client, "contribution-verified-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "0.00"},
    ).json()
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Ada", "role": "member"},
    ).json()
    start = date.today()
    agreement = client.post(
        "/api/v1/contributions",
        json={
            "member_id": member["id"],
            "name": "Monthly contribution",
            "amount": "50000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": start.day,
            "start_date": start.isoformat(),
        },
    ).json()
    transaction = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "20000.00",
            "type": "income",
            "date": start.isoformat(),
            "member_id": member["id"],
            "description": "Contribution received",
        },
    )
    assert transaction.status_code == 201, transaction.text
    linked = client.post(
        f"/api/v1/contributions/{agreement['id']}/records",
        json={
            "amount": "20000.00",
            "contributed_on": start.isoformat(),
            "transaction_id": transaction.json()["id"],
        },
    )
    assert linked.status_code == 201, linked.text

    forecast = client.get("/api/v1/contributions/forecast?horizon_days=90")
    assert forecast.status_code == 200, forecast.text
    body = forecast.json()
    assert Decimal(body["verified_received"]) == Decimal("20000.00")
    assert Decimal(body["outstanding"]) == Decimal(body["expected"]) - Decimal("20000.00")


def test_contribution_forecast_rejects_invalid_horizon(client: TestClient) -> None:
    register(client, "contribution-horizon-owner@example.com")
    response = client.get("/api/v1/contributions/forecast?horizon_days=0")
    assert response.status_code == 422


def test_contribution_link_requires_cleared_income_and_is_unique(
    client: TestClient,
) -> None:
    register(client, "contribution-link-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "0.00"},
    ).json()
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Ada", "role": "member"},
    ).json()
    today = date.today()
    agreement = client.post(
        "/api/v1/contributions",
        json={
            "member_id": member["id"],
            "name": "Monthly contribution",
            "amount": "10000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": today.day,
            "start_date": today.isoformat(),
        },
    ).json()

    pending = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "10000.00",
            "type": "income",
            "date": today.isoformat(),
            "status": "pending",
            "member_id": member["id"],
        },
    )
    assert pending.status_code == 201, pending.text
    rejected = client.post(
        f"/api/v1/contributions/{agreement['id']}/records",
        json={
            "amount": "10000.00",
            "contributed_on": today.isoformat(),
            "transaction_id": pending.json()["id"],
        },
    )
    assert rejected.status_code == 400

    cleared = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "10000.00",
            "type": "income",
            "date": today.isoformat(),
            "status": "cleared",
            "member_id": member["id"],
        },
    )
    assert cleared.status_code == 201, cleared.text
    payload = {
        "amount": "10000.00",
        "contributed_on": today.isoformat(),
        "transaction_id": cleared.json()["id"],
    }
    first = client.post(
        f"/api/v1/contributions/{agreement['id']}/records",
        json=payload,
    )
    assert first.status_code == 201, first.text
    duplicate = client.post(
        f"/api/v1/contributions/{agreement['id']}/records",
        json=payload,
    )
    assert duplicate.status_code == 409


def test_expected_contributions_change_forecast_not_current_safe_to_spend(
    client: TestClient,
) -> None:
    register(client, "contribution-sts-owner@example.com")
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Ada", "role": "member"},
    ).json()
    today = date.today()
    agreement = client.post(
        "/api/v1/contributions",
        json={
            "member_id": member["id"],
            "name": "Expected monthly contribution",
            "amount": "100000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": today.day,
            "start_date": today.isoformat(),
        },
    )
    assert agreement.status_code == 201, agreement.text

    snapshot = client.get("/api/v1/safe-to-spend")
    assert snapshot.status_code == 200, snapshot.text
    body = snapshot.json()
    assert Decimal(body["components"]["expected_contributions"]) == Decimal("100000.00")
    # The projection may include the expected payment; actual current cash may not.
    assert Decimal(body["current"]) == Decimal("0.00")
    assert Decimal(body["forecast"]) < Decimal(body["components"]["expected_contributions"])
