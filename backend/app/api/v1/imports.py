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
from starlette.concurrency import run_in_threadpool

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
    stage_import_rows,
)
from app.services.pdf_imports import parse_statement_document
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


@router.post("/upload", response_model=ImportJobOut, status_code=status.HTTP_201_CREATED)
async def upload_statement(
    account_id: UUID = Form(...),
    file: UploadFile = File(...),
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    filename = (file.filename or "statement").strip()
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
    if len(raw) > upload_limit:
        raise HTTPException(
            status_code=413,
            detail=f"Statement exceeds the configured {upload_limit}-byte upload limit.",
        )
    try:
        if suffix in {"pdf", "png", "jpg", "jpeg", "webp"}:
            rows, extraction_method = await run_in_threadpool(parse_statement_document, raw, suffix)
            source = "statement"
            account = _scoped_account(db, ctx.household.id, account_id)
            job = apply_import_rows(
                db, ctx.household, account, rows, source=source, filename=filename
            )
            job.result = {**(job.result or {}), "extraction_method": extraction_method}
        else:
            content = raw.decode("utf-8-sig")
            source = "csv" if suffix == "csv" else "statement"
            job = run_import(
                db, ctx.household, account_id=account_id, source=source,
                content=content, filename=filename,
            )
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if suffix in {"pdf", "png", "jpg", "jpeg", "webp"}:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise
    db.commit()
    db.refresh(job)
    return job



@router.post("/preview-upload", response_model=ImportJobOut, status_code=status.HTTP_201_CREATED)
async def preview_statement_upload(
    account_id: UUID = Form(...),
    file: UploadFile = File(...),
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    """Upload and parse a supported statement into review without posting transactions."""
    filename = (file.filename or "statement").strip()
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in {"csv", "pdf", "txt", "png", "jpg", "jpeg", "webp"}:
        raise HTTPException(status_code=415, detail="Upload a CSV, PDF, TXT, PNG, JPEG or WebP statement.")
    upload_limit = get_settings().max_import_upload_bytes
    if upload_limit < 1:
        raise HTTPException(status_code=503, detail="Statement uploads are not configured.")
    raw = await file.read(upload_limit + 1)
    if len(raw) > upload_limit:
        raise HTTPException(
            status_code=413,
            detail=f"Statement exceeds the configured {upload_limit}-byte upload limit.",
        )
    account = _scoped_account(db, ctx.household.id, account_id)
    try:
        extraction_method = "csv" if suffix == "csv" else "text"
        if suffix in {"pdf", "png", "jpg", "jpeg", "webp"}:
            rows, extraction_method = await run_in_threadpool(parse_statement_document, raw, suffix)
            source = "statement"
        else:
            content = raw.decode("utf-8-sig")
            source = "csv" if suffix == "csv" else "statement"
            from app.services.import_adapters import get_adapter

            rows = get_adapter(source).parse(content)
        job = stage_import_rows(
            db, ctx.household, account, rows, source=source, filename=filename
        )
        job.result = {**(job.result or {}), "extraction_method": extraction_method}
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if suffix in {"pdf", "png", "jpg", "jpeg", "webp"}:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        raise
    db.commit()
    db.refresh(job)
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
