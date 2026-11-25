from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


def test_purchase_check_returns_explainable_decision_and_impact(
    client: TestClient,
) -> None:
    register(client, "decision-explain-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    )
    assert account.status_code == 201, account.text

    response = client.post(
        "/api/v1/purchase-checks",
        json={"amount": "100000.00", "account_id": account.json()["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "proceed"
    assert body["affordable"] is True
    assert body["impact"]["current_sts_before"] == "500000.00"
    assert body["impact"]["current_sts_after"] == "400000.00"
    assert body["impact"]["minimum_buffer"] == "90000.00"
    assert body["reasons"]
    assert any("fits within current Safe to Spend" in reason for reason in body["reasons"])


def test_purchase_check_rejects_using_protected_account(
    client: TestClient,
) -> None:
    register(client, "decision-protected-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={
            "name": "Emergency reserve",
            "type": "bank",
            "current_balance": "500000.00",
            "is_protected": True,
        },
    )
    assert account.status_code == 201, account.text
    response = client.post(
        "/api/v1/purchase-checks",
        json={"amount": "100000.00", "account_id": account.json()["id"]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "do_not_proceed"
    assert body["affordable"] is False
    assert any("protected" in reason.lower() for reason in body["reasons"])


def test_simulation_applies_contribution_stress_without_mutating_accounts(
    client: TestClient,
) -> None:
    register(client, "decision-contribution-sim@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    ).json()
    assert account["id"]
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Contributor", "role": "member"},
    ).json()
    agreement = client.post(
        "/api/v1/contributions",
        json={
            "member_id": member["id"],
            "name": "Monthly household contribution",
            "amount": "100000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": date.today().day,
            "start_date": date.today().isoformat(),
        },
    )
    assert agreement.status_code == 201, agreement.text
    before = client.get("/api/v1/accounts").json()

    baseline = client.post(
        "/api/v1/simulations",
        json={"horizon_months": 2, "contribution_change_rate": "0"},
    )
    stressed = client.post(
        "/api/v1/simulations",
        json={"horizon_months": 2, "contribution_change_rate": "-0.50"},
    )
    assert baseline.status_code == 201, baseline.text
    assert stressed.status_code == 201, stressed.text
    assert baseline.json()["months"][0]["contributions"] == "100000.00"
    assert stressed.json()["months"][0]["contributions"] == "50000.00"
    assert baseline.json()["parameters"]["engine_version"] == "phase3-v2"
    baseline_inputs = baseline.json()["parameters"]["baseline_snapshot"]
    assert baseline_inputs["expected_contributions"] == "100000.00"
    assert Decimal(stressed.json()["months"][0]["income"]) == (
        Decimal(baseline.json()["months"][0]["income"]) - Decimal("50000.00")
    )
    assert client.get("/api/v1/accounts").json() == before



def test_purchase_check_names_obligations_put_at_risk(
    client: TestClient,
) -> None:
    register(client, "decision-obligation-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    )
    assert account.status_code == 201, account.text
    obligation = client.post(
        "/api/v1/obligations",
        json={
            "name": "School fees",
            "amount": "400000.00",
            "frequency": "monthly",
            "next_due_date": (date.today()).isoformat(),
            "priority": "critical",
        },
    )
    assert obligation.status_code == 201, obligation.text
    response = client.post(
        "/api/v1/purchase-checks",
        json={"amount": "450000.00"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"] == "do_not_proceed"
    assert any("School fees" in row for row in body["obligations_affected"])


def test_contribution_change_rate_cannot_reduce_below_zero() -> None:
    import pytest
    from pydantic import ValidationError

    from app.schemas.simulation import SimulationIn

    with pytest.raises(ValidationError):
        SimulationIn(contribution_change_rate="-1.01")


def test_purchase_check_rejects_personal_account(
    client: TestClient,
) -> None:
    register(client, "decision-personal-account@example.com")
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Member", "role": "member"},
    )
    assert member.status_code == 201, member.text
    personal = client.post(
        "/api/v1/accounts",
        json={
            "name": "Personal current",
            "type": "bank",
            "access_scope": "personal",
            "owner_member_id": member.json()["id"],
            "current_balance": "500000.00",
        },
    )
    assert personal.status_code == 201, personal.text
    response = client.post(
        "/api/v1/purchase-checks",
        json={"amount": "100000.00", "account_id": personal.json()["id"]},
    )
    assert response.status_code == 400
    assert "shared household accounts" in response.json()["detail"]


def test_simulation_uses_shared_spendable_cash_and_remaining_income(
    client: TestClient,
) -> None:
    register(client, "decision-shared-cash@example.com")
    shared = client.post(
        "/api/v1/accounts",
        json={"name": "Household current", "type": "bank", "current_balance": "1000000.00"},
    )
    assert shared.status_code == 201, shared.text
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Member", "role": "member"},
    )
    assert member.status_code == 201, member.text
    personal = client.post(
        "/api/v1/accounts",
        json={
            "name": "Personal current",
            "type": "bank",
            "access_scope": "personal",
            "owner_member_id": member.json()["id"],
            "current_balance": "500000.00",
        },
    )
    assert personal.status_code == 201, personal.text
    source = client.post(
        "/api/v1/income/sources",
        json={
            "member_id": member.json()["id"],
            "name": "Household salary",
            "expected_amount": "200000.00",
            "frequency": "monthly",
        },
    )
    assert source.status_code == 201, source.text
    received = client.post(
        "/api/v1/transactions",
        json={
            "account_id": shared.json()["id"],
            "amount": "50000.00",
            "type": "income",
            "date": date.today().isoformat(),
            "member_id": member.json()["id"],
            "access_scope": "shared",
            "income_source_id": source.json()["id"],
        },
    )
    assert received.status_code == 201, received.text
    accounts_before = client.get("/api/v1/accounts").json()
    transactions_before = client.get("/api/v1/transactions").json()

    response = client.post("/api/v1/simulations", json={"horizon_months": 2})
    assert response.status_code == 201, response.text
    body = response.json()
    baseline = body["parameters"]["baseline_snapshot"]
    assert baseline["cash"] == "1050000.00"
    assert body["parameters"]["cash_basis"] == "current_safe_to_spend"
    assert baseline["expected_income"] == "200000.00"
    assert baseline["first_month_income"] == "150000.00"
    assert body["months"][0]["income"] == "150000.00"
    assert body["months"][1]["income"] == "200000.00"
    assert client.get("/api/v1/accounts").json() == accounts_before
    assert client.get("/api/v1/transactions").json() == transactions_before


def test_household_budget_spend_excludes_personal_transactions(
    client: TestClient,
) -> None:
    register(client, "decision-household-budget-scope@example.com")
    category = client.post(
        "/api/v1/categories",
        json={"name": "Household food", "kind": "expense"},
    )
    assert category.status_code == 201, category.text
    budget = client.post(
        "/api/v1/budget",
        json={
            "name": "Household monthly budget",
            "period_type": "monthly",
            "status": "active",
            "categories": [
                {"category_id": category.json()["id"], "allocated_amount": "100000.00"}
            ],
        },
    )
    assert budget.status_code == 201, budget.text
    member = client.post(
        "/api/v1/members",
        json={"display_name": "Member", "role": "member"},
    )
    assert member.status_code == 201, member.text
    shared = client.post(
        "/api/v1/accounts",
        json={"name": "Household account", "type": "bank", "current_balance": "1000000.00"},
    )
    personal = client.post(
        "/api/v1/accounts",
        json={
            "name": "Personal account",
            "type": "bank",
            "access_scope": "personal",
            "owner_member_id": member.json()["id"],
            "current_balance": "500000.00",
        },
    )
    assert shared.status_code == 201, shared.text
    assert personal.status_code == 201, personal.text
    personal_spend = client.post(
        "/api/v1/transactions",
        json={
            "account_id": personal.json()["id"],
            "amount": "50000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": category.json()["id"],
            "member_id": member.json()["id"],
            "access_scope": "personal",
        },
    )
    shared_spend = client.post(
        "/api/v1/transactions",
        json={
            "account_id": shared.json()["id"],
            "amount": "20000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": category.json()["id"],
            "access_scope": "shared",
        },
    )
    assert personal_spend.status_code == 201, personal_spend.text
    assert shared_spend.status_code == 201, shared_spend.text
    budgets = client.get("/api/v1/budget")
    assert budgets.status_code == 200, budgets.text
    household_budget = next(row for row in budgets.json() if row["id"] == budget.json()["id"])
    assert household_budget["spent_total"] == "20000.00"
    assert household_budget["remaining_total"] == "80000.00"
