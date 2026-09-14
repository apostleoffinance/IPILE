from datetime import date

from fastapi.testclient import TestClient

from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register

SPEC_AMOUNTS = {
    "Tithe": "200000.00",
    "Parents' stipend": "100000.00",
    "University fund": "150000.00",
    "Parents' rent fund": "50000.00",
    "Household essentials": "670000.00",
    "Emergency fund": "150000.00",
    "Investments": "200000.00",
    "Personal allowances": "140000.00",
    "Additional giving": "50000.00",
    "Buffer": "90000.00",
    "Family surplus": "200000.00",
}


def _login_seed(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": SEED_OWNER_EMAIL, "password": SEED_OWNER_PASSWORD},
    )
    assert login.status_code == 200, login.text


def test_seed_two_million_allocation_matches_spec(client: TestClient) -> None:
    db = TestingSessionLocal()
    try:
        seed_household(db)
        db.commit()
    finally:
        db.close()
    _login_seed(client)
    accounts = {row["name"]: row for row in client.get("/api/v1/accounts").json()}
    sources = client.get("/api/v1/income/sources").json()
    posted = client.post(
        "/api/v1/income",
        json={
            "account_id": accounts["Household current"]["id"],
            "amount": "2000000.00",
            "date": date.today().isoformat(),
            "income_source_id": sources[0]["id"],
        },
    )
    assert posted.status_code == 201, posted.text
    latest = client.get("/api/v1/allocations/latest").json()
    amounts = {line["name"]: line["amount"] for line in latest["lines"]}
    assert amounts == SPEC_AMOUNTS
    assert latest["recognized_income"] == "2000000.00"
    assert latest["total_allocated"] == "2000000.00"
    assert latest["surplus"] == "0.00"
    assert latest["unfunded_mandatory"] == []
    overview = client.get("/api/v1/overview").json()
    assert overview["period_income"] == "2000000.00"
    assert overview["allocated_total"] == "2000000.00"
    assert overview["safe_to_spend"]["current"] == "2000000.00"
    assert overview["health_ready"] is True
    assert overview["health"]["label"] in {"Healthy", "Watch", "Strained", "Critical"}
    assert "period_income" in overview
    assert "allocated_total" in overview
    assert "safe_to_spend" in overview


def test_zero_and_short_income_allocation_via_api(client: TestClient) -> None:
    register(client, "alloc-zero@example.com")
    client.post(
        "/api/v1/allocation-rules",
        json={
            "name": "First share",
            "type": "percentage",
            "rate": "0.10",
            "priority": 0,
            "destination_type": "giving",
        },
    )
    client.post(
        "/api/v1/allocation-rules",
        json={
            "name": "Rent reserve",
            "type": "fixed",
            "amount": "100000.00",
            "priority": 1,
            "destination_type": "fund",
        },
    )
    client.post(
        "/api/v1/allocation-rules",
        json={
            "name": "Family surplus",
            "type": "remainder",
            "basis": "remaining",
            "priority": 2,
            "mandatory": False,
            "destination_type": "account",
        },
    )
    zero = client.post("/api/v1/allocations/run").json()
    assert zero["recognized_income"] == "0.00"
    assert zero["total_allocated"] == "0.00"
    assert {row["name"] for row in zero["unfunded_mandatory"]} == {"Rent reserve"}

    account = client.post("/api/v1/accounts", json={"name": "Current", "type": "bank"}).json()
    short = client.post(
        "/api/v1/income",
        json={"account_id": account["id"], "amount": "40000.00", "date": date.today().isoformat()},
    )
    assert short.status_code == 201, short.text
    latest = client.get("/api/v1/allocations/latest").json()
    amounts = {line["name"]: line["amount"] for line in latest["lines"]}
    assert amounts["First share"] == "4000.00"
    assert amounts["Rent reserve"] == "36000.00"
    assert any(row["name"] == "Rent reserve" for row in latest["unfunded_mandatory"])


def test_current_sts_excludes_protected_funds(client: TestClient) -> None:
    register(client, "sts-protect@example.com")
    client.post(
        "/api/v1/accounts",
        json={"name": "Spendable", "type": "bank", "current_balance": "1000000.00"},
    )
    client.post(
        "/api/v1/accounts",
        json={
            "name": "University vault",
            "type": "savings",
            "current_balance": "150000.00",
            "is_protected": True,
            "include_in_safe_to_spend": False,
        },
    )
    sts = client.get("/api/v1/safe-to-spend").json()
    assert sts["current"] == "1000000.00"
    assert sts["components"]["liquid_cash"] == "1000000.00"
    assert Decimalish(sts["components"]["protected_savings"]) >= Decimalish("150000.00")


def Decimalish(value: str):
    from decimal import Decimal

    return Decimal(value)


def test_purchase_check_one_eighty_and_buffer_breach(client: TestClient) -> None:
    register(client, "purchase@example.com")
    client.post(
        "/api/v1/accounts",
        json={"name": "Spendable", "type": "bank", "current_balance": "1400000.00"},
    )
    created = client.post(
        "/api/v1/obligations",
        json={
            "name": "Committed support",
            "amount": "850000.00",
            "frequency": "one_time",
            "next_due_date": date.today().isoformat(),
            "priority": "high",
        },
    )
    assert created.status_code == 201, created.text
    sts = client.get("/api/v1/safe-to-spend").json()
    assert sts["current"] == "550000.00"
    healthy = client.post("/api/v1/purchase-checks", json={"amount": "180000.00"}).json()
    assert healthy["affordable"] is True
    assert healthy["severity"] == "healthy"
    assert healthy["remaining_current_sts"] == "370000.00"
    assert healthy["buffer_breached"] is False
    warn = client.post("/api/v1/purchase-checks", json={"amount": "500000.00"}).json()
    assert warn["affordable"] is True
    assert warn["severity"] == "warning"
    assert warn["buffer_breached"] is True
    assert warn["recommended_action"] == "delay / reduce / use surplus"
