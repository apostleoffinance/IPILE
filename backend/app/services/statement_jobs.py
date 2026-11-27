"""Durable, database-backed statement extraction queue."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.account import Account
from app.models.household import Household
from app.models.imports import ImportJob, StatementExtractionOutbox, StatementExtractionTask
from app.services.imports import stage_import_rows
from app.services.statement_intelligence.engine import extract_statement

logger = logging.getLogger(__name__)


class StatementQueueFullError(RuntimeError):
    """Raised when accepting another raw statement would exceed queue bounds."""



def extraction_payload(extraction) -> dict:
    validation = extraction.validation
    issues = list(extraction.issues or (validation.issues if validation else ()))
    has_errors = any(issue.severity == "error" for issue in issues)
    status = "incomplete" if has_errors or validation is None else validation.status
    requires_review = status != "verified"
    summary = extraction.summary
    return {
        "extraction_method": extraction.extraction_method,
        "status": status,
        "confidence": extraction.confidence,
        "requires_manual_review": requires_review,
        "row_count": len(extraction.rows),
        "summary": {
            "opening_balance": (
                str(summary.opening_balance) if summary.opening_balance is not None else None
            ),
            "closing_balance": (
                str(summary.closing_balance) if summary.closing_balance is not None else None
            ),
            "total_debits": (
                str(summary.total_debits) if summary.total_debits is not None else None
            ),
            "total_credits": (
                str(summary.total_credits) if summary.total_credits is not None else None
            ),
            "debit_count": summary.debit_count,
            "credit_count": summary.credit_count,
            "currency": summary.currency or extraction.metadata.currency,
            "period_start": summary.period_start.isoformat() if summary.period_start else None,
            "period_end": summary.period_end.isoformat() if summary.period_end else None,
        },
        "validation": {
            "status": status,
            "debit_total": str(validation.debit_total) if validation else "0",
            "credit_total": str(validation.credit_total) if validation else "0",
            "debit_count": validation.debit_count if validation else 0,
            "credit_count": validation.credit_count if validation else 0,
            "balance_check_count": validation.balance_check_count if validation else 0,
        },
        "issues": [
            {
                "code": issue.code,
                "message": issue.message,
                "severity": issue.severity,
                "page": issue.page,
                "row": issue.row,
                "field": issue.field,
            }
            for issue in issues
        ],
        "metadata": {
            "institution": extraction.metadata.institution,
            "currency": extraction.metadata.currency,
            "page_count": extraction.metadata.page_count,
            "transaction_pages": list(extraction.metadata.transaction_pages),
        },
    }


def enqueue_statement_extraction(
    db: Session,
    *,
    household_id,
    account_id,
    filename: str,
    suffix: str,
    content: bytes,
    account_section: str | None = None,
) -> ImportJob:
    active_states = ("pending", "processing")
    household_active = db.scalar(
        select(func.count())
        .select_from(StatementExtractionTask)
        .where(
            StatementExtractionTask.household_id == household_id,
            StatementExtractionTask.status.in_(active_states),
        )
    ) or 0
    global_active = db.scalar(
        select(func.count())
        .select_from(StatementExtractionTask)
        .where(StatementExtractionTask.status.in_(active_states))
    ) or 0
    if household_active >= 2 or global_active >= 10:
        raise StatementQueueFullError(
            "Statement processing is busy. Please wait for an existing import to finish."
        )

    job = ImportJob(
        household_id=household_id,
        source="statement",
        filename=filename[:200],
        status="processing",
        result={"account_id": str(account_id), "processing_stage": "queued"},
    )
    db.add(job)
    db.flush()
    task = StatementExtractionTask(
        import_job_id=job.id,
        household_id=household_id,
        account_id=account_id,
        filename=filename[:200],
        suffix=suffix,
        account_section=account_section,
        content=content,
        status="pending",
    )
    db.add(task)
    db.flush()
    db.add(StatementExtractionOutbox(task_id=task.id, status="pending"))
    db.commit()
    db.refresh(job)
    return job


def process_next_statement_task(task_id: UUID | None = None) -> bool:
    """Claim and process one task; optional task ID makes queue delivery idempotent."""
    with SessionLocal() as db:
        now = datetime.now(UTC)
        stale_before = now - timedelta(minutes=15)
        exhausted_query = select(StatementExtractionTask).where(
            StatementExtractionTask.status == "processing",
            StatementExtractionTask.claimed_at < stale_before,
            StatementExtractionTask.attempts >= 3,
        )
        if task_id is not None:
            exhausted_query = exhausted_query.where(StatementExtractionTask.id == task_id)
        exhausted = db.scalar(
            exhausted_query.with_for_update(skip_locked=True).limit(1)
        )
        if exhausted is not None:
            exhausted.status = "failed"
            exhausted.content = b""
            job = db.get(ImportJob, exhausted.import_job_id)
            if job is not None:
                job.status = "failed"
                job.error_count = 1
                job.result = {
                    **(job.result or {}),
                    "processing_stage": "failed",
                    "error": (
                        "Statement processing could not complete after several worker attempts."
                    ),
                }
            db.commit()
            return True
        task_query = select(StatementExtractionTask).where(
            or_(
                StatementExtractionTask.status == "pending",
                (
                    (StatementExtractionTask.status == "processing")
                    & (StatementExtractionTask.claimed_at < stale_before)
                    & (StatementExtractionTask.attempts < 3)
                ),
            )
        )
        if task_id is not None:
            task_query = task_query.where(StatementExtractionTask.id == task_id)
        task = db.scalar(
            task_query.order_by(StatementExtractionTask.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if task is None:
            return False
        task.status = "processing"
        task.claimed_at = now
        task.attempts += 1
        db.commit()
        task_id = task.id

    with SessionLocal() as db:
        task = db.get(StatementExtractionTask, task_id)
        if task is None:
            return True
        job = db.get(ImportJob, task.import_job_id)
        account = db.get(Account, task.account_id)
        household = db.get(Household, task.household_id)
        try:
            if job is None or account is None or household is None:
                raise ValueError("The account or household for this import is no longer available.")
            extraction = extract_statement(bytes(task.content), task.suffix)
            review = extraction_payload(extraction)
            sections = sorted({
                row.account_section for row in extraction.rows if row.account_section
            })
            if len(sections) > 1 and not task.account_section:
                job.status = "needs_section_selection"
                job.result = {
                    **(job.result or {}),
                    "processing_stage": "complete",
                    "available_sections": sections,
                    "section_count": len(sections),
                    "row_count": len(extraction.rows),
                    "extraction_method": extraction.extraction_method,
                    "message": (
                        "This statement contains multiple accounts. Upload it again "
                        "and select the account section you want to review."
                    ),
                }
            else:
                rows = extraction.rows
                if task.account_section:
                    rows = [
                        row for row in rows if row.account_section == task.account_section
                    ]
                    if not rows:
                        raise ValueError(
                            "The selected account section was not found in the extracted statement."
                        )
                if not rows:
                    job.status = "failed"
                    job.error_count = 1
                    job.result = {
                        **(job.result or {}),
                        "processing_stage": "failed",
                        "error": "No transaction rows could be extracted safely.",
                        "extraction": review,
                    }
                else:
                    staged = stage_import_rows(
                        db,
                        household,
                        account,
                        rows,
                        source="statement",
                        filename=task.filename,
                        extraction=review,
                    )
                    # Preserve the original job ID returned to the uploading client.
                    job.status = staged.status
                    job.created_count = staged.created_count
                    job.skipped_count = staged.skipped_count
                    job.error_count = staged.error_count
                    job.result = {
                        **(staged.result or {}),
                        "account_id": str(account.id),
                        "processing_stage": "complete",
                        "extraction_method": extraction.extraction_method,
                        "extraction_status": review["status"],
                        "extraction_issues": review["issues"],
                        "account_section": task.account_section,
                        "section_count": len(sections) or 1,
                        "extraction": review,
                    }
                    db.delete(staged)
            task.status = "completed"
            task.content = b""
            task.claimed_at = None
            db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Statement extraction task %s failed", task_id)
            if job is not None:
                job.status = "failed"
                job.error_count = 1
                job.result = {
                    **(job.result or {}),
                    "processing_stage": "failed",
                    "error": (
                        str(exc)[:500]
                        if isinstance(exc, ValueError)
                        else "Statement processing failed unexpectedly. Please try again."
                    ),
                }
            task.claimed_at = None
            if task.attempts >= 3:
                task.status = "failed"
                task.content = b""
            else:
                task.status = "pending"
                if job is not None:
                    job.status = "processing"
                    job.result = {
                        **(job.result or {}),
                        "processing_stage": "retrying",
                        "last_error": (
                            str(exc)[:500]
                            if isinstance(exc, ValueError)
                            else "Statement processing attempt failed; retrying safely."
                        ),
                    }
            db.commit()
    return True


def run_statement_worker(poll_seconds: float = 2.0) -> None:
    logger.info("Statement extraction worker started")
    while True:
        try:
            worked = process_next_statement_task()
        except Exception:  # noqa: BLE001
            logger.exception("Statement extraction worker iteration failed")
            worked = False
        if not worked:
            time.sleep(poll_seconds)
