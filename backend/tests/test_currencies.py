from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.currencies import (
    CurrencyError,
    convert_amount,
    currency_catalog,
    transaction_amount_in_base,
    validate_currency,
)


def test_currency_catalog_contains_major_global_currencies():
    codes = {row["code"] for row in currency_catalog()}
    assert {"NGN", "USD", "GBP", "EUR", "CHF", "CAD", "AUD", "AED", "GHS", "KES"} <= codes


@pytest.mark.parametrize("code", ["NGN", "USD", "GBP", "EUR", "CHF", "CAD"])
def test_currency_codes_are_normalized(code):
    assert validate_currency(code.lower()) == code


def test_unsupported_currency_is_rejected():
    with pytest.raises(CurrencyError):
        validate_currency("XXX")


def test_identity_conversion_does_not_need_provider_or_database():
    result = convert_amount(
        None, None, Decimal("1234.50"), "NGN", "NGN", date(2026, 11, 26)
    )
    assert result == {
        "amount": "1234.50",
        "original_amount": "1234.50",
        "from_currency": "NGN",
        "to_currency": "NGN",
        "rate": "1.000000000000",
        "rate_date": date(2026, 11, 26),
        "source": "identity",
    }


def test_transaction_uses_persisted_base_amount():
    transaction = SimpleNamespace(
        id="tx-1",
        amount=Decimal("100.00"),
        currency="USD",
        base_amount=Decimal("78.25"),
        base_currency="GBP",
    )
    assert transaction_amount_in_base(transaction, "GBP") == Decimal("78.25")


def test_foreign_transaction_without_historical_conversion_fails_closed():
    transaction = SimpleNamespace(
        id="tx-2",
        amount=Decimal("100.00"),
        currency="USD",
        base_amount=None,
        base_currency=None,
    )
    with pytest.raises(CurrencyError):
        transaction_amount_in_base(transaction, "GBP")


def test_transaction_amount_in_base_rejects_mismatched_snapshot_currency():
    transaction = SimpleNamespace(
        id="tx-3",
        amount=Decimal("100.00"),
        currency="USD",
        base_amount=Decimal("78.25"),
        base_currency="EUR",
    )
    with pytest.raises(CurrencyError):
        transaction_amount_in_base(transaction, "GBP")


def test_transaction_amount_in_base_uses_native_amount_for_identity_currency():
    transaction = SimpleNamespace(
        id="tx-4",
        amount=Decimal("100.10"),
        currency="GBP",
        base_amount=None,
        base_currency="GBP",
    )
    assert transaction_amount_in_base(transaction, "GBP") == Decimal("100.10")


def test_get_rate_uses_stored_observation_only_on_exact_effective_date(monkeypatch):
    import app.services.currencies as currencies

    class Query:
        def __init__(self, row):
            self.row = row
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def first(self):
            return self.row

    class FakeDb:
        def __init__(self, row):
            self.row = row
            self.added = []
        def query(self, model):
            return Query(self.row if model.__name__ == "ExchangeRate" else None)
        def add(self, row):
            self.added.append(row)
        def flush(self):
            pass

    old = SimpleNamespace(
        rate=Decimal("1.25"), rate_date=date(2026, 11, 24), source="manual",
        fetched_at=None,
    )
    db = FakeDb(old)
    def provider(*args, **kwargs):
        raise currencies.httpx.ConnectError("offline")
    monkeypatch.setattr(currencies.httpx, "get", provider)
    with pytest.raises(CurrencyError):
        currencies.get_rate(db, "household", "USD", "GBP", date(2026, 11, 26))


def test_get_rate_accepts_exact_date_stored_manual_observation():
    import app.services.currencies as currencies

    class Query:
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def first(self):
            return SimpleNamespace(
                rate=Decimal("0.80"), rate_date=date(2026, 11, 26),
                source="manual", fetched_at=None,
            )

    class FakeDb:
        def query(self, model):
            return Query()

    rate, rate_date, source = currencies.get_rate(
        FakeDb(), "household", "USD", "GBP", date(2026, 11, 26)
    )
    assert rate == Decimal("0.80")
    assert rate_date == date(2026, 11, 26)
    assert source == "manual"


def test_get_rate_rejects_old_observation_instead_of_relabeling_it():
    import app.services.currencies as currencies

    old = SimpleNamespace(
        rate=Decimal("1.25"),
        rate_date=date(2026, 11, 24),
        source="manual",
        fetched_at=None,
    )

    class Query:
        def __init__(self, row):
            self.row = row
        def filter(self, *args, **kwargs):
            return self
        def order_by(self, *args, **kwargs):
            return self
        def first(self):
            return self.row

    class FakeDb:
        def query(self, model):
            return Query(old if model.__name__ == "ExchangeRate" else None)
        def get(self, model, key):
            return SimpleNamespace(timezone="Africa/Lagos")

    def offline(*args, **kwargs):
        raise currencies.httpx.ConnectError("offline")

    original_get = currencies.httpx.get
    currencies.httpx.get = offline
    try:
        with pytest.raises(CurrencyError):
            currencies.get_rate(
                FakeDb(), "household", "USD", "GBP", date(2026, 11, 26)
            )
    finally:
        currencies.httpx.get = original_get
