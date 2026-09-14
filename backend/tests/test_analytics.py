from decimal import Decimal

from fastapi.testclient import TestClient

from app.services.health_engine import WEIGHTS
from app.services.seed import SEED_OWNER_EMAIL, SEED_OWNER_PASSWORD, seed_household
from tests.conftest import TestingSessionLocal, register


def test_explain_returns_raw_inputs_and_weights(client: TestClient) -> None:
    register(client, "health-explain@example.com")
    body = client.get("/api/v1/financial-health/explain").json()
    assert body["label"] in {"Healthy", "Watch", "Strained", "Critical"}
    points = sum((Decimal(row["points"]) for row in body["components"]), Decimal("0"))
    assert Decimal(body["score"]) == points
    keys = [row["key"] for row in body["components"]]
    assert keys == list(WEIGHTS)
    for row in body["components"]:
        assert Decimal(row["weight"]) == WEIGHTS[row["key"]]
        assert "inputs" in row
        assert row["inputs"]
    cash = next(row for row in body["components"] if row["key"] == "cash_flow")
    assert "recognized_income" in cash["inputs"]
    assert "period_surplus" in cash["inputs"]


def test_seed_snapshots_and_persisted_reports(client: TestClient) -> None:
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
    snapshots = client.get("/api/v1/snapshots").json()
    assert len(snapshots) == 6
    assert snapshots[0]["period_start"] == "2026-04-01"
    assert snapshots[0]["payload"]["shock"] == "Normal ₦2,000,000 income"
    assert snapshots[0]["health_score"] == "88.36"
    monthly = client.get("/api/v1/reports/monthly", params={"period": "2026-04-01"}).json()
    assert monthly["payload"]["income"] == "2000000.00"
    assert monthly["payload"]["health_score"] == "88.36"
    assert monthly["id"]
    again = client.get("/api/v1/reports/monthly", params={"period": "2026-04-01"}).json()
    assert again["id"] == monthly["id"]
    assert again["payload"]["income"] == "2000000.00"
    quarterly = client.get("/api/v1/reports/quarterly", params={"year": 2026, "quarter": 2}).json()
    assert quarterly["payload"]["period_label"] == "Q2 2026"
    assert quarterly["payload"]["income"]
    annual = client.get("/api/v1/reports/annual", params={"year": 2026}).json()
    assert annual["payload"]["period_label"] == "2026"
    giving = client.get("/api/v1/reports/giving", params={"year": 2026}).json()
    assert giving["kind"] == "giving"
    assert "actual" in giving["payload"]
    insights = client.get("/api/v1/insights").json()
    assert len(insights["cash_flow"]) == 6
    assert len(insights["net_worth"]) == 6
    assert insights["health"]["components"][0]["inputs"]
    live_health = client.get("/api/v1/financial-health").json()
    assert live_health["score"] == insights["health"]["score"]
    overview = client.get("/api/v1/overview").json()
    # Overview hides health until accounts have activity (cash, income, or transactions).
    if overview.get("health_ready"):
        assert overview["health"]["score"] == insights["health"]["score"]
    else:
        assert overview["health"] is None


def test_freeze_snapshot_does_not_change_balances(client: TestClient) -> None:
    register(client, "freeze-snap@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    ).json()
    before = client.get("/api/v1/accounts").json()[0]["current_balance"]
    frozen = client.post("/api/v1/snapshots")
    assert frozen.status_code == 201, frozen.text
    after = client.get("/api/v1/accounts").json()[0]["current_balance"]
    assert after == before == account["current_balance"]
    rows = client.get("/api/v1/snapshots").json()
    assert len(rows) == 1
    assert rows[0]["income"] == "0.00"
