from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_member_obligations_calendar_and_overview_are_member_scoped(
    client: TestClient,
) -> None:
    register(client, "obligation-scope-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    register(client, "obligation-scope-a@example.com", "Member A")
    _logout(client)
    register(client, "obligation-scope-b@example.com", "Member B")
    _logout(client)

    login(client, "obligation-scope-owner@example.com")
    headers = {"X-Household-Id": household["id"]}
    member_a = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member A",
            "role": "member",
            "relationship": "other",
            "email": "obligation-scope-a@example.com",
        },
    ).json()
    member_b = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member B",
            "role": "member",
            "relationship": "other",
            "email": "obligation-scope-b@example.com",
        },
    ).json()

    due = date.today() + timedelta(days=5)
    own = client.post(
        "/api/v1/obligations",
        headers=headers,
        json={
            "name": "Member A tuition",
            "amount": "10000.00",
            "next_due_date": due.isoformat(),
            "beneficiary_member_id": member_a["id"],
        },
    )
    other = client.post(
        "/api/v1/obligations",
        headers=headers,
        json={
            "name": "Member B tuition",
            "amount": "20000.00",
            "next_due_date": (due + timedelta(days=1)).isoformat(),
            "beneficiary_member_id": member_b["id"],
        },
    )
    shared = client.post(
        "/api/v1/obligations",
        headers=headers,
        json={
            "name": "Household electricity",
            "amount": "5000.00",
            "next_due_date": (due + timedelta(days=2)).isoformat(),
        },
    )
    assert own.status_code == 201, own.text
    assert other.status_code == 201, other.text
    assert shared.status_code == 201, shared.text
    _logout(client)

    login(client, "obligation-scope-a@example.com")
    obligations = client.get("/api/v1/obligations", headers=headers)
    assert obligations.status_code == 200, obligations.text
    names = {row["name"] for row in obligations.json()}
    assert names == {"Member A tuition", "Household electricity"}

    hidden = client.get(
        f"/api/v1/obligations/{other.json()['id']}",
        headers=headers,
    )
    assert hidden.status_code == 404

    calendar = client.get("/api/v1/calendar", headers=headers)
    assert calendar.status_code == 200, calendar.text
    calendar_titles = {row["title"] for row in calendar.json()}
    assert "Member A tuition" in calendar_titles
    assert "Household electricity" in calendar_titles
    assert "Member B tuition" not in calendar_titles

    overview = client.get("/api/v1/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    upcoming_titles = {row["title"] for row in overview.json()["upcoming_obligations"]}
    assert "Member A tuition" in upcoming_titles
    assert "Household electricity" in upcoming_titles
    assert "Member B tuition" not in upcoming_titles
