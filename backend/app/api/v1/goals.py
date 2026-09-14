from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.api.v1.transactions import create_transaction
from app.models.account import Account
from app.models.goal import Goal
from app.schemas.goal import GoalContributionCreate, GoalCreate, GoalOut
from app.schemas.transaction import TransactionCreate
from app.services.goal_engine import GOAL_TYPES, resolve_status
from app.services.goals import ensure_goal_account, record_contribution, serialize_goal
from app.services.obligations import obligation_category

router = APIRouter(prefix="/goals", tags=["goals"])


def _active(db: Session, household_id: UUID):
    return db.query(Goal).filter(Goal.household_id == household_id, Goal.deleted_at.is_(None))


def _get_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
    account = (
        db.query(Account)
        .filter(
            Account.id == account_id,
            Account.household_id == household_id,
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account


@router.get("", response_model=list[GoalOut])
def list_goals(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = _active(db, ctx.household.id).order_by(Goal.priority, Goal.name)
    return [serialize_goal(row) for row in rows]


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.type not in GOAL_TYPES:
        raise HTTPException(status_code=400, detail="Invalid goal type.")
    if payload.funding_source_account_id:
        _get_account(db, ctx.household.id, payload.funding_source_account_id)
    if payload.account_id:
        _get_account(db, ctx.household.id, payload.account_id)
    goal = Goal(
        household_id=ctx.household.id,
        name=payload.name,
        type=payload.type,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        deadline=payload.deadline,
        monthly_contribution=payload.monthly_contribution,
        priority=payload.priority,
        funding_source_account_id=payload.funding_source_account_id,
        account_id=payload.account_id,
        status=resolve_status(
            Decimal(str(payload.current_amount)),
            Decimal(str(payload.target_amount)),
            "active",
        ),
    )
    db.add(goal)
    db.flush()
    ensure_goal_account(db, goal)
    db.commit()
    db.refresh(goal)
    return serialize_goal(goal)


@router.post("/{goal_id}/contributions", response_model=GoalOut)
def contribute(
    goal_id: UUID,
    payload: GoalContributionCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    goal = _active(db, ctx.household.id).filter(Goal.id == goal_id).first()
    if goal is None:
        raise HTTPException(status_code=404, detail="Goal not found.")
    source = _get_account(db, ctx.household.id, payload.account_id)
    destination = ensure_goal_account(db, goal)
    if source.id == destination.id:
        raise HTTPException(status_code=400, detail="Contribute from a different account.")
    when = payload.date or date.today()
    transaction = create_transaction(
        TransactionCreate(
            account_id=source.id,
            counterparty_account_id=destination.id,
            amount=payload.amount,
            type="transfer",
            date=when,
            category_id=obligation_category(db, ctx.household.id).id,
            description=f"Contribution to {goal.name}",
            goal_id=goal.id,
            status="cleared",
        ),
        ctx,
        db,
    )
    record_contribution(
        db,
        goal,
        account_id=source.id,
        amount=payload.amount,
        contribution_date=when,
        transaction_id=transaction.id,
    )
    db.commit()
    db.refresh(goal)
    return serialize_goal(goal)
