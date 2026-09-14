from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.api.v1.transactions import create_transaction
from app.models.business import Business, BusinessEmployee
from app.schemas.business import (
    BusinessCreate,
    BusinessEmployeeCreate,
    BusinessEmployeeOut,
    BusinessOut,
    BusinessPnLOut,
    BusinessTxCreate,
)
from app.schemas.transaction import TransactionCreate
from app.services.balances import apply_transaction_effect
from app.services.business_engine import BUSINESS_STATUSES, BUSINESS_TX_TYPES
from app.services.businesses import (
    business_pnl,
    ensure_business_account,
    get_account,
    record_business_tx,
    serialize_business,
    serialize_employee,
    serialize_pnl,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])


def _active(db: Session, household_id: UUID):
    return db.query(Business).filter(
        Business.household_id == household_id,
        Business.deleted_at.is_(None),
    )


def _get(db: Session, household_id: UUID, business_id: UUID) -> Business:
    row = _active(db, household_id).filter(Business.id == business_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Business not found.")
    return row


@router.get("", response_model=list[BusinessOut])
def list_businesses(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = _active(db, ctx.household.id).order_by(Business.name)
    return [serialize_business(db, row) for row in rows]


@router.post("", response_model=BusinessOut, status_code=status.HTTP_201_CREATED)
def create_business(
    payload: BusinessCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.account_id:
        get_account(db, ctx.household.id, payload.account_id)
    business = Business(
        household_id=ctx.household.id,
        name=payload.name,
        type=payload.type,
        account_id=payload.account_id,
        status="active",
    )
    db.add(business)
    db.flush()
    account = ensure_business_account(db, business)
    account.business_id = business.id
    if account.type == "business":
        account.include_in_safe_to_spend = False
    db.add(account)
    db.commit()
    db.refresh(business)
    return serialize_business(db, business)


@router.get("/{business_id}", response_model=BusinessOut)
def get_business(
    business_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return serialize_business(db, _get(db, ctx.household.id, business_id))


@router.get("/{business_id}/pnl", response_model=BusinessPnLOut)
def get_pnl(
    business_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return serialize_pnl(business_pnl(db, _get(db, ctx.household.id, business_id)))


@router.post(
    "/{business_id}/employees",
    response_model=BusinessEmployeeOut,
    status_code=status.HTTP_201_CREATED,
)
def add_employee(
    business_id: UUID,
    payload: BusinessEmployeeCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    business = _get(db, ctx.household.id, business_id)
    row = BusinessEmployee(
        household_id=ctx.household.id,
        business_id=business.id,
        name=payload.name,
        role=payload.role,
        compensation=payload.compensation,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_employee(row)


@router.post("/{business_id}/transactions", response_model=BusinessOut)
def post_transaction(
    business_id: UUID,
    payload: BusinessTxCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.type not in BUSINESS_TX_TYPES:
        raise HTTPException(status_code=400, detail="Invalid business transaction type.")
    business = _get(db, ctx.household.id, business_id)
    if business.status not in BUSINESS_STATUSES:
        raise HTTPException(status_code=400, detail="Business is not active.")
    vault = ensure_business_account(db, business)
    vault.business_id = business.id
    if vault.type == "business":
        vault.include_in_safe_to_spend = False
    household_tx_id = None
    when = payload.date or date.today()
    amount = Decimal(str(payload.amount))

    if payload.type == "capital_contribution":
        if payload.account_id is None:
            raise HTTPException(
                status_code=400,
                detail="Capital contribution needs a household account.",
            )
        source = get_account(db, ctx.household.id, payload.account_id)
        if source.id == vault.id:
            raise HTTPException(status_code=400, detail="Contribute from a household account.")
        household_tx = create_transaction(
            TransactionCreate(
                account_id=source.id,
                counterparty_account_id=vault.id,
                amount=payload.amount,
                type="capital_contribution",
                date=when,
                description=payload.description or f"Capital into {business.name}",
                business_id=business.id,
                status="cleared",
            ),
            ctx,
            db,
        )
        household_tx_id = household_tx.id
    elif payload.type == "withdrawal":
        if payload.account_id is None:
            raise HTTPException(status_code=400, detail="Withdrawal needs a household account.")
        destination = get_account(db, ctx.household.id, payload.account_id)
        if destination.id == vault.id:
            raise HTTPException(status_code=400, detail="Withdraw to a household account.")
        household_tx = create_transaction(
            TransactionCreate(
                account_id=destination.id,
                counterparty_account_id=vault.id,
                amount=payload.amount,
                type="withdrawal",
                date=when,
                description=payload.description or f"Withdrawal from {business.name}",
                business_id=business.id,
                status="cleared",
            ),
            ctx,
            db,
        )
        household_tx_id = household_tx.id
    elif payload.type == "revenue":
        apply_transaction_effect(
            db,
            account=vault,
            counterparty=None,
            tx_type="income",
            amount=amount,
            status="cleared",
        )
    else:
        apply_transaction_effect(
            db,
            account=vault,
            counterparty=None,
            tx_type="expense",
            amount=amount,
            status="cleared",
        )

    record_business_tx(
        db,
        business,
        tx_type=payload.type,
        amount=amount,
        when=when,
        account_id=payload.account_id or vault.id,
        employee_id=payload.employee_id,
        description=payload.description,
        household_transaction_id=household_tx_id,
    )
    db.commit()
    db.refresh(business)
    return serialize_business(db, business)
