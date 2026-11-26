"""Coordinate-aware, bank-agnostic PDF transaction table reconstruction."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pdfplumber

from app.services.statement_extraction.field_mapping import (
    ColumnField,
    map_statement_columns,
    normalize_header,
)
from app.services.statement_extraction.models import (
    ExtractedTransaction,
    TransactionDirection,
)

DATE_TIME_RE = re.compile(
    r"^\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"
    r"(?:\s+(\d{1,2}:\d{2}(?::\d{2})?))?\s*$"
)
AMOUNT_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d{1,4})?\)?")


def _group_words(words: list[dict], *, y_tolerance: float = 2.5) -> list[list[dict]]:
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
        if not lines or abs(word["top"] - lines[-1][0]["top"]) > y_tolerance:
            lines.append([word])
        else:
            lines[-1].append(word)
    return lines


def _line_text(words: list[dict]) -> str:
    return " ".join(word["text"] for word in sorted(words, key=lambda item: item["x0"]))


def _header_cells(words: list[dict]) -> list[tuple[str, float, float]]:
    groups: list[list[dict]] = []
    for word in sorted(words, key=lambda item: item["x0"]):
        if not groups or word["x0"] - groups[-1][-1]["x1"] > 8:
            groups.append([word])
        else:
            groups[-1].append(word)
    return [
        (_line_text(group), min(w["x0"] for w in group), max(w["x1"] for w in group))
        for group in groups
    ]


def _find_header(
    page_words: list[dict],
) -> tuple[float, dict[ColumnField, tuple[float, float]]] | None:
    for line in _group_words(page_words):
        cells = _header_cells(line)
        labels = [cell[0] for cell in cells]
        mapping = map_statement_columns(labels)
        has_date = any(
            field in mapping for field in (
                ColumnField.TRANSACTION_DATE, ColumnField.TRANSACTION_TIME,
                ColumnField.DATETIME,
            )
        )
        has_money = any(field in mapping for field in (
            ColumnField.AMOUNT, ColumnField.DEBIT, ColumnField.CREDIT,
        ))
        if not (has_date and has_money):
            continue
        starts = sorted(
            (mapping[field].column_index, field)
            for field in mapping
        )
        positions: dict[ColumnField, tuple[float, float]] = {}
        for index, field in starts:
            left = cells[index][1]
            right = cells[index + 1][1] if index + 1 < len(cells) else float("inf")
            positions[field] = (left, right)
        return line[0]["top"], positions
    return None


def _column_words(
    words: list[dict], bounds: tuple[float, float], top: float, bottom: float,
) -> list[dict]:
    left, right = bounds
    return [
        word for word in words
        if left - 1 <= word["x0"] < right - 1
        and top <= word["top"] < bottom
    ]


def _column_text(
    words: list[dict], bounds: tuple[float, float], top: float, bottom: float,
) -> str:
    selected = _column_words(words, bounds, top, bottom)
    return " ".join(_line_text(line) for line in _group_words(selected)).strip()


def _parse_date_time(value: str):
    match = DATE_TIME_RE.match(value)
    if not match:
        return None, None
    date_text, time_text = match.groups()
    formats = (
        "%d %b %Y", "%d %B %Y", "%d/%m/%Y", "%m/%d/%Y",
        "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y",
    )
    parsed_date = None
    for fmt in formats:
        try:
            parsed_date = datetime.strptime(date_text, fmt).date()
            break
        except ValueError:
            continue
    if parsed_date is None:
        return None, None
    if not time_text:
        return parsed_date, None
    time_formats = ("%H:%M:%S", "%H:%M")
    for fmt in time_formats:
        try:
            parsed_time = datetime.strptime(time_text, fmt).time()
            return parsed_date, datetime.combine(parsed_date, parsed_time)
        except ValueError:
            continue
    return parsed_date, None


def _parse_cell_amount(value: str) -> Decimal | None:
    text = value.strip()
    if not text or text in {"-", "--", "—", "–"}:
        return None
    cleaned = text.replace("₦", "").replace("$", "").replace("£", "").replace("€", "")
    match = AMOUNT_RE.search(cleaned)
    if not match:
        return None
    number = match.group(0).replace(",", "")
    if number.startswith("(") and number.endswith(")"):
        number = "-" + number[1:-1]
    try:
        return abs(Decimal(number))
    except InvalidOperation:
        return None


def _cell_currency(headers: list[str]) -> str | None:
    joined = " ".join(headers).upper()
    for marker, currency in (("₦", "NGN"), ("NGN", "NGN"), ("USD", "USD"),
                             ("$", "USD"), ("GBP", "GBP"), ("£", "GBP"),
                             ("EUR", "EUR"), ("€", "EUR")):
        if marker in joined:
            return currency
    return None




def _detect_account_section(text: str) -> str | None:
    """Read explicit account-section headings without assuming an institution."""
    for line in text.splitlines():
        candidate = " ".join(line.split()).strip(" :-")
        if not candidate or len(candidate) > 90:
            continue
        normalized = normalize_header(candidate)
        if normalized in {"account statement", "account name account number"}:
            continue
        if "account" not in normalized:
            continue
        period_index = normalized.find(" period ")
        if period_index >= 0:
            original_period = re.search(r"\bperiod\s*:", candidate, re.IGNORECASE)
            if original_period:
                label = candidate[:original_period.start()].strip(" :-")
                if label and normalize_header(label) not in {"account name", "account number"}:
                    return label
        if re.fullmatch(r"[a-z][a-z /&-]{1,55} account", normalized):
            return candidate
    return None


def extract_pdf_layout_transactions(content: bytes) -> tuple[ExtractedTransaction, ...]:
    """Extract transactions using detected column geometry and row anchors.

    Wrapped description lines are assigned to the nearest transaction row by
    vertical midpoints between date anchors. No bank name or fixed x-coordinate
    is used; all column boundaries come from the detected table header.
    """
    transactions: list[ExtractedTransaction] = []
    carried_layout: tuple[float, dict[ColumnField, tuple[float, float]]] | None = None
    carried_currency: str | None = None
    account_section: str | None = None
    with pdfplumber.open(BytesIO(content)) as document:
        for page_number, page in enumerate(document.pages, start=1):
            page_text = page.extract_text() or ""
            detected_section = _detect_account_section(page_text)
            if detected_section:
                account_section = detected_section
            words = page.extract_words(x_tolerance=1, y_tolerance=2) or []
            if not words:
                continue
            header = _find_header(words)
            if header:
                carried_layout = header
                header_y, columns = header
                header_words = [
                    word for word in words if abs(word["top"] - header_y) <= 2.5
                ]
                carried_currency = _cell_currency([word["text"] for word in header_words])
            elif carried_layout is not None:
                # Repeated-page statements often omit the table heading after page one.
                # Carry column geometry, but start row bands at the current page top.
                header_y, columns = 0.0, carried_layout[1]
            else:
                continue
            date_field = next(
                (field for field in (
                    ColumnField.DATETIME, ColumnField.TRANSACTION_TIME,
                    ColumnField.TRANSACTION_DATE,
                ) if field in columns),
                None,
            )
            if date_field is None:
                continue
            date_bounds = columns[date_field]
            date_lines = []
            for line in _group_words(words):
                line_words = [
                    word for word in line
                    if date_bounds[0] - 1 <= word["x0"] < date_bounds[1] - 1
                ]
                text = _line_text(line_words)
                parsed_date, parsed_datetime = _parse_date_time(text)
                if parsed_date:
                    date_lines.append((line[0]["top"], parsed_date, parsed_datetime, text))
            if not date_lines:
                continue
            date_lines.sort(key=lambda item: item[0])
            row_bounds = []
            for index, (anchor_y, parsed_date, parsed_datetime, raw_date) in enumerate(date_lines):
                upper = (
                    max(header_y + 2, (date_lines[index - 1][0] + anchor_y) / 2)
                    if index else max(header_y + 2, 0)
                )
                lower = (
                    (anchor_y + date_lines[index + 1][0]) / 2
                    if index + 1 < len(date_lines) else float(page.height)
                )
                row_bounds.append(
                    (upper, lower, anchor_y, parsed_date, parsed_datetime, raw_date)
                )

            for row_index, (
                upper, lower, anchor_y, parsed_date, parsed_datetime, raw_date,
            ) in enumerate(row_bounds):
                def value(field: ColumnField) -> str:
                    bounds = columns.get(field)
                    return _column_text(words, bounds, upper, lower) if bounds else ""

                debit = _parse_cell_amount(value(ColumnField.DEBIT))
                credit = _parse_cell_amount(value(ColumnField.CREDIT))
                amount = _parse_cell_amount(value(ColumnField.AMOUNT))
                direction = TransactionDirection.UNKNOWN
                if debit is not None and credit is None:
                    amount, direction = debit, TransactionDirection.DEBIT
                elif credit is not None and debit is None:
                    amount, direction = credit, TransactionDirection.CREDIT
                elif amount is not None:
                    type_text = normalize_header(value(ColumnField.TYPE))
                    if "debit" in type_text or "dr" in type_text:
                        direction = TransactionDirection.DEBIT
                    elif "credit" in type_text or "cr" in type_text:
                        direction = TransactionDirection.CREDIT

                if amount is None and direction == TransactionDirection.UNKNOWN:
                    continue
                description = value(ColumnField.DESCRIPTION) or None
                reference = value(ColumnField.REFERENCE) or None
                balance = _parse_cell_amount(value(ColumnField.BALANCE))
                value_date_text = value(ColumnField.VALUE_DATE)
                value_date, _ = _parse_date_time(value_date_text)
                channel = value(ColumnField.CHANNEL) or None
                transactions.append(ExtractedTransaction(
                    transaction_date=parsed_date,
                    transaction_datetime=parsed_datetime,
                    value_date=value_date,
                    amount=amount,
                    direction=direction,
                    description=description,
                    reference=reference,
                    running_balance=balance,
                    channel=channel,
                    currency=carried_currency,
                    source_page=page_number,
                    source_row=row_index + 1,
                    account_section=account_section,
                    original_text=raw_date,
                ))
    return tuple(transactions)
