from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    client.post("/api/v1/auth/logout")


def test_partner_can_write_and_viewer_cannot(client: TestClient) -> None:
    register(client, "owner-roles@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    account = client.post("/api/v1/accounts", json={"name": "Main", "type": "bank"}).json()
    _logout(client)

    register(client, "partner-roles@example.com", "Partner")
    _logout(client)
    register(client, "viewer-roles@example.com", "Viewer")
    _logout(client)

    login(client, "owner-roles@example.com")
    assert (
        client.post(
            "/api/v1/members",
            json={
                "display_name": "Partner",
                "role": "partner",
                "relationship": "spouse",
                "email": "partner-roles@example.com",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/members",
            json={
                "display_name": "Viewer",
                "role": "viewer",
                "relationship": "other",
                "email": "viewer-roles@example.com",
            },
        ).status_code
        == 201
    )
    _logout(client)

    headers = {"X-Household-Id": household["id"]}
    login(client, "partner-roles@example.com")
    write = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "amount": "25.00",
            "type": "expense",
            "date": date.today().isoformat(),
        },
    )
    assert write.status_code == 201, write.text
    _logout(client)

    login(client, "viewer-roles@example.com")
    readable = client.get("/api/v1/accounts", headers=headers)
    assert readable.status_code == 200
    blocked = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "amount": "10.00",
            "type": "expense",
            "date": date.today().isoformat(),
        },
    )
    assert blocked.status_code == 403


def test_member_cannot_write_for_someone_else(client: TestClient) -> None:
    register(client, "owner-member@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    owner_member = client.get("/api/v1/members").json()[0]
    account = client.post("/api/v1/accounts", json={"name": "Main", "type": "bank"}).json()
    _logout(client)

    register(client, "limited-member@example.com", "Member")
    _logout(client)
    login(client, "owner-member@example.com")
    member = client.post(
        "/api/v1/members",
        json={
            "display_name": "Member",
            "role": "member",
            "relationship": "other",
            "email": "limited-member@example.com",
        },
    ).json()
    _logout(client)

    login(client, "limited-member@example.com")
    headers = {"X-Household-Id": household["id"]}
    own = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "amount": "12.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "member_id": member["id"],
        },
    )
    assert own.status_code == 201, own.text
    other = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "amount": "12.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "member_id": owner_member["id"],
        },
    )
    assert other.status_code == 403
