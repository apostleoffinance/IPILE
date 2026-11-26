from datetime import date
from decimal import Decimal

from app.services.import_adapters import ImportRow
from app.services.statement_intelligence import (
    CanonicalField,
    StatementSummary,
    map_statement_headers,
    validate_statement,
)


def _row(day: int, amount: str, kind: str, reference: str) -> ImportRow:
    return ImportRow(
        date=date(2026, 1, day),
        amount=Decimal(amount),
        type=kind,
        description="Test transaction",
        external_id=reference,
    )


def test_header_mapper_recognizes_common_bank_synonyms_and_currency_suffixes() -> None:
    mapping = map_statement_headers([
        "Trans. Time",
        "Value Date",
        "Narration",
        "Debit(₦)",
        "Credit(₦)",
        "Balance After(₦)",
        "Channel",
        "Transaction Reference",
    ])
    assert mapping.index_for(CanonicalField.TRANSACTION_DATE) == 0
    assert mapping.index_for(CanonicalField.VALUE_DATE) == 1
    assert mapping.index_for(CanonicalField.DESCRIPTION) == 2
    assert mapping.index_for(CanonicalField.DEBIT) == 3
    assert mapping.index_for(CanonicalField.CREDIT) == 4
    assert mapping.index_for(CanonicalField.BALANCE) == 5
    assert mapping.index_for(CanonicalField.CHANNEL) == 6
    assert mapping.index_for(CanonicalField.REFERENCE) == 7


def test_header_mapper_does_not_guess_ambiguous_duplicate_columns() -> None:
    mapping = map_statement_headers(["Date", "Date", "Amount", "Narration"])
    assert mapping.index_for(CanonicalField.TRANSACTION_DATE) is None
    assert mapping.index_for(CanonicalField.AMOUNT) == 2


def test_statement_validation_reconciles_counts_totals_and_closing_balance() -> None:
    rows = [
        _row(1, "125.00", "expense", "debit-1"),
        _row(2, "300.00", "income", "credit-1"),
    ]
    report = validate_statement(
        rows,
        StatementSummary(
            opening_balance=Decimal("100.00"),
            closing_balance=Decimal("275.00"),
            total_debits=Decimal("125.00"),
            total_credits=Decimal("300.00"),
            debit_count=1,
            credit_count=1,
        ),
    )
    assert report.status == "verified"
    assert report.debit_total == Decimal("125.00")
    assert report.credit_total == Decimal("300.00")
    assert report.debit_count == 1
    assert report.credit_count == 1


def test_statement_validation_blocks_total_or_count_mismatches() -> None:
    rows = [_row(1, "125.00", "expense", "debit-1")]
    report = validate_statement(
        rows,
        StatementSummary(
            opening_balance=Decimal("100.00"),
            closing_balance=Decimal("300.00"),
            total_debits=Decimal("125.00"),
            total_credits=Decimal("300.00"),
            debit_count=2,
            credit_count=1,
        ),
    )
    assert report.status == "incomplete"
    assert {issue.code for issue in report.issues} >= {
        "debit_count_mismatch",
        "credit_count_mismatch",
        "closing_balance_mismatch",
    }
