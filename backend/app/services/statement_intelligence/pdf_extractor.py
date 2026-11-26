"""Bank-neutral PDF statement extraction using semantic headers and page geometry."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

import pdfplumber

from app.services.import_adapters import ImportRow, _make_row, _parse_amount
from app.services.statement_intelligence.field_mapping import (
    _NORMALIZED_ALIASES,
    normalize_header,
)
from app.services.statement_intelligence.schema import (
    CanonicalField,
    ColumnMapping,
    ExtractionIssue,
    ExtractionResult,
    StatementMetadata,
    StatementSummary,
)
from app.services.statement_intelligence.validation import validate_statement

DATE_TIME_FORMATS = (
    "%d %b %Y %H:%M:%S",
    "%d %B %Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
)
DATE_FORMATS = (
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
)
DATE_PREFIX = re.compile(
    r"^\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\s+\d{2}:\d{2}:\d{2}|"
    r"\d{4}-\d{1,2}-\d{1,2}(?:\s+\d{2}:\d{2}:\d{2})?|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{2}:\d{2}:\d{2})?)"
)
AMOUNT_TOKEN = re.compile(
    r"^\s*(?:₦|NGN|\$|USD|€|EUR|£|GBP)?\s*"
    r"([\d,]+(?:\.\d{1,4})?|\([\d,]+(?:\.\d{1,4})?\))\s*"
    r"(CR|DR)?\s*$",
    re.I,
)
SUMMARY_PATTERNS = {
    "opening_balance": re.compile(r"opening\s+balance\s*[:\n ]*[^\d\n]*([\d,]+\.\d{2})", re.I),
    "closing_balance": re.compile(r"closing\s+balance\s*[:\n ]*[^\d\n]*([\d,]+\.\d{2})", re.I),
    "total_debits": re.compile(r"total\s+debits?\s*[:\n ]*[^\d\n]*([\d,]+\.\d{2})", re.I),
    "total_credits": re.compile(r"total\s+credits?\s*[:\n ]*[^\d\n]*([\d,]+\.\d{2})", re.I),
    "debit_count": re.compile(r"debit\s+count\s*[:\n ]*(\d+)", re.I),
    "credit_count": re.compile(r"credit\s+count\s*[:\n ]*(\d+)", re.I),
}


def _cluster_words(
    words: list[dict[str, Any]], tolerance: float = 2.0
) -> dict[float, list[dict[str, Any]]]:
    """Group words into visual text lines without depending on a bank's font size."""
    lines: dict[float, list[dict[str, Any]]] = {}
    for word in sorted(words, key=lambda item: (float(item["top"]), float(item["x0"]))):
        top = float(word["top"])
        key = next((candidate for candidate in lines if abs(candidate - top) <= tolerance), None)
        lines[key if key is not None else top].append(word)
    return lines


def _header_candidates(words: list[dict[str, Any]]) -> dict[CanonicalField, list[float]]:
    """Find canonical header phrases, preferring the longest phrase at each position."""
    candidates: dict[CanonicalField, list[float]] = defaultdict(list)
    ordered = sorted(words, key=lambda item: float(item["x0"]))
    index = 0
    while index < len(ordered):
        matched_end = index + 1
        matched_field = None
        for end in range(min(len(ordered), index + 4), index, -1):
            phrase = " ".join(str(word["text"]) for word in ordered[index:end])
            normalized = normalize_header(phrase)
            field_name = next(
                (
                    candidate
                    for candidate, aliases in _NORMALIZED_ALIASES.items()
                    if normalized in aliases
                ),
                None,
            )
            if field_name is not None:
                matched_end = end
                matched_field = field_name
                break
        if matched_field is None:
            index += 1
            continue
        candidates[matched_field].append(float(ordered[index]["x0"]))
        index = matched_end
    return candidates

def detect_column_mapping(page: Any) -> tuple[ColumnMapping, dict[CanonicalField, float], float]:
    """Detect a transaction table header and retain its x-coordinate boundaries."""
    lines = _cluster_words(page.extract_words(x_tolerance=2, y_tolerance=3))
    for top, words in sorted(lines.items()):
        candidates = _header_candidates(words)
        has_date = bool(candidates.get(CanonicalField.TRANSACTION_DATE))
        has_money = bool(
            candidates.get(CanonicalField.AMOUNT)
            or candidates.get(CanonicalField.DEBIT)
            or candidates.get(CanonicalField.CREDIT)
        )
        if not has_date or not has_money:
            continue
        # Statement summaries often repeat "Debit" and "Credit"; the transaction
        # table header is the right-most occurrence on the candidate header line.
        positions = {
            field_name: max(values)
            for field_name, values in candidates.items()
            if values
        }
        headers = tuple(
            field_name.value for field_name in positions
        )
        mapping = ColumnMapping(
            indexes={field_name: index for index, field_name in enumerate(positions)},
            headers=headers,
            confidence=min(1.0, len(positions) / 6),
        )
        return mapping, positions, top
    raise ValueError("We couldn't identify a transaction table in this PDF.")


