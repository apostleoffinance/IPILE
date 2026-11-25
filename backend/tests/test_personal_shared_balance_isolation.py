from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_personal_transactions_cannot_change_shared_account_balances(
    client: TestClient,
) -> None:
    register(client, "scope-owner@example.com", "Owner")
    household = client.get("/api/v1/households/current").json()
    _logout(client)

    register(client, "scope-member-a@example.com", "Member A")
    _logout(client)
    register(client, "scope-member-b@example.com", "Member B")
    _logout(client)

    login(client, "scope-owner@example.com")
    headers = {"X-Household-Id": household["id"]}
    member_a = client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member A",
            "role": "member",
            "relationship": "other",
            "email": "scope-member-a@example.com",
        },
    ).json()
    client.post(
        "/api/v1/members",
        headers=headers,
        json={
            "display_name": "Member B",
            "role": "member",
            "relationship": "other",
            "email": "scope-member-b@example.com",
        },
    )
    shared = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={"name": "Household", "type": "bank", "current_balance": "1000.00"},
    ).json()
    personal = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Member A private",
            "type": "bank",
            "access_scope": "personal",
            "owner_member_id": member_a["id"],
            "current_balance": "500.00",
        },
    ).json()
    assert personal["access_scope"] == "personal"
    _logout(client)

    login(client, "scope-member-a@example.com")
    tx_date = date.today().isoformat()
    private_on_shared = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": shared["id"],
            "amount": "50.00",
            "type": "expense",
            "date": tx_date,
            "member_id": member_a["id"],
            "access_scope": "personal",
        },
    )
    assert private_on_shared.status_code == 400

    shared_on_personal = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": personal["id"],
            "amount": "50.00",
            "type": "expense",
            "date": tx_date,
            "member_id": member_a["id"],
            "access_scope": "shared",
        },
    )
    assert shared_on_personal.status_code == 400

    valid_personal = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": personal["id"],
            "amount": "50.00",
            "type": "expense",
            "date": tx_date,
            "member_id": member_a["id"],
            "access_scope": "personal",
        },
    )
    assert valid_personal.status_code == 201, valid_personal.text

    accounts = client.get("/api/v1/accounts", headers=headers).json()
    by_id = {row["id"]: row for row in accounts}
    assert Decimal(by_id[shared["id"]]["current_balance"]) == Decimal("1000.00")
    assert Decimal(by_id[personal["id"]]["current_balance"]) == Decimal("450.00")
