"""Bank-agnostic statement extraction contracts and normalization primitives."""

from app.services.statement_extraction.extractor import extract_statement_document
from app.services.statement_extraction.field_mapping import (
    ColumnField,
    ColumnMapping,
    map_statement_columns,
    normalize_header,
)
from app.services.statement_extraction.models import (
    ExtractedTransaction,
    ExtractionMethod,
    ExtractionResult,
    ExtractionStatus,
    StatementAccountSection,
    StatementMetadata,
    StatementSummary,
    TransactionDirection,
    ValidationIssue,
    ValidationReport,
)
from app.services.statement_extraction.validation import validate_extraction

__all__ = [
    "ColumnField",
    "ColumnMapping",
    "ExtractedTransaction",
    "ExtractionMethod",
    "ExtractionResult",
    "ExtractionStatus",
    "StatementAccountSection",
    "StatementMetadata",
    "StatementSummary",
    "TransactionDirection",
    "ValidationIssue",
    "ValidationReport",
    "extract_statement_document",
    "map_statement_columns",
    "normalize_header",
    "validate_extraction",
]
