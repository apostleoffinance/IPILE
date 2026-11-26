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
