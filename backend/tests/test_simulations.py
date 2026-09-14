from decimal import Decimal

from fastapi.testclient import TestClient

from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register


def test_simulation_does_not_change_production_balances(client: TestClient) -> None:
    db = TestingSessionLocal()
    try:
        seed_household(db)
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": SEED_OWNER_EMAIL, "password": SEED_OWNER_PASSWORD},
    )
    assert login.status_code == 200
    before = {row["id"]: row["current_balance"] for row in client.get("/api/v1/accounts").json()}
    obligations = {row["name"]: row for row in client.get("/api/v1/obligations").json()}
    fee_id = obligations["Sibling University Fees"]["id"]
    posted = client.post(
        "/api/v1/simulations",
        json={
            "name": "Income cut and fees",
            "income_change_rate": "-0.20",
            "obligation_deltas": {fee_id: "0.15"},
            "unexpected_expense": "300000.00",
            "horizon_months": 6,
        },
    )
    assert posted.status_code == 201, posted.text
    body = posted.json()
    assert body["status"] == "completed"
    first = body["months"][0]
    assert first["income"] == "1600000.00"
    assert first["cash_flow"] == "critical"
    assert first["obligations"] == "unfunded"
    assert first["emergency_fund"] == "critical"
    assert body["summary"]["cash_flow"] in {"healthy", "warning", "critical"}
    assert body["summary"]["obligations"] in {"funded", "at risk", "unfunded"}
    assert len(body["months"]) == 6
    after = {row["id"]: row["current_balance"] for row in client.get("/api/v1/accounts").json()}
    assert after == before
    fetched = client.get(f"/api/v1/simulations/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert fetched.json()["summary"]["income"]
    assert Decimal(first["surplus"]) < 0


def test_new_household_simulation_persists_run(client: TestClient) -> None:
    register(client, "sim-empty@example.com")
    client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    )
    before = client.get("/api/v1/accounts").json()[0]["current_balance"]
    posted = client.post(
        "/api/v1/simulations",
        json={
            "unexpected_expense": "300000.00",
            "income_change_rate": "-0.20",
            "horizon_months": 3,
        },
    )
    assert posted.status_code == 201, posted.text
    assert posted.json()["months"][0]["cash_flow"] == "critical"
    assert client.get("/api/v1/accounts").json()[0]["current_balance"] == before
