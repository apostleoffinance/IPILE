import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.models.account import Account
from app.models.imports import ImportJob, ImportMailbox
from app.schemas.imports import ImportBody, ImportJobOut
from app.services.email_imports import parse_bank_alert
from app.services.import_adapters import ImportRow
from app.services.imports import apply_import_rows, run_import

router = APIRouter(prefix="/imports", tags=["imports"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class ImportApprovalBody(BaseModel):
    account_id: UUID


def _mailbox_address(token: str) -> str:
    domain = get_settings().inbound_email_domain.strip().lower()
    if not domain:
        raise HTTPException(status_code=503, detail="Inbound email domain is not configured.")
    return f"bank-alert+{token}@{domain}"


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
    if suffix not in {"csv", "pdf", "txt"}:
        raise HTTPException(status_code=415, detail="Upload a CSV, PDF, or TXT statement.")
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > min(MAX_UPLOAD_BYTES, get_settings().max_import_upload_bytes):
        raise HTTPException(status_code=413, detail="Statement exceeds the 10 MB upload limit.")
    try:
        if suffix == "pdf":
            reader = PdfReader(BytesIO(raw), strict=True)
            if reader.is_encrypted:
                raise ValueError("Password-protected PDFs are not supported.")
            content = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not content.strip():
                raise ValueError("No selectable text found. Scanned PDFs are not supported yet.")
            source = "statement"
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
        if suffix == "pdf":
            raise HTTPException(status_code=400, detail="Could not read this PDF statement.") from exc
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
    return {"address": _mailbox_address(token), "enabled": True, "note": "Store this address privately. Regenerating it invalidates the previous address."}


@router.post("/inbound-email", status_code=status.HTTP_202_ACCEPTED)
def receive_inbound_email(
    payload: dict,
    x_inbound_email_secret: str | None = Header(default=None, alias="X-Inbound-Email-Secret"),
    db: Session = Depends(get_db),
):
    configured_secret = get_settings().inbound_email_webhook_secret
    if not configured_secret or not x_inbound_email_secret or not hmac.compare_digest(
        configured_secret, x_inbound_email_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid inbound email signature.")
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
    sender = str(payload.get("From") or payload.get("from") or payload.get("sender") or "")
    subject = str(payload.get("Subject") or payload.get("subject") or "Bank transaction alert")
    body = str(payload.get("TextBody") or payload.get("text_body") or payload.get("text") or "")
    if not body:
        raise HTTPException(status_code=400, detail="Email contains no plain-text body.")
    try:
        row = parse_bank_alert(sender=sender, subject=subject, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    job = ImportJob(
        household_id=mailbox.household_id,
        source="email",
        filename=subject[:200],
        status="pending_review",
        result={
            "sender": sender[:200],
            "rows": [{
                "date": row.date.isoformat(),
                "amount": str(row.amount),
                "type": row.type,
                "description": row.description,
                "external_id": row.external_id,
                "merchant": row.merchant,
            }],
        },
    )
    mailbox.last_received_at = datetime.now(UTC)
    db.add(job)
    db.add(mailbox)
    db.commit()
    db.refresh(job)
    return {"id": str(job.id), "status": job.status, "message": "Alert received for household review."}


@router.get("/review", response_model=list[ImportJobOut])
def list_import_review(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    return (
        db.query(ImportJob)
        .filter(ImportJob.household_id == ctx.household.id, ImportJob.status == "pending_review")
        .order_by(ImportJob.created_at.desc())
        .limit(100)
        .all()
    )


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
    rows = [
        ImportRow(
            date=datetime.fromisoformat(item["date"]).date(),
            amount=Decimal(item["amount"]),
            type=item["type"],
            description=item.get("description"),
            external_id=item["external_id"],
            merchant=item.get("merchant"),
        )
        for item in job.result.get("rows", [])
    ]
    applied = apply_import_rows(db, ctx.household, account, rows, source="email", filename=job.filename)
    job.status = "approved"
    job.created_count = applied.created_count
    job.skipped_count = applied.skipped_count
    job.error_count = applied.error_count
    job.result = {"sender": job.result.get("sender"), "errors": applied.result.get("errors", [])}
    db.delete(applied)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
