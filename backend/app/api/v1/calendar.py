from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.schemas.calendar import CalendarEventOut
from app.services.calendar_events import build_calendar_events
from app.services.finance_access import has_member_permission

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=list[CalendarEventOut])
def list_calendar(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=730),
):
    if ctx.role in {"owner", "partner"}:
        return build_calendar_events(db, ctx.household.id, days=days)
    if ctx.role == "member":
        return build_calendar_events(
            db,
            ctx.household.id,
            days=days,
            member_id=ctx.member.id,
            include_all_obligations=has_member_permission(ctx, "view_all_obligations"),
        )
    raise HTTPException(status_code=403, detail="Insufficient permissions.")
