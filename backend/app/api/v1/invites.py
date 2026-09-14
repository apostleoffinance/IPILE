from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_current_user, get_db, require_roles
from app.models.user import User
from app.schemas.member import MemberOut
from app.schemas.public import InviteAccept, InviteCreate, InviteOut
from app.services.invites import (
    InviteError,
    accept_invite,
    create_invite,
    list_invites,
    revoke_invite,
)

router = APIRouter(prefix="/invites", tags=["invites"])


@router.get("", response_model=list[InviteOut])
def get_invites(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    return list_invites(db, ctx.household.id)


@router.post("", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def post_invite(
    payload: InviteCreate,
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    try:
        invite = create_invite(
            db,
            household=ctx.household,
            invited_by=ctx.user,
            email=str(payload.email),
            role=payload.role,
        )
    except InviteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(invite)
    return invite


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invite(
    invite_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    try:
        revoke_invite(db, ctx.household.id, invite_id, user_id=ctx.user.id)
    except InviteError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    return None


@router.post("/accept", response_model=MemberOut)
def post_accept_invite(
    payload: InviteAccept,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        member = accept_invite(db, user, payload.token)
    except InviteError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(member)
    return member
