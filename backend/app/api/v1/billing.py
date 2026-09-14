from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.schemas.public import BillingChange, BillingOut
from app.services.billing import billing_snapshot, change_plan

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("", response_model=BillingOut)
def get_billing(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    return billing_snapshot(ctx.household)


@router.post("/plan", response_model=BillingOut)
def post_billing_plan(
    payload: BillingChange,
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    try:
        change_plan(db, ctx.household, user_id=ctx.user.id, plan=payload.plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(ctx.household)
    return billing_snapshot(ctx.household)
