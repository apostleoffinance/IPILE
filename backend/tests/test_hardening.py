from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    client.post("/api/v1/auth/logout")


def test_export_includes_transactions(client: TestClient) -> None:
    register(client, "export-owner@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    posted = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "2500.00",
            "type": "expense",
            "date": "2026-09-14",
            "description": "Export probe",
        },
    )
    assert posted.status_code == 201, posted.text
    exported = client.get("/api/v1/export")
    assert exported.status_code == 200, exported.text
    body = exported.json()
    assert any(row["description"] == "Export probe" for row in body["transactions"])
    assert body["accounts"][0]["current_balance"] == "97500.00"


def test_partner_can_export_member_cannot(client: TestClient) -> None:
    register(client, "export-roles-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    register(client, "export-roles-partner@example.com", "Partner")
    _logout(client)
    register(client, "export-roles-member@example.com", "Member")
    _logout(client)

    login(client, "export-roles-owner@example.com")
    assert (
        client.post(
            "/api/v1/members",
            json={
                "display_name": "Partner",
                "role": "partner",
                "relationship": "spouse",
                "email": "export-roles-partner@example.com",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/members",
            json={
                "display_name": "Member",
                "role": "member",
                "relationship": "other",
                "email": "export-roles-member@example.com",
            },
        ).status_code
        == 201
    )
    _logout(client)

    headers = {"X-Household-Id": household["id"]}
    login(client, "export-roles-partner@example.com")
    assert client.get("/api/v1/export", headers=headers).status_code == 200
    _logout(client)

    login(client, "export-roles-member@example.com")
    assert client.get("/api/v1/export", headers=headers).status_code == 403


def test_owner_delete_household_blocks_access(client: TestClient) -> None:
    register(client, "delete-owner@example.com")
    household = client.get("/api/v1/households/current").json()
    deleted = client.delete("/api/v1/households/current")
    assert deleted.status_code == 204, deleted.text
    assert client.get("/api/v1/households/current").status_code == 404
    listed = client.get("/api/v1/households").json()
    assert all(row["id"] != household["id"] for row in listed)


def test_request_id_header_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id")
