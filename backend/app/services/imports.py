from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.household import Household
from app.models.imports import ImportJob
from app.models.transaction import Transaction
from app.services.balances import apply_transaction_effect
from app.services.budgets import evaluate_budget_alerts
from app.services.currencies import get_rate
from app.services.import_adapters import ImportAdapter, ImportRow, get_adapter


def _category_id(db: Session, household_id: UUID, name: str | None) -> UUID | None:
    if not name:
        return None
    row = (
        db.query(Category)
        .filter(
            Category.household_id == household_id,
            Category.name == name,
            Category.deleted_at.is_(None),
        )
        .first()
    )
    return row.id if row else None


def _existing(db: Session, household_id: UUID, external_id: str) -> Transaction | None:
    return (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household_id,
            Transaction.external_id == external_id,
            Transaction.deleted_at.is_(None),
        )
        .first()
    )


def apply_import_rows(
    db: Session,
    household: Household,
    account: Account,
    rows: list[ImportRow],
    *,
    source: str,
    filename: str | None = None,
) -> ImportJob:
    created = 0
    created_income = False
    skipped = 0
    errors: list[str] = []
    for row in rows:
        if _existing(db, household.id, row.external_id):
            skipped += 1
            continue
        if row.type == "transfer":
            errors.append(
                f"{row.external_id}: "
                "Transfers must be matched to a counterparty account before import."
            )
            continue
        try:
            with db.begin_nested():
                source_currency = account.currency or household.base_currency
                rate, rate_date, rate_source = get_rate(
                    db, household.id, source_currency, household.base_currency, row.date
                )
                base_amount = (row.amount * rate).quantize(Decimal("0.01"))
                tx = Transaction(
                    household_id=household.id,
                    account_id=account.id,
                    amount=row.amount,
                    currency=source_currency,
                    base_amount=base_amount,
                    base_currency=household.base_currency,
                    exchange_rate=rate,
                    exchange_rate_date=rate_date,
                    exchange_rate_source=rate_source,
                    type=row.type,
                    category_id=_category_id(db, household.id, row.category_name),
                    date=row.date,
                    merchant=row.merchant,
                    description=row.description,
                    status="cleared",
                    external_id=row.external_id,
                    import_source=source,
                )
                db.add(tx)
                db.flush()
                apply_transaction_effect(
                    db,
                    account=account,
                    counterparty=None,
                    tx_type=tx.type,
                    amount=tx.amount,
                    status=tx.status,
                )
                db.add(account)
                db.flush()
            created += 1
            created_income = created_income or tx.type == "income"
        except Exception as exc:  # noqa: BLE001 — collect row errors into job result
            errors.append(f"{row.external_id}: {exc}")
    evaluate_budget_alerts(db, household.id)
    if created:
        if created_income:
            from app.services.automation import run_tick

            _, skipped = run_tick(db, household, tick_type="income_recognized")
            if skipped:
                from app.services.automation import run_income_recognized_chain

                run_income_recognized_chain(db, household)
        else:
            from app.services.financial_intelligence import run_financial_intelligence
            from app.services.notifications import sync_notifications_from_alerts

            run_financial_intelligence(db, household)
            sync_notifications_from_alerts(db, household.id)
    job = ImportJob(
        household_id=household.id,
        source=source,
        filename=filename,
        status="completed" if not errors else "completed_with_errors",
        created_count=created,
        skipped_count=skipped,
        error_count=len(errors),
        result={"errors": errors},
    )
    db.add(job)
    db.flush()
    return job


