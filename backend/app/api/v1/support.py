from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.household import Household
from app.models.member import HouseholdMember
from app.models.user import User
from app.schemas.public import SupportTicketCreate, SupportTicketOut
from app.services.support import create_ticket, list_tickets

router = APIRouter(prefix="/support", tags=["support"])


def _optional_household_id(
    db: Session,
    user: User,
    x_household_id: str | None,
) -> None | object:
    query = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.deleted_at.is_(None),
    )
    if x_household_id:
        from uuid import UUID

        try:
            hid = UUID(x_household_id)
        except ValueError:
            return None
        member = query.filter(HouseholdMember.household_id == hid).first()
    else:
        member = query.first()
    if member is None:
        return None
    household = db.get(Household, member.household_id)
    if household is None or household.deleted_at is not None:
        return None
    return household.id


@router.get("/tickets", response_model=list[SupportTicketOut])
def get_tickets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_tickets(db, user.id)


@router.post("/tickets", response_model=SupportTicketOut, status_code=status.HTTP_201_CREATED)
def post_ticket(
    payload: SupportTicketCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_household_id: str | None = Header(default=None, alias="X-Household-Id"),
):
    household_id = _optional_household_id(db, user, x_household_id)
    ticket = create_ticket(
        db,
        user_id=user.id,
        household_id=household_id,  # type: ignore[arg-type]
        subject=payload.subject,
        body=payload.body,
    )
    db.commit()
    db.refresh(ticket)
    return ticket
