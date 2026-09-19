from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.account import Account
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate
from app.services.allocations import ensure_period_allocation
from app.services.audit import write_audit
from app.services.balances import TRANSFER_TYPE, apply_transaction_effect
from app.services.budgets import evaluate_budget_alerts

router = APIRouter(prefix="/transactions", tags=["transactions"])
TX_TYPES = {
    "income",
    "expense",
    "transfer",
    "refund",
    "investment",
    "debt_payment",
    "capital_contribution",
    "withdrawal",
    "giving",
}
TX_STATUSES = {"pending", "cleared", "reconciled", "voided"}


def _scoped_accounts(db: Session, household_id: UUID):
    return db.query(Account).filter(
        Account.household_id == household_id,
        Account.deleted_at.is_(None),
    )


def _get_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
    account = _scoped_accounts(db, household_id).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account


def _authorize_write(ctx: HouseholdContext, member_id: UUID | None) -> UUID | None:
    if ctx.role in {"viewer", "advisor"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    if ctx.role == "member":
        if member_id and member_id != ctx.member.id:
            raise HTTPException(
                status_code=403,
                detail="Members may only record their own transactions.",
            )
        return ctx.member.id
    return member_id


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
    type: str | None = Query(default=None),
    account_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, le=200),
):
    query = db.query(Transaction).filter(
        Transaction.household_id == ctx.household.id,
        Transaction.deleted_at.is_(None),
    )
    if type:
        query = query.filter(Transaction.type == type)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    return query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(limit).all()


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    member_id = _authorize_write(ctx, payload.member_id)
    if payload.type not in TX_TYPES:
        raise HTTPException(status_code=400, detail="Invalid transaction type.")
    if payload.status not in TX_STATUSES or payload.status == "voided":
        raise HTTPException(status_code=400, detail="Invalid transaction status.")
    paired = {TRANSFER_TYPE, "capital_contribution", "withdrawal"}
    if payload.type in paired and not payload.counterparty_account_id:
        raise HTTPException(status_code=400, detail="This type requires a counterparty account.")
    if payload.counterparty_account_id == payload.account_id:
        raise HTTPException(status_code=400, detail="Transfer accounts must be different.")

    account = _get_account(db, ctx.household.id, payload.account_id)
    counterparty = None
    if payload.counterparty_account_id:
        counterparty = _get_account(db, ctx.household.id, payload.counterparty_account_id)

    transaction = Transaction(
        household_id=ctx.household.id,
        account_id=account.id,
        counterparty_account_id=counterparty.id if counterparty else None,
        member_id=member_id,
        amount=payload.amount,
        currency=payload.currency or ctx.household.base_currency,
        type=payload.type,
        category_id=payload.category_id,
        date=payload.date,
        merchant=payload.merchant,
        description=payload.description,
        income_source_id=payload.income_source_id,
        obligation_id=payload.obligation_id,
        fund_id=payload.fund_id,
        goal_id=payload.goal_id,
        business_id=payload.business_id,
        status=payload.status,
        import_source="manual",
    )
    db.add(transaction)
    apply_transaction_effect(
        db,
        account=account,
        counterparty=counterparty,
        tx_type=transaction.type,
        amount=transaction.amount,
        status=transaction.status,
    )
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    if transaction.type == "income" and transaction.status in {"cleared", "reconciled"}:
        from app.services.automation import run_tick

        run_tick(db, ctx.household, tick_type="income_recognized")
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="create",
        entity_type="transaction",
        entity_id=transaction.id,
        detail={"type": transaction.type, "amount": str(transaction.amount)},
    )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.household_id == ctx.household.id,
            Transaction.deleted_at.is_(None),
        )
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.household_id == ctx.household.id,
            Transaction.deleted_at.is_(None),
        )
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    _authorize_write(ctx, payload.member_id or transaction.member_id)
    if ctx.role == "member" and transaction.member_id != ctx.member.id:
        raise HTTPException(status_code=403, detail="Members may only edit their own transactions.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)
    db.add(transaction)
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="update",
        entity_type="transaction",
        entity_id=transaction.id,
        detail={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/{transaction_id}/void", response_model=TransactionOut)
def void_transaction(
    transaction_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.household_id == ctx.household.id,
            Transaction.deleted_at.is_(None),
        )
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    if transaction.status == "voided":
        raise HTTPException(status_code=400, detail="Transaction is already voided.")
    account = _get_account(db, ctx.household.id, transaction.account_id)
    counterparty = None
    if transaction.counterparty_account_id:
        counterparty = _get_account(db, ctx.household.id, transaction.counterparty_account_id)
    apply_transaction_effect(
        db,
        account=account,
        counterparty=counterparty,
        tx_type=transaction.type,
        amount=transaction.amount,
        status=transaction.status,
        reverse=True,
    )
    was_income = transaction.type == "income"
    transaction.status = "voided"
    db.add(transaction)
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    if was_income:
        ensure_period_allocation(db, ctx.household)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="void",
        entity_type="transaction",
        entity_id=transaction.id,
        detail={"type": transaction.type, "amount": str(transaction.amount)},
    )
    db.commit()
    db.refresh(transaction)
    return transaction
