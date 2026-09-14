from datetime import date

from fastapi.testclient import TestClient

from tests.conftest import register


def _categories(client: TestClient) -> dict[str, dict]:
    return {row["name"]: row for row in client.get("/api/v1/categories").json()}


def _account(client: TestClient) -> dict:
    response = client.post("/api/v1/accounts", json={"name": "Current", "type": "bank"})
    assert response.status_code == 201, response.text
    return response.json()


def test_dependent_budget_only_counts_that_member(client: TestClient) -> None:
    register(client, "plan-owner@example.com")
    account = _account(client)
    categories = _categories(client)
    food_id = categories["Food"]["id"]
    child = client.post(
        "/api/v1/members",
        json={
            "display_name": "Child One",
            "role": "member",
            "relationship": "child",
            "member_type": "dependent",
        },
    )
    assert child.status_code == 201, child.text
    child_id = child.json()["id"]

    household_budget = client.post(
        "/api/v1/budget",
        json={
            "name": "Household food",
            "categories": [{"category_id": food_id, "allocated_amount": "100000.00"}],
        },
    )
    assert household_budget.status_code == 201, household_budget.text
    dependent_budget = client.post(
        "/api/v1/budget",
        json={
            "name": "Child One budget",
            "member_id": child_id,
            "categories": [{"category_id": food_id, "allocated_amount": "150000.00"}],
        },
    )
    assert dependent_budget.status_code == 201, dependent_budget.text
    assert dependent_budget.json()["member_id"] == child_id
    assert "safe_to_spend" not in dependent_budget.json()

    household_spend = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "20000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": food_id,
        },
    )
    assert household_spend.status_code == 201
    child_spend = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "30000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": food_id,
            "member_id": child_id,
        },
    )
    assert child_spend.status_code == 201

    household = client.get(f"/api/v1/budget/{household_budget.json()['id']}").json()
    dependent = client.get(f"/api/v1/budget/{dependent_budget.json()['id']}").json()
    assert household["spent_total"] == "50000.00"
    assert household["remaining_total"] == "50000.00"
    assert household["categories"][0]["utilization"] == "0.50"
    assert dependent["spent_total"] == "30000.00"
    assert dependent["remaining_total"] == "120000.00"
    assert dependent["member_name"] == "Child One"


def test_threshold_and_overspend_alerts_and_refund(client: TestClient) -> None:
    register(client, "alerts-owner@example.com")
    account = _account(client)
    food_id = _categories(client)["Food"]["id"]
    created = client.post(
        "/api/v1/budget",
        json={
            "name": "Food plan",
            "categories": [{"category_id": food_id, "allocated_amount": "100000.00"}],
        },
    )
    assert created.status_code == 201

    warning_spend = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "80000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": food_id,
        },
    )
    assert warning_spend.status_code == 201
    warning_alerts = client.get("/api/v1/alerts").json()
    assert len(warning_alerts) == 1
    assert warning_alerts[0]["type"] == "budget_threshold"
    assert warning_alerts[0]["severity"] == "warning"
    assert warning_alerts[0]["status"] == "open"

    overspend = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "25000.00",
            "type": "expense",
            "date": date.today().isoformat(),
            "category_id": food_id,
        },
    )
    assert overspend.status_code == 201
    critical_alerts = client.get("/api/v1/alerts").json()
    assert len(critical_alerts) == 1
    assert critical_alerts[0]["type"] == "budget_overspend"
    assert critical_alerts[0]["severity"] == "critical"

    refund = client.post(
        "/api/v1/transactions",
        json={
            "account_id": account["id"],
            "amount": "10000.00",
            "type": "refund",
            "date": date.today().isoformat(),
            "category_id": food_id,
        },
    )
    assert refund.status_code == 201
    budget = client.get(f"/api/v1/budget/{created.json()['id']}").json()
    assert budget["spent_total"] == "95000.00"
    assert budget["categories"][0]["status"] == "warning"
    restored = client.get("/api/v1/alerts").json()
    assert restored[0]["type"] == "budget_threshold"

    marked = client.post(f"/api/v1/alerts/{restored[0]['id']}/read")
    assert marked.status_code == 200
    assert marked.json()["status"] == "read"
    assert client.get("/api/v1/alerts").json() == []


def test_recurring_post_advances_next_date(client: TestClient) -> None:
    register(client, "recurring-owner@example.com")
    account = _account(client)
    food_id = _categories(client)["Food"]["id"]
    next_date = date(2026, 9, 1)
    created = client.post(
        "/api/v1/recurring",
        json={
            "account_id": account["id"],
            "amount": "15000.00",
            "type": "expense",
            "frequency": "monthly",
            "next_date": next_date.isoformat(),
            "category_id": food_id,
            "description": "School snacks",
        },
    )
    assert created.status_code == 201, created.text
    posted = client.post(f"/api/v1/recurring/{created.json()['id']}/post")
    assert posted.status_code == 200, posted.text
    assert posted.json()["amount"] == "15000.00"
    assert posted.json()["date"] == next_date.isoformat()
    template = client.get("/api/v1/recurring").json()[0]
    assert template["next_date"] == "2026-10-01"


def test_budget_tenancy_and_no_safe_to_spend(client: TestClient) -> None:
    register(client, "budget-a@example.com", "A")
    household_a = client.get("/api/v1/households/current").json()
    food_id = _categories(client)["Food"]["id"]
    created = client.post(
        "/api/v1/budget",
        json={
            "name": "A food",
            "categories": [{"category_id": food_id, "allocated_amount": "10000.00"}],
        },
    )
    assert created.status_code == 201
    client.post("/api/v1/auth/logout")

    register(client, "budget-b@example.com", "B")
    forbidden = client.get("/api/v1/budget", headers={"X-Household-Id": household_a["id"]})
    assert forbidden.status_code == 403
    sneak = client.get(f"/api/v1/budget/{created.json()['id']}")
    assert sneak.status_code == 404
    listed = client.get("/api/v1/budget").json()
    assert listed == []
    assert "safe_to_spend" not in created.json()
