import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.models.account import Account
from app.models.household import Household
from app.models.imports import ImportJob, ImportMailbox
from app.models.transaction import Transaction
from app.schemas.imports import ImportBody, ImportCommitBody, ImportJobOut, ImportPreviewBody
from app.services.email_imports import apply_alert_automation, parse_bank_alert
from app.services.import_adapters import ImportRow
from app.services.imports import (
    apply_import_rows,
    commit_staged_import,
    run_import,
    stage_import,
)
from app.services.statement_jobs import (
    StatementQueueFullError,
    enqueue_statement_extraction,
    process_next_statement_task,
)
from app.services.transaction_intelligence import enrich_bank_alert

router = APIRouter(prefix="/imports", tags=["imports"])
INBOUND_BASIC_AUTH = HTTPBasic(auto_error=False)


class ImportApprovalBody(BaseModel):
    account_id: UUID


class ImportCorrectionBody(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    date: date_type | None = None
    type: str | None = Field(default=None, pattern="^(income|expense)$")
    description: str | None = Field(default=None, max_length=500)
    currency: str | None = Field(default=None, min_length=3, max_length=3, pattern="^[A-Za-z]{3}$")
    category_name: str | None = Field(default=None, max_length=120)


class StatementReviewConfirmationBody(BaseModel):
    acknowledge_discrepancies: bool
    reason: str = Field(min_length=20, max_length=500)


def _mailbox_address(token: str) -> str:
    domain = get_settings().inbound_email_domain.strip().lower()
    if not domain:
        raise HTTPException(status_code=503, detail="Inbound email domain is not configured.")
    return f"bank-alert+{token}@{domain}"




def _reject_inbound_email(
    db: Session,
    mailbox: ImportMailbox,
    *,
    sender: str,
    subject: str,
    message_id: str,
    reason: str,
) -> dict[str, str]:
    job = ImportJob(
        household_id=mailbox.household_id,
        source="email",
        filename=subject[:200],
        status="rejected",
        error_count=1,
        result={
            "sender": sender[:200],
            "message_id": message_id or None,
            "errors": [reason],
        },
    )
    mailbox.last_received_at = datetime.now(UTC)
    db.add(job)
    db.add(mailbox)
    db.commit()
    db.refresh(job)
    return {
        "id": str(job.id),
        "status": job.status,
        "message": "Alert rejected and not posted.",
    }

def _scoped_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
    account = (
        db.query(Account)
        .filter(
            Account.id == account_id,
            Account.household_id == household_id,
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account



@router.post("/preview", response_model=ImportJobOut, status_code=status.HTTP_201_CREATED)
def preview_statement_import(
    payload: ImportPreviewBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    """Parse a statement for review. This endpoint never posts ledger transactions."""
    try:
        job = stage_import(
            db, ctx.household, account_id=payload.account_id, source=payload.source,
            content=payload.content, filename=payload.filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(job)
    return job


@router.post(
    "/jobs/{job_id}/review-confirmation",
    response_model=ImportJobOut,
)
def confirm_statement_review(
    job_id: UUID,
    payload: StatementReviewConfirmationBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    """Record explicit human acceptance of non-fatal reconciliation discrepancies."""
    job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.household_id == ctx.household.id,
        ImportJob.status == "pending_review",
        ImportJob.source.in_(["csv", "statement"]),
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Pending statement import not found.")
    extraction = dict(job.result.get("extraction") or {})
    if not extraction.get("requires_manual_review"):
        raise HTTPException(
            status_code=409,
            detail="This statement does not require a review override.",
        )
    if not payload.acknowledge_discrepancies:
        raise HTTPException(
            status_code=400,
            detail="Confirm that you reviewed the discrepancies before proceeding.",
        )
    issues = extraction.get("issues") or []
    hard_errors = [
        issue for issue in issues
        if issue.get("code") in {
            "unparsed_transaction_row", "no_transactions", "mixed_text_and_scanned_pages"
        }
    ]
    if hard_errors:
        raise HTTPException(
            status_code=409,
            detail=(
                "Some transaction rows could not be extracted safely. "
                "This statement cannot be approved with missing or unreadable rows."
            ),
        )
    extraction["requires_manual_review"] = False
    extraction["status"] = "manually_accepted"
    extraction["manual_review"] = {
        "acknowledged": True,
        "reason": payload.reason.strip(),
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    job.result = {**job.result, "extraction": extraction}
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/commit", response_model=ImportJobOut)
def commit_statement_import(
    job_id: UUID,
    payload: ImportCommitBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    job = db.query(ImportJob).filter(
        ImportJob.id == job_id, ImportJob.household_id == ctx.household.id
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found.")
    try:
        committed = commit_staged_import(
            db, ctx.household, job=job, account_id=payload.account_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(committed)
    return committed

@router.post("/csv", response_model=ImportJobOut, status_code=status.HTTP_201_CREATED)
def import_csv(
    payload: ImportBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    try:
        job = run_import(
            db, ctx.household, account_id=payload.account_id, source="csv",
            content=payload.content, filename=payload.filename or "upload.csv",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(job)
    return job


@router.post("/statement", response_model=ImportJobOut, status_code=status.HTTP_201_CREATED)
def import_statement(
    payload: ImportBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    try:
        job = run_import(
            db, ctx.household, account_id=payload.account_id, source="statement",
            content=payload.content, filename=payload.filename or "statement.txt",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(job)
    return job


@router.post("/upload", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_statement(
    account_id: UUID = Form(...),
    file: UploadFile = File(...),
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    """Legacy upload URL now follows the same staged-review workflow."""
    return await preview_statement_upload(
        account_id=account_id,
        file=file,
        ctx=ctx,
        db=db,
    )


@router.post("/preview-upload", response_model=ImportJobOut, status_code=status.HTTP_202_ACCEPTED)
async def preview_statement_upload(
    account_id: UUID = Form(...),
    file: UploadFile = File(...),
    account_section: str | None = Form(default=None, max_length=120),
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    """Queue extraction and return immediately; no ledger write occurs here."""
    filename = (file.filename or "statement").strip()[:200]
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in {"csv", "pdf", "txt", "png", "jpg", "jpeg", "webp"}:
        raise HTTPException(
            status_code=415,
            detail="Upload a CSV, PDF, TXT, PNG, JPEG or WebP statement.",
        )
    upload_limit = get_settings().max_import_upload_bytes
    if upload_limit < 1:
        raise HTTPException(status_code=503, detail="Statement uploads are not configured.")
    raw = await file.read(upload_limit + 1)
    await file.close()
    if len(raw) > upload_limit:
        raise HTTPException(
            status_code=413,
            detail=f"Statement exceeds the configured {upload_limit}-byte upload limit.",
        )
    _scoped_account(db, ctx.household.id, account_id)
    try:
        return enqueue_statement_extraction(
            db,
            household_id=ctx.household.id,
            account_id=account_id,
            filename=filename,
            suffix=suffix,
            content=raw,
            account_section=account_section,
        )
    except StatementQueueFullError as exc:
        db.rollback()
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Statement processing could not be queued. Please try again.",
        ) from exc


@router.post("/internal/statement-tasks/{task_id}/process")
def process_statement_task_internal(
    task_id: UUID,
    x_statement_worker_secret: str | None = Header(
        default=None, alias="X-Statement-Worker-Secret"
    ),
    db: Session = Depends(get_db),
):
    """Authenticated Cloudflare Container entrypoint; never exposes task data publicly."""
    configured = get_settings().internal_statement_worker_secret
    if not configured or not x_statement_worker_secret or not hmac.compare_digest(
        configured, x_statement_worker_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid statement worker credentials.")
    from app.models.imports import StatementExtractionTask

    task = db.query(StatementExtractionTask).filter(
        StatementExtractionTask.id == task_id
    ).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Statement task not found.")
    if task.status == "completed":
        return {"task_id": str(task_id), "status": "completed", "idempotent_replay": True}
    if task.status == "failed":
        raise HTTPException(status_code=409, detail="Statement task has already failed.")
    processed = process_next_statement_task(task_id=task_id)
    db.expire_all()
    task = db.query(StatementExtractionTask).filter(
        StatementExtractionTask.id == task_id
    ).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Statement task not found.")
    if task.status == "completed":
        return {"task_id": str(task_id), "status": "completed"}
    if task.status == "failed":
        raise HTTPException(status_code=500, detail="Statement task processing failed.")
    if not processed:
        raise HTTPException(status_code=409, detail="Statement task is already being processed.")
    return {"task_id": str(task_id), "status": task.status}


@router.get("/jobs/{job_id}", response_model=ImportJobOut)
def get_statement_import_job(
    job_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    """Poll an extraction job without exposing jobs from another household."""
    job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.household_id == ctx.household.id,
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found.")
    return job

@router.post("/mailbox")
def create_mailbox(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.inbound_email_domain or not settings.inbound_email_webhook_secret:
        raise HTTPException(status_code=503, detail="Inbound email is not configured.")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    mailbox = db.query(ImportMailbox).filter(ImportMailbox.household_id == ctx.household.id).first()
    if mailbox is None:
        mailbox = ImportMailbox(household_id=ctx.household.id, token_hash=token_hash, enabled=True)
        db.add(mailbox)
    else:
        mailbox.token_hash = token_hash
        mailbox.enabled = True
    db.commit()
    return {
        "address": _mailbox_address(token),
        "enabled": True,
        "note": "Store this address privately. Regenerating it invalidates the previous address.",
    }


@router.post("/inbound-email", status_code=status.HTTP_200_OK)
def receive_inbound_email(
    payload: dict,
    x_inbound_email_secret: str | None = Header(default=None, alias="X-Inbound-Email-Secret"),
    credentials: HTTPBasicCredentials | None = Depends(INBOUND_BASIC_AUTH),
    db: Session = Depends(get_db),
):
    configured_secret = get_settings().inbound_email_webhook_secret
    header_valid = bool(
        configured_secret
        and x_inbound_email_secret
        and hmac.compare_digest(configured_secret, x_inbound_email_secret)
    )
    basic_valid = bool(
        configured_secret
        and credentials
        and hmac.compare_digest(credentials.username, "ipile")
        and hmac.compare_digest(credentials.password, configured_secret)
    )
    if not configured_secret or not (header_valid or basic_valid):
        raise HTTPException(status_code=401, detail="Invalid inbound email authentication.")
    recipient = str(payload.get("To") or payload.get("to") or payload.get("recipient") or "")
    match = re.search(r"bank-alert\+([A-Za-z0-9_-]+)@", recipient, re.IGNORECASE)
    if not match:
        raise HTTPException(status_code=400, detail="Unknown recipient address.")
    token_hash = hashlib.sha256(match.group(1).encode("utf-8")).hexdigest()
    mailbox = (
        db.query(ImportMailbox)
        .filter(ImportMailbox.token_hash == token_hash, ImportMailbox.enabled.is_(True))
        .first()
    )
    if mailbox is None:
        raise HTTPException(status_code=404, detail="Import mailbox not found.")
    message_id = str(payload.get("MessageID") or payload.get("message_id") or "").strip()
    if message_id:
        existing = (
            db.query(ImportJob)
            .filter(
                ImportJob.household_id == mailbox.household_id,
                ImportJob.source == "email",
                ImportJob.result["message_id"].as_string() == message_id,
            )
            .first()
        )
        if existing is not None:
            return {
                "id": str(existing.id),
                "status": existing.status,
                "message": "Duplicate provider delivery acknowledged.",
            }
    sender = str(payload.get("From") or payload.get("from") or payload.get("sender") or "")
    subject = str(payload.get("Subject") or payload.get("subject") or "Bank transaction alert")
    body = str(payload.get("TextBody") or payload.get("text_body") or payload.get("text") or "")
    if not body:
        return _reject_inbound_email(
            db, mailbox, sender=sender, subject=subject,
            message_id=message_id, reason="Email contains no plain-text body.",
        )
    try:
        row = parse_bank_alert(
            sender=sender,
            subject=subject,
            body=body,
            email_date=str(payload.get("Date") or payload.get("date") or "") or None,
            message_id=str(payload.get("MessageID") or payload.get("message_id") or "") or None,
        )
    except ValueError as exc:
        return _reject_inbound_email(
            db, mailbox, sender=sender, subject=subject,
            message_id=message_id, reason=str(exc),
        )
    # A bank reference/fingerprint is more reliable than the provider Message-ID:
    # the same alert can be forwarded more than once with different Message-IDs.
    existing_transaction = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == mailbox.household_id,
            Transaction.external_id == row.external_id,
            Transaction.deleted_at.is_(None),
        )
        .first()
    )
    if existing_transaction is not None:
        return {
            "id": str(existing_transaction.id),
            "status": "duplicate",
            "message": "This bank transaction is already in the household ledger.",
        }

    pending_jobs = (
        db.query(ImportJob)
        .filter(
            ImportJob.household_id == mailbox.household_id,
            ImportJob.source == "email",
            ImportJob.status == "pending_review",
        )
        .all()
    )
    for pending_job in pending_jobs:
        pending_rows = pending_job.result.get("rows", [])
        if any(item.get("external_id") == row.external_id for item in pending_rows):
            return {
                "id": str(pending_job.id),
                "status": "duplicate",
                "message": "This bank alert is already waiting for household review.",
            }

    row, suggested_account, intelligence = enrich_bank_alert(
        db,
        mailbox.household_id,
        row,
        sender=sender,
        provider="cloudflare_forwarding",
        provider_event_id=message_id or None,
        sender_verified=True,
        classification_context=body,
    )

    job = ImportJob(
        household_id=mailbox.household_id,
        source="email",
        filename=subject[:200],
        status="pending_review",
        result={
            "sender": sender[:200],
            "message_id": message_id or None,
            "suggested_account_id": str(suggested_account.id) if suggested_account else None,
            "account_match": intelligence["account_match"],
            "intelligence": intelligence,
            "rows": [{
                "date": row.date.isoformat(),
                "amount": str(row.amount),
                "currency": row.currency,
                "type": row.type,
                "description": row.description,
                "external_id": row.external_id,
                "merchant": row.merchant,
                "category_name": row.category_name,
            }],
        },
    )
    household = db.query(Household).filter(Household.id == mailbox.household_id).first()
    if household is not None:
        apply_alert_automation(db, household, job, row, suggested_account)
    mailbox.last_received_at = datetime.now(UTC)
    db.add(job)
    db.add(mailbox)
    db.commit()
    db.refresh(job)
    return {
        "id": str(job.id),
        "status": job.status,
        "message": "Alert received and processed according to household preferences.",
    }


@router.get("/review", response_model=list[ImportJobOut])
def list_import_review(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    return (
        db.query(ImportJob)
        .filter(
            ImportJob.household_id == ctx.household.id,
            ImportJob.status.in_(["pending_review", "rejected"]),
        )
        .order_by(ImportJob.created_at.desc())
        .limit(100)
        .all()
    )


@router.patch("/{job_id}/review", response_model=ImportJobOut)
def correct_email_import(
    job_id: UUID,
    payload: ImportCorrectionBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    """Correct extracted fields before approval; never changes the ledger."""
    job = (
        db.query(ImportJob)
        .filter(
            ImportJob.id == job_id,
            ImportJob.household_id == ctx.household.id,
            ImportJob.status == "pending_review",
            ImportJob.source == "email",
        )
        .first()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Pending email import not found.")
    rows = list(job.result.get("rows", []))
    if len(rows) != 1:
        raise HTTPException(status_code=400, detail="This alert cannot be safely edited.")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="Provide at least one field to correct.")
    row = dict(rows[0])
    for key, value in changes.items():
        if value is None:
            continue
        if key == "amount":
            row[key] = str(value)
        elif key == "date":
            row[key] = value.isoformat()
        else:
            row[key] = value
    rows[0] = row
    job.result = {**job.result, "rows": rows, "corrected": True}
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/approve", response_model=ImportJobOut)
def approve_email_import(
    job_id: UUID,
    payload: ImportApprovalBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    job = (
        db.query(ImportJob)
        .filter(
            ImportJob.id == job_id,
            ImportJob.household_id == ctx.household.id,
            ImportJob.status == "pending_review",
            ImportJob.source == "email",
        )
        .first()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Pending email import not found.")
    account = _scoped_account(db, ctx.household.id, payload.account_id)
    source_rows = list(job.result.get("rows", []))
    for item in source_rows:
        alert_currency = str(item.get("currency") or "").upper()
        if alert_currency and alert_currency != account.currency.upper():
            raise HTTPException(
                status_code=409,
                detail=(
                    f"This alert is denominated in {alert_currency}, but the selected "
                    f"account uses {account.currency}. Choose a matching account or correct "
                    "the currency before approval."
                ),
            )
    rows = [
        ImportRow(
            date=datetime.fromisoformat(item["date"]).date(),
            amount=Decimal(item["amount"]),
            type=item["type"],
            description=item.get("description"),
            external_id=item["external_id"],
            merchant=item.get("merchant"),
            currency=(str(item.get("currency") or account.currency).upper()),
            category_name=item.get("category_name"),
        )
        for item in source_rows
    ]
    applied = apply_import_rows(
        db,
        ctx.household,
        account,
        rows,
        source="email",
        filename=job.filename,
    )
    job.status = "approved"
    job.created_count = applied.created_count
    job.skipped_count = applied.skipped_count
    job.error_count = applied.error_count
    job.result = {
        **job.result,
        "approved_account_id": str(account.id),
        "approved_at": datetime.now(UTC).isoformat(),
        "errors": applied.result.get("errors", []),
    }
    db.delete(applied)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
