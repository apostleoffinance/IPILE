# ruff: noqa: I001
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import register


PNG_BYTES = b"\x89PNG\r\n\x1a\nreceipt-test-image"


def test_receipt_preview_is_pending_and_does_not_change_ledger(
    client: TestClient, monkeypatch
) -> None:
    from app.api.v1 import receipts as receipts_api

    register(client, "receipt-preview@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "50000.00"},
    ).json()
    monkeypatch.setattr(
        receipts_api,
        "extract_receipt",
        lambda *_: {
            "merchant": "FRESH MART",
            "date": "2026-11-20",
            "amount": "4500.00",
            "currency": "NGN",
            "field_confidence": {"merchant": 0.91, "date": 0.88, "amount": 0.82},
            "overall_confidence": 0.87,
            "warnings": [],
        },
    )
    preview = client.post(
        "/api/v1/receipts/preview",
        data={"account_id": account["id"]},
        files={"file": ("receipt.png", PNG_BYTES, "image/png")},
    )
    assert preview.status_code == 201, preview.text
    body = preview.json()
    assert body["status"] == "pending_review"
    assert body["merchant"] == "FRESH MART"
    assert body["amount"] == "4500.00"
    assert body["extracted"]["field_confidence"]["amount"] == 0.82
    assert client.get("/api/v1/transactions").json() == []
    assert Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"]) == Decimal(
        "50000.00"
    )


def test_receipt_approval_posts_once_and_duplicate_upload_is_idempotent(
    client: TestClient, monkeypatch
) -> None:
    from app.api.v1 import receipts as receipts_api

    register(client, "receipt-approve@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "50000.00"},
    ).json()
    monkeypatch.setattr(
        receipts_api,
        "extract_receipt",
        lambda *_: {
            "merchant": "FRESH MART",
            "date": "2026-11-20",
            "amount": "4500.00",
            "currency": "NGN",
            "field_confidence": {"merchant": 0.9, "date": 0.9, "amount": 0.9},
            "overall_confidence": 0.9,
            "warnings": [],
        },
    )
    form = {"account_id": account["id"]}
    files = {"file": ("receipt.png", PNG_BYTES, "image/png")}
    preview = client.post("/api/v1/receipts/preview", data=form, files=files)
    assert preview.status_code == 201, preview.text
    duplicate = client.post("/api/v1/receipts/preview", data=form, files=files)
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == preview.json()["id"]
    approved = client.post(f"/api/v1/receipts/{preview.json()['id']}/approve")
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["transaction_id"]
    assert len(client.get("/api/v1/transactions").json()) == 1
    assert Decimal(client.get("/api/v1/accounts").json()[0]["current_balance"]) == Decimal(
        "45500.00"
    )
    repeated = client.post(f"/api/v1/receipts/{preview.json()['id']}/approve")
    assert repeated.status_code == 409
    assert len(client.get("/api/v1/transactions").json()) == 1


def test_receipt_missing_fields_can_be_corrected_before_approval(
    client: TestClient, monkeypatch
) -> None:
    from app.api.v1 import receipts as receipts_api

    register(client, "receipt-correct@example.com")
    account = client.post(
        "/api/v1/accounts",
        json={"name": "Current", "type": "bank", "current_balance": "10000.00"},
    ).json()
    monkeypatch.setattr(
        receipts_api,
        "extract_receipt",
        lambda *_: {
            "merchant": None,
            "date": None,
            "amount": None,
            "currency": None,
            "field_confidence": {"merchant": 0.0, "date": 0.0, "amount": 0.0},
            "overall_confidence": 0.0,
            "warnings": ["No readable fields"],
        },
    )
    preview = client.post(
        "/api/v1/receipts/preview",
        data={"account_id": account["id"]},
        files={"file": ("receipt.png", PNG_BYTES, "image/png")},
    )
    assert preview.status_code == 201
    assert client.post(f"/api/v1/receipts/{preview.json()['id']}/approve").status_code == 422
    corrected = client.patch(
        f"/api/v1/receipts/{preview.json()['id']}",
        json={
            "merchant": "Corner Shop",
            "date": "2026-11-20",
            "amount": "1250.00",
            "currency": "NGN",
        },
    )
    assert corrected.status_code == 200, corrected.text
    approved = client.post(f"/api/v1/receipts/{preview.json()['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_receipts_are_household_scoped(client: TestClient, monkeypatch) -> None:
    from app.api.v1 import receipts as receipts_api

    monkeypatch.setattr(
        receipts_api,
        "extract_receipt",
        lambda *_: {
            "merchant": "Shop",
            "date": "2026-11-20",
            "amount": "100.00",
            "currency": "NGN",
            "field_confidence": {},
            "overall_confidence": 0.9,
            "warnings": [],
        },
    )
    register(client, "receipt-scope-a@example.com")
    account_a = client.post(
        "/api/v1/accounts",
        json={"name": "A", "type": "bank", "current_balance": "1000.00"},
    ).json()
    created = client.post(
        "/api/v1/receipts/preview",
        data={"account_id": account_a["id"]},
        files={"file": ("receipt.png", PNG_BYTES, "image/png")},
    )
    assert created.status_code == 201
    receipt_id = created.json()["id"]

    client.post("/api/v1/auth/logout")
    register(client, "receipt-scope-b@example.com")
    assert client.get("/api/v1/receipts").json() == []
    assert client.post(f"/api/v1/receipts/{receipt_id}/approve").status_code == 404