def _parse_datetime(value: str) -> datetime | None:
    text = " ".join(value.split())
    for fmt in DATE_TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.combine(datetime.strptime(text, fmt).date(), datetime.min.time())
        except ValueError:
            pass
    return None


def _amount_or_zero(value: str) -> Decimal:
    text = " ".join(value.split()).strip()
    if not text or text in {"-", "--", "—", "–"}:
        return Decimal("0")
    match = AMOUNT_TOKEN.match(text)
    if not match:
        raise ValueError(f"Unrecognized statement amount: {text}")
    amount = _parse_amount(match.group(1))
    marker = (match.group(2) or "").upper()
    if marker == "DR":
        return -abs(amount)
    if marker == "CR":
        return abs(amount)
    return amount


def _cell_values(
    words: list[dict[str, Any]],
    positions: dict[CanonicalField, float],
) -> dict[CanonicalField, str]:
    ordered_fields = sorted(positions, key=lambda field_name: positions[field_name])
    values = {field_name: [] for field_name in ordered_fields}
    for word in sorted(words, key=lambda item: float(item["x0"])):
        x = float(word["x0"])
        selected = None
        for index, field_name in enumerate(ordered_fields):
            start = positions[field_name] - 1.0
            end = (
                positions[ordered_fields[index + 1]] - 1.0
                if index + 1 < len(ordered_fields)
                else float("inf")
            )
            if start <= x < end:
                selected = field_name
                break
        if selected is not None:
            values[selected].append(str(word["text"]))
    return {field_name: " ".join(parts).strip() for field_name, parts in values.items()}


def _parse_summary(text: str) -> StatementSummary:
    values: dict[str, Any] = {}
    for key, pattern in SUMMARY_PATTERNS.items():
        match = pattern.search(text)
        if match:
            values[key] = (
                int(match.group(1))
                if key.endswith("_count")
                else _parse_amount(match.group(1))
            )
    currency = "NGN" if "₦" in text or re.search(r"\bNGN\b", text, re.I) else None
    period = re.search(
        r"(?:period|statement period)\s*:?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})"
        r"\s*(?:-|to|through)\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        text,
        re.I,
    )
    start_date = end_date = None
    if period:
        start_date = _parse_datetime(period.group(1)).date()
        end_date = _parse_datetime(period.group(2)).date()
    return StatementSummary(
        opening_balance=values.get("opening_balance"),
        closing_balance=values.get("closing_balance"),
        total_debits=values.get("total_debits"),
        total_credits=values.get("total_credits"),
        debit_count=values.get("debit_count"),
        credit_count=values.get("credit_count"),
        currency=currency,
        period_start=start_date,
        period_end=end_date,
    )


