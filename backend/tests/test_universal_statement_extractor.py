from datetime import date
from decimal import Decimal

from app.services.statement_extraction import (
    ExtractedTransaction,
    ExtractionMethod,
    ExtractionStatus,
    TransactionDirection,
    extract_statement_document,
)
from app.services.statement_extraction.document_intelligence import (
    PDFContentKind,
    PDFDocumentProfile,
)


def test_universal_pdf_extractor_preserves_multiple_account_sections(monkeypatch) -> None:
    from app.services.statement_extraction import extractor

    transactions = (
        ExtractedTransaction(
            transaction_date=date(2026, 1, 1), amount=Decimal("100.00"),
            direction=TransactionDirection.DEBIT, account_section="Wallet Account",
            source_page=1, reference="wallet-1",
        ),
        ExtractedTransaction(
            transaction_date=date(2026, 1, 2), amount=Decimal("200.00"),
            direction=TransactionDirection.CREDIT, account_section="Savings Account",
            source_page=3, reference="savings-1",
        ),
    )
    monkeypatch.setattr(
        extractor,
        "inspect_pdf_document",
        lambda _content: PDFDocumentProfile(
            page_count=3, pages=(), content_kind=PDFContentKind.TEXT,
            has_selectable_text=True, has_tables=True, scanned_page_numbers=(),
        ),
    )
    monkeypatch.setattr(extractor, "extract_pdf_layout_transactions", lambda _content: transactions)

    result = extract_statement_document(b"pdf", "pdf", filename="statement.pdf")
    assert result.method == ExtractionMethod.PDF_TABLE
    assert result.status == ExtractionStatus.VERIFIED
    assert len(result.sections) == 2
    assert result.sections[0].label == "Wallet Account"
    assert result.sections[0].source_page_start == 1
    assert result.sections[1].label == "Savings Account"
    assert result.sections[1].source_page_end == 3
    assert result.metadata.source_page_count == 3


def test_universal_pdf_extractor_fails_closed_when_table_is_unrecognized(monkeypatch) -> None:
    from app.services.statement_extraction import extractor

    monkeypatch.setattr(
        extractor,
        "inspect_pdf_document",
        lambda _content: PDFDocumentProfile(
            page_count=1, pages=(), content_kind=PDFContentKind.TEXT,
            has_selectable_text=True, has_tables=False, scanned_page_numbers=(),
        ),
    )
    monkeypatch.setattr(extractor, "extract_pdf_layout_transactions", lambda _content: ())

    def reject_legacy_fallback(*_args):
        raise ValueError("The legacy parser could not identify transaction rows.")

    monkeypatch.setattr(extractor, "parse_statement_document", reject_legacy_fallback)
    result = extract_statement_document(b"synthetic-pdf-bytes", "pdf")
    assert result.status == ExtractionStatus.INCOMPLETE
    assert result.transactions == ()
    assert "no_recognized_transaction_table" in {issue.code for issue in result.issues}


def test_mixed_pdf_is_never_reported_as_complete(monkeypatch) -> None:
    from app.services.statement_extraction import extractor

    transaction = ExtractedTransaction(
        transaction_date=date(2026, 1, 1), amount=Decimal("10.00"),
        direction=TransactionDirection.DEBIT, account_section="Current Account",
    )
    monkeypatch.setattr(
        extractor,
        "inspect_pdf_document",
        lambda _content: PDFDocumentProfile(
            page_count=2, pages=(), content_kind=PDFContentKind.MIXED,
            has_selectable_text=True, has_tables=True, scanned_page_numbers=(2,),
        ),
    )
    monkeypatch.setattr(
        extractor, "extract_pdf_layout_transactions", lambda _content: (transaction,)
    )
    result = extract_statement_document(b"pdf", "pdf")
    assert result.status == ExtractionStatus.INCOMPLETE
    assert "mixed_text_and_scanned_pages" in {issue.code for issue in result.issues}


def test_csv_uses_same_canonical_extraction_contract() -> None:
    content = (
        "Transaction Date,Narration,Debit,Credit,Reference\n"
        "2026-01-01,Groceries,2500.00,,csv-1\n"
        "2026-01-02,Salary,,150000.00,csv-2\n"
    )
    result = extract_statement_document(content.encode(), "csv", filename="bank.csv")
    assert result.method == ExtractionMethod.CSV
    assert len(result.transactions) == 2
    assert result.transactions[0].direction == TransactionDirection.DEBIT
    assert result.transactions[1].direction == TransactionDirection.CREDIT
    assert result.metadata.source_filename == "bank.csv"
