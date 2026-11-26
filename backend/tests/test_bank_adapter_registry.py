from datetime import date
from decimal import Decimal

import pytest

from app.services.import_adapters import ImportRow
from app.services.statement_intelligence.bank_adapters import (
    register_bank_adapter,
    unregister_bank_adapter,
)
from app.services.statement_intelligence.pdf_extractor import extract_pdf_statement
from app.services.statement_intelligence.schema import ExtractionResult
from app.services.statement_intelligence.validation import validate_statement


class FakePage:
    def extract_words(self, **_kwargs):
        return []

    def extract_text(self):
        return "Example Bank statement"


class FakePdf:
    pages = [FakePage()]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class ExampleBankAdapter:
    name = "example-bank-test"

    def supports(self, document_text: str) -> bool:
        return "Example Bank" in document_text

    def extract_pdf(self, content: bytes) -> ExtractionResult:
        assert content == b"bank-specific"
        rows = [
            ImportRow(
                date=date(2026, 1, 1),
                amount=Decimal("25.00"),
                type="expense",
                description="Example purchase",
                external_id="example-1",
            )
        ]
        return ExtractionResult(
            rows=rows,
            extraction_method="bank_adapter:example-bank-test",
            validation=validate_statement(rows),
            confidence=0.99,
        )


def test_optional_bank_adapter_is_used_only_after_generic_pdf_extraction_fails(monkeypatch):
    from app.services.statement_intelligence import pdf_extractor

    adapter = ExampleBankAdapter()
    register_bank_adapter(adapter)
    monkeypatch.setattr(pdf_extractor.pdfplumber, "open", lambda _buffer: FakePdf())
    try:
        result = extract_pdf_statement(b"bank-specific")
        assert result.extraction_method == "bank_adapter:example-bank-test"
        assert result.rows[0].external_id == "example-1"
    finally:
        unregister_bank_adapter(adapter.name)


def test_duplicate_optional_bank_adapter_names_are_rejected():
    adapter = ExampleBankAdapter()
    register_bank_adapter(adapter)
    try:
        with pytest.raises(ValueError, match="already registered"):
            register_bank_adapter(ExampleBankAdapter())
    finally:
        unregister_bank_adapter(adapter.name)
