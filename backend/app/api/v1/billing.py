from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.schemas.public import BillingChange, BillingOut
from app.services.audit import write_audit
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


@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def billing_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_billing_secret: str | None = Header(default=None, alias="X-Billing-Secret"),
) -> dict[str, Any]:
    """PSP-ready stub. Verify shared secret; audit the event; return 202.

    Wire Paystack/Stripe signature verification here later — see docs/BILLING.md.
    """
    secret = (get_settings().billing_webhook_secret or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing webhook is not configured.",
        )
    if not x_billing_secret or x_billing_secret != secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid billing secret.",
        )

    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {"raw": str(payload)}

    event_type = str(payload.get("event") or payload.get("type") or "billing.webhook")
    write_audit(
        db,
        household_id=None,
        user_id=None,
        action="webhook",
        entity_type="billing",
        entity_id=str(payload.get("id") or payload.get("reference") or ""),
        detail={
            "event": event_type,
            "provider": payload.get("provider"),
            "keys": list(payload.keys()),
        },
    )
    db.commit()
    return {"status": "accepted", "event": event_type}
