"""Convert validated universal extraction candidates into ledger import rows."""

from __future__ import annotations

import hashlib
from decimal import Decimal

from app.services.import_adapters import ImportRow
from app.services.statement_extraction.models import (
    ExtractionResult,
    ExtractionStatus,
    StatementAccountSection,
    TransactionDirection,
)


def select_statement_section(
    result: ExtractionResult,
    section_label: str | None = None,
) -> StatementAccountSection:
    if result.status in {ExtractionStatus.FAILED, ExtractionStatus.INCOMPLETE}:
        messages = [issue.message for issue in result.issues if issue.severity == "error"]
        detail = messages[0] if messages else "The statement could not be extracted completely."
        raise ValueError(detail)
    if not result.sections:
        raise ValueError("No transaction section was found in this statement.")
    if section_label is None:
        if len(result.sections) > 1:
            labels = [section.label or "Unlabelled account" for section in result.sections]
            raise ValueError(
                "This statement contains multiple account sections. Select one to review: "
                + ", ".join(labels)
            )
        return result.sections[0]
    for section in result.sections:
        if section.label == section_label:
            return section
    raise ValueError("The selected account section was not found in this statement.")


def normalize_section_rows(
    result: ExtractionResult,
    section_label: str | None = None,
) -> tuple[list[ImportRow], StatementAccountSection]:
    section = select_statement_section(result, section_label)
    rows: list[ImportRow] = []
    errors: list[str] = []
    for index, candidate in enumerate(section.transactions, start=1):
        if candidate.transaction_date is None:
            errors.append(f"Row {index}: transaction date is missing.")
            continue
        if candidate.amount is None or candidate.amount <= 0:
            errors.append(f"Row {index}: transaction amount is missing or invalid.")
            continue
        if candidate.direction not in {TransactionDirection.DEBIT, TransactionDirection.CREDIT}:
            errors.append(f"Row {index}: money-in or money-out direction is uncertain.")
            continue
        external_id = candidate.reference
        if not external_id:
            fingerprint = "|".join((
                candidate.transaction_date.isoformat(),
                str(candidate.amount),
                str(candidate.direction),
                candidate.description or "",
                str(candidate.source_page or ""),
                str(candidate.source_row or index),
                section.label or "",
            ))
            external_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        rows.append(ImportRow(
            date=candidate.transaction_date,
            amount=candidate.amount.quantize(Decimal("0.01")),
            type=(
                "income" if candidate.direction == TransactionDirection.CREDIT
                else "expense"
            ),
            description=candidate.description,
            external_id=external_id,
            merchant=candidate.description,
            currency=candidate.currency,
            transaction_datetime=candidate.transaction_datetime,
            value_date=candidate.value_date,
            running_balance=candidate.running_balance,
            channel=candidate.channel,
            source_page=candidate.source_page,
            source_row=candidate.source_row,
            account_section=candidate.account_section,
            confidence=candidate.confidence,
            warnings=candidate.warnings,
        ))
    if errors:
        raise ValueError(
            "Some transaction rows could not be normalized safely. "
            "No rows were staged. " + " ".join(errors[:5])
        )
    if not rows:
        raise ValueError("No complete transactions were extracted from this account section.")
    return rows, section
