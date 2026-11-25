from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_member_can_create_and_update_only_their_own_personal_accounts(
    client: TestClient,
) -> None:
    register(client, "personal-account-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    register(client, "personal-account-member-a@example.com", "Member A")
    _logout(client)
    register(client, "personal-account-member-b@example.com", "Member B")
    _logout(client)

    login(client, "personal-account-owner@example.com")
    headers = {"X-Household-Id": household["id"]}
    member_a = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member A",
            "role": "member",
            "relationship": "other",
            "email": "personal-account-member-a@example.com",
        },
    ).json()
    member_b = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member B",
            "role": "member",
            "relationship": "other",
            "email": "personal-account-member-b@example.com",
        },
    ).json()
    _logout(client)

    login(client, "personal-account-member-a@example.com")
    own = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Member A savings",
            "type": "savings",
            "access_scope": "personal",
            "owner_member_id": member_a["id"],
        },
    )
    assert own.status_code == 201, own.text
    own_id = own.json()["id"]

    shared = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Not allowed", "type": "bank"},
    )
    assert shared.status_code == 403

    other_personal = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Member B savings",
            "type": "savings",
            "access_scope": "personal",
            "owner_member_id": member_b["id"],
        },
    )
    assert other_personal.status_code == 403

    updated = client.patch(
        f"/api/v1/accounts/{own_id}",
        headers=headers,
        json={"name": "Member A emergency savings"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Member A emergency savings"

    owner_only_update = client.patch(
        f"/api/v1/accounts/{own_id}",
        headers=headers,
        json={"is_protected": True},
    )
    assert owner_only_update.status_code == 200

    _logout(client)
    login(client, "personal-account-member-b@example.com")
    hidden = client.get(f"/api/v1/accounts/{own_id}", headers=headers)
    assert hidden.status_code == 404
