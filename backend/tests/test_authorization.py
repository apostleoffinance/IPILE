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


def test_advisor_can_read_cannot_write(client: TestClient) -> None:
    register(client, "owner-advisor@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    account = client.post("/api/v1/accounts", json={"name": "Main", "type": "bank"}).json()
    _logout(client)

    register(client, "advisor-roles@example.com", "Advisor")
    _logout(client)

    login(client, "owner-advisor@example.com")
    assert (
        client.post(
            "/api/v1/members",
            json={
                "display_name": "Advisor",
                "role": "advisor",
                "relationship": "other",
                "email": "advisor-roles@example.com",
            },
        ).status_code
        == 201
    )
    _logout(client)

    headers = {"X-Household-Id": household["id"]}
    login(client, "advisor-roles@example.com")
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



def test_members_cannot_read_each_others_personal_finances(client: TestClient) -> None:
    register(client, "privacy-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    register(client, "privacy-a@example.com", "Member A")
    _logout(client)
    register(client, "privacy-b@example.com", "Member B")
    _logout(client)

    login(client, "privacy-owner@example.com")
    headers = {"X-Household-Id": household["id"]}
    member_a = client.post("/api/v1/members", headers=headers, json={
        "display_name": "Member A", "role": "member", "relationship": "other", "email": "privacy-a@example.com"
    }).json()
    member_b = client.post("/api/v1/members", headers=headers, json={
        "display_name": "Member B", "role": "member", "relationship": "other", "email": "privacy-b@example.com"
    }).json()
    shared = client.post("/api/v1/accounts", headers=headers, json={"name": "Household", "type": "bank"}).json()
    private_a = client.post("/api/v1/accounts", headers=headers, json={
        "name": "A private", "type": "bank", "access_scope": "personal", "owner_member_id": member_a["id"]
    })
    private_b = client.post("/api/v1/accounts", headers=headers, json={
        "name": "B private", "type": "bank", "access_scope": "personal", "owner_member_id": member_b["id"]
    })
    assert private_a.status_code == 201, private_a.text
    assert private_b.status_code == 201, private_b.text
    private_a = private_a.json()
    private_b = private_b.json()
    tx_a = client.post("/api/v1/transactions", headers=headers, json={
        "account_id": private_a["id"], "amount": "41.00", "type": "expense",
        "date": date.today().isoformat(), "member_id": member_a["id"], "access_scope": "personal",
        "description": "A private purchase",
    })
    tx_b = client.post("/api/v1/transactions", headers=headers, json={
        "account_id": private_b["id"], "amount": "92.00", "type": "expense",
        "date": date.today().isoformat(), "member_id": member_b["id"], "access_scope": "personal",
        "description": "B private purchase",
    })
    assert tx_a.status_code == 201, tx_a.text
    assert tx_b.status_code == 201, tx_b.text
    tx_b_id = tx_b.json()["id"]
    _logout(client)

    login(client, "privacy-a@example.com")
    visible_accounts = client.get("/api/v1/accounts", headers=headers).json()
    visible_ids = {row["id"] for row in visible_accounts}
    assert shared["id"] in visible_ids
    assert private_a["id"] in visible_ids
    assert private_b["id"] not in visible_ids
    assert client.get(f"/api/v1/accounts/{private_b['id']}", headers=headers).status_code == 404

    visible_transactions = client.get("/api/v1/transactions", headers=headers).json()
    assert {row["id"] for row in visible_transactions}.isdisjoint({tx_b_id})
    assert client.get(f"/api/v1/transactions/{tx_b_id}", headers=headers).status_code == 404
    overview = client.get("/api/v1/overview", headers=headers)
    assert overview.status_code == 200, overview.text
    overview_data = overview.json()
    assert private_b["id"] not in {row["id"] for row in overview_data["accounts"]}
    assert tx_b_id not in {row["id"] for row in overview_data["recent_transactions"]}
