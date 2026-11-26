from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    HouseholdContext,
    get_current_user,
    get_db,
    get_household_context,
    require_roles,
)
from app.core.rate_limit import enforce_rate_limit
from app.models.household import Household
from app.models.member import HouseholdMember
from app.models.user import User
from app.schemas.household import (
    HouseholdCreate,
    HouseholdMembershipOut,
    HouseholdOut,
    HouseholdUpdate,
)
from app.schemas.public import OnboardingCreate
from app.services.audit import write_audit
from app.services.currencies import CurrencyError, validate_currency
from app.services.export import soft_delete_household
from app.services.households import create_household_for_owner

router = APIRouter(tags=["households"])


@router.get("/households", response_model=list[HouseholdMembershipOut])
def list_households(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    return [
        HouseholdMembershipOut(
            id=household.id,
            name=household.name,
            role=member.role,
            slug=household.slug,
        )
        for member, household in rows
    ]


@router.post("/households", response_model=HouseholdOut, status_code=status.HTTP_201_CREATED)
def create_household(
    payload: HouseholdCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        base_currency = validate_currency(payload.base_currency)
    except CurrencyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    household, _member = create_household_for_owner(
        db, user, payload.name, base_currency=base_currency, country=payload.country
    )
    db.commit()
    db.refresh(household)
    return household


@router.post(
    "/onboarding/household",
    response_model=HouseholdOut,
    status_code=status.HTTP_201_CREATED,
)
def onboard_household(
    payload: OnboardingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a household for public onboarding (works after seed deletion too)."""
    active = (
        db.query(HouseholdMember)
        .join(Household, Household.id == HouseholdMember.household_id)
        .filter(
            HouseholdMember.user_id == user.id,
            HouseholdMember.deleted_at.is_(None),
            Household.deleted_at.is_(None),
        )
        .count()
    )
    try:
        base_currency = validate_currency(payload.base_currency)
    except CurrencyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    default_buffer = "90000.00" if base_currency == "NGN" else "0.00"
    buffer = Decimal(payload.minimum_buffer_amount or default_buffer)
    household, _member = create_household_for_owner(
        db,
        user,
        payload.name,
        minimum_buffer_amount=buffer,
        base_currency=base_currency,
        country=payload.country,
    )
    write_audit(
        db,
        household_id=household.id,
        user_id=user.id,
        action="create",
        entity_type="household",
        entity_id=household.id,
        detail={"onboarding": True, "prior_active_memberships": active},
    )
    db.commit()
    db.refresh(household)
    return household


@router.get("/households/current", response_model=HouseholdOut)
def current_household(ctx: HouseholdContext = Depends(get_household_context)):
    return ctx.household


@router.patch("/households/current", response_model=HouseholdOut)
def update_household(
    payload: HouseholdUpdate,
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    household = ctx.household
    data = payload.model_dump(exclude_unset=True)
    if "reporting_currency" in data:
        try:
            data["reporting_currency"] = validate_currency(data["reporting_currency"])
        except CurrencyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    for key, value in data.items():
        setattr(household, key, value)
    db.add(household)
    write_audit(
        db,
        household_id=household.id,
        user_id=ctx.user.id,
        action="update",
        entity_type="household",
        entity_id=household.id,
        detail={"fields": sorted(data.keys())},
    )
    db.commit()
    db.refresh(household)
    return household


@router.delete("/households/current", status_code=status.HTTP_204_NO_CONTENT)
def delete_household(
    ctx: HouseholdContext = Depends(require_roles("owner")),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(
        f"delete-household:{ctx.user.id}",
        limit=3,
        window_seconds=300,
    )
    soft_delete_household(db, ctx.household, user_id=ctx.user.id)
    db.commit()
    return None
