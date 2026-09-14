from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.money import quantize_money
from app.services.goal_engine import months_left, remaining, required_monthly
from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register


def test_seed_relocation_matches_spec(client: TestClient) -> None:
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
    assert login.status_code == 200, login.text
    goals = {row["name"]: row for row in client.get("/api/v1/goals").json()}
    relocation = goals["Future relocation"]
    assert relocation["target_amount"] == "8000000.00"
    assert relocation["current_amount"] == "2100000.00"
    assert relocation["deadline"] == "2027-06-30"
    assert relocation["percent"] == 26
    today = date.today()
    expected = required_monthly(
        Decimal("8000000.00"),
        Decimal("2100000.00"),
        date(2027, 6, 30),
        today,
    )
    assert relocation["required_monthly"] == f"{expected:.2f}"
    assert relocation["remaining"] == "5900000.00"
    assert relocation["months_left"] == months_left(today, date(2027, 6, 30))
    assert "Family emergency reserve" in goals
    assert "Long-term wealth" in goals


def test_required_monthly_matches_formula(client: TestClient) -> None:
    register(client, "goal-math@example.com")
    created = client.post(
        "/api/v1/goals",
        json={
            "name": "Move",
            "type": "relocation",
            "target_amount": "8000000.00",
            "current_amount": "2100000.00",
            "deadline": "2027-06-30",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    expected = required_monthly(
        Decimal("8000000.00"),
        Decimal("2100000.00"),
        date(2027, 6, 30),
        date.today(),
    )
    assert body["required_monthly"] == f"{expected:.2f}"
    assert body["remaining"] == f"{remaining(Decimal('8000000.00'), Decimal('2100000.00')):.2f}"


def test_goal_completes_when_current_reaches_target(client: TestClient) -> None:
    register(client, "goal-done@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "6000000.00"},
    ).json()
    goal = client.post(
        "/api/v1/goals",
        json={
            "name": "Laptop",
            "type": "purchase",
            "target_amount": "500000.00",
            "current_amount": "400000.00",
        },
    ).json()
    assert goal["status"] == "active"
    paid = client.post(
        f"/api/v1/goals/{goal['id']}/contributions",
        json={"account_id": account["id"], "amount": "100000.00"},
    )
    assert paid.status_code == 200, paid.text
    body = paid.json()
    assert body["current_amount"] == "500000.00"
    assert body["status"] == "completed"
    assert body["required_monthly"] == "0.00"
    after = client.get("/api/v1/net-worth").json()
    assert after["net_worth"] == "6000000.00"


def test_allocation_rule_can_target_a_goal(client: TestClient) -> None:
    register(client, "goal-alloc@example.com")
    goal = client.post(
        "/api/v1/goals",
        json={"name": "Buffer goal", "type": "other", "target_amount": "200000.00"},
    ).json()
    rule = client.post(
        "/api/v1/allocation-rules",
        json={
            "name": "Goal buffer",
            "type": "fixed",
            "basis": "recognized_income",
            "amount": "20000.00",
            "priority": 1,
            "destination_type": "goal",
            "destination_id": goal["id"],
        },
    )
    assert rule.status_code == 201, rule.text
    assert rule.json()["destination_type"] == "goal"
    assert rule.json()["destination_id"] == goal["id"]


def test_emergency_goal_without_account_counts_once(client: TestClient) -> None:
    register(client, "goal-emerg@example.com")
    client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "1000000.00"},
    )
    created = client.post(
        "/api/v1/goals",
        json={
            "name": "Reserve",
            "type": "emergency",
            "target_amount": "300000.00",
            "current_amount": "300000.00",
        },
    )
    assert created.status_code == 201, created.text
    wealth = client.get("/api/v1/net-worth").json()
    assert wealth["emergency_fund"] == "0.00"
    assert quantize_money(Decimal(wealth["net_worth"])) == Decimal("1000000.00")
