from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.schemas.calendar import CalendarEventOut
from app.services.calendar_events import build_calendar_events

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=list[CalendarEventOut])
def list_calendar(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=730),
):
    return build_calendar_events(db, ctx.household.id, days=days)
