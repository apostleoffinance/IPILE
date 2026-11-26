"""Optional institution-specific extensions for the universal statement engine.

The generic extractor always runs first. Registered adapters are consulted only
when a document cannot be parsed generically; adapters must return the same
normalized ExtractionResult contract and must not post ledger entries.
"""

from __future__ import annotations

from typing import Protocol

from app.services.statement_intelligence.schema import ExtractionResult


class BankStatementAdapter(Protocol):
    name: str

    def supports(self, document_text: str) -> bool: ...

    def extract_pdf(self, content: bytes) -> ExtractionResult: ...


_BANK_ADAPTERS: list[BankStatementAdapter] = []


def register_bank_adapter(adapter: BankStatementAdapter) -> None:
    """Register an optional adapter; duplicate names are rejected."""
    if any(existing.name.casefold() == adapter.name.casefold() for existing in _BANK_ADAPTERS):
        raise ValueError(f"Bank statement adapter already registered: {adapter.name}")
    _BANK_ADAPTERS.append(adapter)


def unregister_bank_adapter(name: str) -> None:
    """Remove a previously registered adapter, primarily for controlled tests."""
    _BANK_ADAPTERS[:] = [
        adapter for adapter in _BANK_ADAPTERS if adapter.name.casefold() != name.casefold()
    ]


def extract_with_bank_adapter(content: bytes, document_text: str) -> ExtractionResult | None:
    """Try registered institution adapters without making them mandatory."""
    for adapter in tuple(_BANK_ADAPTERS):
        if adapter.supports(document_text):
            return adapter.extract_pdf(content)
    return None
