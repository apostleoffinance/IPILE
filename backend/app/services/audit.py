from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def write_audit(
    db: Session,
    *,
    household_id: UUID | None,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | UUID | None = None,
    detail: dict | None = None,
) -> AuditLog:
    row = AuditLog(
        household_id=household_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id),
        detail=detail or {},
    )
    db.add(row)
    db.flush()
    return row
