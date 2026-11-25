from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import login, register


def _logout(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204


def test_transaction_cannot_reference_a_member_from_another_household(
    client: TestClient,
) -> None:
    register(client, "tx-reference-a@example.com", "Household A")
    account_a = client.post(
        "/api/v1/accounts",
        json={"name": "A current", "type": "bank"},
    ).json()
    _logout(client)

    register(client, "tx-reference-b@example.com", "Household B")
    member_b = client.get("/api/v1/members").json()[0]
    _logout(client)

    login(client, "tx-reference-a@example.com")
    response = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_a["id"],
            "amount": "100.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "member_id": member_b["id"],
            "access_scope": "personal",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Member not found in this household."
    assert client.get("/api/v1/transactions").json() == []

    valid = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account_a["id"],
            "amount": "25.00",
            "type": "expense",
            "date": date.today().isoformat(),
        },
    )
    assert valid.status_code == 201, valid.text
    update = client.patch(
        f"/api/v1/transactions/{valid.json()['id']}",
        json={"member_id": member_b["id"]},
    )
    assert update.status_code == 404
    assert update.json()["detail"] == "Member not found in this household."
