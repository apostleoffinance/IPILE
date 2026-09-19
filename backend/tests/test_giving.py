from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


def _account_id(client: TestClient) -> str:
    accounts = client.get("/api/v1/accounts").json()
    if accounts:
        return accounts[0]["id"]
    created = client.post(
        "/api/v1/accounts",
        json={"name": "Giving bank", "type": "bank", "current_balance": "500000.00"},
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_giving_policy_limits_and_post(client: TestClient) -> None:
    register(client, "give@example.com")
    account_id = _account_id(client)
    policy = client.post(
        "/api/v1/giving/policies",
        json={
            "name": "Charity",
            "kind": "Charity",
            "monthly_limit": "50000.00",
            "requires_dual_approval": False,
        },
    )
    assert policy.status_code == 201, policy.text
    policy_id = policy.json()["id"]

    posted = client.post(
        "/api/v1/giving",
        json={
            "kind": "Charity",
            "amount": "43000.00",
            "account_id": account_id,
            "policy_id": policy_id,
            "beneficiary": "Local fund",
        },
    )
    assert posted.status_code == 201, posted.text
    body = posted.json()
    assert body["status"] == "posted"
    assert body["transaction_id"] is not None
    assert body["limit_warning"] is None

    over = client.post(
        "/api/v1/giving",
        json={
            "kind": "Charity",
            "amount": "10000.00",
            "account_id": account_id,
            "policy_id": policy_id,
        },
    )
    assert over.status_code == 201, over.text
    assert "Monthly limit exceeded" in (over.json()["limit_warning"] or "")

    summary = client.get("/api/v1/giving/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert Decimal(payload["total_posted_month"]) == Decimal("53000.00")
    assert payload["policies"][0]["limit_breached"] is True


def test_giving_dual_approval(client: TestClient) -> None:
    register(client, "owner-give@example.com", "Owner")
    account_id = _account_id(client)
    policy = client.post(
        "/api/v1/giving/policies",
        json={
            "name": "Large gift",
            "kind": "Gift",
            "monthly_limit": "1000000.00",
            "requires_dual_approval": True,
        },
    ).json()

    pending = client.post(
        "/api/v1/giving",
        json={
            "kind": "Gift",
            "amount": "20000.00",
            "account_id": account_id,
            "policy_id": policy["id"],
        },
    )
    assert pending.status_code == 201
    assert pending.json()["status"] == "pending_approval"
    assert pending.json()["transaction_id"] is None

    # Owner may self-approve (owner exception)
    approved = client.post(f"/api/v1/giving/{pending.json()['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["transaction_id"] is not None
