from uuid import uuid4

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _attach_member(client: TestClient, owner_email: str, member_email: str) -> dict:
    register(client, owner_email, "Owner")
    household = client.get("/api/v1/households/current").json()
    client.post("/api/v1/auth/logout")
    register(client, member_email, "Member")
    client.post("/api/v1/auth/logout")
    login(client, owner_email)
    response = client.post(
        "/api/v1/members",
        json={
            "display_name": "Member",
            "role": "member",
            "relationship": "other",
            "email": member_email,
        },
    )
    assert response.status_code == 201, response.text
    client.post("/api/v1/auth/logout")
    login(client, member_email)
    return household


def test_member_cannot_read_household_wide_financial_aggregates(client: TestClient) -> None:
    household = _attach_member(
        client, "phase1-owner@example.com", "phase1-member@example.com"
    )
    headers = {"X-Household-Id": household["id"]}

    endpoints = [
        "/api/v1/net-worth",
        "/api/v1/assets",
        "/api/v1/liabilities",
        "/api/v1/investments",
        "/api/v1/safe-to-spend",
        "/api/v1/financial-health",
        "/api/v1/financial-health/explain",
        "/api/v1/insights",
        "/api/v1/snapshots",
        "/api/v1/reports/monthly",
        "/api/v1/reports/quarterly",
        "/api/v1/reports/annual",
        "/api/v1/reports/giving",
        "/api/v1/export",
        "/api/v1/cash-flow",
        "/api/v1/debts/strategies",
        "/api/v1/allocations/latest",
        "/api/v1/allocation-rules",
        "/api/v1/giving/summary",
        "/api/v1/giving",
        "/api/v1/budget",
        f"/api/v1/simulations/{uuid4()}",
        "/api/v1/imports/review",
    ]
    for endpoint in endpoints:
        response = client.get(endpoint, headers=headers)
        assert response.status_code == 403, (endpoint, response.status_code, response.text)

    purchase_check = client.post(
        "/api/v1/purchase-checks",
        headers=headers,
        json={"amount": "1000.00"},
    )
    assert purchase_check.status_code == 403

    simulation = client.post(
        "/api/v1/simulations",
        headers=headers,
        json={"unexpected_expense": "1000.00", "horizon_months": 1},
    )
    assert simulation.status_code == 403

    ai_explanation = client.post("/api/v1/ai/explain", headers=headers)
    assert ai_explanation.status_code == 403


def test_member_overview_redacts_household_wide_derived_finances(
    client: TestClient,
) -> None:
    household = _attach_member(
        client, "phase1-overview-owner@example.com", "phase1-overview-member@example.com"
    )
    headers = {"X-Household-Id": household["id"]}
    overview = client.get("/api/v1/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    body = overview.json()
    assert body["wealth"] is None
    assert body["safe_to_spend"] is None
    assert body["allocation"] is None
    assert body["allocated_total"] is None
    assert body["surplus"] is None
    assert body["health"] is None
    assert body["foundation"] is None
    assert body["upcoming_obligations"] == []
