from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.automation import Notification


def sync_notifications_from_alerts(db: Session, household_id: UUID) -> list[Notification]:
    alerts = (
        db.query(Alert)
        .filter(Alert.household_id == household_id, Alert.status == "open")
        .order_by(Alert.created_at.desc())
        .all()
    )
    created: list[Notification] = []
    for alert in alerts:
        existing = (
            db.query(Notification)
            .filter(
                Notification.household_id == household_id,
                Notification.alert_id == alert.id,
                Notification.channel == "in_app",
            )
            .first()
        )
        if existing is not None:
            continue
        row = Notification(
            household_id=household_id,
            alert_id=alert.id,
            channel="in_app",
            title=alert.title,
            body=alert.body,
            severity=alert.severity,
            status="unread",
        )
        db.add(row)
        created.append(row)
    db.flush()
    return created


def list_notifications(
    db: Session, household_id: UUID, *, unread_only: bool = False
) -> list[Notification]:
    query = db.query(Notification).filter(Notification.household_id == household_id)
    if unread_only:
        query = query.filter(Notification.status == "unread")
    return query.order_by(Notification.created_at.desc()).all()


def mark_notification_read(db: Session, row: Notification) -> Notification:
    row.status = "read"
    row.read_at = datetime.now(UTC)
    db.add(row)
    db.flush()
    if row.alert_id:
        alert = db.get(Alert, row.alert_id)
        if alert is not None and alert.status == "open":
            alert.status = "read"
            db.add(alert)
    return row
