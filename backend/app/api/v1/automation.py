import hmac
import logging
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.models.automation import Notification
from app.models.household import Household
from app.schemas.automation import NotificationOut, TickIn, TickOut
from app.services.automation import run_tick
from app.services.notifications import list_notifications, mark_notification_read

router = APIRouter(tags=["automation"])
logger = logging.getLogger("ipile.automation")


@router.post("/automation/cron/daily")
def run_daily_automation_cron(
    x_automation_cron_secret: str | None = Header(
        default=None, alias="X-Automation-Cron-Secret"
    ),
    db: Session = Depends(get_db),
):
    """Run one idempotent daily automation tick for each active household."""
    secret = get_settings().automation_cron_secret
    if (
        not secret
        or not x_automation_cron_secret
        or not hmac.compare_digest(secret, x_automation_cron_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid automation scheduler credentials.")

    households = db.query(Household).filter(Household.deleted_at.is_(None)).all()
    result = {"households": len(households), "processed": 0, "skipped": 0, "failed": 0}
    for household in households:
        try:
            try:
                timezone = ZoneInfo(household.timezone or "UTC")
            except ZoneInfoNotFoundError:
                timezone = ZoneInfo("UTC")
            local_today = datetime.now(UTC).astimezone(timezone).date()
            with db.begin_nested():
                _, skipped = run_tick(
                    db,
                    household,
                    tick_type="daily",
                    period_key=local_today.isoformat(),
                    today=local_today,
                )
                db.flush()
            result["skipped" if skipped else "processed"] += 1
        except Exception:
            logger.exception("daily_automation_failed household_id=%s", household.id)
            result["failed"] += 1
    db.commit()
    return result


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
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    return list_notifications(db, ctx.household.id, unread_only=unread_only)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
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
