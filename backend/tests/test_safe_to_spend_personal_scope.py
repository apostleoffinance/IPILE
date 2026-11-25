from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


def test_household_safe_to_spend_excludes_personal_cash_and_transactions(
    client: TestClient,
) -> None:
    register(client, "household-sts-scope-owner@example.com", "Owner")
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Member", "role": "member"},
    )
    assert member.status_code == 201, member.text
    member_id = member.json()["id"]
    shared = client.post(
        "/api/v1/accounts",
        json={"name": "Household current", "type": "bank", "current_balance": "1000000.00"},
    )
    assert shared.status_code == 201, shared.text
    personal = client.post(
        "/api/v1/accounts",
        json={
            "name": "Private reserve",
            "type": "bank",
            "access_scope": "personal",
            "owner_member_id": member_id,
            "current_balance": "500000.00",
            "is_protected": True,
            "include_in_safe_to_spend": False,
        },
    )
    assert personal.status_code == 201, personal.text

    source = client.post(
        "/api/v1/income/sources",
        json={
            "member_id": member_id,
            "name": "Member personal salary",
            "expected_amount": "200000.00",
            "frequency": "monthly",
        },
    )
    assert source.status_code == 201, source.text
    personal_income = client.post(
        "/api/v1/transactions",
        json={
            "account_id": personal.json()["id"],
            "amount": "50000.00",
            "type": "income",
            "date": date.today().isoformat(),
            "member_id": member_id,
            "access_scope": "personal",
            "income_source_id": source.json()["id"],
        },
    )
    assert personal_income.status_code == 201, personal_income.text
    recurring_personal_bill = client.post(
        "/api/v1/recurring",
        json={
            "account_id": personal.json()["id"],
            "amount": "30000.00",
            "type": "expense",
            "frequency": "monthly",
            "next_date": date.today().isoformat(),
            "member_id": member_id,
        },
    )
    assert recurring_personal_bill.status_code == 201, recurring_personal_bill.text
    pending_personal_expense = client.post(
        "/api/v1/transactions",
        json={
            "account_id": personal.json()["id"],
            "amount": "10000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "member_id": member_id,
            "access_scope": "personal",
            "status": "pending",
        },
    )
    assert pending_personal_expense.status_code == 201, pending_personal_expense.text

    response = client.get("/api/v1/safe-to-spend")
    assert response.status_code == 200, response.text
    body = response.json()
    components = body["components"]
    assert Decimal(components["liquid_cash"]) == Decimal("1000000.00")
    assert Decimal(components["pending_transactions"]) == Decimal("0.00")
    assert Decimal(components["protected_savings"]) == Decimal("0.00")
    assert Decimal(components["upcoming_bills"]) == Decimal("0.00")
    assert Decimal(components["expected_income"]) == Decimal("200000.00")
    assert Decimal(body["current"]) == Decimal("1000000.00")
