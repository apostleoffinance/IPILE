from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.schemas.safe_to_spend import PurchaseCheckIn, PurchaseCheckOut, SafeToSpendOut
from app.services.safe_to_spend import compute_safe_to_spend, run_purchase_check

router = APIRouter(tags=["safe-to-spend"])


@router.get("/safe-to-spend", response_model=SafeToSpendOut)
def get_safe_to_spend(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return compute_safe_to_spend(db, ctx.household)


@router.post("/purchase-checks", response_model=PurchaseCheckOut)
def create_purchase_check(
    payload: PurchaseCheckIn,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner", "member")),
    db: Session = Depends(get_db),
):
    return run_purchase_check(
        db,
        ctx.household,
        payload.amount,
        category_id=payload.category_id,
        account_id=payload.account_id,
    )
