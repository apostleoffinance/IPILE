"""Generic bank CSV extraction using canonical fields and conservative direction rules."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal

from app.services.import_adapters import ImportRow, _make_row, _parse_amount
from app.services.statement_intelligence import CanonicalField, map_statement_headers

DATE_FORMATS = (
    "%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S",
    "%d %b %Y", "%d %B %Y", "%Y-%m-%d",
    "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d",
)


def _parse_datetime(value: str) -> datetime:
    normalized = " ".join(value.strip().split())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized transaction date: {value}")


def _amount_or_zero(value: str) -> Decimal:
    text = value.strip()
    if not text or text in {"-", "--", "—", "–"}:
        return Decimal("0")
    return _parse_amount(text)


def _currency_from_headers(headers: list[str]) -> str | None:
    joined = " ".join(headers).upper()
    for marker, currency in (("₦", "NGN"), ("NGN", "NGN"), ("$", "USD"),
                             ("USD", "USD"), ("€", "EUR"), ("EUR", "EUR"),
                             ("£", "GBP"), ("GBP", "GBP")):
        if marker in joined:
            return currency
    return None


def parse_universal_csv(content: str) -> list[ImportRow]:
    """Parse varied bank CSV headers; reject ambiguous transaction direction."""
    reader = csv.reader(io.StringIO(content))
    try:
        headers = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV requires a header row.") from exc
    mapping = map_statement_headers(headers)
    date_index = mapping.index_for(CanonicalField.TRANSACTION_DATE)
    amount_index = mapping.index_for(CanonicalField.AMOUNT)
    debit_index = mapping.index_for(CanonicalField.DEBIT)
    credit_index = mapping.index_for(CanonicalField.CREDIT)
    if date_index is None:
        raise ValueError("CSV needs one unambiguous transaction date column.")
    if not any(index is not None for index in (amount_index, debit_index, credit_index)):
        raise ValueError("CSV needs an amount, debit, or credit column.")

    description_index = mapping.index_for(CanonicalField.DESCRIPTION)
    reference_index = mapping.index_for(CanonicalField.REFERENCE)
    value_date_index = mapping.index_for(CanonicalField.VALUE_DATE)
    balance_index = mapping.index_for(CanonicalField.BALANCE)
    currency_index = mapping.index_for(CanonicalField.CURRENCY)
    direction_index = mapping.index_for(CanonicalField.DIRECTION)
    transaction_type_index = mapping.index_for(CanonicalField.TRANSACTION_TYPE)
    merchant_index = mapping.index_for(CanonicalField.MERCHANT)
    category_index = mapping.index_for(CanonicalField.CATEGORY)
    time_index = mapping.index_for(CanonicalField.TRANSACTION_TIME)
    inferred_currency = _currency_from_headers(headers)
    rows: list[ImportRow] = []

    for row_number, values in enumerate(reader, start=2):
        if not any(value.strip() for value in values):
            continue

        def cell(index: int | None) -> str:
            return values[index].strip() if index is not None and index < len(values) else ""

        try:
            date_value = cell(date_index)
            time_value = cell(time_index)
            transaction_datetime = _parse_datetime(
                date_value if time_value and time_value in date_value
                else (date_value + " " + time_value).strip()
            )
            if debit_index is not None or credit_index is not None:
                debit = abs(_amount_or_zero(cell(debit_index)))
                credit = abs(_amount_or_zero(cell(credit_index)))
                if debit and credit:
                    raise ValueError("Both debit and credit columns contain amounts.")
                if not debit and not credit:
                    raise ValueError("Neither debit nor credit amount is populated.")
                amount = credit if credit else -debit
                tx_type = "income" if credit else "expense"
            else:
                raw_amount = cell(amount_index)
                amount = _parse_amount(raw_amount)
                direction = cell(direction_index).lower()
                declared_type = cell(transaction_type_index).lower()
                marker = raw_amount.upper()
                is_debit = "DR" in marker or direction in {
                    "debit", "dr", "out", "outgoing", "expense",
                }
                is_credit = "CR" in marker or direction in {
                    "credit", "cr", "in", "incoming", "income", "refund",
                }
                if is_debit == is_credit:
                    if declared_type == "expense":
                        is_debit = True
                    elif declared_type in {"income", "refund"}:
                        is_credit = True
                    else:
                        raise ValueError(
                            "Transaction direction is unclear; this amount was not guessed."
                        )
                tx_type = declared_type or ("expense" if is_debit else "income")
                if tx_type not in {
                    "income", "expense", "transfer", "refund", "investment",
                    "debt_payment", "giving",
                }:
                    tx_type = "expense" if is_debit else "income"
                amount = abs(amount)

            description = cell(description_index) or None
            merchant = cell(merchant_index) or description
            category = cell(category_index) or None
            reference = cell(reference_index) or None
            value_date_text = cell(value_date_index)
            value_date = _parse_datetime(value_date_text).date() if value_date_text else None
            balance_text = cell(balance_index)
            running_balance = (
                abs(_amount_or_zero(balance_text))
                if balance_text and balance_text not in {"-", "--", "—", "–"}
                else None
            )
            currency = cell(currency_index).upper() if currency_index is not None else ""
            rows.append(_make_row(
                raw_date=transaction_datetime.date().isoformat(),
                amount=amount,
                tx_type=tx_type,
                description=description,
                external_id=reference,
                merchant=merchant,
                category=category,
                row_index=row_number,
                currency=currency or inferred_currency,
                value_date=value_date,
                transaction_datetime=transaction_datetime,
                running_balance=running_balance,
                extraction_confidence=mapping.confidence,
            ))
        except (ValueError, IndexError) as exc:
            raise ValueError(f"CSV row {row_number}: {exc}") from exc

    if not rows:
        raise ValueError("No supported transaction rows found in CSV.")
    return rows
