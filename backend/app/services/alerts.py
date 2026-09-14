from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alert import Alert


def upsert_alert(
    db: Session,
    *,
    household_id: UUID,
    alert_type: str,
    severity: str,
    title: str,
    body: str,
    related_entity_type: str,
    related_entity_id: UUID,
    period_key: str,
) -> Alert:
    existing = (
        db.query(Alert)
        .filter(
            Alert.household_id == household_id,
            Alert.type == alert_type,
            Alert.related_entity_id == related_entity_id,
            Alert.period_key == period_key,
        )
        .first()
    )
    if existing:
        existing.severity = severity
        existing.title = title
        existing.body = body
        existing.status = "open"
        db.add(existing)
        return existing
    alert = Alert(
        household_id=household_id,
        type=alert_type,
        severity=severity,
        title=title,
        body=body,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        period_key=period_key,
        status="open",
    )
    db.add(alert)
    return alert


def resolve_alert(
    db: Session,
    *,
    household_id: UUID,
    alert_type: str,
    related_entity_id: UUID,
    period_key: str,
) -> None:
    existing = (
        db.query(Alert)
        .filter(
            Alert.household_id == household_id,
            Alert.type == alert_type,
            Alert.related_entity_id == related_entity_id,
            Alert.period_key == period_key,
            Alert.status == "open",
        )
        .first()
    )
    if existing:
        existing.status = "resolved"
        db.add(existing)
