from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.allocation import AllocationRule
from app.schemas.allocation import AllocationRuleCreate, AllocationRuleOut, AllocationRunOut
from app.services.allocations import (
    ensure_period_allocation,
    latest_run,
    serialize_rule,
    serialize_run,
    validate_rule_payload,
)
from app.services.audit import write_audit

router = APIRouter(tags=["allocations"])


@router.get("/allocation-rules", response_model=list[AllocationRuleOut])
def list_allocation_rules(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(AllocationRule)
        .filter(
            AllocationRule.household_id == ctx.household.id,
            AllocationRule.deleted_at.is_(None),
        )
        .order_by(AllocationRule.priority, AllocationRule.created_at)
        .all()
    )
    return [serialize_rule(row) for row in rows]


@router.post(
    "/allocation-rules",
    response_model=AllocationRuleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_allocation_rule(
    payload: AllocationRuleCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    rate, amount = validate_rule_payload(
        rule_type=payload.type,
        basis=payload.basis,
        destination_type=payload.destination_type,
        rate=payload.rate,
        amount=payload.amount,
    )
    rule = AllocationRule(
        household_id=ctx.household.id,
        name=payload.name,
        type=payload.type,
        basis=payload.basis,
        rate=rate,
        amount=amount,
        priority=payload.priority,
        mandatory=payload.mandatory,
        destination_type=payload.destination_type,
        destination_id=payload.destination_id,
        income_source_id=payload.income_source_id,
        is_active=payload.is_active,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
    )
    db.add(rule)
    db.flush()
    ensure_period_allocation(db, ctx.household)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="create",
        entity_type="allocation_rule",
        entity_id=rule.id,
        detail={"name": rule.name, "type": rule.type, "priority": rule.priority},
    )
    db.commit()
    db.refresh(rule)
    return serialize_rule(rule)


@router.post("/allocations/run", response_model=AllocationRunOut)
def run_allocation(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    run = ensure_period_allocation(db, ctx.household)
    db.commit()
    return serialize_run(db, run)


@router.get("/allocations/latest", response_model=AllocationRunOut)
def get_latest_allocation(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    run = latest_run(db, ctx.household.id)
    if run is None:
        run = ensure_period_allocation(db, ctx.household)
        db.commit()
    return serialize_run(db, run)
