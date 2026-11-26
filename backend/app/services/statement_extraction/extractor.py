"""Bank-agnostic orchestration for supported statement document formats."""

from __future__ import annotations

from collections import defaultdict

from app.services.import_adapters import CsvImportAdapter, ImportRow, StatementImportAdapter
from app.services.pdf_imports import parse_statement_document, parse_statement_image
from app.services.statement_extraction.document_intelligence import (
    PDFContentKind,
    inspect_pdf_document,
)
from app.services.statement_extraction.models import (
    ExtractedTransaction,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
    StatementAccountSection,
    StatementMetadata,
    TransactionDirection,
    ValidationIssue,
)
from app.services.statement_extraction.pdf_layout import extract_pdf_layout_transactions
from app.services.statement_extraction.validation import validate_extraction
from app.services.statement_ocr import extract_pdf_ocr_text, parse_ocr_statement


def _candidate_from_import_row(row: ImportRow, *, source_row: int) -> ExtractedTransaction:
    direction = (
        TransactionDirection.CREDIT if row.type == "income"
        else TransactionDirection.DEBIT if row.type == "expense"
        else TransactionDirection.UNKNOWN
    )
    return ExtractedTransaction(
        transaction_date=row.date,
        amount=row.amount,
        direction=direction,
        description=row.description,
        reference=row.external_id,
        currency=row.currency,
        source_row=source_row,
        original_text=row.description,
    )


def _sections(
    transactions: tuple[ExtractedTransaction, ...],
) -> tuple[StatementAccountSection, ...]:
    grouped: dict[str | None, list[ExtractedTransaction]] = defaultdict(list)
    for transaction in transactions:
        grouped[transaction.account_section].append(transaction)
    return tuple(
        StatementAccountSection(
            label=label,
            transactions=tuple(rows),
            source_page_start=min(
                (row.source_page for row in rows if row.source_page is not None),
                default=None,
            ),
            source_page_end=max(
                (row.source_page for row in rows if row.source_page is not None),
                default=None,
            ),
        )
        for label, rows in grouped.items()
    )


def _result(
    method: ExtractionMethod,
    transactions: tuple[ExtractedTransaction, ...],
    metadata: StatementMetadata,
    *,
    extra_issues: tuple[ValidationIssue, ...] = (),
) -> ExtractionResult:
    report = validate_extraction(transactions)
    issues = (*report.issues, *extra_issues)
    status = report.status
    if any(issue.severity == "error" for issue in extra_issues):
        status = ExtractionStatus.INCOMPLETE
    elif extra_issues and status == ExtractionStatus.VERIFIED:
        status = ExtractionStatus.NEEDS_REVIEW
    return ExtractionResult(
        method=method,
        transactions=transactions,
        sections=_sections(transactions),
        metadata=metadata,
        status=status,
        issues=tuple(issues),
    )


def extract_statement_document(
    content: bytes,
    suffix: str,
    *,
    filename: str | None = None,
) -> ExtractionResult:
    """Extract a document into canonical candidates without writing to the ledger.

    PDF layout extraction is preferred for selectable text. OCR is used for
    image-only PDFs and statement images. Mixed PDFs are explicitly marked
    incomplete until every scanned page can be processed and reconciled.
    """
    extension = suffix.lower().lstrip(".")
    if extension == "pdf":
        profile = inspect_pdf_document(content)
        metadata = StatementMetadata(
            source_page_count=profile.page_count,
            source_filename=filename,
        )
        if profile.content_kind == PDFContentKind.EMPTY:
            raise ValueError("This PDF does not contain readable statement content.")
        if profile.content_kind == PDFContentKind.SCANNED:
            ocr_rows = parse_ocr_statement(extract_pdf_ocr_text(content))
            transactions = tuple(
                _candidate_from_import_row(row, source_row=index)
                for index, row in enumerate(ocr_rows, start=1)
            )
            return _result(ExtractionMethod.PDF_OCR, transactions, metadata)
        transactions = extract_pdf_layout_transactions(content)
        method = ExtractionMethod.PDF_TABLE
        if not transactions:
            # Use the existing generic text/table adapter as a secondary strategy.
            # It shares the canonical output contract and is not bank-specific.
            legacy_rows, legacy_method = parse_statement_document(content, "pdf")
            transactions = tuple(
                _candidate_from_import_row(row, source_row=index)
                for index, row in enumerate(legacy_rows, start=1)
            )
            method = (
                ExtractionMethod.PDF_OCR if legacy_method == "pdf_ocr"
                else ExtractionMethod.PDF_TEXT
            )
        if not transactions:
            return _result(
                ExtractionMethod.PDF_TEXT,
                (),
                metadata,
                extra_issues=(ValidationIssue(
                    code="no_recognized_transaction_table",
                    message=(
                        "Readable PDF text was found, but its transaction table "
                        "could not be identified reliably."
                    ),
                    severity="error",
                ),),
            )
        issues: tuple[ValidationIssue, ...] = ()
        if profile.content_kind == PDFContentKind.MIXED:
            issues = (ValidationIssue(
                code="mixed_text_and_scanned_pages",
                message=(
                    "This PDF contains both selectable-text and scanned pages. "
                    "Some pages still need OCR before the statement can be complete."
                ),
                severity="error",
            ),)
        return _result(method, transactions, metadata, extra_issues=issues)

    if extension in {"png", "jpg", "jpeg", "webp"}:
        rows = parse_statement_image(content)
        transactions = tuple(
            _candidate_from_import_row(row, source_row=index)
            for index, row in enumerate(rows, start=1)
        )
        return _result(
            ExtractionMethod.IMAGE_OCR,
            transactions,
            StatementMetadata(source_filename=filename),
        )

    if extension in {"csv", "txt"}:
        text = content.decode("utf-8-sig")
        rows = (
            CsvImportAdapter().parse(text)
            if extension == "csv"
            else StatementImportAdapter().parse(text)
        )
        transactions = tuple(
            _candidate_from_import_row(row, source_row=index)
            for index, row in enumerate(rows, start=1)
        )
        method = ExtractionMethod.CSV if extension == "csv" else ExtractionMethod.PASTED_TEXT
        return _result(
            method,
            transactions,
            StatementMetadata(source_filename=filename),
        )

    raise ValueError("Unsupported statement document type.")
