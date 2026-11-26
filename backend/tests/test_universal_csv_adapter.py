from datetime import datetime
from decimal import Decimal

from app.services.import_adapters import CsvImportAdapter


def test_csv_adapter_routes_opay_column_names_to_universal_engine() -> None:
    content = (
        "Trans. Time,Value Date,Description,Debit(₦),Credit(₦),"
        "Balance After(₦),Channel,Transaction Reference\n"
        "01 Jan 2026 20:35:26,01 Jan 2026,Transfer to Merchant,5000.00,--,"
        "1492.35,Mobile,ref-1\n"
    )
    rows = CsvImportAdapter().parse(content)
    assert len(rows) == 1
    assert rows[0].transaction_datetime == datetime(2026, 1, 1, 20, 35, 26)
    assert rows[0].amount == Decimal("5000.00")
    assert rows[0].type == "expense"
    assert rows[0].currency == "NGN"
