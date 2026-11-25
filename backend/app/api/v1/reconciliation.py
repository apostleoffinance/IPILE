import hashlib
from datetime import UTC, date as Date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.models.account import Account
from app.models.banking import ReconciliationItem, ReconciliationSession
from app.models.transaction import Transaction
from app.services.import_adapters import CsvImportAdapter, ImportRow
from app.services.imports import apply_import_rows
from app.services.pdf_imports import parse_pdf_statement
from app.services.reconciliation import create_statement_session, refresh_summary

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


class MatchBody(BaseModel):
    transaction_id: UUID


def _account(db: Session, household_id: UUID, account_id: UUID):
    row = db.query(Account).filter(Account.id == account_id, Account.household_id == household_id,
        Account.access_scope == "shared", Account.deleted_at.is_(None)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Shared household account not found.")
    return row


def _candidate_query(db: Session, item: ReconciliationItem):
    used = [row[0] for row in db.query(ReconciliationItem.matched_transaction_id).filter(
        ReconciliationItem.household_id == item.household_id,
        ReconciliationItem.matched_transaction_id.is_not(None)).all()]
    kinds = {"expense": ["expense", "debt_payment", "giving", "investment"],
             "income": ["income", "refund"]}.get(item.type, [item.type])
    query = db.query(Transaction).filter(Transaction.household_id == item.household_id,
        Transaction.account_id == item.account_id, Transaction.amount == item.amount,
        Transaction.currency == item.currency, Transaction.type.in_(kinds),
        Transaction.date >= Date.fromordinal(item.date.toordinal() - 3),
        Transaction.date <= Date.fromordinal(item.date.toordinal() + 3),
        Transaction.status.in_(["cleared", "reconciled"]), Transaction.deleted_at.is_(None))
    if used:
        query = query.filter(~Transaction.id.in_(used))
    return query.limit(25)


def _tx_out(tx):
    if tx is None:
        return None
    return {"id": str(tx.id), "date": tx.date.isoformat(), "amount": str(tx.amount),
        "currency": tx.currency, "type": tx.type, "merchant": tx.merchant, "description": tx.description}


def _item_out(db, item):
    suggested = db.get(Transaction, item.suggested_transaction_id) if item.suggested_transaction_id else None
    matched = db.get(Transaction, item.matched_transaction_id) if item.matched_transaction_id else None
    return {"id": str(item.id), "date": item.date.isoformat(), "amount": str(item.amount),
        "currency": item.currency, "type": item.type, "description": item.description,
        "merchant": item.merchant, "source": item.source, "status": item.status,
        "match_score": str(item.match_score) if item.match_score is not None else None,
        "match_reason": item.match_reason, "suggested_transaction": _tx_out(suggested),
        "matched_transaction": _tx_out(matched)}


def _session_out(db, row, include_items=False):
    result = {"id": str(row.id), "account_id": str(row.account_id), "source": row.source,
        "status": row.status, "statement_start": row.statement_start.isoformat() if row.statement_start else None,
        "statement_end": row.statement_end.isoformat() if row.statement_end else None,
        "opening_balance": str(row.opening_balance) if row.opening_balance is not None else None,
        "closing_balance": str(row.closing_balance) if row.closing_balance is not None else None,
        "calculated_closing_balance": str(row.calculated_closing_balance) if row.calculated_closing_balance is not None else None,
        "balance_difference": str(row.balance_difference) if row.balance_difference is not None else None,
        "total_rows": row.total_rows, "duplicate_rows": row.duplicate_rows,
        "matched_count": row.matched_count, "suggested_count": row.suggested_count,
        "unmatched_count": row.unmatched_count, "conflict_count": row.conflict_count,
        "created_at": row.created_at.isoformat() if row.created_at else None}
    if include_items:
        rows = db.query(ReconciliationItem).filter(ReconciliationItem.session_id == row.id,
            ReconciliationItem.household_id == row.household_id).order_by(ReconciliationItem.date.desc()).all()
        result["items"] = [_item_out(db, item) for item in rows]
    return result


def _ensure_open(db, item):
    row = db.query(ReconciliationSession).filter(ReconciliationSession.id == item.session_id,
        ReconciliationSession.household_id == item.household_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Reconciliation session not found.")
    if row.status != "review":
        raise HTTPException(status_code=409, detail="Reconciliation session is already closed.")
    return row


@router.post("/sessions/preview", status_code=201)
async def preview_statement(account_id: UUID = Form(...), file: UploadFile = File(...),
    opening_balance: Decimal | None = Form(default=None), closing_balance: Decimal | None = Form(default=None),
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    account = _account(db, ctx.household.id, account_id)
    limit = get_settings().max_import_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise HTTPException(status_code=413, detail=f"Statement exceeds the {limit}-byte upload limit.")
    filename, media = (file.filename or "").lower(), (file.content_type or "").lower()
    try:
        if filename.endswith(".pdf") or media == "application/pdf":
            if not content.startswith(b"%PDF-"):
                raise ValueError("Statement file content does not match PDF format.")
            rows = parse_pdf_statement(content)
        else:
            if not (filename.endswith(".csv") or media in {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"}):
                raise ValueError("Upload a CSV or selectable-text PDF bank statement.")
            try:
                raw_text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                raw_text = content.decode("utf-16")
            rows = CsvImportAdapter().parse(raw_text)
        session = create_statement_session(db, household_id=ctx.household.id, member_id=ctx.member.id,
            account=account, rows=rows, opening_balance=opening_balance, closing_balance=closing_balance)
        db.commit()
        db.refresh(session)
    except (ValueError, UnicodeDecodeError) as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _session_out(db, session, True)


@router.get("/sessions", response_model=list[dict])
def list_sessions(ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    rows = db.query(ReconciliationSession).filter(ReconciliationSession.household_id == ctx.household.id).order_by(
        ReconciliationSession.created_at.desc()).limit(100).all()
    return [_session_out(db, row) for row in rows]


@router.get("/sessions/{session_id}")
def get_session(session_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    row = db.query(ReconciliationSession).filter(ReconciliationSession.id == session_id,
        ReconciliationSession.household_id == ctx.household.id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Reconciliation session not found.")
    return _session_out(db, row, True)


@router.get("/items/{item_id}/candidates", response_model=list[dict])
def candidates(item_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    item = db.query(ReconciliationItem).filter(ReconciliationItem.id == item_id,
        ReconciliationItem.household_id == ctx.household.id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Statement item not found.")
    _ensure_open(db, item)
    return [_tx_out(tx) for tx in _candidate_query(db, item).all()]


@router.post("/items/{item_id}/match")
def match_item(item_id: UUID, body: MatchBody, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    item = db.query(ReconciliationItem).filter(ReconciliationItem.id == item_id,
        ReconciliationItem.household_id == ctx.household.id).with_for_update().first()
    if item is None:
        raise HTTPException(status_code=404, detail="Statement item not found.")
    session = _ensure_open(db, item)
    if item.status in {"matched", "posted", "ignored"}:
        raise HTTPException(status_code=409, detail="Statement item has already been resolved.")
    tx = _candidate_query(db, item).filter(Transaction.id == body.transaction_id).first()
    if tx is None:
        raise HTTPException(status_code=422, detail="Selected transaction does not match amount, currency, direction and date.")
    item.matched_transaction_id = item.suggested_transaction_id = tx.id
    item.match_score = Decimal("1.0000")
    item.match_reason = "Manually confirmed by an authorized household member."
    item.status = "matched"
    db.add(item)
    refresh_summary(db, session)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="That ledger transaction is already reconciled.") from exc
    db.refresh(item)
    return _item_out(db, item)


@router.post("/items/{item_id}/post")
def post_item(item_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    item = db.query(ReconciliationItem).filter(ReconciliationItem.id == item_id,
        ReconciliationItem.household_id == ctx.household.id).with_for_update().first()
    if item is None:
        raise HTTPException(status_code=404, detail="Statement item not found.")
    session = _ensure_open(db, item)
    if item.status in {"matched", "posted", "ignored"}:
        raise HTTPException(status_code=409, detail="Statement item has already been resolved.")
    if item.type == "transfer":
        raise HTTPException(status_code=422, detail="Transfers must be matched to an existing transfer pair.")
    account = _account(db, ctx.household.id, item.account_id)
    external_id = "reconciliation:" + hashlib.sha256(f"{item.source}:{item.source_reference}".encode()).hexdigest()
    row = ImportRow(date=item.date, amount=item.amount, type=item.type,
        description=item.description or "Statement transaction", external_id=external_id, merchant=item.merchant)
    applied = apply_import_rows(db, ctx.household, account, [row],
        source="open_banking" if item.source == "mono" else "statement", filename="reconciliation")
    if applied.created_count != 1 or applied.error_count:
        db.rollback()
        raise HTTPException(status_code=409, detail="Statement transaction could not be posted safely.")
    tx = db.query(Transaction).filter(Transaction.household_id == ctx.household.id,
        Transaction.external_id == external_id, Transaction.deleted_at.is_(None)).first()
    if tx is None:
        db.rollback()
        raise HTTPException(status_code=409, detail="Posted transaction could not be verified.")
    item.matched_transaction_id = tx.id
    item.status = "posted"
    item.match_reason = "New ledger transaction created after explicit statement review."
    db.add(item)
    refresh_summary(db, session)
    db.commit()
    db.refresh(item)
    return _item_out(db, item)


@router.post("/items/{item_id}/ignore")
def ignore_item(item_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    item = db.query(ReconciliationItem).filter(ReconciliationItem.id == item_id,
        ReconciliationItem.household_id == ctx.household.id).with_for_update().first()
    if item is None:
        raise HTTPException(status_code=404, detail="Statement item not found.")
    session = _ensure_open(db, item)
    if item.status in {"matched", "posted", "ignored"}:
        raise HTTPException(status_code=409, detail="Statement item has already been resolved.")
    item.status = "ignored"
    item.match_reason = "Ignored by an authorized household member."
    db.add(item)
    refresh_summary(db, session)
    db.commit()
    db.refresh(item)
    return _item_out(db, item)


@router.post("/sessions/{session_id}/complete")
def complete_session(session_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    row = db.query(ReconciliationSession).filter(ReconciliationSession.id == session_id,
        ReconciliationSession.household_id == ctx.household.id).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Reconciliation session not found.")
    if row.status != "review":
        raise HTTPException(status_code=409, detail="Reconciliation session is already closed.")
    refresh_summary(db, row)
    unresolved = db.query(ReconciliationItem.id).filter(ReconciliationItem.session_id == row.id,
        ReconciliationItem.status.in_(["suggested", "unmatched", "conflict"])).count()
    if unresolved:
        raise HTTPException(status_code=409, detail="Resolve or ignore every statement row before completing reconciliation.")
    row.status, row.completed_at = "completed", datetime.now(UTC)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _session_out(db, row)
