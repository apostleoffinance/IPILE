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
    assert baseline.json()["parameters"]["engine_version"] == "phase3-v1"
    assert baseline.json()["parameters"]["baseline_snapshot"]["expected_contributions"] == "100000.00"
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
