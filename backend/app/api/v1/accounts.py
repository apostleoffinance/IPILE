from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.account import Account
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate
from app.services.balances import snapshot_balance

router = APIRouter(prefix="/accounts", tags=["accounts"])
ACCOUNT_TYPES = {"bank", "savings", "cash", "wallet", "investment", "business", "credit", "other"}


def _accounts(db: Session, household_id: UUID):
    return db.query(Account).filter(
        Account.household_id == household_id,
        Account.deleted_at.is_(None),
    )


@router.get("", response_model=list[AccountOut])
def list_accounts(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return _accounts(db, ctx.household.id).order_by(Account.created_at).all()


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.type not in ACCOUNT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid account type.")
    opening = Decimal(payload.current_balance)
    include_sts = False if payload.type == "business" else payload.include_in_safe_to_spend
    account = Account(
        household_id=ctx.household.id,
        name=payload.name,
        type=payload.type,
        currency=payload.currency,
        institution=payload.institution,
        owner_member_id=payload.owner_member_id,
        business_id=payload.business_id,
        current_balance=opening,
        available_balance=opening,
        is_protected=payload.is_protected,
        is_emergency=payload.is_emergency,
        include_in_safe_to_spend=include_sts,
        include_in_net_worth=payload.include_in_net_worth,
        status="active",
    )
    db.add(account)
    db.flush()
    snapshot_balance(db, account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountOut)
def get_account(
    account_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    account = _accounts(db, ctx.household.id).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account


@router.patch("/{account_id}", response_model=AccountOut)
def update_account(
    account_id: UUID,
    payload: AccountUpdate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    account = _accounts(db, ctx.household.id).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account
