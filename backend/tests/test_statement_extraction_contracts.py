from datetime import date
from decimal import Decimal

from app.services.statement_extraction import (
    ColumnField, ExtractionStatus, ExtractedTransaction, StatementSummary, TransactionDirection,
    map_statement_columns, normalize_header, validate_extraction,
)


def test_header_normalization_ignores_currency_and_punctuation() -> None:
    assert normalize_header("Debit(₦)") == "debit"
    assert normalize_header("Balance After (NGN)") == "balance after"
    assert normalize_header("Trans. Time") == "trans time"


def test_column_mapping_is_bank_agnostic_and_order_independent() -> None:
    headers = [
        "Trans. Time", "Value Date", "Description", "Debit(₦)", "Credit(₦)",
        "Balance After(₦)", "Channel", "Transaction Reference",
    ]
    mapped = map_statement_columns(headers)
    assert mapped[ColumnField.VALUE_DATE].column_index == 1
    assert mapped[ColumnField.DESCRIPTION].column_index == 2
    assert mapped[ColumnField.DEBIT].column_index == 3
    assert mapped[ColumnField.CREDIT].column_index == 4
    assert mapped[ColumnField.BALANCE].column_index == 5
    assert mapped[ColumnField.CHANNEL].column_index == 6
    assert mapped[ColumnField.REFERENCE].column_index == 7


def test_validation_detects_unknown_direction_and_duplicate_reference() -> None:
    rows = [
        ExtractedTransaction(
            transaction_date=date(2026, 1, 1), amount=Decimal("100.00"),
            direction=TransactionDirection.DEBIT, reference="same", confidence=Decimal("0.99"),
        ),
        ExtractedTransaction(
            transaction_date=date(2026, 1, 2), amount=Decimal("50.00"),
            direction=TransactionDirection.UNKNOWN, reference="same", confidence=Decimal("0.70"),
        ),
    ]
    report = validate_extraction(rows)
    assert report.status == ExtractionStatus.INCOMPLETE
    assert report.duplicate_reference_count == 1
    assert {issue.code for issue in report.issues} >= {
        "duplicate_references", "unknown_direction", "low_confidence",
    }


def test_statement_summary_reconciliation_flags_mismatches() -> None:
    rows = [
        ExtractedTransaction(
            transaction_date=date(2026, 1, 1), amount=Decimal("75.00"),
            direction="debit", confidence=Decimal("0.99"),
        ),
        ExtractedTransaction(
            transaction_date=date(2026, 1, 2), amount=Decimal("100.00"),
            direction=TransactionDirection.CREDIT, confidence=Decimal("0.99"),
        ),
    ]
    report = validate_extraction(
        rows,
        StatementSummary(
            total_debits=Decimal("80.00"), debit_count=1,
            total_credits=Decimal("100.00"), credit_count=1,
        ),
        opening_balance=Decimal("10.00"), closing_balance=Decimal("30.00"),
    )
    assert report.status == ExtractionStatus.NEEDS_REVIEW
    assert report.debit_total == Decimal("75.00")
    assert "debit_total_mismatch" in {issue.code for issue in report.issues}
    assert "balance_reconciliation_mismatch" in {issue.code for issue in report.issues}


def test_empty_extraction_fails_closed() -> None:
    report = validate_extraction([])
    assert report.status == ExtractionStatus.FAILED
    assert report.checked_transaction_count == 0
