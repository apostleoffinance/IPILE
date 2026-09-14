"""Import adapters: all sources become Transaction rows."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from app.money import quantize_money

IMPORT_SOURCES = frozenset({"csv", "statement", "api", "open_banking"})
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


class ImportAdapter(Protocol):
    source: str

    def parse(self, content: str) -> list[ImportRow]: ...


def _parse_date(raw: str) -> date:
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {raw}")


def _parse_amount(raw: str) -> Decimal:
    text = raw.strip().replace(",", "").replace("₦", "")
    try:
        return quantize_money(Decimal(text))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid amount: {raw}") from exc


def _normalize_type(raw: str, amount: Decimal) -> str:
    value = (raw or "").strip().lower()
    if value in TX_TYPES:
        return value
    if amount < 0:
        return "expense"
    if value in {"credit", "cr", "inflow"}:
        return "income"
    if value in {"debit", "dr", "outflow"}:
        return "expense"
    return "expense" if amount >= 0 and value == "" else (value or "expense")


class CsvImportAdapter:
    source = "csv"

    def parse(self, content: str) -> list[ImportRow]:
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise ValueError("CSV requires a header row.")
        fields = {name.lower().strip(): name for name in reader.fieldnames if name}
        required = {"date", "amount", "external_id"}
        missing = required - set(fields)
        if missing:
            raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")
        rows: list[ImportRow] = []
        for index, raw in enumerate(reader, start=2):
            amount = _parse_amount(raw[fields["amount"]])
            tx_type = _normalize_type(raw.get(fields.get("type", ""), ""), abs(amount))
            external_id = (raw[fields["external_id"]] or "").strip()
            if not external_id:
                raise ValueError(f"Row {index}: external_id is required.")
            rows.append(
                ImportRow(
                    date=_parse_date(raw[fields["date"]]),
                    amount=abs(amount),
                    type=tx_type if tx_type in TX_TYPES else "expense",
                    description=(raw.get(fields.get("description", ""), "") or None),
                    external_id=external_id,
                    merchant=(raw.get(fields.get("merchant", ""), "") or None),
                    category_name=(raw.get(fields.get("category", ""), "") or None),
                )
            )
        return rows


class StatementImportAdapter:
    """Bank statement path: date | amount | narrative | reference (pipe or tab)."""

    source = "statement"

    def parse(self, content: str) -> list[ImportRow]:
        rows: list[ImportRow] = []
        for index, line in enumerate(content.splitlines(), start=1):
            text = line.strip()
            if not text or text.lower().startswith("date"):
                continue
            parts = [part.strip() for part in text.replace("\t", "|").split("|")]
            if len(parts) < 4:
                raise ValueError(f"Statement line {index} needs date|amount|narrative|reference.")
            amount = _parse_amount(parts[1])
            tx_type = "income" if amount < 0 else "expense"
            # signed statement: credits negative in some exports — treat negative as income
            if amount < 0:
                amount = abs(amount)
                tx_type = "income"
            else:
                tx_type = "expense"
            rows.append(
                ImportRow(
                    date=_parse_date(parts[0]),
                    amount=amount,
                    type=tx_type,
                    description=parts[2] or None,
                    external_id=parts[3],
                    merchant=parts[2] or None,
                )
            )
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
