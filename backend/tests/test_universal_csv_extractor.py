from datetime import datetime
from decimal import Decimal

import pytest

from app.services.statement_intelligence.csv_extractor import parse_universal_csv


def test_universal_csv_parses_opay_style_headings_and_rows() -> None:
    content = (
        "Trans. Time,Value Date,Description,Debit(₦),Credit(₦),"
        "Balance After(₦),Channel,Transaction Reference\n"
        "01 Jan 2026 20:35:26,01 Jan 2026,Transfer to Merchant,5000.00,--,"
        "1492.35,Mobile,260101020100888055507351\n"
        "02 Jan 2026 16:57:50,02 Jan 2026,Transfer from Employer,--,"
        "103000.00,103992.35,Mobile,000004260102152118005167080866\n"
    )
    rows = parse_universal_csv(content)
    assert len(rows) == 2
    assert rows[0].date.isoformat() == "2026-01-01"
    assert rows[0].transaction_datetime == datetime(2026, 1, 1, 20, 35, 26)
    assert rows[0].value_date.isoformat() == "2026-01-01"
    assert rows[0].amount == Decimal("5000.00")
    assert rows[0].type == "expense"
    assert rows[0].running_balance == Decimal("1492.35")
    assert rows[0].currency == "NGN"
    assert rows[0].external_id == "260101020100888055507351"
    assert rows[1].amount == Decimal("103000.00")
    assert rows[1].type == "income"


def test_universal_csv_rejects_rows_with_both_debit_and_credit() -> None:
    content = (
        "Trans. Time,Description,Debit(₦),Credit(₦),Transaction Reference\n"
        "01 Jan 2026 20:35:26,Ambiguous,100.00,200.00,ref-1\n"
    )
    with pytest.raises(ValueError, match="Both debit and credit"):
        parse_universal_csv(content)


def test_universal_csv_rejects_unsigned_amount_without_direction() -> None:
    content = (
        "Transaction Date,Description,Amount,Reference\n"
        "2026-01-01,Ambiguous,100.00,ref-1\n"
    )
    with pytest.raises(ValueError, match="direction is unclear"):
        parse_universal_csv(content)


def test_universal_csv_rejects_ambiguous_duplicate_date_headers() -> None:
    content = (
        "Date,Transaction Date,Amount,Direction\n"
        "2026-01-01,2026-01-01,100.00,expense\n"
    )
    with pytest.raises(ValueError, match="unambiguous transaction date"):
        parse_universal_csv(content)


@pytest.mark.parametrize(
    ("content", "expected_type", "expected_currency", "expected_reference"),
    [
        (
            "Transaction Date,Value Date,Narration,Debit,Credit,Available Balance,"
            "Reference Number,Currency\n"
            "2026-02-01,2026-02-01,Groceries,12500.00,,87500.00,ACC-001,NGN\n",
            "expense", "NGN", "ACC-001",
        ),
        (
            "Date,Description,Withdrawal,Deposit,Balance,Transaction ID\n"
            "02/02/2026,POS purchase,2500.00,,85000.00,GT-002\n",
            "expense", None, "GT-002",
        ),
        (
            "Posting Date,Transaction Details,Amount,Direction,Running Balance,Reference\n"
            "2026-02-03,Client payment,850.00,credit,85850.00,UBA-003\n",
            "income", None, "UBA-003",
        ),
        (
            "Date,Particulars,Amount,Type,Reference,Currency\n"
            "04 Feb 2026,Monthly subscription,1500.00,expense,KD-004,NGN\n",
            "expense", "NGN", "KD-004",
        ),
        (
            "Transaction Date,Details,Debit Amount,Credit Amount,Ledger Balance,Session ID\n"
            "2026-02-05,Salary,,125000.00,210850.00,FB-005\n",
            "income", None, "FB-005",
        ),
    ],
)
def test_universal_csv_supports_different_bank_header_conventions(
    content: str,
    expected_type: str,
    expected_currency: str | None,
    expected_reference: str,
) -> None:
    rows = parse_universal_csv(content)
    assert len(rows) == 1
    assert rows[0].type == expected_type
    assert rows[0].currency == expected_currency
    assert rows[0].external_id == expected_reference



def test_universal_csv_combines_separate_transaction_date_and_time_columns() -> None:
    content = (
        "Transaction Date,Time,Description,Debit,Credit,Reference\n"
        "2026-02-10,09:45:30,Transport,250.00,,TIME-001\n"
    )
    rows = parse_universal_csv(content)
    assert rows[0].transaction_datetime == datetime(2026, 2, 10, 9, 45, 30)
    assert rows[0].type == "expense"
