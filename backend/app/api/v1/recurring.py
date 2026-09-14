from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.api.v1.transactions import TX_TYPES, create_transaction
from app.models.account import Account
from app.models.category import Category
from app.models.member import HouseholdMember
from app.models.recurring import RecurringTransaction
from app.schemas.recurring import RecurringCreate, RecurringOut
from app.schemas.transaction import TransactionCreate, TransactionOut
from app.services.recurring import advance_recurring

router = APIRouter(prefix="/recurring", tags=["recurring"])
FREQUENCIES = {"weekly", "biweekly", "monthly", "quarterly", "annual"}


def _templates(db: Session, household_id: UUID):
    return db.query(RecurringTransaction).filter(
        RecurringTransaction.household_id == household_id,
        RecurringTransaction.deleted_at.is_(None),
    )


def _require_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
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


@router.get("", response_model=list[RecurringOut])
def list_recurring(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return _templates(db, ctx.household.id).order_by(RecurringTransaction.next_date).all()


@router.post("", response_model=RecurringOut, status_code=status.HTTP_201_CREATED)
def create_recurring(
    payload: RecurringCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.frequency not in FREQUENCIES:
        raise HTTPException(status_code=400, detail="Invalid frequency.")
    if payload.type not in TX_TYPES:
        raise HTTPException(status_code=400, detail="Invalid transaction type.")
    if payload.type == "transfer" and not payload.counterparty_account_id:
        raise HTTPException(status_code=400, detail="Transfer requires a counterparty account.")
    _require_account(db, ctx.household.id, payload.account_id)
    if payload.counterparty_account_id:
        if payload.counterparty_account_id == payload.account_id:
            raise HTTPException(status_code=400, detail="Transfer accounts must be different.")
        _require_account(db, ctx.household.id, payload.counterparty_account_id)
    if payload.member_id:
        member = (
            db.query(HouseholdMember)
            .filter(
                HouseholdMember.id == payload.member_id,
                HouseholdMember.household_id == ctx.household.id,
                HouseholdMember.deleted_at.is_(None),
            )
            .first()
        )
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found.")
    if payload.category_id:
        category = (
            db.query(Category)
            .filter(
                Category.id == payload.category_id,
                Category.household_id == ctx.household.id,
                Category.deleted_at.is_(None),
            )
            .first()
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found.")
    template = RecurringTransaction(
        household_id=ctx.household.id,
        account_id=payload.account_id,
        counterparty_account_id=payload.counterparty_account_id,
        member_id=payload.member_id,
        category_id=payload.category_id,
        amount=payload.amount,
        currency=payload.currency,
        type=payload.type,
        frequency=payload.frequency,
        next_date=payload.next_date,
        merchant=payload.merchant,
        description=payload.description,
        is_active=True,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.post("/{recurring_id}/post", response_model=TransactionOut)
def post_recurring(
    recurring_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    template = (
        _templates(db, ctx.household.id).filter(RecurringTransaction.id == recurring_id).first()
    )
    if template is None or not template.is_active:
        raise HTTPException(status_code=404, detail="Recurring transaction not found.")
    transaction = create_transaction(
        TransactionCreate(
            account_id=template.account_id,
            amount=template.amount,
            type=template.type,
            date=template.next_date,
            currency=template.currency,
            counterparty_account_id=template.counterparty_account_id,
            member_id=template.member_id,
            category_id=template.category_id,
            merchant=template.merchant,
            description=template.description,
            status="cleared",
        ),
        ctx,
        db,
    )
    db.refresh(template)
    advance_recurring(template)
    db.add(template)
    db.commit()
    db.refresh(template)
    return transaction


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(
    recurring_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    template = (
        _templates(db, ctx.household.id).filter(RecurringTransaction.id == recurring_id).first()
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Recurring transaction not found.")
    template.deleted_at = datetime.now(UTC)
    db.add(template)
    db.commit()
