from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register

CSV = """date,amount,type,description,external_id,category
2026-09-01,25000.00,expense,Market run,csv-1,Food
2026-09-02,10000.00,expense,Fuel,csv-2,Transport
"""


def test_csv_import_creates_transactions_and_dedups(client: TestClient) -> None:
    register(client, "import-csv@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "500000.00"},
    ).json()
    first = client.post(
        "/api/v1/imports/csv",
        json={"account_id": account["id"], "content": CSV, "filename": "sept.csv"},
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["source"] == "csv"
    assert body["created_count"] == 2
    assert body["skipped_count"] == 0
    txs = client.get("/api/v1/transactions").json()
    imported = [row for row in txs if row["import_source"] == "csv"]
    assert len(imported) == 2
    assert all(row["import_source"] == "csv" for row in imported)
    after_first = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert after_first == Decimal("465000.00")
    second = client.post(
        "/api/v1/imports/csv",
        json={"account_id": account["id"], "content": CSV, "filename": "sept.csv"},
    )
    assert second.status_code == 201, second.text
    assert second.json()["created_count"] == 0
    assert second.json()["skipped_count"] == 2
    after_second = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert after_second == after_first


def test_statement_import_path(client: TestClient) -> None:
    register(client, "import-stmt@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "200000.00"},
    ).json()
    content = "\n".join(
        [
            "date|amount|narrative|reference",
            "2026-09-10|-50000.00|Salary|stmt-pay-1",
            "2026-09-11|12000.00|POS shop|stmt-pos-1",
        ]
    )
    posted = client.post(
        "/api/v1/imports/statement",
        json={"account_id": account["id"], "content": content},
    )
    assert posted.status_code == 201, posted.text
    assert posted.json()["source"] == "statement"
    assert posted.json()["created_count"] == 2
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    # income 50k + expense 12k from 200k => 238k
    assert balance == Decimal("238000.00")
    again = client.post(
        "/api/v1/imports/statement",
        json={"account_id": account["id"], "content": content},
    )
    assert again.json()["skipped_count"] == 2
    assert Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"]) == balance


def test_csv_import_supports_separate_debit_and_credit_columns(client: TestClient) -> None:
    register(client, "import-columns@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    statement = """date,description,debit,credit,reference
2026-09-01,Groceries,12500.00,,debit-1
2026-09-02,Salary,,250000.00,credit-1
"""
    response = client.post(
        "/api/v1/imports/csv",
        json={"account_id": account["id"], "content": statement},
    )
    assert response.status_code == 201, response.text
    assert response.json()["created_count"] == 2
    transactions = client.get("/api/v1/transactions").json()
    by_reference = {row["external_id"]: row for row in transactions}
    assert by_reference["debit-1"]["type"] == "expense"
    assert by_reference["credit-1"]["type"] == "income"
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert balance == Decimal("337500.00")


def test_forwarded_bank_alert_is_reviewed_before_posting(client: TestClient, monkeypatch) -> None:
    from app.core.config import Settings
    from app.api.v1 import imports as imports_api

    register(client, "import-email@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "50000.00"},
    ).json()
    monkeypatch.setattr(
        imports_api,
        "get_settings",
        lambda: Settings(inbound_email_domain="imports.example.test", inbound_email_webhook_secret="test-secret"),
    )
    mailbox = client.post("/api/v1/imports/mailbox")
    assert mailbox.status_code == 200, mailbox.text
    address = mailbox.json()["address"]
    inbound = client.post(
        "/api/v1/imports/inbound-email",
        headers={"X-Inbound-Email-Secret": "test-secret"},
        json={
            "To": address,
            "From": "alerts@bank.example",
            "Subject": "Debit Alert",
            "TextBody": "Your account was debited NGN 5,000.00 on 15/11/2026. Ref: ABC12345",
        },
    )
    assert inbound.status_code == 202, inbound.text
    queue = client.get("/api/v1/imports/review")
    assert queue.status_code == 200
    assert len(queue.json()) == 1
    assert queue.json()[0]["status"] == "pending_review"
    before = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert before == Decimal("50000.00")
    approved = client.post(
        f"/api/v1/imports/{queue.json()[0]['id']}/approve",
        json={"account_id": account["id"]},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    after = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert after == Decimal("45000.00")


def test_inbound_email_rejects_invalid_webhook_secret(client: TestClient) -> None:
    response = client.post(
        "/api/v1/imports/inbound-email",
        headers={"X-Inbound-Email-Secret": "wrong"},
        json={"To": "bank-alert+unknown@imports.example.test", "TextBody": "debit NGN 10"},
    )
    assert response.status_code == 401
