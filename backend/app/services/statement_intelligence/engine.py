"""Single entry point for extracting bank statements into canonical rows."""

from __future__ import annotations

from app.services.import_adapters import get_adapter
from app.services.statement_intelligence.schema import ExtractionResult
from app.services.statement_intelligence.validation import validate_statement


def extract_statement(content: bytes, suffix: str) -> ExtractionResult:
    """Dispatch all supported statement formats through one extraction contract."""
    normalized_suffix = suffix.lower().lstrip(".")
    if normalized_suffix in {"pdf", "png", "jpg", "jpeg", "webp"}:
        from app.services.pdf_imports import extract_statement_document

        return extract_statement_document(content, normalized_suffix)

    if normalized_suffix not in {"csv", "txt"}:
        raise ValueError("Unsupported statement format.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("This statement is not valid UTF-8 text.") from exc

    source = "csv" if normalized_suffix == "csv" else "statement"
    rows = get_adapter(source).parse(text)
    validation = validate_statement(rows)
    return ExtractionResult(
        rows=rows,
        extraction_method="csv_structured" if source == "csv" else "text_structured",
        issues=list(validation.issues),
        validation=validation,
        confidence=1.0,
        diagnostics={"status": validation.status},
    )
