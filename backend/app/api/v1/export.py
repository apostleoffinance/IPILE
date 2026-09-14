from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.rate_limit import enforce_rate_limit
from app.services.audit import write_audit
from app.services.export import build_household_export

router = APIRouter(tags=["export"])


@router.get("/export")
def export_household(
    request: Request,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        f"export:{ctx.user.id}:{ctx.household.id}",
        limit=5,
        window_seconds=60,
    )
    payload = build_household_export(db, ctx.household)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="export",
        entity_type="household",
        entity_id=ctx.household.id,
        detail={
            "transaction_count": len(payload["transactions"]),
            "account_count": len(payload["accounts"]),
            "client": request.client.host if request.client else None,
        },
    )
    db.commit()
    return JSONResponse(content=payload)
