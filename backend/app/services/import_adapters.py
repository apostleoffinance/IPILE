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
    transaction_datetime: datetime | None = None
    value_date: date | None = None
    running_balance: Decimal | None = None
    channel: str | None = None
    source_page: int | None = None
    source_row: int | None = None
    account_section: str | None = None
    confidence: Decimal | None = None
    warnings: tuple[str, ...] = ()


class ImportAdapter(Protocol):
    source: str

    def parse(self, content: str) -> list[ImportRow]: ...


def _parse_date(raw: str) -> date:
    text = raw.strip()
    for fmt in (
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
        "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%d-%b-%Y",
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
    row_index: int | None = None,
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
    )


class CsvImportAdapter:
    source = "csv"

    def parse(self, content: str) -> list[ImportRow]:
        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            raise ValueError("CSV requires a header row.")
        fields = {name.lower().strip(): name for name in reader.fieldnames if name}
        date_col = next(
            (fields[k] for k in ("date", "transaction date", "value date") if k in fields),
            None,
        )
        amount_col = fields.get("amount")
        debit_col = next(
            (fields[k] for k in ("debit", "withdrawal", "money out") if k in fields),
            None,
        )
        credit_col = next(
            (fields[k] for k in ("credit", "deposit", "money in") if k in fields),
            None,
        )
        if not date_col or not (amount_col or debit_col or credit_col):
            raise ValueError("CSV needs a date and amount, debit, or credit column.")
        rows: list[ImportRow] = []
        for index, raw in enumerate(reader, start=2):
            try:
                if debit_col or credit_col:
                    debit_raw = raw.get(debit_col, "") if debit_col else "0"
                    credit_raw = raw.get(credit_col, "") if credit_col else ""
                    if not (debit_raw or "").strip() and not (credit_raw or "").strip():
                        raise ValueError("A row must contain a debit or credit amount.")
                    debit = (
                        _parse_amount(debit_raw)
                        if debit_col and (debit_raw or "").strip()
                        else Decimal("0")
                    )
                    credit = (
                        _parse_amount(credit_raw)
                        if credit_col and (credit_raw or "").strip()
                        else Decimal("0")
                    )
                    if debit and credit:
                        raise ValueError("A row cannot contain both debit and credit amounts.")
                    amount = credit if credit else -abs(debit)
                    inferred_type = "income" if credit else "expense"
                else:
                    amount = _parse_amount(raw.get(amount_col, "") or "")
                    inferred_type = "income" if amount < 0 else "expense"
                type_col = fields.get("type") or fields.get("transaction type", "")
                tx_type = (raw.get(type_col, "") or inferred_type) if type_col else inferred_type
                description_col = (
                    fields.get("description")
                    or fields.get("narration")
                    or fields.get("details")
                )
                merchant_col = fields.get("merchant") or fields.get("payee")
                category_col = fields.get("category")
                row = _make_row(
                    raw_date=raw.get(date_col, ""),
                    amount=amount,
                    tx_type=tx_type,
                    description=raw.get(description_col, "") if description_col else None,
                    external_id=(
                        raw.get(
                            next(
                                (
                                    fields[key]
                                    for key in (
                                        "external_id",
                                        "reference",
                                        "transaction id",
                                        "transaction reference",
                                        "ref",
                                    )
                                    if key in fields
                                ),
                                "",
                            ),
                            "",
                        )
                        if any(
                            key in fields
                            for key in (
                                "external_id",
                                "reference",
                                "transaction id",
                                "transaction reference",
                                "ref",
                            )
                        )
                        else None
                    ),
                    merchant=raw.get(merchant_col, "") if merchant_col else None,
                    category=raw.get(category_col, "") if category_col else None,
                    row_index=index,
                )
                rows.append(row)
            except (ValueError, InvalidOperation) as exc:
                raise ValueError(f"CSV row {index}: {exc}") from exc
        return rows


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
