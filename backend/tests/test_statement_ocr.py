from datetime import date
from decimal import Decimal

import pytest

from app.services.statement_ocr import parse_ocr_statement


def test_ocr_parser_extracts_debit_and_credit_columns() -> None:
    text = """
    DATE DESCRIPTION DEBIT CREDIT BALANCE
    26/11/2026 POS PURCHASE 2,500.00 0.00 15,000.00
    27/11/2026 SALARY PAYMENT 0.00 85,000.00 100,000.00
    """
    rows = parse_ocr_statement(text)
    assert len(rows) == 2
    assert rows[0].date == date(2026, 11, 26)
    assert rows[0].amount == Decimal("2500.00")
    assert rows[0].type == "expense"
    assert rows[1].amount == Decimal("85000.00")
    assert rows[1].type == "income"


def test_ocr_parser_requires_clear_transaction_direction() -> None:
    with pytest.raises(ValueError, match="could not confidently identify"):
        parse_ocr_statement("26/11/2026 TRANSFER 5,000.00 20,000.00")


def test_ocr_parser_ignores_non_transaction_lines() -> None:
    rows = parse_ocr_statement(
        "IPILE BANK STATEMENT\n"
        "Opening balance 50,000.00\n"
        "26 Nov 2026 ATM WITHDRAWAL 1,000.00 DR 49,000.00"
    )
    assert len(rows) == 1
    assert rows[0].date == date(2026, 11, 26)
    assert rows[0].type == "expense"
    assert rows[0].amount == Decimal("1000.00")
