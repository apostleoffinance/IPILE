from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register


def test_transfer_does_not_change_net_worth(client: TestClient) -> None:
    register(client, "nw-transfer@example.com")
    current = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "1000000.00"},
    ).json()
    savings = client.post(
        "/api/v1/accounts",
        json={"name": "Savings", "type": "savings", "current_balance": "500000.00"},
    ).json()
    before = client.get("/api/v1/net-worth").json()
    assert before["net_worth"] == "1500000.00"
    transfer = client.post(
        "/api/v1/transactions",
        json={
            "account_id": current["id"],
            "counterparty_account_id": savings["id"],
            "amount": "200000.00",
            "type": "transfer",
            "date": date.today().isoformat(),
        },
    )
    assert transfer.status_code == 201, transfer.text
    after = client.get("/api/v1/net-worth").json()
    assert after["net_worth"] == "1500000.00"
    assert after["total_assets"] == "1500000.00"
    assert after["buckets"]["cash"] == "800000.00"
    assert after["buckets"]["savings"] == "700000.00"


def test_asset_account_link_is_not_double_counted(client: TestClient) -> None:
    register(client, "nw-dedup@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "House cash", "type": "bank", "current_balance": "1000000.00"},
    ).json()
    created = client.post(
        "/api/v1/assets",
        json={
            "name": "House cash asset",
            "type": "cash",
            "current_value": "1000000.00",
            "account_id": account["id"],
        },
    )
    assert created.status_code == 201, created.text
    nw = client.get("/api/v1/net-worth").json()
    assert nw["total_assets"] == "1000000.00"
    assert nw["net_worth"] == "1000000.00"


def test_debt_paid_off_clears_liability(client: TestClient) -> None:
    register(client, "nw-debt@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "1000000.00"},
    ).json()
    loan = client.post(
        "/api/v1/liabilities",
        json={"name": "Car loan", "type": "loan", "current_balance": "400000.00"},
    )
    assert loan.status_code == 201, loan.text
    before = client.get("/api/v1/net-worth").json()
    assert before["debt"] == "400000.00"
    assert before["net_worth"] == "600000.00"
    paid = client.post(
        f"/api/v1/liabilities/{loan.json()['id']}/payments",
        json={"account_id": account["id"], "amount": "400000.00"},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["current_balance"] == "0.00"
    assert paid.json()["status"] == "paid_off"
    after = client.get("/api/v1/net-worth").json()
    assert after["debt"] == "0.00"
    assert after["net_worth"] == "600000.00"
    assert after["total_assets"] == "600000.00"


def test_investment_buy_updates_value(client: TestClient) -> None:
    register(client, "nw-invest@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    ).json()
    created = client.post(
        "/api/v1/investments",
        json={"name": "Index fund", "type": "fund", "current_value": "0.00"},
    )
    assert created.status_code == 201, created.text
    bought = client.post(
        f"/api/v1/investments/{created.json()['id']}/transactions",
        json={
            "type": "buy",
            "amount": "200000.00",
            "date": date.today().isoformat(),
            "account_id": account["id"],
        },
    )
    assert bought.status_code == 201, bought.text
    investments = client.get("/api/v1/investments").json()
    assert investments[0]["current_value"] == "200000.00"
    assert investments[0]["cost_basis"] == "200000.00"
    nw = client.get("/api/v1/net-worth").json()
    assert nw["investments"] == "200000.00"
    assert nw["net_worth"] == "500000.00"


def test_crypto_investment_type_accepted(client: TestClient) -> None:
    register(client, "nw-crypto@example.com")
    created = client.post(
        "/api/v1/investments",
        json={"name": "BTC wallet", "type": "crypto", "current_value": "150000.00"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["type"] == "crypto"
    listed = client.get("/api/v1/investments").json()
    assert listed[0]["type"] == "crypto"


def test_seed_identifies_emergency_and_exposes_wealth(client: TestClient) -> None:
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
    accounts = {row["name"]: row for row in client.get("/api/v1/accounts").json()}
    assert accounts["Emergency savings"]["is_emergency"] is True
    assets = {row["name"]: row for row in client.get("/api/v1/assets").json()}
    assert assets["Emergency fund"]["is_emergency"] is True
    investments = {row["name"]: row for row in client.get("/api/v1/investments").json()}
    assert "Family investments" in investments
    overview = client.get("/api/v1/overview").json()
    assert "wealth" in overview
    if overview.get("health_ready"):
        assert overview["health"]["label"] in {"Healthy", "Watch", "Strained", "Critical"}
    else:
        assert overview["health"] is None
    assert overview["wealth"]["debt"] == "0.00"
    nw = client.get("/api/v1/net-worth").json()
    assert nw["net_worth"] == overview["wealth"]["net_worth"]
    assert len(nw["history"]) >= 1
    expected = Decimal(nw["total_assets"]) - Decimal(nw["total_liabilities"])
    assert Decimal(nw["net_worth"]) == expected
