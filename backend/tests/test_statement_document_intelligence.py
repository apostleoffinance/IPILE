from decimal import Decimal

from app.services.statement_extraction.field_mapping import ColumnField
from app.services.statement_extraction.pdf_layout import (
    _find_header,
    _parse_cell_amount,
    _parse_date_time,
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



def test_pdf_layout_reconstructs_wrapped_descriptions_and_repeated_pages(monkeypatch) -> None:
    from app.services.statement_extraction import pdf_layout
    from app.services.statement_extraction.models import TransactionDirection

    def word(text, x0, x1, top):
        return {"text": text, "x0": x0, "x1": x1, "top": top}

    header = [
        word("Trans.", 10, 28, 10), word("Time", 29, 43, 10),
        word("Description", 70, 110, 10), word("Debit(₦)", 150, 185, 10),
        word("Credit(₦)", 200, 240, 10),
        word("Transaction", 260, 300, 10), word("Reference", 301, 330, 10),
    ]
    first_page_words = header + [
        word("Transfer", 70, 105, 20), word("from", 106, 125, 20),
        word("ALPHA", 126, 145, 20),
        word("01", 10, 18, 25), word("Jan", 19, 30, 25),
        word("2026", 31, 45, 25), word("09:15:00", 46, 65, 25),
        word("--", 150, 160, 25), word("1,250.00", 200, 240, 25),
        word("REF-001", 260, 310, 25),
        word("LIMITED", 70, 110, 30),
        word("02", 10, 18, 50), word("Jan", 19, 30, 50),
        word("2026", 31, 45, 50), word("10:00:00", 46, 65, 50),
        word("SHOP", 70, 100, 50),
        word("500.00", 150, 185, 50), word("--", 200, 210, 50),
        word("REF-002", 260, 310, 50),
    ]

    class FakePage:
        height = 100
        images = []

        def __init__(self, words):
            self.words = words

        def extract_words(self, **_kwargs):
            return self.words

    class FakeDocument:
        pages = [FakePage(first_page_words), FakePage([
            word("03", 10, 18, 10), word("Jan", 19, 30, 10),
            word("2026", 31, 45, 10), word("11:00:00", 46, 65, 10),
            word("SECOND", 70, 110, 10), word("--", 150, 160, 10),
            word("900.00", 200, 240, 10), word("REF-003", 260, 310, 10),
        ])]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(pdf_layout.pdfplumber, "open", lambda _content: FakeDocument())
    rows = pdf_layout.extract_pdf_layout_transactions(b"synthetic-pdf")
    assert len(rows) == 3
    assert rows[0].description == "Transfer from ALPHA LIMITED"
    assert rows[0].direction == TransactionDirection.CREDIT
    assert rows[0].amount == Decimal("1250.00")
    assert rows[0].reference == "REF-001"
    assert rows[1].direction == TransactionDirection.DEBIT
    assert rows[2].source_page == 2
