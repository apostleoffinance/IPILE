from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import hash_session_token, session_expiry
from app.models.household import Household
from app.models.member import HouseholdMember
from app.models.session import SessionToken
from app.models.user import User

READ_ROLES = frozenset({"owner", "partner", "member", "viewer"})
WRITE_ROLES = frozenset({"owner", "partner"})
OWNER_ROLES = frozenset({"owner"})


@dataclass
class HouseholdContext:
    user: User
    household: Household
    member: HouseholdMember
    role: str


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def get_current_user(
    db: Session = Depends(get_db),
    session_token: str | None = Cookie(default=None, alias=get_settings().session_cookie_name),
) -> User:
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    token_hash = hash_session_token(session_token)
    record = db.query(SessionToken).filter(SessionToken.token_hash == token_hash).first()
    now = datetime.now(UTC)
    if (
        record is None
        or record.revoked_at is not None
        or _aware(record.idle_expires_at) < now
        or _aware(record.absolute_expires_at) < now
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    idle, _absolute = session_expiry(now)
    absolute = _aware(record.absolute_expires_at)
    record.idle_expires_at = idle if idle < absolute else absolute
    db.add(record)
    db.commit()

    user = db.get(User, record.user_id)
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return user


def get_household_context(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    x_household_id: str | None = Header(default=None, alias="X-Household-Id"),
) -> HouseholdContext:
    query = db.query(HouseholdMember).filter(
        HouseholdMember.user_id == user.id,
        HouseholdMember.deleted_at.is_(None),
    )
    if x_household_id:
        try:
            household_id = UUID(x_household_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid household id.",
            ) from exc
        member = query.filter(HouseholdMember.household_id == household_id).first()
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this household.",
            )
    else:
        member = query.first()
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No household. Create one first.",
            )

    household = db.get(Household, member.household_id)
    if household is None or household.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found.")
    return HouseholdContext(user=user, household=household, member=member, role=member.role)


def require_roles(*roles: str):
    allowed = frozenset(roles)

    def dependency(ctx: HouseholdContext = Depends(get_household_context)) -> HouseholdContext:
        if ctx.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return ctx

    return dependency
