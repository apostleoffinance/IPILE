from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.rate_limit import enforce_rate_limit
from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    session_expiry,
    verify_password,
)
from app.models.household import Household
from app.models.member import HouseholdMember
from app.models.session import SessionToken
from app.models.user import User
from app.schemas.auth import HouseholdSummary, LoginRequest, MeOut, RegisterRequest, UserOut
from app.services.households import create_household_for_owner

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = get_settings().session_cookie_name


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_absolute_days * 24 * 60 * 60,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=get_settings().session_cookie_name, path="/")


def _create_session(db: Session, user: User) -> str:
    token = new_session_token()
    idle, absolute = session_expiry()
    db.add(
        SessionToken(
            user_id=user.id,
            token_hash=hash_session_token(token),
            idle_expires_at=idle,
            absolute_expires_at=absolute,
        )
    )
    user.last_login_at = datetime.now(UTC)
    return token


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    enforce_rate_limit(f"register:{request.client.host if request.client else 'unknown'}")
    email = payload.email.lower()
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        status="active",
    )
    db.add(user)
    db.flush()
    if payload.invite_token:
        from app.services.invites import InviteError, accept_invite

        try:
            accept_invite(db, user, payload.invite_token)
        except InviteError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif payload.create_household:
        create_household_for_owner(db, user, f"{payload.display_name}'s household")
    token = _create_session(db, user)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, token)
    return user


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    enforce_rate_limit(f"login:{request.client.host if request.client else 'unknown'}")
    email = payload.email.lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled.")

    token = _create_session(db, user)
    db.commit()
    db.refresh(user)
    _set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    session_token: str | None = Cookie(default=None, alias=COOKIE),
) -> None:
    if session_token:
        token_hash = hash_session_token(session_token)
        record = (
            db.query(SessionToken)
            .filter(SessionToken.user_id == user.id, SessionToken.token_hash == token_hash)
            .first()
        )
        if record and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            db.add(record)
            db.commit()
    _clear_session_cookie(response)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeOut:
    rows = (
        db.query(HouseholdMember, Household)
        .join(Household, Household.id == HouseholdMember.household_id)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.deleted_at.is_(None),
            Household.deleted_at.is_(None),
        )
        .all()
    )
    return MeOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        households=[
            HouseholdSummary(
                id=household.id,
                name=household.name,
                role=member.role,
                slug=household.slug,
            )
            for member, household in rows
        ],
    )
