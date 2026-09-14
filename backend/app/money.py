"""Decimal money helpers. Never use float for financial amounts."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

TWOPLACES = Decimal("0.01")


class MoneyError(ValueError):
    pass


def parse_money(value: str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        amount = value
    else:
        text = (value or "").strip()
        if not text:
            raise MoneyError("Amount is required.")
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise MoneyError("Amount must be a decimal string.") from exc
    if amount != amount.quantize(TWOPLACES):
        amount = amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    return amount


def format_money(value: str | Decimal) -> str:
    return f"{parse_money(value):.2f}"


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
