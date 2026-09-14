from fastapi.testclient import TestClient

from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, SEED_SLUG, seed_household
from tests.conftest import TestingSessionLocal


def test_seed_household_is_a_normal_household(client: TestClient) -> None:
    db = TestingSessionLocal()
    try:
        household = seed_household(db)
        db.commit()
        assert household.slug == SEED_SLUG
        assert household.base_currency == "NGN"
    finally:
        db.close()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": SEED_OWNER_EMAIL, "password": SEED_OWNER_PASSWORD},
    )
    assert login.status_code == 200, login.text
    current = client.get("/api/v1/households/current").json()
    assert current["name"] == "Seed Household"
    assert current["slug"] == SEED_SLUG

    members = {row["display_name"]: row for row in client.get("/api/v1/members").json()}
    assert set(members) == {"Partner A", "Partner B", "Baby"}
    assert members["Partner A"]["role"] == "owner"
    assert members["Baby"]["member_type"] == "dependent"
    assert members["Baby"]["user_id"] is None

    accounts = {row["name"]: row for row in client.get("/api/v1/accounts").json()}
    assert "Household current" in accounts
    assert accounts["Emergency savings"]["is_protected"] is True
    assert isinstance(accounts["Household current"]["current_balance"], str)

    sources = client.get("/api/v1/income/sources").json()
    assert sources[0]["expected_amount"] == "2000000.00"
    assert sources[0]["name"] == "Household income"

    overview = client.get("/api/v1/overview").json()
    assert "safe_to_spend" in overview
    assert overview["health_ready"] is False
    assert overview["health"] is None
    assert overview["cash_total"] == "0.00"
    assert overview["allocated_total"] == "0.00"
    assert overview["period_income"] == "0.00"
    assert overview["safe_to_spend"]["current"] == "0.00"
    rules = {row["name"]: row for row in client.get("/api/v1/allocation-rules").json()}
    assert rules["Tithe"]["type"] == "percentage"
    assert rules["Family surplus"]["type"] == "remainder"

    budgets = {row["name"]: row for row in client.get("/api/v1/budget").json()}
    assert budgets["Household essentials"]["allocated_total"] == "670000.00"
    assert budgets["Baby budget"]["allocated_total"] == "150000.00"
    assert budgets["Baby budget"]["member_name"] == "Baby"
    assert "safe_to_spend" not in budgets["Household essentials"]
    recurring = client.get("/api/v1/recurring").json()
    assert recurring[0]["amount"] == "40000.00"

    obligations = {row["name"]: row for row in client.get("/api/v1/obligations").json()}
    assert obligations["Sibling University Fees"]["required_monthly"] == "150000.00"
    assert obligations["Parents' rent"]["required_monthly"] == "50000.00"
    assert obligations["Sibling University Fees"]["next_due_date"] == "2026-10-15"
    funds = {row["name"]: row for row in client.get("/api/v1/funds").json()}
    assert funds["University fund"]["target_amount"] == "450000.00"
    assert funds["Parents Rent Fund"]["required_monthly"] == "50000.00"
    assert accounts["Emergency savings"]["is_emergency"] is True
    assert "wealth" in overview
    assert "health" in overview
    goals = {row["name"]: row for row in client.get("/api/v1/goals").json()}
    assert goals["Future relocation"]["target_amount"] == "8000000.00"
    assert goals["Future relocation"]["current_amount"] == "2100000.00"
    assert goals["Future relocation"]["deadline"] == "2027-06-30"
    businesses = {row["name"]: row for row in client.get("/api/v1/businesses").json()}
    assert businesses["Salon"]["type"] == "service"
    assert businesses["Salon"]["pnl"]["family_invested"] == "0.00"
    snapshots = client.get("/api/v1/snapshots").json()
    assert len(snapshots) == 6
    shocks = [row["payload"]["shock"] for row in snapshots]
    assert shocks[0] == "Normal ₦2,000,000 income"
    assert shocks[1] == "University fees due (₦450,000)"
    assert shocks[2] == "Income falls to ₦1,500,000"
    assert shocks[3] == "Income increases to ₦2,800,000"
    assert shocks[4] == "Parents' rent due (₦600,000)"
    assert shocks[5] == "Unexpected ₦300,000 family expense"
    assert snapshots[0]["health_score"] == "88.36"
