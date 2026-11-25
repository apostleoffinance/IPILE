from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.models.account import Account
from app.models.category import Category
from app.schemas.safe_to_spend import PurchaseCheckIn, PurchaseCheckOut, SafeToSpendOut
from app.services.safe_to_spend import compute_safe_to_spend, run_purchase_check

router = APIRouter(tags=["safe-to-spend"])


@router.get("/safe-to-spend", response_model=SafeToSpendOut)
def get_safe_to_spend(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    return compute_safe_to_spend(db, ctx.household)


@router.post("/purchase-checks", response_model=PurchaseCheckOut)
def create_purchase_check(
    payload: PurchaseCheckIn,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.account_id is not None:
        account = db.query(Account).filter(
            Account.id == payload.account_id,
            Account.household_id == ctx.household.id,
            Account.deleted_at.is_(None),
        ).first()
        if account is None:
            raise HTTPException(status_code=404, detail="Account not found.")
    if payload.category_id is not None:
        category = db.query(Category).filter(
            Category.id == payload.category_id,
            Category.household_id == ctx.household.id,
            Category.deleted_at.is_(None),
        ).first()
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found.")
    return run_purchase_check(
        db,
        ctx.household,
        payload.amount,
        category_id=payload.category_id,
        account_id=payload.account_id,
    )
