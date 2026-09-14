from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.api.v1.transactions import create_transaction
from app.models.account import Account
from app.models.fund import SinkingFund
from app.models.obligation import Obligation
from app.schemas.fund import FundContributionCreate, FundCreate, FundOut
from app.schemas.transaction import TransactionCreate
from app.services.funds import ensure_fund_account, record_contribution, serialize_fund
from app.services.obligations import generate_occurrences, obligation_category

router = APIRouter(prefix="/funds", tags=["funds"])


def _active(db: Session, household_id: UUID):
    return db.query(SinkingFund).filter(
        SinkingFund.household_id == household_id,
        SinkingFund.deleted_at.is_(None),
    )


def _get_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
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


@router.get("", response_model=list[FundOut])
def list_funds(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = _active(db, ctx.household.id).order_by(SinkingFund.name)
    return [serialize_fund(db, row) for row in rows]


@router.post("", response_model=FundOut, status_code=status.HTTP_201_CREATED)
def create_fund(
    payload: FundCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    obligation = None
    if payload.obligation_id:
        obligation = (
            db.query(Obligation)
            .filter(
                Obligation.id == payload.obligation_id,
                Obligation.household_id == ctx.household.id,
                Obligation.deleted_at.is_(None),
            )
            .first()
        )
        if obligation is None:
            raise HTTPException(status_code=404, detail="Obligation not found.")
    if payload.account_id:
        _get_account(db, ctx.household.id, payload.account_id)
    fund = SinkingFund(
        household_id=ctx.household.id,
        name=payload.name,
        target_amount=payload.target_amount,
        current_amount=0,
        target_date=payload.target_date,
        obligation_id=payload.obligation_id,
        monthly_contribution=payload.monthly_contribution,
        account_id=payload.account_id,
        is_protected=payload.is_protected,
        status="active",
    )
    db.add(fund)
    db.flush()
    ensure_fund_account(db, fund)
    if obligation and not obligation.fund_id:
        obligation.fund_id = fund.id
        obligation.sinking_fund = True
        db.add(obligation)
    db.commit()
    db.refresh(fund)
    return serialize_fund(db, fund)


@router.post("/{fund_id}/contributions", response_model=FundOut)
def contribute(
    fund_id: UUID,
    payload: FundContributionCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    fund = _active(db, ctx.household.id).filter(SinkingFund.id == fund_id).first()
    if fund is None:
        raise HTTPException(status_code=404, detail="Fund not found.")
    source = _get_account(db, ctx.household.id, payload.account_id)
    destination = ensure_fund_account(db, fund)
    if source.id == destination.id:
        raise HTTPException(status_code=400, detail="Contribute from a different account.")
    when = payload.date or date.today()
    category_id = None
    if fund.obligation_id:
        linked = db.get(Obligation, fund.obligation_id)
        category_id = linked.category_id if linked else None
    if category_id is None:
        category_id = obligation_category(db, ctx.household.id).id
    transaction = create_transaction(
        TransactionCreate(
            account_id=source.id,
            counterparty_account_id=destination.id,
            amount=payload.amount,
            type="transfer",
            date=when,
            category_id=category_id,
            description=f"Contribution to {fund.name}",
            fund_id=fund.id,
            obligation_id=fund.obligation_id,
            status="cleared",
        ),
        ctx,
        db,
    )
    record_contribution(
        db,
        fund,
        account_id=source.id,
        amount=payload.amount,
        contribution_date=when,
        transaction_id=transaction.id,
    )
    if fund.obligation_id:
        obligation = db.get(Obligation, fund.obligation_id)
        if obligation:
            generate_occurrences(db, obligation)
    db.commit()
    db.refresh(fund)
    return serialize_fund(db, fund)
