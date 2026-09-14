from decimal import Decimal

import pytest

from app.money import MoneyError, format_money, parse_money, quantize_money


def test_parse_and_format_two_decimals() -> None:
    assert format_money("2000000") == "2000000.00"
    assert parse_money("150000.1") == Decimal("150000.10")


def test_quantize_half_up() -> None:
    assert quantize_money(Decimal("1.225")) == Decimal("1.23")
    assert quantize_money(Decimal("1.224")) == Decimal("1.22")


def test_reject_invalid_amount() -> None:
    with pytest.raises(MoneyError):
        parse_money("not-money")
