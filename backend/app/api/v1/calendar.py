from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.models.obligation import Obligation, ObligationOccurrence
from app.money import quantize_money
from app.schemas.calendar import CalendarEventOut
from app.services.obligation_engine import coverage, coverage_label

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=list[CalendarEventOut])
def list_calendar(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=730),
):
    today = date.today()
    end = today + timedelta(days=days)
    rows = (
        db.query(ObligationOccurrence, Obligation)
        .join(Obligation, Obligation.id == ObligationOccurrence.obligation_id)
        .filter(
            ObligationOccurrence.household_id == ctx.household.id,
            Obligation.deleted_at.is_(None),
            ObligationOccurrence.due_date >= today,
            ObligationOccurrence.due_date <= end,
        )
        .order_by(ObligationOccurrence.due_date)
        .all()
    )
    events: list[CalendarEventOut] = []
    for occurrence, obligation in rows:
        ratio = coverage(occurrence.funded_amount, occurrence.amount)
        events.append(
            CalendarEventOut(
                id=occurrence.id,
                kind="obligation",
                title=obligation.name,
                date=occurrence.due_date,
                amount=quantize_money(occurrence.amount),
                status=occurrence.status,
                coverage_label=coverage_label(ratio),
                obligation_id=obligation.id,
                occurrence_id=occurrence.id,
            )
        )
    return events
