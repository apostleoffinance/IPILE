"""Bank-agnostic statement column recognition."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum


class ColumnField(StrEnum):
    TRANSACTION_DATE = "transaction_date"
    TRANSACTION_TIME = "transaction_time"
    DATETIME = "transaction_datetime"
    VALUE_DATE = "value_date"
    DESCRIPTION = "description"
    DEBIT = "debit_amount"
    CREDIT = "credit_amount"
    AMOUNT = "amount"
    BALANCE = "running_balance"
    REFERENCE = "reference"
    CHANNEL = "channel"
    CURRENCY = "currency"
    TYPE = "transaction_type"


ALIASES: dict[ColumnField, tuple[str, ...]] = {
    ColumnField.TRANSACTION_DATE: (
        "date", "transaction date", "txn date", "trans date", "posting date",
        "posted date", "booking date",
    ),
    ColumnField.TRANSACTION_TIME: ("transaction time", "trans time", "txn time", "time"),
    ColumnField.DATETIME: ("transaction datetime", "transaction date time", "date time", "timestamp"),
    ColumnField.VALUE_DATE: ("value date", "effective date", "settlement date"),
    ColumnField.DESCRIPTION: (
        "description", "narration", "particulars", "details", "transaction details",
        "remarks", "memo", "payment details", "transaction description",
    ),
    ColumnField.DEBIT: (
        "debit", "debit amount", "amount debited", "withdrawal", "withdrawals",
        "money out", "paid out", "outflow",
    ),
    ColumnField.CREDIT: (
        "credit", "credit amount", "amount credited", "deposit", "deposits",
        "money in", "paid in", "inflow",
    ),
    ColumnField.AMOUNT: ("amount", "transaction amount", "value"),
    ColumnField.BALANCE: (
        "balance", "running balance", "balance after", "available balance",
        "ledger balance", "closing balance",
    ),
    ColumnField.REFERENCE: (
        "reference", "transaction reference", "transaction id", "txn id",
        "session id", "session reference", "rrn", "retrieval reference number",
    ),
    ColumnField.CHANNEL: ("channel", "transaction channel", "payment channel", "source"),
    ColumnField.CURRENCY: ("currency", "ccy", "currency code"),
    ColumnField.TYPE: ("type", "transaction type", "dr cr", "debit credit", "direction"),
}


@dataclass(frozen=True, slots=True)
class ColumnMapping:
    field: ColumnField
    column_index: int
    original_header: str
    normalized_header: str
    confidence: float


def normalize_header(value: str) -> str:
    """Normalize punctuation, case, diacritics and currency decorations."""
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ")
    text = re.sub(r"\([^)]*₦[^)]*\)|\[[^]]*₦[^]]*\]", " ", text)
    text = re.sub(r"\b(?:ngn|usd|gbp|eur|kes|ghs)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def map_statement_columns(headers: list[str]) -> dict[ColumnField, ColumnMapping]:
    """Map recognized headers independent of institution or column ordering.

    Exact aliases win. Conservative token matching handles decorated variants
    while avoiding ambiguous generic matches such as amount => debit/credit.
    """
    aliases = {
        field: {normalize_header(alias) for alias in values}
        for field, values in ALIASES.items()
    }
    result: dict[ColumnField, ColumnMapping] = {}
    for index, original in enumerate(headers):
        normalized = normalize_header(original)
        if not normalized:
            continue
        candidates = [
            (field, 1.0)
            for field, values in aliases.items()
            if normalized in values
        ]
        if not candidates:
            tokens = set(normalized.split())
            if "debit" in tokens or "withdrawal" in tokens:
                candidates.append((ColumnField.DEBIT, 0.9))
            if "credit" in tokens or "deposit" in tokens:
                candidates.append((ColumnField.CREDIT, 0.9))
            if "balance" in tokens:
                candidates.append((ColumnField.BALANCE, 0.9))
            if "reference" in tokens or "session" in tokens or "rrn" in tokens:
                candidates.append((ColumnField.REFERENCE, 0.85))
            if "narration" in tokens or "description" in tokens or "particulars" in tokens:
                candidates.append((ColumnField.DESCRIPTION, 0.9))
            if "date" in tokens and "value" not in tokens:
                candidates.append((ColumnField.TRANSACTION_DATE, 0.85))
        for field, confidence in candidates:
            if field not in result:
                result[field] = ColumnMapping(
                    field=field, column_index=index, original_header=original,
                    normalized_header=normalized, confidence=confidence,
                )
    return result
