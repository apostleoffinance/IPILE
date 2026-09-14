from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import login, register


def test_cross_household_access_is_denied(client: TestClient) -> None:
    register(client, "a@example.com", "A")
    household_a = client.get("/api/v1/households/current").json()
    account_a = client.post(
        "/api/v1/accounts",
        json={"name": "A current", "type": "bank"},
    ).json()
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com", "B")
    forbidden = client.get("/api/v1/accounts", headers={"X-Household-Id": household_a["id"]})
    assert forbidden.status_code == 403

    sneak = client.get(f"/api/v1/accounts/{account_a['id']}")
    assert sneak.status_code == 404

    create_on_a = client.post(
        "/api/v1/transactions",
        headers={"X-Household-Id": household_a["id"]},
        json={
            "account_id": account_a["id"],
            "amount": "100.00",
            "type": "expense",
            "date": date.today().isoformat(),
        },
    )
    assert create_on_a.status_code == 403


def test_register_creates_a_household(client: TestClient) -> None:
    register(client, "solo@example.com", "Solo")
    households = client.get("/api/v1/households").json()
    assert len(households) == 1
    assert households[0]["role"] == "owner"
    me = client.get("/api/v1/auth/me").json()
    assert me["households"][0]["id"] == households[0]["id"]
    login(client, "solo@example.com")
