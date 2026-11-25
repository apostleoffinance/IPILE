from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


def test_edited_linked_income_no_longer_verifies_contribution_receipt(
    client: TestClient,
) -> None:
    register(client, "contribution-edited-transaction@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "0.00"},
    ).json()
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Contributor", "role": "member"},
    ).json()
    today = date.today()
    agreement = client.post(
        "/api/v1/contributions",
        json={
            "member_id": member["id"],
            "name": "Monthly contribution",
            "amount": "50000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": today.day,
            "start_date": today.isoformat(),
        },
    ).json()
    transaction = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "20000.00",
            "type": "income",
            "date": today.isoformat(),
            "member_id": member["id"],
            "description": "Contribution received",
        },
    )
    assert transaction.status_code == 201, transaction.text
    linked = client.post(
        f"/api/v1/contributions/{agreement['id']}/records",
        json={
            "amount": "20000.00",
            "contributed_on": today.isoformat(),
            "transaction_id": transaction.json()["id"],
        },
    )
    assert linked.status_code == 201, linked.text

    edited = client.patch(
        f"/api/v1/transactions/{transaction.json()['id']}",
        json={"amount": "30000.00"},
    )
    assert edited.status_code == 200, edited.text

    forecast = client.get("/api/v1/contributions/forecast?horizon_days=90")
    assert forecast.status_code == 200, forecast.text
    body = forecast.json()
    assert Decimal(body["verified_received"]) == Decimal("0.00")
    assert Decimal(body["outstanding"]) == Decimal(body["expected"])


def test_personal_income_cannot_verify_shared_household_contribution(
    client: TestClient,
) -> None:
    register(client, "contribution-personal-income@example.com")
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Contributor", "role": "member"},
    ).json()
    account = client.post(
        "/api/v1/accounts",
        json={
            "name": "Personal account",
            "type": "bank",
            "current_balance": "0.00",
            "access_scope": "personal",
            "owner_member_id": member["id"],
        },
    )
    assert account.status_code == 201, account.text
    today = date.today()
    agreement = client.post(
        "/api/v1/contributions",
        json={
            "member_id": member["id"],
            "name": "Monthly household contribution",
            "amount": "50000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": today.day,
            "start_date": today.isoformat(),
        },
    )
    assert agreement.status_code == 201, agreement.text
    transaction = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account.json()["id"],
            "amount": "20000.00",
            "type": "income",
            "date": today.isoformat(),
            "member_id": member["id"],
            "access_scope": "personal",
            "description": "Personal income",
        },
    )
    assert transaction.status_code == 201, transaction.text
    linked = client.post(
        f"/api/v1/contributions/{agreement.json()['id']}/records",
        json={
            "amount": "20000.00",
            "contributed_on": today.isoformat(),
            "transaction_id": transaction.json()["id"],
        },
    )
    assert linked.status_code == 400
    assert "shared income transactions" in linked.json()["detail"]
