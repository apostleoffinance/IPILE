"""Durable, database-backed statement extraction queue."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.account import Account
from app.models.household import Household
from app.models.imports import ImportJob, StatementExtractionTask
from app.services.imports import stage_import_rows
from app.services.statement_intelligence.engine import extract_statement

logger = logging.getLogger(__name__)


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
    db.commit()
    db.refresh(job)
    return job


def process_next_statement_task() -> bool:
    """Claim and process one task; database row locks prevent duplicate workers."""
    with SessionLocal() as db:
        now = datetime.now(UTC)
        stale_before = now - timedelta(minutes=15)
        exhausted = db.scalar(
            select(StatementExtractionTask)
            .where(
                StatementExtractionTask.status == "processing",
                StatementExtractionTask.claimed_at < stale_before,
                StatementExtractionTask.attempts >= 3,
            )
            .with_for_update(skip_locked=True)
            .limit(1)
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
        task = db.scalar(
            select(StatementExtractionTask)
            .where(
                or_(
                    StatementExtractionTask.status == "pending",
                    (
                        (StatementExtractionTask.status == "processing")
                        & (StatementExtractionTask.claimed_at < stale_before)
                        & (StatementExtractionTask.attempts < 3)
                    ),
                )
            )
            .order_by(StatementExtractionTask.created_at)
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
                    "error": str(exc)[:500],
                }
            task.status = "failed"
            task.content = b""
            task.claimed_at = None
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
