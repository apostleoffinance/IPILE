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
