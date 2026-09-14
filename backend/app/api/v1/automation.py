from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.automation import Notification
from app.schemas.automation import NotificationOut, TickIn, TickOut
from app.services.automation import run_tick
from app.services.notifications import list_notifications, mark_notification_read

router = APIRouter(tags=["automation"])


@router.post("/automation/tick", response_model=TickOut)
def post_tick(
    payload: TickIn,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    allowed = {"daily", "income_recognized"}
    tick_type = payload.tick_type if payload.tick_type in allowed else "daily"
    tick, skipped = run_tick(
        db, ctx.household, tick_type=tick_type, period_key=payload.period_key
    )
    db.commit()
    db.refresh(tick)
    return TickOut(
        id=tick.id,
        household_id=tick.household_id,
        tick_type=tick.tick_type,
        period_key=tick.period_key,
        status=tick.status,
        result=tick.result or {},
        skipped=skipped,
    )


@router.get("/notifications", response_model=list[NotificationOut])
def get_notifications(
    unread_only: bool = Query(default=False),
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return list_notifications(db, ctx.household.id, unread_only=unread_only)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.household_id == ctx.household.id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    mark_notification_read(db, row)
    db.commit()
    db.refresh(row)
    return row
