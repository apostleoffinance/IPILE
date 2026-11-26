"""Stable, bank-neutral contracts for statement extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from app.services.import_adapters import ImportRow


class CanonicalField(StrEnum):
    TRANSACTION_DATE = "transaction_date"
    VALUE_DATE = "value_date"
    DESCRIPTION = "description"
    AMOUNT = "amount"
    DEBIT = "debit"
    CREDIT = "credit"
    BALANCE = "running_balance"
    REFERENCE = "reference"
    CHANNEL = "channel"
    CURRENCY = "currency"
    TRANSACTION_TIME = "transaction_time"
    DIRECTION = "direction"
    TRANSACTION_TYPE = "transaction_type"
    MERCHANT = "merchant"
    CATEGORY = "category"


@dataclass(frozen=True)
class ColumnMapping:
    """Maps canonical fields to source column indexes and retains original labels."""

    indexes: dict[CanonicalField, int]
    headers: tuple[str, ...]
    confidence: float
    unmapped_headers: tuple[str, ...] = ()

    def index_for(self, field_name: CanonicalField) -> int | None:
        return self.indexes.get(field_name)


@dataclass(frozen=True)
class StatementSummary:
    opening_balance: Decimal | None = None
    closing_balance: Decimal | None = None
    total_debits: Decimal | None = None
    total_credits: Decimal | None = None
    debit_count: int | None = None
    credit_count: int | None = None
    currency: str | None = None
    period_start: date | None = None
    period_end: date | None = None


@dataclass(frozen=True)
class StatementMetadata:
    institution: str | None = None
    account_mask: str | None = None
    currency: str | None = None
    page_count: int = 0
    transaction_pages: tuple[int, ...] = ()


@dataclass(frozen=True)
class ExtractionIssue:
    code: str
    message: str
    severity: str = "warning"
    page: int | None = None
    row: int | None = None
    field: str | None = None


@dataclass(frozen=True)
class ValidationReport:
    status: str
    issues: tuple[ExtractionIssue, ...] = ()
    debit_total: Decimal = Decimal("0")
    credit_total: Decimal = Decimal("0")
    debit_count: int = 0
    credit_count: int = 0
    balance_check_count: int = 0


@dataclass
class ExtractionResult:
    """Normalized extraction result; never implies that rows are ledger-posted."""

    rows: list[ImportRow]
    metadata: StatementMetadata = field(default_factory=StatementMetadata)
    summary: StatementSummary = field(default_factory=StatementSummary)
    extraction_method: str = "unknown"
    issues: list[ExtractionIssue] = field(default_factory=list)
    validation: ValidationReport | None = None
    confidence: float = 0.0
    raw_page_text: dict[int, str] = field(default_factory=dict, repr=False)
    diagnostics: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def is_importable(self) -> bool:
        return (
            bool(self.rows)
            and self.validation is not None
            and self.validation.status == "verified"
            and not any(issue.severity == "error" for issue in self.issues)
        )
