"""Conservative transaction and statement-level validation."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.services.statement_extraction.models import (
    ExtractedTransaction,
    ExtractionStatus,
    StatementSummary,
    ValidationIssue,
    ValidationReport,
)

TOLERANCE = Decimal("0.01")


def validate_extraction(
    transactions: tuple[ExtractedTransaction, ...] | list[ExtractedTransaction],
    summary: StatementSummary | None = None,
    *,
    opening_balance: Decimal | None = None,
    closing_balance: Decimal | None = None,
    confidence_threshold: Decimal = Decimal("0.90"),
) -> ValidationReport:
    """Validate completeness, direction, duplicates, totals and balance flow.

    Missing or ambiguous values are errors for completeness. Low confidence
    and reconciliation mismatches require review. This function never guesses.
    """
    issues: list[ValidationIssue] = []
    refs = [
        row.reference.strip() for row in transactions
        if row.reference and row.reference.strip()
    ]
    duplicate_refs = sum(count - 1 for count in Counter(refs).values() if count > 1)
    if duplicate_refs:
        issues.append(ValidationIssue(
            code="duplicate_references",
            message=f"{duplicate_refs} duplicate transaction reference(s) were found.",
            severity="warning",
        ))

    debit_total = Decimal("0")
    credit_total = Decimal("0")
    for index, row in enumerate(transactions):
        if row.transaction_date is None:
            issues.append(ValidationIssue(
                code="missing_transaction_date",
                message="Transaction date could not be identified.",
                severity="error", transaction_index=index, source_page=row.source_page,
            ))
        if row.amount is None or row.amount <= 0:
            issues.append(ValidationIssue(
                code="invalid_amount",
                message="A positive transaction amount could not be identified.",
                severity="error", transaction_index=index, source_page=row.source_page,
            ))
        if row.direction not in {"debit", "credit"}:
            issues.append(ValidationIssue(
                code="unknown_direction",
                message="Money-in or money-out direction needs review.",
                severity="error", transaction_index=index, source_page=row.source_page,
            ))
        elif row.amount is not None and row.amount > 0:
            if row.direction == "debit":
                debit_total += row.amount
            else:
                credit_total += row.amount
        if row.confidence is not None and row.confidence < confidence_threshold:
            issues.append(ValidationIssue(
                code="low_confidence",
                message="Some extracted fields are uncertain and need manual review.",
                severity="warning", transaction_index=index, source_page=row.source_page,
            ))

    if summary:
        if summary.debit_count is not None and summary.debit_count != sum(
            1 for row in transactions if row.direction == "debit"
        ):
            issues.append(ValidationIssue(
                code="debit_count_mismatch",
                message="Extracted debit count does not match the statement summary.",
                severity="warning",
            ))
        if summary.credit_count is not None and summary.credit_count != sum(
            1 for row in transactions if row.direction == "credit"
        ):
            issues.append(ValidationIssue(
                code="credit_count_mismatch",
                message="Extracted credit count does not match the statement summary.",
                severity="warning",
            ))
        if summary.total_debits is not None and abs(debit_total - summary.total_debits) > TOLERANCE:
            issues.append(ValidationIssue(
                code="debit_total_mismatch",
                message="Extracted debit total does not match the statement summary.",
                severity="warning",
            ))
        if (
            summary.total_credits is not None
            and abs(credit_total - summary.total_credits) > TOLERANCE
        ):
            issues.append(ValidationIssue(
                code="credit_total_mismatch",
                message="Extracted credit total does not match the statement summary.",
                severity="warning",
            ))

    if opening_balance is not None and closing_balance is not None:
        expected = opening_balance + credit_total - debit_total
        if abs(expected - closing_balance) > TOLERANCE:
            issues.append(ValidationIssue(
                code="balance_reconciliation_mismatch",
                message=(
                    "Opening balance plus credits less debits does not match "
                    "the closing balance."
                ),
                severity="warning",
            ))

    has_errors = any(issue.severity == "error" for issue in issues)
    status = (
        ExtractionStatus.FAILED if not transactions
        else ExtractionStatus.INCOMPLETE if has_errors
        else ExtractionStatus.NEEDS_REVIEW if issues
        else ExtractionStatus.VERIFIED
    )
    return ValidationReport(
        status=status, issues=tuple(issues),
        checked_transaction_count=len(transactions),
        duplicate_reference_count=duplicate_refs,
        debit_total=debit_total, credit_total=credit_total,
    )
