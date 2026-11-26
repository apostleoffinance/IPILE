from datetime import date
from decimal import Decimal

from app.services.import_adapters import ImportRow
from app.services.statement_intelligence.engine import extract_statement
from app.services.statement_intelligence.schema import ExtractionResult
from app.services.statement_intelligence.validation import validate_statement


def test_universal_engine_dispatches_opay_style_csv_to_canonical_rows() -> None:
    content = (
        "Trans. Time,Value Date,Description,Debit(₦),Credit(₦),"
        "Balance After(₦),Channel,Transaction Reference\n"
        "01 Jan 2026 20:35:26,01 Jan 2026,Transfer to Merchant,5000.00,--,"
        "1492.35,Mobile,ref-1\n"
    ).encode()
    result = extract_statement(content, "csv")
    assert result.extraction_method == "csv_structured"
    assert len(result.rows) == 1
    assert result.rows[0].amount == Decimal("5000.00")
    assert result.rows[0].type == "expense"
    assert result.rows[0].currency == "NGN"


def test_universal_engine_dispatches_pdf_to_document_extractor(monkeypatch) -> None:
    from app.services import pdf_imports

    expected = ExtractionResult(
        rows=[
            ImportRow(
                date=date(2026, 1, 1),
                amount=Decimal("10.00"),
                type="expense",
                description="Test",
                external_id="pdf-1",
            )
        ],
        extraction_method="pdf_text_layout",
        validation=validate_statement([
            ImportRow(
                date=date(2026, 1, 1),
                amount=Decimal("10.00"),
                type="expense",
                description="Test",
                external_id="pdf-1",
            )
        ]),
    )
    monkeypatch.setattr(pdf_imports, "extract_statement_document", lambda *_args: expected)
    result = extract_statement(b"pdf", "pdf")
    assert result is expected

