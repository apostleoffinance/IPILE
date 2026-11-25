from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_non_privileged_roles_cannot_read_household_wide_financial_views(
    client: TestClient,
) -> None:
    register(client, "privacy-views-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    members = []
    for role in ("member", "viewer", "advisor"):
        email = f"privacy-views-{role}@example.com"
        register(client, email, role.title())
        _logout(client)
        members.append((role, email))

    login(client, "privacy-views-owner@example.com")
    headers = {"X-Household-Id": household["id"]}
    for role, email in members:
        response = client.post(
            "/api/v1/members",
            headers=headers,
            json={
                "display_name": role.title(),
                "role": role,
                "relationship": "other",
                "email": email,
            },
        )
        assert response.status_code == 201, response.text
    _logout(client)

    household_financial_views = (
        "/api/v1/businesses",
        "/api/v1/calendar",
        "/api/v1/goals",
        "/api/v1/funds",
        "/api/v1/income/sources",
        "/api/v1/income",
        "/api/v1/obligations",
        "/api/v1/recurring",
        "/api/v1/alerts",
        "/api/v1/notifications",
        "/api/v1/contributions",
    )
    for role, email in members:
        login(client, email)
        allowed_member_views = {"/api/v1/calendar", "/api/v1/obligations"}
        for endpoint in household_financial_views:
            if role == "member" and endpoint in allowed_member_views:
                continue
            response = client.get(endpoint, headers=headers)
            assert response.status_code == 403, (
                f"{role} unexpectedly accessed {endpoint}: {response.status_code} "
                f"{response.text}"
            )
        if role == "member":
            assert client.get("/api/v1/obligations", headers=headers).status_code == 200
            assert client.get("/api/v1/calendar", headers=headers).status_code == 200
        _logout(client)
