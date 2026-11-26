"""Optional bank-specific adapters layered over the universal extraction engine."""

from __future__ import annotations

from typing import Protocol

from app.services.statement_intelligence.schema import ExtractionResult


class BankStatementAdapter(Protocol):
    """A bank-specific adapter may override parsing without replacing validation."""

    bank_id: str

    def supports(self, content: bytes, suffix: str) -> bool: ...

    def extract(self, content: bytes, suffix: str) -> ExtractionResult: ...


class BankAdapterRegistry:
    """Ordered adapter registry; generic extraction remains the default fallback."""

    def __init__(self) -> None:
        self._adapters: list[BankStatementAdapter] = []

    def register(self, adapter: BankStatementAdapter) -> None:
        if any(item.bank_id == adapter.bank_id for item in self._adapters):
            raise ValueError(f"A statement adapter is already registered for {adapter.bank_id}.")
        self._adapters.append(adapter)

    def select(self, content: bytes, suffix: str) -> BankStatementAdapter | None:
        return next(
            (adapter for adapter in self._adapters if adapter.supports(content, suffix)),
            None,
        )

    @property
    def bank_ids(self) -> tuple[str, ...]:
        return tuple(adapter.bank_id for adapter in self._adapters)


DEFAULT_BANK_ADAPTERS = BankAdapterRegistry()
