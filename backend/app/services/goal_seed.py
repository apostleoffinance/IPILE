from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.goal import Goal
from app.models.household import Household
from app.money import quantize_money
from app.services.goal_engine import resolve_status
from app.services.goals import ensure_goal_account

SEED_GOALS = (
    {
        "name": "Family emergency reserve",
        "type": "emergency",
        "target_amount": Decimal("150000.00"),
        "current_amount": Decimal("0.00"),
        "deadline": None,
        "monthly_contribution": Decimal("150000.00"),
        "priority": 2,
        "link_account": "Emergency savings",
    },
    {
        "name": "Future relocation",
        "type": "relocation",
        "target_amount": Decimal("8000000.00"),
        "current_amount": Decimal("2100000.00"),
        "deadline": date(2027, 6, 30),
        "monthly_contribution": None,
        "priority": 1,
        "link_account": None,
    },
    {
        "name": "Long-term wealth",
        "type": "other",
        "target_amount": Decimal("200000.00"),
        "current_amount": Decimal("0.00"),
        "deadline": None,
        "monthly_contribution": Decimal("200000.00"),
        "priority": 3,
        "link_account": "Investments",
    },
)


def _account(db: Session, household_id, name: str) -> Account | None:
    return (
        db.query(Account)
        .filter(
            Account.household_id == household_id,
            Account.name == name,
            Account.deleted_at.is_(None),
        )
        .first()
    )


def seed_goals(db: Session, household: Household) -> None:
    for spec in SEED_GOALS:
        existing = (
            db.query(Goal)
            .filter(
                Goal.household_id == household.id,
                Goal.name == spec["name"],
                Goal.deleted_at.is_(None),
            )
            .first()
        )
        if existing is not None:
            continue
        linked = _account(db, household.id, spec["link_account"]) if spec["link_account"] else None
        current = quantize_money(spec["current_amount"])
        target = quantize_money(spec["target_amount"])
        goal = Goal(
            household_id=household.id,
            name=spec["name"],
            type=spec["type"],
            target_amount=target,
            current_amount=current,
            deadline=spec["deadline"],
            monthly_contribution=spec["monthly_contribution"],
            priority=spec["priority"],
            funding_source_account_id=None,
            account_id=linked.id if linked else None,
            status=resolve_status(current, target, "active"),
        )
        db.add(goal)
        db.flush()
        if linked is None:
            ensure_goal_account(db, goal)
    db.flush()
