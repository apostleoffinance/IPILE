import hashlib
from datetime import UTC, datetime, time
from datetime import date as Date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.models.account import Account
from app.models.receipt import ReceiptDocument
from app.models.transaction import Transaction
from app.services.import_adapters import ImportRow
from app.services.imports import apply_import_rows
from app.services.receipt_ocr import extract_receipt

router = APIRouter(prefix="/receipts", tags=["receipts"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


class ReceiptCorrectionBody(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    date: Date | None = None
    merchant: str | None = Field(default=None, max_length=200)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


def _out(receipt: ReceiptDocument) -> dict:
    return {
        "id": str(receipt.id),
        "account_id": str(receipt.account_id),
        "filename": receipt.filename,
        "media_type": receipt.media_type,
        "status": receipt.status,
        "merchant": receipt.merchant,
        "date": receipt.receipt_date.date().isoformat() if receipt.receipt_date else None,
        "amount": str(receipt.amount) if receipt.amount is not None else None,
        "currency": receipt.currency,
        "extracted": receipt.extracted,
        "transaction_id": str(receipt.transaction_id) if receipt.transaction_id else None,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None,
    }


@router.post("/preview", status_code=status.HTTP_201_CREATED)
async def preview_receipt(
    account_id: UUID = Form(...),
    file: UploadFile = File(...),
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.household_id == ctx.household.id,
        Account.deleted_at.is_(None),
        Account.access_scope == "shared",
    ).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Shared household account not found.")
    limit = get_settings().max_import_upload_bytes
    if limit < 1:
        raise HTTPException(status_code=503, detail="Receipt uploads are not configured.")
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(
            status_code=413,
            detail=f"Receipt exceeds the {limit}-byte upload limit.",
        )
    media_type = file.content_type or ""
    if media_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, WEBP image or PDF.")
    signatures = {
        "application/pdf": content.startswith(b"%PDF-"),
        "image/jpeg": content.startswith(b"\xff\xd8\xff"),
        "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
    }
    if media_type in signatures and not signatures[media_type]:
        raise HTTPException(status_code=400, detail="File content does not match its media type.")
    digest = hashlib.sha256(content).hexdigest()
    existing = db.query(ReceiptDocument).filter(
        ReceiptDocument.household_id == ctx.household.id,
        ReceiptDocument.content_sha256 == digest,
    ).first()
    if existing:
        return _out(existing)
    try:
        extracted = extract_receipt(content, media_type)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    parsed_date = Date.fromisoformat(extracted["date"]) if extracted.get("date") else None
    amount = Decimal(extracted["amount"]) if extracted.get("amount") else None
    currency = extracted.get("currency") or account.currency or ctx.household.base_currency
    receipt = ReceiptDocument(
        household_id=ctx.household.id,
        account_id=account.id,
        filename=(file.filename or "receipt")[:200],
        media_type=media_type,
        content_sha256=digest,
        status="pending_review",
        extracted=extracted,
        amount=amount,
        currency=currency,
        merchant=extracted.get("merchant"),
        receipt_date=(
            datetime.combine(parsed_date, time.min, tzinfo=UTC) if parsed_date else None
        ),
    )
    db.add(receipt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.query(ReceiptDocument).filter(
            ReceiptDocument.household_id == ctx.household.id,
            ReceiptDocument.content_sha256 == digest,
        ).first()
        if duplicate is None:
            raise
        return _out(duplicate)
    db.refresh(receipt)
    return _out(receipt)


@router.get("", response_model=list[dict])
def list_receipts(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ReceiptDocument)
        .filter(ReceiptDocument.household_id == ctx.household.id)
        .order_by(ReceiptDocument.created_at.desc())
        .limit(100)
        .all()
    )
    return [_out(row) for row in rows]


@router.patch("/{receipt_id}")
def correct_receipt(
    receipt_id: UUID,
    payload: ReceiptCorrectionBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    receipt = db.query(ReceiptDocument).filter(
        ReceiptDocument.id == receipt_id,
        ReceiptDocument.household_id == ctx.household.id,
    ).with_for_update().first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    if receipt.status != "pending_review":
        raise HTTPException(status_code=409, detail="Only pending receipts can be corrected.")
    changes = payload.model_dump(exclude_unset=True)
    if "amount" in changes:
        receipt.amount = changes["amount"]
    if "date" in changes:
        value = changes["date"]
        receipt.receipt_date = (
            datetime.combine(value, time.min, tzinfo=UTC) if value else None
        )
    if "merchant" in changes:
        receipt.merchant = changes["merchant"]
    if "currency" in changes:
        receipt.currency = changes["currency"].upper() if changes["currency"] else None
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return _out(receipt)


@router.post("/{receipt_id}/approve")
def approve_receipt(
    receipt_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    receipt = db.query(ReceiptDocument).filter(
        ReceiptDocument.id == receipt_id,
        ReceiptDocument.household_id == ctx.household.id,
    ).with_for_update().first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    if receipt.status != "pending_review":
        raise HTTPException(status_code=409, detail="Receipt is no longer awaiting review.")
    if receipt.amount is None or receipt.receipt_date is None:
        raise HTTPException(
            status_code=422,
            detail="Receipt needs a manually confirmed amount and date.",
        )
    account = db.query(Account).filter(
        Account.id == receipt.account_id,
        Account.household_id == ctx.household.id,
        Account.deleted_at.is_(None),
        Account.access_scope == "shared",
    ).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Shared household account not found.")
    if receipt.currency != (account.currency or ctx.household.base_currency):
        raise HTTPException(
            status_code=422,
            detail="Receipt currency does not match the selected account.",
        )
    external_id = f"receipt:{receipt.content_sha256}"
    existing = db.query(Transaction).filter(
        Transaction.household_id == ctx.household.id,
        Transaction.external_id == external_id,
        Transaction.deleted_at.is_(None),
    ).first()
    if existing:
        receipt.status = "duplicate"
        receipt.transaction_id = existing.id
        db.add(receipt)
        db.commit()
        db.refresh(receipt)
        return _out(receipt)
    row = ImportRow(
        date=receipt.receipt_date.date(),
        amount=receipt.amount,
        type="expense",
        description=f"Receipt: {receipt.merchant or receipt.filename or 'Purchase'}",
        external_id=external_id,
        merchant=receipt.merchant,
    )
    applied = apply_import_rows(
        db, ctx.household, account, [row], source="receipt_ocr", filename=receipt.filename
    )
    if applied.created_count != 1 or applied.error_count:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Receipt transaction could not be posted safely.",
        )
    tx = db.query(Transaction).filter(
        Transaction.household_id == ctx.household.id,
        Transaction.external_id == external_id,
        Transaction.deleted_at.is_(None),
    ).first()
    receipt.status = "approved"
    receipt.transaction_id = tx.id if tx else None
    db.add(receipt)
    db.delete(applied)
    db.commit()
    db.refresh(receipt)
    return _out(receipt)


@router.post("/{receipt_id}/reject")
def reject_receipt(
    receipt_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    receipt = db.query(ReceiptDocument).filter(
        ReceiptDocument.id == receipt_id,
        ReceiptDocument.household_id == ctx.household.id,
    ).with_for_update().first()
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    if receipt.status != "pending_review":
        raise HTTPException(status_code=409, detail="Receipt is no longer awaiting review.")
    receipt.status = "rejected"
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return _out(receipt)