def extract_pdf_statement(content: bytes) -> ExtractionResult:
    """Extract a bank-neutral statement result from a selectable-text PDF."""
    rows: list[ImportRow] = []
    issues: list[ExtractionIssue] = []
    raw_page_text: dict[int, str] = {}
    positions: dict[CanonicalField, float] | None = None
    header_top: float | None = None
    mapping: ColumnMapping | None = None
    page_count = 0

    try:
        pdf = pdfplumber.open(BytesIO(content))
    except Exception as exc:
        raise ValueError("This PDF could not be opened. Please upload a valid PDF.") from exc

    with pdf:
        page_count = len(pdf.pages)
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            raw_page_text[page_number] = page_text
            if positions is None:
                try:
                    mapping, positions, header_top = detect_column_mapping(page)
                except ValueError:
                    continue

            lines = _cluster_words(page.extract_words(x_tolerance=2, y_tolerance=3))
            date_rows: list[tuple[float, dict[CanonicalField, str], datetime]] = []
            for top, words in sorted(lines.items()):
                cells = _cell_values(words, positions)
                date_value = cells.get(CanonicalField.TRANSACTION_DATE, "")
                parsed_datetime = _parse_datetime(date_value)
                if parsed_datetime is not None:
                    date_rows.append((top, cells, parsed_datetime))

            for row_index, (top, cells, transaction_datetime) in enumerate(date_rows, start=1):
                debit_text = cells.get(CanonicalField.DEBIT, "")
                credit_text = cells.get(CanonicalField.CREDIT, "")
                amount_text = cells.get(CanonicalField.AMOUNT, "")
                direction_text = cells.get(CanonicalField.DIRECTION, "").strip().lower()
                try:
                    if CanonicalField.DEBIT in positions or CanonicalField.CREDIT in positions:
                        debit = abs(_amount_or_zero(debit_text))
                        credit = abs(_amount_or_zero(credit_text))
                        if debit and credit:
                            raise ValueError("Both debit and credit columns contain an amount.")
                        if not debit and not credit:
                            raise ValueError("Neither debit nor credit amount was found.")
                        amount = credit if credit else -debit
                        tx_type = "income" if credit else "expense"
                    else:
                        amount = _amount_or_zero(amount_text)
                        if amount == 0:
                            raise ValueError("Transaction amount is missing.")
                        marker = amount_text.upper()
                        is_debit = (
                            amount < 0
                            or "DR" in marker
                            or direction_text in {"debit", "dr", "out", "outgoing"}
                        )
                        is_credit = (
                            "CR" in marker
                            or direction_text in {"credit", "cr", "in", "incoming"}
                        )
                        if is_debit:
                            amount, tx_type = -abs(amount), "expense"
                        elif is_credit:
                            amount, tx_type = abs(amount), "income"
                        else:
                            raise ValueError(
                                "Transaction direction is unclear; this amount was not guessed."
                            )

                    description_lines: list[tuple[float, str]] = []
                    for line_top, line_words in lines.items():
                        if page_number == 1 and header_top is not None and line_top <= header_top:
                            continue
                        nearest_row = min(date_rows, key=lambda item: abs(item[0] - line_top))
                        if nearest_row[0] != top:
                            continue
                        line_cells = _cell_values(line_words, positions)
                        description = line_cells.get(CanonicalField.DESCRIPTION, "")
                        if description:
                            description_lines.append((line_top, description))
                    description = " ".join(
                        text for _, text in sorted(description_lines)
                    ).strip()
                    reference = cells.get(CanonicalField.REFERENCE, "").strip()
                    balance_text = cells.get(CanonicalField.BALANCE, "")
                    running_balance = (
                        abs(_amount_or_zero(balance_text))
                        if balance_text and balance_text not in {"-", "--", "—"}
                        else None
                    )
                    currency = (
                        cells.get(CanonicalField.CURRENCY)
                        or ("NGN" if "₦" in page_text else None)
                    )
                    value_date_text = cells.get(CanonicalField.VALUE_DATE, "")
                    value_date_datetime = (
                        _parse_datetime(value_date_text) if value_date_text else None
                    )
                    rows.append(
                        _make_row(
                            raw_date=transaction_datetime.date().isoformat(),
                            amount=amount,
                            tx_type=tx_type,
                            description=description or "Statement transaction",
                            external_id=reference or None,
                            merchant=description or None,
                            row_index=(page_number * 100000) + row_index,
                        )
                    )
                    rows[-1].running_balance = running_balance
                    rows[-1].transaction_datetime = transaction_datetime
                    rows[-1].value_date = (
                        value_date_datetime.date() if value_date_datetime else None
                    )
                    rows[-1].source_page = page_number
                    rows[-1].currency = currency
                    rows[-1].extraction_confidence = mapping.confidence if mapping else None
                except ValueError as exc:
                    issues.append(
                        ExtractionIssue(
                            code="unparsed_transaction_row",
                            message=str(exc),
                            severity="error",
                            page=page_number,
                            row=row_index,
                        )
                    )

    if not rows:
        raise ValueError(
            "We couldn't identify transaction rows in this statement. "
            "Try a clearer PDF or upload the bank's CSV export."
        )

    first_page_text = raw_page_text.get(1, "")
    summary = _parse_summary(first_page_text)
    validation = validate_statement(rows, summary)
    combined_issues = [*issues, *validation.issues]
    status = validation.status
    if issues:
        status = "incomplete"
    metadata = StatementMetadata(
        institution=None,
        currency=summary.currency,
        page_count=page_count,
        transaction_pages=tuple(sorted({row.source_page for row in rows if row.source_page})),
    )
    return ExtractionResult(
        rows=rows,
        metadata=metadata,
        summary=summary,
        extraction_method="pdf_text_layout",
        issues=combined_issues,
        validation=validation,
        confidence=(mapping.confidence if mapping else 0.0),
        raw_page_text=raw_page_text,
        diagnostics={
            "status": status,
            "header_mapping": {
                field_name.value: index
                for field_name, index in (mapping.indexes.items() if mapping else [])
            },
        },
    )
