from datetime import date

from fastapi.testclient import TestClient

from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register


def test_seed_salon_is_isolated_from_sts(client: TestClient) -> None:
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
    rows = {row["name"]: row for row in client.get("/api/v1/businesses").json()}
    assert "Salon" in rows
    salon = rows["Salon"]
    assert salon["pnl"]["family_invested"] == "0.00"
    accounts = {row["name"]: row for row in client.get("/api/v1/accounts").json()}
    assert accounts["Salon"]["type"] == "business"
    assert accounts["Salon"]["include_in_safe_to_spend"] is False


def test_capital_into_salon_does_not_hit_lifestyle_budget(client: TestClient) -> None:
    register(client, "salon-budget@example.com")
    household = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "1000000.00"},
    ).json()
    food = {row["name"]: row for row in client.get("/api/v1/categories").json()}["Food"]
    budget = client.post(
        "/api/v1/budget",
        json={
            "name": "Lifestyle",
            "categories": [{"category_id": food["id"], "allocated_amount": "250000.00"}],
        },
    )
    assert budget.status_code == 201, budget.text
    salon = client.post("/api/v1/businesses", json={"name": "Salon", "type": "service"}).json()
    before_sts = client.get("/api/v1/safe-to-spend").json()["current"]
    posted = client.post(
        f"/api/v1/businesses/{salon['id']}/transactions",
        json={
            "type": "capital_contribution",
            "amount": "200000.00",
            "date": date.today().isoformat(),
            "account_id": household["id"],
            "description": "Family capital",
        },
    )
    assert posted.status_code == 200, posted.text
    body = posted.json()
    assert body["pnl"]["family_invested"] == "200000.00"
    assert body["pnl"]["current_business_equity"] == "200000.00"
    assert body["pnl"]["family_return"] == "0.00"
    lifestyle = client.get(f"/api/v1/budget/{budget.json()['id']}").json()
    assert lifestyle["spent_total"] == "0.00"
    after_sts = client.get("/api/v1/safe-to-spend").json()["current"]
    assert before_sts == "1000000.00"
    assert after_sts == "800000.00"
    wealth = client.get("/api/v1/net-worth").json()
    assert wealth["net_worth"] == "1000000.00"
    assert wealth["buckets"]["business"] == "200000.00"


def test_business_account_excluded_until_explicitly_included(client: TestClient) -> None:
    register(client, "salon-sts@example.com")
    client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    )
    salon = client.post("/api/v1/businesses", json={"name": "Salon"}).json()
    linked = client.post(
        "/api/v1/accounts",
        json={
            "name": "Salon till",
            "type": "bank",
            "current_balance": "300000.00",
            "business_id": salon["id"],
            "include_in_safe_to_spend": False,
        },
    ).json()
    assert client.get("/api/v1/safe-to-spend").json()["current"] == "500000.00"
    updated = client.patch(
        f"/api/v1/accounts/{linked['id']}",
        json={"include_in_safe_to_spend": True},
    )
    assert updated.status_code == 200, updated.text
    assert client.get("/api/v1/safe-to-spend").json()["current"] == "800000.00"


def test_revenue_and_withdrawal_update_return(client: TestClient) -> None:
    register(client, "salon-return@example.com")
    household = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "400000.00"},
    ).json()
    salon = client.post("/api/v1/businesses", json={"name": "Salon"}).json()
    client.post(
        f"/api/v1/businesses/{salon['id']}/transactions",
        json={
            "type": "capital_contribution",
            "amount": "200000.00",
            "date": date.today().isoformat(),
            "account_id": household["id"],
        },
    )
    client.post(
        f"/api/v1/businesses/{salon['id']}/transactions",
        json={"type": "revenue", "amount": "50000.00", "date": date.today().isoformat()},
    )
    withdrawn = client.post(
        f"/api/v1/businesses/{salon['id']}/transactions",
        json={
            "type": "withdrawal",
            "amount": "10000.00",
            "date": date.today().isoformat(),
            "account_id": household["id"],
        },
    )
    assert withdrawn.status_code == 200, withdrawn.text
    pnl = client.get(f"/api/v1/businesses/{salon['id']}/pnl").json()
    assert pnl["family_invested"] == "200000.00"
    assert pnl["family_withdrawn"] == "10000.00"
    assert pnl["revenue"] == "50000.00"
    assert pnl["current_business_equity"] == "240000.00"
    assert pnl["family_return"] == "50000.00"
