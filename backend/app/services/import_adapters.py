"""Bank statement adapters normalise source rows before they reach the ledger."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from app.money import quantize_money

IMPORT_SOURCES = frozenset({"csv", "statement", "api", "open_banking", "email"})
TX_TYPES = frozenset(
    {"income", "expense", "transfer", "refund", "investment", "debt_payment", "giving"}
)


@dataclass(frozen=True)
class ImportRow:
    date: date
    amount: Decimal
    type: str
    description: str | None
    external_id: str
    merchant: str | None = None
    category_name: str | None = None
    currency: str | None = None
    value_date: date | None = None
    transaction_datetime: datetime | None = None
    running_balance: Decimal | None = None
    source_page: int | None = None
    extraction_confidence: float | None = None


class ImportAdapter(Protocol):
    source: str

    def parse(self, content: str) -> list[ImportRow]: ...


def _parse_date(raw: str) -> date:
    text = raw.strip()
    for fmt in (
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
        "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%d-%b-%Y",
        "%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {raw}")


def _parse_amount(raw: str) -> Decimal:
    text = raw.strip().replace(",", "").replace("₦", "").replace("NGN", "").strip()
    text = re.sub(r"[^0-9.()\-]", "", text)
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return quantize_money(Decimal(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid amount: {raw}") from exc


def _stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _make_row(
    *, raw_date: str, amount: Decimal, tx_type: str, description: str | None,
    external_id: str | None, merchant: str | None = None, category: str | None = None,
    row_index: int | None = None, currency: str | None = None,
    value_date: date | None = None, transaction_datetime: datetime | None = None,
    running_balance: Decimal | None = None, source_page: int | None = None,
    extraction_confidence: float | None = None,
) -> ImportRow:
    parsed_date = _parse_date(raw_date)
    if amount == 0:
        raise ValueError("Transaction amount must be greater than zero.")
    tx_type = tx_type.strip().lower()
    if tx_type not in TX_TYPES:
        tx_type = "income" if amount < 0 else "expense"
    return ImportRow(
        date=parsed_date,
        amount=abs(amount),
        type=tx_type,
        description=description.strip() if description else None,
        external_id=(external_id or "").strip() or _stable_id(
            parsed_date.isoformat(), str(amount), description or "", merchant or "",
            str(row_index or ""),
        ),
        merchant=merchant.strip() if merchant else None,
        category_name=category.strip() if category else None,
        currency=currency,
        value_date=value_date,
        transaction_datetime=transaction_datetime,
        running_balance=running_balance,
        source_page=source_page,
        extraction_confidence=extraction_confidence,
    )


class CsvImportAdapter:
    source = "csv"

    def parse(self, content: str) -> list[ImportRow]:
        # One semantic mapper serves CSV exports from every bank. It refuses to
        # infer transaction direction from an unsigned amount-only column.
        from app.services.statement_intelligence.csv_extractor import parse_universal_csv

        return parse_universal_csv(content)


class StatementImportAdapter:
    """Supports pipe/tab-delimited exports and common CSV statement layouts."""

    source = "statement"

    def parse(self, content: str) -> list[ImportRow]:
        first_line = next((line for line in content.splitlines() if line.strip()), "")
        if "," in first_line and "|" not in first_line:
            return CsvImportAdapter().parse(content)
        rows: list[ImportRow] = []
        for index, line in enumerate(content.splitlines(), start=1):
            text = line.strip()
            if not text or text.lower().startswith(("date", "transaction date")):
                continue
            parts = [part.strip() for part in text.replace("\t", "|").split("|")]
            if len(parts) < 3:
                if "|" in text:
                    raise ValueError(
                        f"Statement line {index}: expected at least three columns."
                    )
                continue
            try:
                parsed_date = _parse_date(parts[0])
            except ValueError as exc:
                raise ValueError(f"Statement line {index}: {exc}") from exc
            if len(parts) >= 5:
                debit = _parse_amount(parts[2] or "0")
                credit = _parse_amount(parts[3] or "0")
                if debit and credit:
                    raise ValueError(
                        f"Statement line {index}: both debit and credit are populated."
                    )
                amount = credit if credit else -abs(debit)
                tx_type = "income" if credit else "expense"
                description, external_id = parts[1], parts[4]
            else:
                amount = _parse_amount(parts[1])
                tx_type = "income" if amount < 0 else "expense"
                description, external_id = parts[2], parts[3] if len(parts) > 3 else ""
            rows.append(
                _make_row(
                    raw_date=parsed_date.isoformat(),
                    amount=amount,
                    tx_type=tx_type,
                    description=description,
                    external_id=external_id,
                    merchant=description,
                    row_index=index,
                )
            )
        if not rows:
            raise ValueError("No supported transaction rows found in statement.")
        return rows


ADAPTERS: dict[str, ImportAdapter] = {
    "csv": CsvImportAdapter(),
    "statement": StatementImportAdapter(),
}


def get_adapter(source: str) -> ImportAdapter:
    adapter = ADAPTERS.get(source)
    if adapter is None:
        raise ValueError(f"Unknown import source: {source}")
    return adapter
