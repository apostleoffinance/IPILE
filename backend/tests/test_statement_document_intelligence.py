from app.services.statement_extraction.document_intelligence import PDFContentKind
from app.services.statement_extraction.field_mapping import ColumnField
from app.services.statement_extraction.pdf_layout import (
    _find_header, _parse_date_time, _parse_cell_amount,
)


def test_pdf_date_and_time_parsing_supports_common_locales() -> None:
    parsed_date, parsed_datetime = _parse_date_time("01 Jan 2026 20:35:26")
    assert parsed_date.isoformat() == "2026-01-01"
    assert parsed_datetime.isoformat() == "2026-01-01T20:35:26"


def test_amount_parser_handles_grouping_and_empty_cells() -> None:
    assert str(_parse_cell_amount("62,455,727.93")) == "62455727.93"
    assert _parse_cell_amount("--") is None
    assert str(_parse_cell_amount("(1,250.50)")) == "1250.50"


def test_pdf_header_detection_uses_header_geometry_not_bank_name() -> None:
    words = [
        {"text": "Trans.", "x0": 10, "x1": 30, "top": 100},
        {"text": "Time", "x0": 31, "x1": 45, "top": 100},
        {"text": "Description", "x0": 70, "x1": 110, "top": 100},
        {"text": "Debit(₦)", "x0": 150, "x1": 185, "top": 100},
        {"text": "Credit(₦)", "x0": 200, "x1": 240, "top": 100},
        {"text": "Transaction", "x0": 260, "x1": 300, "top": 100},
        {"text": "Reference", "x0": 301, "x1": 330, "top": 100},
    ]
    found = _find_header(words)
    assert found is not None
    _, columns = found
    assert ColumnField.TRANSACTION_TIME in columns
    assert ColumnField.DESCRIPTION in columns
    assert ColumnField.DEBIT in columns
    assert ColumnField.CREDIT in columns
    assert ColumnField.REFERENCE in columns
