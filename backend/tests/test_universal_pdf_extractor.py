from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.statement_intelligence.pdf_extractor import extract_pdf_statement


class FakePage:
    def __init__(self, words, text):
        self._words = words
        self._text = text

    def extract_words(self, **_kwargs):
        return self._words

    def extract_text(self):
        return self._text


class FakePdf:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _word(text: str, x: float, y: float) -> dict:
    return {"text": text, "x0": x, "top": y}


def _opay_layout_page() -> FakePage:
    words = [
        _word("Trans.", 56, 261), _word("Time", 71, 261),
        _word("Value", 123, 261), _word("Date", 137, 261),
        _word("Description", 164, 261), _word("Debit(₦)", 290, 261),
        _word("Credit(₦)", 331, 261), _word("Balance", 372, 261),
        _word("After(₦)", 392, 261), _word("Channel", 420, 261),
        _word("Transaction", 461, 261), _word("Reference", 489, 261),
        # First row description is wrapped around its transaction line.
        _word("Coffee", 164, 274), _word("Shop", 196, 274),
        _word("01", 56, 280), _word("Jan", 62, 280),
        _word("2026", 73, 280), _word("10:00:00", 84, 280),
        _word("01", 123, 280), _word("Jan", 130, 280),
        _word("2026", 140, 280), _word("100.00", 290, 280),
        _word("--", 331, 280), _word("0.00", 372, 280),
        _word("Mobile", 420, 280), _word("debit-ref", 461, 280),
        _word("02", 56, 320), _word("Jan", 62, 320),
        _word("2026", 73, 320), _word("11:00:00", 84, 320),
        _word("02", 123, 320), _word("Jan", 130, 320),
        _word("2026", 140, 320), _word("Salary", 164, 320),
        _word("--", 290, 320), _word("1,000.00", 331, 320),
        _word("1,000.00", 372, 320), _word("Mobile", 420, 320),
        _word("credit-ref", 461, 320),
    ]
    text = (
        "Opening Balance ₦100.00 Total Debit ₦100.00 Debit Count 1 "
        "Closing Balance ₦1,000.00 Total Credit ₦1,000.00 Credit Count 1 "
        "Period: 01 Jan 2026 - 02 Jan 2026"
    )
    return FakePage(words, text)


def test_universal_pdf_extractor_maps_columns_and_reconstructs_wrapped_rows(monkeypatch) -> None:
    from app.services.statement_intelligence import pdf_extractor
    from app.services.statement_intelligence.schema import CanonicalField

    monkeypatch.setattr(
        pdf_extractor.pdfplumber,
        "open",
        lambda _buffer: FakePdf([_opay_layout_page()]),
    )
    page = _opay_layout_page()
    mapping, positions, _header_top = pdf_extractor.detect_column_mapping(page)
    assert positions[CanonicalField.TRANSACTION_DATE] == 56
    assert positions[CanonicalField.VALUE_DATE] == 123
    lines = pdf_extractor._cluster_words(page.extract_words())
    date_cells = next(
        pdf_extractor._cell_values(words, positions)
        for top, words in lines.items()
        if top == 280
    )
    assert date_cells[CanonicalField.TRANSACTION_DATE] == "01 Jan 2026 10:00:00"
    assert date_cells[CanonicalField.DEBIT] == "100.00"
    result = extract_pdf_statement(b"synthetic statement")
    assert len(result.rows) == 2
    assert result.rows[0].description == "Coffee Shop"
    assert result.rows[0].amount == Decimal("100.00")
    assert result.rows[0].type == "expense"
    assert result.rows[0].running_balance == Decimal("0.00")
    assert result.rows[0].external_id == "debit-ref"
    assert result.rows[1].description == "Salary"
    assert result.rows[1].type == "income"
    assert result.rows[1].amount == Decimal("1000.00")
    assert result.rows[1].running_balance == Decimal("1000.00")
    assert result.validation.status == "verified"
    assert result.metadata.page_count == 1


def test_universal_pdf_extractor_does_not_guess_amount_direction(monkeypatch) -> None:
    from app.services.statement_intelligence import pdf_extractor

    page = FakePage(
        [
            _word("Transaction", 50, 20), _word("Date", 75, 20),
            _word("Description", 150, 20), _word("Amount", 300, 20),
            _word("Reference", 400, 20),
            _word("01", 50, 40), _word("Jan", 58, 40),
            _word("2026", 70, 40), _word("Coffee", 150, 40),
            _word("100.00", 300, 40), _word("ref-1", 400, 40),
        ],
        "Statement",
    )
    monkeypatch.setattr(
        pdf_extractor.pdfplumber,
        "open",
        lambda _buffer: FakePdf([page]),
    )
    with pytest.raises(ValueError, match="couldn't identify transaction rows"):
        extract_pdf_statement(b"ambiguous statement")
