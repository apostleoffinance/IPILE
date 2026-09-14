from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.goal import Goal, GoalContribution
from app.money import format_money, quantize_money
from app.schemas.goal import GoalOut
from app.services.goal_engine import (
    apply_contribution,
    goal_progress,
    months_left,
    remaining,
    required_monthly,
    resolve_status,
)
from app.services.obligation_engine import coverage_label


def serialize_goal(goal: Goal, today: date | None = None) -> GoalOut:
    today = today or date.today()
    current = quantize_money(Decimal(str(goal.current_amount)))
    target = quantize_money(Decimal(str(goal.target_amount)))
    explicit = (
        quantize_money(Decimal(str(goal.monthly_contribution)))
        if goal.monthly_contribution is not None
        else None
    )
    progress = goal_progress(current, target)
    left = months_left(today, goal.deadline)
    return GoalOut(
        id=goal.id,
        household_id=goal.household_id,
        name=goal.name,
        type=goal.type,
        target_amount=target,
        current_amount=current,
        remaining=remaining(target, current),
        deadline=goal.deadline,
        monthly_contribution=explicit,
        required_monthly=required_monthly(target, current, goal.deadline, today, explicit),
        months_left=left,
        priority=goal.priority,
        funding_source_account_id=goal.funding_source_account_id,
        account_id=goal.account_id,
        progress=format_money(progress),
        percent=int(progress * 100),
        coverage_label=coverage_label(progress),
        status=resolve_status(current, target, goal.status),
    )


def ensure_goal_account(db: Session, goal: Goal) -> Account:
    if goal.account_id:
        account = db.get(Account, goal.account_id)
        if account:
            return account
    account = Account(
        household_id=goal.household_id,
        name=goal.name,
        type="savings",
        currency="NGN",
        current_balance=Decimal("0.00"),
        available_balance=Decimal("0.00"),
        is_protected=True,
        include_in_safe_to_spend=False,
        include_in_net_worth=True,
        is_emergency=goal.type == "emergency",
        status="active",
    )
    db.add(account)
    db.flush()
    goal.account_id = account.id
    db.add(goal)
    return account


def record_contribution(
    db: Session,
    goal: Goal,
    *,
    account_id: UUID,
    amount: Decimal,
    contribution_date: date,
    transaction_id: UUID | None,
) -> GoalContribution:
    goal.current_amount = apply_contribution(Decimal(str(goal.current_amount)), amount)
    goal.status = resolve_status(
        Decimal(str(goal.current_amount)),
        Decimal(str(goal.target_amount)),
        goal.status,
    )
    row = GoalContribution(
        household_id=goal.household_id,
        goal_id=goal.id,
        account_id=account_id,
        amount=quantize_money(amount),
        date=contribution_date,
        transaction_id=transaction_id,
    )
    db.add(row)
    db.add(goal)
    return row
