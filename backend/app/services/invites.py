from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.household import Household
from app.models.member import HouseholdMember
from app.models.public import HouseholdInvite
from app.models.user import User
from app.services.audit import write_audit

INVITE_ROLES = frozenset({"partner", "member", "viewer"})
INVITE_DAYS = 14


class InviteError(ValueError):
    pass


def create_invite(
    db: Session,
    *,
    household: Household,
    invited_by: User,
    email: str,
    role: str,
) -> HouseholdInvite:
    email = email.lower().strip()
    if role not in INVITE_ROLES:
        raise InviteError("Invalid invite role.")
    existing_member = (
        db.query(HouseholdMember)
        .join(User, User.id == HouseholdMember.user_id)
        .filter(
            HouseholdMember.household_id == household.id,
            HouseholdMember.deleted_at.is_(None),
            func.lower(User.email) == email,
        )
        .first()
    )
    if existing_member:
        raise InviteError("User is already a household member.")
    pending = (
        db.query(HouseholdInvite)
        .filter(
            HouseholdInvite.household_id == household.id,
            HouseholdInvite.email == email,
            HouseholdInvite.status == "pending",
        )
        .first()
    )
    if pending:
        pending.role = role
        pending.expires_at = datetime.now(UTC) + timedelta(days=INVITE_DAYS)
        pending.invited_by_user_id = invited_by.id
        db.add(pending)
        db.flush()
        return pending
    invite = HouseholdInvite(
        household_id=household.id,
        email=email,
        role=role,
        invited_by_user_id=invited_by.id,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(days=INVITE_DAYS),
    )
    db.add(invite)
    db.flush()
    write_audit(
        db,
        household_id=household.id,
        user_id=invited_by.id,
        action="create",
        entity_type="invite",
        entity_id=invite.id,
        detail={"email": email, "role": role},
    )
    return invite


def list_invites(db: Session, household_id: UUID) -> list[HouseholdInvite]:
    return (
        db.query(HouseholdInvite)
        .filter(
            HouseholdInvite.household_id == household_id,
            HouseholdInvite.status == "pending",
        )
        .order_by(HouseholdInvite.created_at.desc())
        .all()
    )


def revoke_invite(db: Session, household_id: UUID, invite_id: UUID, *, user_id: UUID) -> None:
    invite = (
        db.query(HouseholdInvite)
        .filter(
            HouseholdInvite.id == invite_id,
            HouseholdInvite.household_id == household_id,
        )
        .first()
    )
    if invite is None:
        raise InviteError("Invite not found.")
    invite.status = "revoked"
    db.add(invite)
    write_audit(
        db,
        household_id=household_id,
        user_id=user_id,
        action="delete",
        entity_type="invite",
        entity_id=invite.id,
        detail={"email": invite.email},
    )
    db.flush()


def accept_invite(db: Session, user: User, token: str) -> HouseholdMember:
    invite = db.query(HouseholdInvite).filter(HouseholdInvite.token == token).first()
    if invite is None:
        raise InviteError("Invite not found.")
    if invite.status != "pending":
        raise InviteError("Invite is no longer pending.")
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        invite.status = "expired"
        db.add(invite)
        db.flush()
        raise InviteError("Invite has expired.")
    if user.email.lower() != invite.email.lower():
        raise InviteError("Invite email does not match the signed-in user.")
    household = db.get(Household, invite.household_id)
    if household is None or household.deleted_at is not None:
        raise InviteError("Household not found.")
    existing = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household.id,
            HouseholdMember.user_id == user.id,
            HouseholdMember.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        invite.status = "accepted"
        invite.accepted_at = datetime.now(UTC)
        db.add(invite)
        db.flush()
        return existing
    member = HouseholdMember(
        household_id=household.id,
        user_id=user.id,
        display_name=user.display_name,
        role=invite.role,
        relationship="other",
        member_type="adult",
        is_financial_contributor=invite.role in {"partner", "owner"},
    )
    db.add(member)
    invite.status = "accepted"
    invite.accepted_at = datetime.now(UTC)
    db.add(invite)
    db.flush()
    write_audit(
        db,
        household_id=household.id,
        user_id=user.id,
        action="accept",
        entity_type="invite",
        entity_id=invite.id,
        detail={"role": invite.role},
    )
    return member
