from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.conftest import register


def _account(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "2000000.00"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_occurrence_generation_is_idempotent(client: TestClient) -> None:
    register(client, "ob-owner@example.com")
    created = client.post(
        "/api/v1/obligations",
        json={
            "name": "Sibling University Fees",
            "amount": "450000.00",
            "frequency": "quarterly",
            "next_due_date": "2026-10-15",
            "sinking_fund": True,
            "priority": "critical",
        },
    )
    assert created.status_code == 201, created.text
    first = created.json()
    assert first["required_monthly"] == "150000.00"
    assert first["fund_id"] is not None
    count = len(first["occurrences"])
    assert count >= 2
    updated = client.patch(
        f"/api/v1/obligations/{first['id']}",
        json={"priority": "critical"},
    )
    assert updated.status_code == 200
    assert len(updated.json()["occurrences"]) == count
    dues = [row["due_date"] for row in updated.json()["occurrences"]]
    assert len(dues) == len(set(dues))


def test_late_occurrence_is_missed_and_alerted(client: TestClient) -> None:
    register(client, "late-owner@example.com")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    created = client.post(
        "/api/v1/obligations",
        json={
            "name": "Overdue bill",
            "amount": "10000.00",
            "frequency": "one_time",
            "next_due_date": yesterday,
            "priority": "high",
        },
    )
    assert created.status_code == 201, created.text
    occurrence = created.json()["occurrences"][0]
    assert occurrence["status"] == "missed"
    alerts = client.get("/api/v1/alerts").json()
    assert any(row["type"] == "obligation_missed" for row in alerts)


def test_fund_progress_matches_contributions_and_university_is_not_lifestyle(
    client: TestClient,
) -> None:
    register(client, "fund-owner@example.com")
    account = _account(client)
    categories = {row["name"]: row for row in client.get("/api/v1/categories").json()}
    food_id = categories["Food"]["id"]
    client.post(
        "/api/v1/budget",
        json={
            "name": "Lifestyle",
            "categories": [{"category_id": food_id, "allocated_amount": "250000.00"}],
        },
    )
    created = client.post(
        "/api/v1/obligations",
        json={
            "name": "Sibling University Fees",
            "amount": "450000.00",
            "frequency": "quarterly",
            "next_due_date": "2026-10-15",
            "sinking_fund": True,
        },
    )
    assert created.status_code == 201, created.text
    fund_id = created.json()["fund_id"]
    contributed = client.post(
        f"/api/v1/funds/{fund_id}/contributions",
        json={"account_id": account["id"], "amount": "150000.00"},
    )
    assert contributed.status_code == 200, contributed.text
    fund = contributed.json()
    assert fund["current_amount"] == "150000.00"
    assert fund["progress"] == "0.33"
    assert fund["required_monthly"] == "150000.00"

    budget = client.get("/api/v1/budget").json()[0]
    assert budget["spent_total"] == "0.00"
    txs = client.get("/api/v1/transactions").json()
    university = next(row for row in txs if row.get("fund_id") == fund_id)
    assert university["type"] == "transfer"
    categories = {row["id"]: row for row in client.get("/api/v1/categories").json()}
    category = categories[university["category_id"]]
    assert category["kind"] == "system"
    assert category["name"] != "Food"


def test_calendar_lists_obligation_due_dates(client: TestClient) -> None:
    register(client, "cal-owner@example.com")
    client.post(
        "/api/v1/obligations",
        json={
            "name": "Parents' stipend",
            "amount": "100000.00",
            "frequency": "monthly",
            "next_due_date": date.today().isoformat(),
        },
    )
    events = client.get("/api/v1/calendar?days=30").json()
    assert events[0]["kind"] == "obligation"
    assert events[0]["title"] == "Parents' stipend"
    overview = client.get("/api/v1/overview").json()
    assert "safe_to_spend" in overview
    if overview.get("health_ready"):
        assert overview["health"]["label"] in {"Healthy", "Watch", "Strained", "Critical"}
    else:
        assert overview["health"] is None
    assert overview["upcoming_obligations"][0]["title"] == "Parents' stipend"