def run_import(
    db: Session,
    household: Household,
    *,
    account_id: UUID,
    source: str,
    content: str,
    filename: str | None = None,
) -> ImportJob:
    account = (
        db.query(Account)
        .filter(
            Account.id == account_id,
            Account.household_id == household.id,
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise ValueError("Account not found.")
    adapter: ImportAdapter = get_adapter(source)
    rows = adapter.parse(content)
    return apply_import_rows(
        db, household, account, rows, source=adapter.source, filename=filename
    )


def stage_import(
    db: Session,
    household: Household,
    *,
    account_id: UUID,
    source: str,
    content: str,
    filename: str | None = None,
) -> ImportJob:
    """Parse a statement for review without changing account balances."""
    account = (
        db.query(Account)
        .filter(
            Account.id == account_id,
            Account.household_id == household.id,
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise ValueError("Account not found.")
    if source not in {"csv", "statement"}:
        raise ValueError("Only CSV and text statements can be staged.")
    rows = get_adapter(source).parse(content)
    return stage_import_rows(
        db, household, account, rows, source=source, filename=filename
    )


def stage_import_rows(
    db: Session,
    household: Household,
    account: Account,
    rows: list[ImportRow],
    *,
    source: str,
    filename: str | None = None,
    extraction: dict | None = None,
) -> ImportJob:
    """Persist normalized rows for review, never posting ledger effects."""
    if account.household_id != household.id or account.deleted_at is not None:
        raise ValueError("Account not found.")
    if source not in {"csv", "statement"}:
        raise ValueError("Only CSV and text statements can be staged.")
    serialized = [
        {
            "date": row.date.isoformat(),
            "amount": str(row.amount),
            "type": row.type,
            "description": row.description,
            "external_id": row.external_id,
            "merchant": row.merchant,
            "category_name": row.category_name,
            "currency": row.currency,
            "value_date": row.value_date.isoformat() if row.value_date else None,
            "transaction_datetime": (
                row.transaction_datetime.isoformat() if row.transaction_datetime else None
            ),
            "running_balance": (
                str(row.running_balance) if row.running_balance is not None else None
            ),
            "source_page": row.source_page,
            "extraction_confidence": row.extraction_confidence,
        }
        for row in rows
    ]
    duplicate_count = sum(
        1 for row in rows if _existing(db, household.id, row.external_id)
    )
    job = ImportJob(
        household_id=household.id,
        source=source,
        filename=filename,
        status="pending_review",
        result={
            "account_id": str(account.id),
            "row_count": len(serialized),
            "duplicate_count_at_preview": duplicate_count,
            "rows": serialized,
            "errors": [],
            **({"extraction": extraction} if extraction else {}),
            **(
                {"extraction_method": extraction.get("extraction_method")}
                if extraction and extraction.get("extraction_method")
                else {}
            ),
        },
    )
    db.add(job)
    db.flush()
    return job

def commit_staged_import(
    db: Session,
    household: Household,
    *,
    job: ImportJob,
    account_id: UUID,
) -> ImportJob:
    """Commit a staged import once, rechecking duplicates at commit time."""
    if job.household_id != household.id:
        raise ValueError("Import job not found.")
    if job.status != "pending_review" or job.source not in {"csv", "statement"}:
        raise ValueError("This import is not awaiting confirmation.")
    extraction = job.result.get("extraction") or {}
    if extraction.get("requires_manual_review"):
        raise ValueError(
            "This statement has unresolved extraction or reconciliation issues. "
            "Review and correct the flagged information before importing it."
        )
    if str(job.result.get("account_id")) != str(account_id):
        raise ValueError("Choose the account selected during preview.")
    account = (
        db.query(Account)
        .filter(
            Account.id == account_id,
            Account.household_id == household.id,
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise ValueError("Account not found.")
    rows = [
        ImportRow(
            date=date.fromisoformat(item["date"]),
            amount=Decimal(item["amount"]),
            type=item["type"],
            description=item.get("description"),
            external_id=item["external_id"],
            merchant=item.get("merchant"),
            category_name=item.get("category_name"),
            currency=item.get("currency"),
            value_date=(
                date.fromisoformat(item["value_date"]) if item.get("value_date") else None
            ),
            transaction_datetime=(
                datetime.fromisoformat(item["transaction_datetime"])
                if item.get("transaction_datetime") else None
            ),
            running_balance=(
                Decimal(item["running_balance"]) if item.get("running_balance") is not None else None
            ),
            source_page=item.get("source_page"),
            extraction_confidence=item.get("extraction_confidence"),
        )
        for item in job.result.get("rows", [])
    ]
    for row in rows:
        row_currency = (row.currency or "").upper()
        if row_currency and row_currency != account.currency.upper():
            raise ValueError(
                f"Statement currency {row_currency} does not match selected account currency "
                f"{account.currency}. Choose an account in the statement currency."
            )
    applied = apply_import_rows(
        db, household, account, rows, source=job.source, filename=job.filename
    )
    job.status = "committed" if applied.error_count == 0 else "committed_with_errors"
    job.created_count = applied.created_count
    job.skipped_count = applied.skipped_count
    job.error_count = applied.error_count
    job.result = {"row_count": len(rows), "errors": applied.result.get("errors", [])}
    db.delete(applied)
    db.add(job)
    db.flush()
    return job
