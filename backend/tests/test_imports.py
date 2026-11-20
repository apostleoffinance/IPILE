from decimal import Decimal

import pytest
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
    from app.api.v1 import imports as imports_api
    from app.core.config import Settings

    register(client, "import-email@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "50000.00"},
    ).json()
    monkeypatch.setattr(
        imports_api,
        "get_settings",
        lambda: Settings(
            inbound_email_domain="imports.example.test",
            inbound_email_webhook_secret="test-secret",
        ),
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
    assert inbound.status_code == 200, inbound.text
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


def test_postmark_basic_auth_inbound_webhook(client: TestClient, monkeypatch) -> None:
    from app.api.v1 import imports as imports_api
    from app.core.config import Settings

    register(client, "postmark-basic@example.com")
    monkeypatch.setattr(
        imports_api,
        "get_settings",
        lambda: Settings(
            inbound_email_domain="imports.example.test",
            inbound_email_webhook_secret="test-secret",
        ),
    )
    mailbox = client.post("/api/v1/imports/mailbox")
    assert mailbox.status_code == 200, mailbox.text
    response = client.post(
        "/api/v1/imports/inbound-email",
        auth=("ipile", "test-secret"),
        json={
            "To": mailbox.json()["address"],
            "From": "alerts@bank.example",
            "Subject": "Debit Alert",
            "TextBody": "Your account was debited NGN 5,000.00 on 15/11/2026. Ref: PM123456",
            "Date": "Sun, 15 Nov 2026 10:00:00 +0100",
            "MessageID": "postmark-message-0001",
        },
    )
    assert response.status_code == 200, response.text
    first_job_id = response.json()["id"]
    duplicate = client.post(
        "/api/v1/imports/inbound-email",
        auth=("ipile", "test-secret"),
        json={
            "To": mailbox.json()["address"],
            "From": "alerts@bank.example",
            "Subject": "Debit Alert",
            "TextBody": "Your account was debited NGN 5,000.00 on 15/11/2026. Ref: PM123456",
            "Date": "Sun, 15 Nov 2026 10:00:00 +0100",
            "MessageID": "postmark-message-0001",
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["id"] == first_job_id
    queue = client.get("/api/v1/imports/review")
    assert len(queue.json()) == 1


def test_email_parser_rejects_ambiguous_amount_and_missing_date() -> None:
    from app.services.email_imports import parse_bank_alert

    with pytest.raises(ValueError, match="exactly one unambiguous"):
        parse_bank_alert(
            sender="alerts@bank.example",
            subject="Debit Alert",
            body="Debited NGN 5,000.00. Available balance NGN 45,000.00.",
        )
    with pytest.raises(ValueError, match="no transaction date"):
        parse_bank_alert(
            sender="alerts@bank.example",
            subject="Debit Alert",
            body="Your account was debited NGN 5,000.00.",
        )


def test_csv_import_rejects_empty_debit_and_credit(client: TestClient) -> None:
    register(client, "empty-columns@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    response = client.post(
        "/api/v1/imports/csv",
        json={
            "account_id": account["id"],
            "content": "date,description,debit,credit,reference\n2026-09-01,Empty,,,empty-1\n",
        },
    )
    assert response.status_code == 400
    assert "must contain a debit or credit" in response.json()["detail"]
    assert client.get("/api/v1/transactions").json() == []


def test_identical_transactions_without_references_keep_distinct_ids(client: TestClient) -> None:
    from decimal import Decimal

    register(client, "identical-rows@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    response = client.post(
        "/api/v1/imports/csv",
        json={
            "account_id": account["id"],
            "content": (
                "date,description,amount\n"
                "2026-09-01,POS purchase,500.00\n"
                "2026-09-01,POS purchase,500.00\n"
            ),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["created_count"] == 2
    rows = client.get("/api/v1/transactions").json()
    assert len(rows) == 2
    assert rows[0]["external_id"] != rows[1]["external_id"]
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert balance == Decimal("99000.00")


def test_email_mailbox_and_approval_are_household_scoped(client: TestClient, monkeypatch) -> None:
    from app.api.v1 import imports as imports_api
    from app.core.config import Settings

    settings = Settings(
        inbound_email_domain="imports.example.test",
        inbound_email_webhook_secret="test-secret",
    )
    monkeypatch.setattr(imports_api, "get_settings", lambda: settings)

    register(client, "household-a-import@example.com")
    mailbox = client.post("/api/v1/imports/mailbox")
    assert mailbox.status_code == 200, mailbox.text
    inbound = client.post(
        "/api/v1/imports/inbound-email",
        headers={"X-Inbound-Email-Secret": "test-secret"},
        json={
            "To": mailbox.json()["address"],
            "From": "alerts@bank.example",
            "Subject": "Debit Alert",
            "TextBody": "Your account was debited NGN 5,000.00 on 15/11/2026. Ref: TENANT123",
            "Date": "Sun, 15 Nov 2026 10:00:00 +0100",
            "MessageID": "tenant-a-message-0001",
        },
    )
    assert inbound.status_code == 200, inbound.text
    job_id = inbound.json()["id"]

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    register(client, "household-b-import@example.com")
    account_b = client.post(
        "/api/v1/accounts",
        json={"name": "B Current", "type": "bank", "current_balance": "200000.00"},
    ).json()
    assert client.get("/api/v1/imports/review").json() == []

    approval = client.post(
        f"/api/v1/imports/{job_id}/approve",
        json={"account_id": account_b["id"]},
    )
    assert approval.status_code == 404
    assert client.get("/api/v1/transactions").json() == []


def test_bank_alert_uses_provider_date_only_when_transaction_date_is_absent() -> None:
    from datetime import date

    from app.services.email_imports import parse_bank_alert

    row = parse_bank_alert(
        sender="alerts@bank.example",
        subject="Debit Alert",
        body="Your account was debited NGN 5,000.00. Ref: PM123456",
        email_date="Sun, 15 Nov 2026 10:00:00 +0100",
    )
    assert row.date == date(2026, 11, 15)


def test_text_statement_rejects_malformed_transaction_rows_without_partial_posting(
    client: TestClient,
) -> None:
    register(client, "malformed-statement@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    response = client.post(
        "/api/v1/imports/statement",
        json={
            "account_id": account["id"],
            "content": (
                "date|amount|narrative|reference\n"
                "2026-09-10|-50000.00|Salary|good-row\n"
                "not-a-date|12000.00|Malformed|bad-row\n"
            ),
        },
    )
    assert response.status_code == 400
    assert client.get("/api/v1/transactions").json() == []
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert balance == Decimal("100000.00")


def test_statement_upload_uses_configured_size_limit(client: TestClient, monkeypatch) -> None:
    from app.api.v1 import imports as imports_api
    from app.core.config import Settings

    register(client, "upload-limit@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    monkeypatch.setattr(
        imports_api,
        "get_settings",
        lambda: Settings(max_import_upload_bytes=8),
    )
    response = client.post(
        "/api/v1/imports/upload",
        data={"account_id": account["id"]},
        files={"file": ("statement.csv", b"date,amount\n2026-09-01,500.00\n", "text/csv")},
    )
    assert response.status_code == 413
    assert "8-byte" in response.json()["detail"]


def test_permanently_unparseable_postmark_alert_is_acknowledged_without_retry(
    client: TestClient, monkeypatch
) -> None:
    from app.api.v1 import imports as imports_api
    from app.core.config import Settings

    register(client, "rejected-alert@example.com")
    monkeypatch.setattr(
        imports_api,
        "get_settings",
        lambda: Settings(
            inbound_email_domain="imports.example.test",
            inbound_email_webhook_secret="test-secret",
        ),
    )
    mailbox = client.post("/api/v1/imports/mailbox")
    response = client.post(
        "/api/v1/imports/inbound-email",
        auth=("ipile", "test-secret"),
        json={
            "To": mailbox.json()["address"],
            "From": "alerts@bank.example",
            "Subject": "Debit Alert",
            "TextBody": "Debited NGN 5,000.00. Available balance NGN 45,000.00.",
            "Date": "Sun, 15 Nov 2026 10:00:00 +0100",
            "MessageID": "postmark-rejected-0001",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    queue = client.get("/api/v1/imports/review").json()
    assert len(queue) == 1
    assert queue[0]["status"] == "rejected"
    assert "unambiguous" in queue[0]["result"]["errors"][0]


def test_imported_transfer_is_not_posted_without_counterparty_account(client: TestClient) -> None:
    from decimal import Decimal

    register(client, "transfer-import@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    response = client.post(
        "/api/v1/imports/csv",
        json={
            "account_id": account["id"],
            "content": (
                "date,amount,type,description,external_id\n"
                "2026-09-01,5000.00,transfer,Transfer to savings,transfer-1\n"
            ),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["created_count"] == 0
    assert response.json()["error_count"] == 1
    assert response.json()["status"] == "completed_with_errors"
    assert "counterparty account" in response.json()["result"]["errors"][0]
    assert client.get("/api/v1/transactions").json() == []
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert balance == Decimal("100000.00")


def test_preview_does_not_post_transactions_until_explicit_commit(client: TestClient) -> None:
    register(client, "staged-import@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "100000.00"},
    ).json()
    content = (
        "date,amount,type,description,external_id\n"
        "2026-09-01,2500.00,expense,Market,stage-1\n"
    )
    preview = client.post(
        "/api/v1/imports/preview",
        json={"account_id": account["id"], "source": "csv", "content": content},
    )
    assert preview.status_code == 201, preview.text
    assert preview.json()["status"] == "pending_review"
    assert preview.json()["result"]["row_count"] == 1
    assert client.get("/api/v1/transactions").json() == []
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert balance == Decimal("100000.00")

    committed = client.post(
        f"/api/v1/imports/jobs/{preview.json()['id']}/commit",
        json={"account_id": account["id"]},
    )
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert committed.json()["created_count"] == 1
    assert len(client.get("/api/v1/transactions").json()) == 1
    balance = Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"])
    assert balance == Decimal("97500.00")


def test_staged_import_commit_is_idempotent_and_household_scoped(client: TestClient) -> None:
    register(client, "staged-scope-a@example.com")
    account_a = client.post(
        "/api/v1/accounts",
        json={"name": "A Current", "type": "bank", "current_balance": "10000.00"},
    ).json()
    preview = client.post(
        "/api/v1/imports/preview",
        json={
            "account_id": account_a["id"],
            "source": "csv",
            "content": "date,amount,external_id\n2026-09-01,500.00,stage-scope-1\n",
        },
    )
    assert preview.status_code == 201, preview.text
    job_id = preview.json()["id"]
    assert client.post(
        f"/api/v1/imports/jobs/{job_id}/commit",
        json={"account_id": account_a["id"]},
    ).status_code == 200
    second = client.post(
        f"/api/v1/imports/jobs/{job_id}/commit",
        json={"account_id": account_a["id"]},
    )
    assert second.status_code == 400

    client.post("/api/v1/auth/logout")
    register(client, "staged-scope-b@example.com")
    account_b = client.post(
        "/api/v1/accounts",
        json={"name": "B Current", "type": "bank", "current_balance": "10000.00"},
    ).json()
    foreign = client.post(
        f"/api/v1/imports/jobs/{job_id}/commit",
        json={"account_id": account_b["id"]},
    )
    assert foreign.status_code == 404
