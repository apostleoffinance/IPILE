from uuid import UUID

from sqlalchemy.orm import Session

from app.models.public import SupportTicket
from app.services.audit import write_audit


def create_ticket(
    db: Session,
    *,
    user_id: UUID,
    household_id: UUID | None,
    subject: str,
    body: str,
) -> SupportTicket:
    ticket = SupportTicket(
        user_id=user_id,
        household_id=household_id,
        subject=subject.strip(),
        body=body.strip(),
        status="open",
    )
    db.add(ticket)
    db.flush()
    write_audit(
        db,
        household_id=household_id,
        user_id=user_id,
        action="create",
        entity_type="support_ticket",
        entity_id=ticket.id,
        detail={"subject": ticket.subject},
    )
    return ticket


def list_tickets(db: Session, user_id: UUID) -> list[SupportTicket]:
    return (
        db.query(SupportTicket)
        .filter(SupportTicket.user_id == user_id)
        .order_by(SupportTicket.created_at.desc())
        .all()
    )
