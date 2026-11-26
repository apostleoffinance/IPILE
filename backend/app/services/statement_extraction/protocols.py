"""Plug-in contracts for generic document extractors and optional bank adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.services.statement_extraction.models import (
    ExtractionMethod,
    ExtractionResult,
    StatementMetadata,
)


@dataclass(frozen=True, slots=True)
class ExtractionContext:
    filename: str | None = None
    mime_type: str | None = None
    preferred_currency: str | None = None
    metadata: StatementMetadata | None = None


@runtime_checkable
class DocumentExtractor(Protocol):
    """Generic extractor selected by document capability, not bank identity."""

    supported_methods: tuple[ExtractionMethod, ...]

    def can_extract(self, content: bytes, context: ExtractionContext) -> bool: ...

    def extract(self, content: bytes, context: ExtractionContext) -> ExtractionResult: ...


@runtime_checkable
class BankStatementAdapter(Protocol):
    """Optional layout hint provider; must return the universal extraction result."""

    adapter_id: str

    def can_handle(self, text: str, metadata: StatementMetadata) -> bool: ...

    def extract(self, text: str, context: ExtractionContext) -> ExtractionResult: ...
