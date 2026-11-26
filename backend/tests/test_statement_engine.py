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

def test_optional_bank_adapter_is_selected_before_generic_csv_parser() -> None:
    from app.services.statement_intelligence.adapters import BankAdapterRegistry

    class ExampleBankAdapter:
        bank_id = "example_bank"

        def supports(self, content: bytes, suffix: str) -> bool:
            return suffix == "csv" and content.startswith(b"EXAMPLE")

        def extract(self, _content: bytes, _suffix: str) -> ExtractionResult:
            row = ImportRow(
                date=date(2026, 1, 1),
                amount=Decimal("25.00"),
                type="expense",
                description="Adapter-specific transaction",
                external_id="adapter-1",
            )
            return ExtractionResult(
                rows=[row],
                extraction_method="example_bank_adapter",
                validation=validate_statement([row]),
                confidence=0.99,
            )

    registry = BankAdapterRegistry()
    registry.register(ExampleBankAdapter())
    result = extract_statement(
        b"EXAMPLE,proprietary,statement", "csv", bank_adapters=registry
    )
    assert result.extraction_method == "example_bank_adapter"
    assert result.rows[0].external_id == "adapter-1"
    assert registry.bank_ids == ("example_bank",)


def test_bank_adapter_registry_rejects_duplicate_bank_ids() -> None:
    import pytest

    from app.services.statement_intelligence.adapters import BankAdapterRegistry

    class ExampleAdapter:
        bank_id = "duplicate"

        def supports(self, _content: bytes, _suffix: str) -> bool:
            return False

        def extract(self, _content: bytes, _suffix: str) -> ExtractionResult:
            raise AssertionError("This adapter should never be selected.")

    registry = BankAdapterRegistry()
    registry.register(ExampleAdapter())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(ExampleAdapter())
