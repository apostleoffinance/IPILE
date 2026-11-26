"""Generic CSV extraction using canonical statement fields and conservative direction rules."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal

from app.services.import_adapters import ImportRow, _make_row, _parse_amount
from app.services.statement_intelligence import CanonicalField, map_statement_headers

DATE_FORMATS = (
    "%d %b %Y %H:%M:%S",
    "%d %B %Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
)


def _parse_statement_datetime(value: str) -> datetime:
    normalized = " ".join(value.strip().split())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized transaction date: {value}")


def _amount_or_zero(value: str | None) -> Decimal:
    text = (value or "").strip()
    if not text or text in {"-", "--", "—", "–"}:
        return Decimal("0")
    return _parse_amount(text)


def _currency_from_headers(headers: list[str]) -> str | None:
    joined = " ".join(headers).upper()
    if "₦" in joined or "NGN" in joined:
        return "NGN"
    if "$" in joined or "USD" in joined:
        return "USD"
    if "€" in joined or "EUR" in joined:
        return "EUR"
    if "£" in joined or "GBP" in joined:
        return "GBP"
    return None


def parse_universal_csv(content: str) -> list[ImportRow]:
    """Parse bank CSVs with varied column names; ambiguous rows are rejected."""
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
    time_index = mapping.index_for(CanonicalField.TRANSACTION_TIME)
    inferred_currency = _currency_from_headers(headers)
    rows: list[ImportRow] = []
    for row_number, values in enumerate(reader, start=2):
        if not any(value.strip() for value in values):
            continue

        def cell(index: int | None) -> str:
            return values[index].strip() if index is not None and index < len(values) else ""

        try:
            raw_date = cell(date_index)
            raw_time = cell(time_index)
            transaction_datetime = _parse_statement_datetime(
                f"{raw_date} {raw_time}".strip() if raw_time else raw_date
            )
            if debit_index is not None or credit_index is not None:
                debit = abs(_amount_or_zero(cell(debit_index)))
                credit = abs(_amount_or_zero(cell(credit_index)))
                if debit and credit:
                    raise ValueError("Both debit and credit columns contain amounts.")
                if not debit and not credit:
                    raise ValueError("A transaction row must contain a debit or credit amount; neither column is populated.")
                amount = credit if credit else -debit
                tx_type = "income" if credit else "expense"
            else:
                raw_amount = cell(amount_index)
                amount = _parse_amount(raw_amount)
                direction = cell(direction_index).lower()
                declared_type = cell(transaction_type_index).lower()
                marker = raw_amount.upper()
                if declared_type == "transfer":
                    tx_type = "transfer"
                    cash_direction = "unknown"
                    amount = abs(amount)
                else:
                    is_debit = amount < 0 or "DR" in marker or direction in {
                        "debit", "dr", "out", "outgoing", "expense",
                        "withdrawal", "withdraw", "payment",
                    }
                    is_credit = "CR" in marker or direction in {
                        "credit", "cr", "in", "incoming", "income", "refund", "deposit",
                    }
                    is_debit = is_debit or declared_type in {
                        "debit", "dr", "withdrawal", "withdraw", "payment",
                        "expense", "debit card", "withdrawal transaction",
                    }
                    is_credit = is_credit or declared_type in {
                        "credit", "cr", "deposit", "income", "refund",
                    }
                    if is_debit == is_credit:
                        raise ValueError(
                            "Transaction direction is unclear; this amount was not guessed."
                        )
                    tx_type = declared_type or ("expense" if is_debit else "income")
                    if tx_type in {"debit", "dr", "withdrawal", "withdraw", "payment"}:
                        tx_type = "expense"
                    elif tx_type in {"credit", "cr", "deposit"}:
                        tx_type = "income"
                    if tx_type not in {
                        "income", "expense", "refund", "transfer", "investment",
                        "debt_payment", "giving",
                    }:
                        tx_type = "expense" if is_debit else "income"
                    amount = -abs(amount) if is_debit else abs(amount)
                    cash_direction = "debit" if is_debit else "credit"

            description = cell(description_index) or None
            reference = cell(reference_index) or None
            value_date_text = cell(value_date_index)
            value_date = (
                _parse_statement_datetime(value_date_text).date()
                if value_date_text else None
            )
            balance_text = cell(balance_index)
            running_balance = (
                abs(_amount_or_zero(balance_text))
                if balance_text and balance_text not in {"-", "--", "—", "–"}
                else None
            )
            currency = (
                cell(currency_index).upper() or inferred_currency
                if currency_index is not None
                else inferred_currency
            )
            rows.append(
                _make_row(
                    raw_date=transaction_datetime.date().isoformat(),
                    amount=amount,
                    tx_type=tx_type,
                    description=description,
                    external_id=reference,
                    merchant=description,
                    row_index=row_number,
                    currency=currency,
                    value_date=value_date,
                    transaction_datetime=transaction_datetime,
                    running_balance=running_balance,
                    cash_direction=(cash_direction if tx_type == "transfer" else cash_direction),
                )
            )
        except (ValueError, IndexError) as exc:
            raise ValueError(f"CSV row {row_number}: {exc}") from exc

    if not rows:
        raise ValueError("No supported transaction rows found in CSV.")
    return rows
