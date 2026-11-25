from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_contribution_forecast_respects_member_visibility_grants(
    client: TestClient,
) -> None:
    register(client, "contribution-forecast-scope-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    register(client, "contribution-forecast-scope-a@example.com", "Member A")
    _logout(client)
    register(client, "contribution-forecast-scope-b@example.com", "Member B")
    _logout(client)

    login(client, "contribution-forecast-scope-owner@example.com")
    headers = {"X-Household-Id": household["id"]}
    member_a = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member A",
            "role": "member",
            "relationship": "other",
            "email": "contribution-forecast-scope-a@example.com",
        },
    )
    member_b = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member B",
            "role": "member",
            "relationship": "other",
            "email": "contribution-forecast-scope-b@example.com",
        },
    )
    assert member_a.status_code == 201, member_a.text
    assert member_b.status_code == 201, member_b.text

    today = date.today()
    agreement_a = client.post(
        "/api/v1/contributions",
        headers=headers,
        json={
            "member_id": member_a.json()["id"],
            "name": "Member A contribution",
            "amount": "1000.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": today.day,
            "start_date": today.isoformat(),
        },
    )
    agreement_b = client.post(
        "/api/v1/contributions",
        headers=headers,
        json={
            "member_id": member_b.json()["id"],
            "name": "Member B contribution",
            "amount": "500.00",
            "currency": "NGN",
            "cadence": "monthly",
            "due_day": today.day,
            "start_date": today.isoformat(),
        },
    )
    assert agreement_a.status_code == 201, agreement_a.text
    assert agreement_b.status_code == 201, agreement_b.text

    household_forecast = client.get(
        "/api/v1/contributions/forecast?horizon_days=90",
        headers=headers,
    )
    assert household_forecast.status_code == 200, household_forecast.text
    household_expected = household_forecast.json()["expected"]
    _logout(client)

    login(client, "contribution-forecast-scope-a@example.com")
    own_forecast = client.get(
        "/api/v1/contributions/forecast?horizon_days=90",
        headers=headers,
    )
    assert own_forecast.status_code == 200, own_forecast.text
    assert own_forecast.json()["expected"] != household_expected
    assert {
        row["member_id"] for row in own_forecast.json()["rows"]
    } == {member_a.json()["id"]}
    _logout(client)

    login(client, "contribution-forecast-scope-owner@example.com")
    grant = client.patch(
        f"/api/v1/members/{member_a.json()['id']}",
        headers=headers,
        json={"permissions": {"view_all_contributions": True}},
    )
    assert grant.status_code == 200, grant.text
    _logout(client)

    login(client, "contribution-forecast-scope-a@example.com")
    granted_forecast = client.get(
        "/api/v1/contributions/forecast?horizon_days=90",
        headers=headers,
    )
    assert granted_forecast.status_code == 200, granted_forecast.text
    assert granted_forecast.json()["expected"] == household_expected
    assert {
        row["member_id"] for row in granted_forecast.json()["rows"]
    } == {member_a.json()["id"], member_b.json()["id"]}
