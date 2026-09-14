from decimal import Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, PlainSerializer

from app.money import MoneyError, parse_money


def _coerce(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise MoneyError("Amount must be a decimal string.")
    if isinstance(value, int):
        return parse_money(str(value))
    if isinstance(value, Decimal):
        return parse_money(value)
    if isinstance(value, str):
        return parse_money(value)
    raise MoneyError("Amount must be a decimal string.")


def _non_negative(value: Decimal) -> Decimal:
    if value < 0:
        raise MoneyError("Amount must be greater than or equal to 0.")
    return value


def _parse_signed(value: Any) -> Decimal:
    return _coerce(value)


def _parse_amount(value: Any) -> Decimal:
    return _non_negative(_coerce(value))


MoneySigned = Annotated[
    Decimal,
    BeforeValidator(_parse_signed),
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str),
    Field(examples=["2000000.00"]),
]

MoneyAmount = Annotated[
    Decimal,
    BeforeValidator(_parse_amount),
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str),
    Field(examples=["2000000.00"]),
]
