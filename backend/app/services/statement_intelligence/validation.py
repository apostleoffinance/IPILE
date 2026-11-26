"""Financial integrity checks for normalized statement transactions."""

from __future__ import annotations

from decimal import Decimal

from app.services.import_adapters import ImportRow
from app.services.statement_intelligence.schema import (
    ExtractionIssue,
    StatementSummary,
    ValidationReport,
)


def validate_statement(
    rows: list[ImportRow],
    summary: StatementSummary | None = None,
    *,
    opening_balance: Decimal | None = None,
    balance_tolerance: Decimal = Decimal("0.02"),
) -> ValidationReport:
    """Validate normalized rows against available statement totals and balances.

    A mismatch never silently drops rows. The caller receives a review-required result.
    """
    summary = summary or StatementSummary(opening_balance=opening_balance)
    issues: list[ExtractionIssue] = []
    debit_rows = [row for row in rows if row.type in {"expense", "debt_payment", "giving"}]
    credit_rows = [row for row in rows if row.type in {"income", "refund"}]
    debit_total = sum((row.amount for row in debit_rows), Decimal("0"))
    credit_total = sum((row.amount for row in credit_rows), Decimal("0"))

    if not rows:
        issues.append(
            ExtractionIssue(
                "no_transactions",
                "No transaction rows were extracted.",
                "error",
            )
        )

    if summary.debit_count is not None and len(debit_rows) != summary.debit_count:
        issues.append(ExtractionIssue(
            "debit_count_mismatch",
            f"Statement reports {summary.debit_count} debits; {len(debit_rows)} were extracted.",
            "error",
        ))
    if summary.credit_count is not None and len(credit_rows) != summary.credit_count:
        issues.append(ExtractionIssue(
            "credit_count_mismatch",
            f"Statement reports {summary.credit_count} credits; {len(credit_rows)} were extracted.",
            "error",
        ))
    if (
        summary.total_debits is not None
        and abs(debit_total - summary.total_debits) > balance_tolerance
    ):
        issues.append(ExtractionIssue(
            "debit_total_mismatch",
            (
                f"Statement debit total {summary.total_debits} does not match "
                f"extracted total {debit_total}."
            ),
            "error",
        ))
    if (
        summary.total_credits is not None
        and abs(credit_total - summary.total_credits) > balance_tolerance
    ):
        issues.append(ExtractionIssue(
            "credit_total_mismatch",
            (
                f"Statement credit total {summary.total_credits} does not match "
                f"extracted total {credit_total}."
            ),
            "error",
        ))

    balance_checks = 0
    previous_balance = summary.opening_balance
    for row in rows:
        if row.running_balance is None or previous_balance is None:
            continue
        delta = row.amount if row.type in {"income", "refund"} else -row.amount
        expected_balance = previous_balance + delta
        balance_checks += 1
        if abs(expected_balance - row.running_balance) > balance_tolerance:
            issues.append(ExtractionIssue(
                "running_balance_mismatch",
                (
                    f"Running balance on {row.date.isoformat()} does not match "
                    "the preceding balance and transaction amount."
                ),
                "error",
                page=row.source_page,
                field="running_balance",
            ))
        previous_balance = row.running_balance

    if summary.opening_balance is not None and summary.closing_balance is not None:
        expected = summary.opening_balance + credit_total - debit_total
        if abs(expected - summary.closing_balance) > balance_tolerance:
            issues.append(ExtractionIssue(
                "closing_balance_mismatch",
                f"Opening balance plus extracted credits less debits ({expected}) "
                f"does not match closing balance {summary.closing_balance}.",
                "error",
            ))

    if issues:
        status = (
            "incomplete"
            if any(issue.severity == "error" for issue in issues)
            else "needs_review"
        )
    else:
        status = "verified"
    return ValidationReport(
        status=status,
        issues=tuple(issues),
        debit_total=debit_total,
        credit_total=credit_total,
        debit_count=len(debit_rows),
        credit_count=len(credit_rows),
        balance_check_count=balance_checks,
    )
