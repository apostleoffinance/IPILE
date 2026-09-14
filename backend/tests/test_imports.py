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
