"""Semantic mapping of bank-specific headings to canonical statement fields."""

from __future__ import annotations

import re
import unicodedata

from app.services.statement_intelligence.schema import CanonicalField, ColumnMapping

ALIASES: dict[CanonicalField, frozenset[str]] = {
    CanonicalField.TRANSACTION_DATE: frozenset({
        "date", "transaction date", "trans date", "trans. date", "trans time",
        "transaction time", "txn date", "txn time", "posting date", "entry date",
    }),
    CanonicalField.VALUE_DATE: frozenset({"value date", "effective date", "settlement date"}),
    CanonicalField.DESCRIPTION: frozenset({
        "description", "narration", "particulars", "details", "transaction details",
        "remarks", "reference details", "payment details", "transaction description",
    }),
    CanonicalField.AMOUNT: frozenset({
        "amount", "transaction amount", "value", "amount ngn",
        "amount usd", "amount gbp", "amount eur",
    }),
    CanonicalField.DEBIT: frozenset({
        "debit", "debit amount", "withdrawal", "withdrawals", "money out",
        "paid out", "amount debited", "debit ngn", "debit amount ngn",
    }),
    CanonicalField.CREDIT: frozenset({
        "credit", "credit amount", "deposit", "deposits", "money in",
        "paid in", "amount credited", "credit ngn", "credit amount ngn",
    }),
    CanonicalField.BALANCE: frozenset({
        "balance", "running balance", "balance after", "available balance",
        "ledger balance", "closing balance", "balance ngn", "balance after ngn",
    }),
    CanonicalField.REFERENCE: frozenset({
        "reference", "transaction reference", "transaction id", "transaction no",
        "transaction number", "reference number", "transaction ref", "bank reference",
        "session id", "session reference", "external id",
        "rrn", "narration reference",
    }),
    CanonicalField.CHANNEL: frozenset({
        "channel", "payment channel", "transaction channel", "mode",
    }),
    CanonicalField.CURRENCY: frozenset({"currency", "ccy", "currency code"}),
    CanonicalField.TRANSACTION_TIME: frozenset({"time", "time of transaction"}),
    CanonicalField.DIRECTION: frozenset({
        "direction", "debit credit indicator", "dr cr", "dr cr indicator",
    }),
    CanonicalField.TRANSACTION_TYPE: frozenset({"type", "transaction type"}),
    CanonicalField.MERCHANT: frozenset({
        "merchant", "payee", "beneficiary", "counterparty", "recipient",
    }),
    CanonicalField.CATEGORY: frozenset({"category", "transaction category"}),
}


def normalize_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("₦", " ngn ").replace("$", " usd ").replace("€", " eur ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


_NORMALIZED_ALIASES = {
    field_name: frozenset(normalize_header(alias) for alias in aliases)
    for field_name, aliases in ALIASES.items()
}


def map_statement_headers(headers: list[str] | tuple[str, ...]) -> ColumnMapping:
    """Map recognizable headings; ambiguous duplicates are deliberately left unmapped."""
    normalized = [normalize_header(header) for header in headers]
    candidates: dict[CanonicalField, list[int]] = {}
    for index, header in enumerate(normalized):
        for field_name, aliases in _NORMALIZED_ALIASES.items():
            if header in aliases:
                candidates.setdefault(field_name, []).append(index)

    indexes = {
        field_name: positions[0]
        for field_name, positions in candidates.items()
        if len(positions) == 1
    }
    recognized = sum(len(positions) == 1 for positions in candidates.values())
    unmapped = tuple(headers[i] for i, header in enumerate(normalized) if not any(
        header in aliases for aliases in _NORMALIZED_ALIASES.values()
    ))
    return ColumnMapping(
        indexes=indexes,
        headers=tuple(headers),
        confidence=min(1.0, recognized / 7),
        unmapped_headers=unmapped,
    )
