from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.member import HouseholdMember
from app.models.user import User
from app.schemas.member import MemberCreate, MemberOut, MemberUpdate
from app.services.audit import write_audit

router = APIRouter(prefix="/members", tags=["members"])
ROLES = {"owner", "partner", "member", "viewer", "advisor"}
RELATIONSHIPS = {"self", "spouse", "child", "parent", "sibling", "other"}
MEMBER_TYPES = {"adult", "dependent"}


def _active_members(db: Session, household_id: UUID):
    return db.query(HouseholdMember).filter(
        HouseholdMember.household_id == household_id,
        HouseholdMember.deleted_at.is_(None),
    )


@router.get("", response_model=list[MemberOut])
def list_members(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return _active_members(db, ctx.household.id).order_by(HouseholdMember.created_at).all()


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberCreate,
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")
    if payload.relationship not in RELATIONSHIPS:
        raise HTTPException(status_code=400, detail="Invalid relationship.")
    if payload.member_type not in MEMBER_TYPES:
        raise HTTPException(status_code=400, detail="Invalid member type.")
    if payload.role == "owner":
        raise HTTPException(status_code=400, detail="A household already has an owner.")

    user_id = payload.user_id
    if payload.email:
        user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        user_id = user.id
    if user_id:
        existing = (
            _active_members(db, ctx.household.id)
            .filter(HouseholdMember.user_id == user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="User is already a household member.")

    member = HouseholdMember(
        household_id=ctx.household.id,
        user_id=user_id,
        display_name=payload.display_name,
        role=payload.role,
        relationship=payload.relationship,
        member_type=payload.member_type,
        date_of_birth=payload.date_of_birth,
        is_financial_contributor=payload.is_financial_contributor,
    )
    db.add(member)
    db.flush()
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="create",
        entity_type="member",
        entity_id=member.id,
        detail={"role": member.role, "display_name": member.display_name},
    )
    db.commit()
    db.refresh(member)
    return member


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(
    member_id: UUID,
    payload: MemberUpdate,
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    member = _active_members(db, ctx.household.id).filter(HouseholdMember.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    data = payload.model_dump(exclude_unset=True)
    if data.get("role") == "owner" and member.role != "owner":
        raise HTTPException(status_code=400, detail="Cannot transfer ownership in this phase.")
    if "role" in data and data["role"] not in ROLES:
        raise HTTPException(status_code=400, detail="Invalid role.")
    for key, value in data.items():
        setattr(member, key, value)
    db.add(member)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="update",
        entity_type="member",
        entity_id=member.id,
        detail={"fields": sorted(data.keys())},
    )
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    member = _active_members(db, ctx.household.id).filter(HouseholdMember.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    if member.role == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove the household owner.")
    member.deleted_at = datetime.now(UTC)
    db.add(member)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="delete",
        entity_type="member",
        entity_id=member.id,
        detail={"display_name": member.display_name},
    )
    db.commit()
