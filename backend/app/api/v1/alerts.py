from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.models.alert import Alert
from app.schemas.alert import AlertOut

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Alert)
        .filter(Alert.household_id == ctx.household.id, Alert.status == "open")
        .order_by(Alert.created_at.desc())
        .all()
    )


@router.post("/{alert_id}/read", response_model=AlertOut)
def read_alert(
    alert_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    alert = (
        db.query(Alert)
        .filter(Alert.id == alert_id, Alert.household_id == ctx.household.id)
        .first()
    )
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    alert.status = "read"
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
