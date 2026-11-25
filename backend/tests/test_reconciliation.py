from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from cryptography.fernet import Fernet

from app.services import bank_security, reconciliation
from app.services.mono import MonoClient


@pytest.mark.parametrize(
    ("raw", "currency", "expected"),
    [
        ("450000", "NGN", "4500.00"),
        ("1234", "USD", "12.34"),
        ("0", "JPY", "0.00"),
    ],
)
def test_minor_units_use_currency_precision(raw, currency, expected):
    assert reconciliation.minor_to_major(
        raw, currency, allow_nonpositive=True
    ) == Decimal(expected)


def test_unknown_currency_precision_is_rejected():
    with pytest.raises(ValueError, match="Unsupported currency precision"):
        reconciliation.minor_to_major("100", "XYZ")


def test_nonpositive_transaction_amount_is_rejected():
    with pytest.raises(ValueError, match="non-positive"):
        reconciliation.minor_to_major("-100", "NGN")


def test_provider_date_parsing_and_invalid_date():
    assert reconciliation.parse_provider_date(
        "2026-11-25T14:30:00Z"
    ).isoformat() == "2026-11-25"
    with pytest.raises(ValueError, match="invalid transaction date"):
        reconciliation.parse_provider_date("not-a-date")


def test_provider_account_id_is_encrypted(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(
        bank_security,
        "get_settings",
        lambda: SimpleNamespace(bank_data_encryption_key=key),
    )
    encrypted = bank_security.encrypt_provider_account_id("mono-secret-id")
    assert encrypted != "mono-secret-id"
    assert bank_security.decrypt_provider_account_id(encrypted) == "mono-secret-id"


def test_encryption_fails_closed_without_key(monkeypatch):
    monkeypatch.setattr(
        bank_security,
        "get_settings",
        lambda: SimpleNamespace(bank_data_encryption_key=""),
    )
    with pytest.raises(RuntimeError, match="not configured"):
        bank_security.encrypt_provider_account_id("mono-secret-id")


def test_mono_transaction_client_uses_documented_account_endpoint():
    def handler(request):
        assert request.url.path == "/v2/accounts/mono-account/transactions"
        assert request.headers["mono-sec-key"] == "test-secret"
        assert request.url.params["page"] == "2"
        return httpx.Response(200, json={
            "status": "successful",
            "data": [{"id": "txn-1", "amount": 1000, "type": "debit"}],
            "meta": {"page": 2, "next": None},
        })

    client = MonoClient("test-secret", transport=httpx.MockTransport(handler))
    try:
        rows, meta = client.fetch_transactions("mono-account", page=2)
    finally:
        client.close()
    assert rows[0]["id"] == "txn-1"
    assert meta["page"] == 2
