"""Canonical, bank-agnostic data contracts for statement extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class ExtractionMethod(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF_TEXT = "pdf_text"
    PDF_TABLE = "pdf_table"
    PDF_OCR = "pdf_ocr"
    IMAGE_OCR = "image_ocr"
    PASTED_TEXT = "pasted_text"


class TransactionDirection(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"
    UNKNOWN = "unknown"


class ExtractionStatus(StrEnum):
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StatementMetadata:
    institution_name: str | None = None
    account_name: str | None = None
    account_number_masked: str | None = None
    account_type: str | None = None
    currency: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    source_page_count: int | None = None
    source_filename: str | None = None


@dataclass(frozen=True, slots=True)
class StatementSummary:
    total_debits: Decimal | None = None
    debit_count: int | None = None
    total_credits: Decimal | None = None
    credit_count: int | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedTransaction:
    """Candidate transaction, never a ledger transaction.

    Amount is a positive magnitude. Direction is explicit and may be unknown;
    unknown direction must be reviewed rather than guessed.
    """

    transaction_date: date | None
    amount: Decimal | None
    direction: TransactionDirection | str
    description: str | None = None
    reference: str | None = None
    currency: str | None = None
    transaction_datetime: datetime | None = None
    value_date: date | None = None
    running_balance: Decimal | None = None
    channel: str | None = None
    source_page: int | None = None
    source_row: int | None = None
    account_section: str | None = None
    original_text: str | None = None
    confidence: Decimal | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "warning"
    transaction_index: int | None = None
    source_page: int | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    status: ExtractionStatus
    issues: tuple[ValidationIssue, ...] = ()
    checked_transaction_count: int = 0
    duplicate_reference_count: int = 0
    debit_total: Decimal = Decimal("0")
    credit_total: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    method: ExtractionMethod
    transactions: tuple[ExtractedTransaction, ...]
    metadata: StatementMetadata = field(default_factory=StatementMetadata)
    summary: StatementSummary = field(default_factory=StatementSummary)
    status: ExtractionStatus = ExtractionStatus.NEEDS_REVIEW
    issues: tuple[ValidationIssue, ...] = ()
    provider: str | None = None
    raw_document_metadata: dict[str, Any] = field(default_factory=dict)
