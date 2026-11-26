"""Extract transaction rows from selectable-text PDF bank statements."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pdfplumber

from app.services.import_adapters import ImportRow, StatementImportAdapter, _make_row, _parse_amount
from app.services.statement_intelligence.pdf_extractor import extract_pdf_statement
from app.services.statement_intelligence.schema import ExtractionResult
from app.services.statement_intelligence.validation import validate_statement
from app.services.statement_ocr import (
    extract_image_ocr_text,
    extract_pdf_ocr_text,
    parse_ocr_statement,
)

DATE_HEADERS = {"date", "transaction date", "txn date", "value date", "posting date"}
AMOUNT_HEADERS = {"amount", "transaction amount"}
DEBIT_HEADERS = {"debit", "withdrawal", "amount debited", "money out", "withdrawals"}
CREDIT_HEADERS = {"credit", "deposit", "amount credited", "money in", "deposits"}
DESCRIPTION_HEADERS = {"description", "narration", "particulars", "details", "transaction details"}
REFERENCE_HEADERS = {"reference", "ref", "transaction id", "transaction reference", "session id"}


def _cell(value: str | None) -> str:
    return (value or "").strip()


def _zero_or_amount(value: str | None) -> Decimal:
    text = _cell(value)
    if text in {"", "-", "—", "–"}:
        return Decimal("0")
    return _parse_amount(text)


def _parse_selectable_pdf(content: bytes) -> list[ImportRow]:
    table_rows: list[ImportRow] = []
    extracted_text: list[str] = []
    row_errors: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            extracted_text.append(page.extract_text() or "")
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                header_index = next(
                    (
                        index for index, row in enumerate(table[:4])
                        if row and any(_cell(cell).lower() in DATE_HEADERS for cell in row)
                    ),
                    None,
                )
                if header_index is None:
                    continue
                headers = [_cell(cell).lower() for cell in table[header_index]]
                date_idx = next(
                    (i for i, value in enumerate(headers) if value in DATE_HEADERS),
                    None,
                )
                amount_idx = next(
                    (i for i, value in enumerate(headers) if value in AMOUNT_HEADERS),
                    None,
                )
                debit_idx = next(
                    (i for i, value in enumerate(headers) if value in DEBIT_HEADERS),
                    None,
                )
                credit_idx = next(
                    (i for i, value in enumerate(headers) if value in CREDIT_HEADERS),
                    None,
                )
                desc_idx = next(
                    (i for i, value in enumerate(headers) if value in DESCRIPTION_HEADERS),
                    None,
                )
                ref_idx = next(
                    (i for i, value in enumerate(headers) if value in REFERENCE_HEADERS),
                    None,
                )
                if date_idx is None or not any(
                    index is not None for index in (amount_idx, debit_idx, credit_idx)
                ):
                    continue
                for row_index, row in enumerate(table[header_index + 1 :], start=header_index + 2):
                    if not row or date_idx >= len(row):
                        continue
                    raw_date = _cell(row[date_idx])
                    if not raw_date:
                        continue
                    try:
                        if debit_idx is not None or credit_idx is not None:
                            debit_cell = (
                                row[debit_idx]
                                if debit_idx is not None and debit_idx < len(row)
                                else None
                            )
                            debit = _zero_or_amount(debit_cell)
                            credit_cell = (
                                row[credit_idx]
                                if credit_idx is not None and credit_idx < len(row)
                                else None
                            )
                            credit = _zero_or_amount(credit_cell)
                            if debit and credit:
                                raise ValueError("Both debit and credit amounts are populated.")
                            amount = credit if credit else -abs(debit)
                            tx_type = "income" if credit else "expense"
                        else:
                            amount_cell = (
                                _cell(row[amount_idx])
                                if amount_idx is not None and amount_idx < len(row)
                                else ""
                            )
                            amount = _parse_amount(amount_cell)
                            tx_type = "income" if amount < 0 else "expense"
                        description = (
                            _cell(row[desc_idx])
                            if desc_idx is not None and desc_idx < len(row)
                            else None
                        )
                        reference = (
                            _cell(row[ref_idx])
                            if ref_idx is not None and ref_idx < len(row)
                            else None
                        )
                        table_rows.append(
                            _make_row(
                                raw_date=raw_date,
                                amount=amount,
                                tx_type=tx_type,
                                description=description,
                                external_id=reference,
                                merchant=description,
                                row_index=row_index,
                            )
                        )
                    except ValueError as exc:
                        row_errors.append(f"row {row_index}: {exc}")
    if row_errors:
        raise ValueError(
            "PDF statement contains rows that could not be imported safely: "
            + "; ".join(row_errors[:10])
        )
    if table_rows:
        return table_rows
    text = "\n".join(extracted_text).strip()
    if not text:
        raise ValueError("No selectable text or transaction tables found in this PDF.")
    return StatementImportAdapter().parse(text)



def parse_pdf_statement(content: bytes) -> list[ImportRow]:
    """Parse embedded PDF text first, then fall back to private OCR."""
    try:
        return _parse_selectable_pdf(content)
    except ValueError as text_error:
        try:
            return parse_ocr_statement(extract_pdf_ocr_text(content))
        except ValueError as ocr_error:
            raise ValueError(str(ocr_error)) from text_error


def parse_statement_image(content: bytes) -> list[ImportRow]:
    return parse_ocr_statement(extract_image_ocr_text(content))


def extract_statement_document(content: bytes, suffix: str) -> ExtractionResult:
    """Extract a document through the universal pipeline, with local OCR fallback."""
    if suffix == "pdf":
        try:
            return extract_pdf_statement(content)
        except ValueError as text_error:
            try:
                rows = parse_ocr_statement(extract_pdf_ocr_text(content))
            except ValueError as ocr_error:
                raise ValueError(str(ocr_error)) from text_error
            return ExtractionResult(
                rows=rows,
                extraction_method="pdf_ocr",
                validation=validate_statement(rows),
                confidence=0.65,
                diagnostics={"status": "verified"},
            )
    if suffix in {"png", "jpg", "jpeg", "webp"}:
        rows = parse_statement_image(content)
        return ExtractionResult(
            rows=rows,
            extraction_method="image_ocr",
            validation=validate_statement(rows),
            confidence=0.6,
            diagnostics={"status": "verified"},
        )
    raise ValueError("Unsupported statement document type.")


def parse_statement_document(content: bytes, suffix: str) -> tuple[list[ImportRow], str]:
    """Compatibility wrapper for callers that only need rows and extraction method."""
    result = extract_statement_document(content, suffix)
    return result.rows, result.extraction_method
