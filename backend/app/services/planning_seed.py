from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget, BudgetCategory
from app.models.category import Category
from app.models.household import Household
from app.models.member import HouseholdMember
from app.models.recurring import RecurringTransaction
from app.services.budgets import current_month_bounds

HOUSEHOLD_LINES = [
    ("Food", Decimal("250000.00")),
    ("Transport", Decimal("100000.00")),
    ("Utilities", Decimal("80000.00")),
    ("Personal", Decimal("140000.00")),
    ("Gifts", Decimal("50000.00")),
    ("Healthcare", Decimal("50000.00")),
]

DEPENDENT_LINES = [
    ("Food", Decimal("40000.00")),
    ("Diapers", Decimal("35000.00")),
    ("Wipes", Decimal("15000.00")),
    ("Healthcare", Decimal("25000.00")),
    ("Clothing", Decimal("20000.00")),
    ("Other", Decimal("15000.00")),
]


def _category(db: Session, household_id, name: str, kind: str = "expense") -> Category:
    row = (
        db.query(Category)
        .filter(
            Category.household_id == household_id,
            Category.name == name,
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if row:
        return row
    row = Category(
        household_id=household_id,
        name=name,
        kind=kind,
        is_system=False,
        sort_order=200,
    )
    db.add(row)
    db.flush()
    return row


def seed_planning(db: Session, household: Household) -> None:
    existing = (
        db.query(Budget)
        .filter(Budget.household_id == household.id, Budget.deleted_at.is_(None))
        .first()
    )
    if existing:
        _seed_recurring(db, household)
        return

    start, end = current_month_bounds()
    household_budget = Budget(
        household_id=household.id,
        name="Household essentials",
        period_type="monthly",
        start_date=start,
        end_date=end,
        member_id=None,
        status="active",
    )
    db.add(household_budget)
    db.flush()
    for name, amount in HOUSEHOLD_LINES:
        kind = "giving" if name == "Gifts" else "expense"
        category = _category(db, household.id, name, kind)
        db.add(
            BudgetCategory(
                household_id=household.id,
                budget_id=household_budget.id,
                category_id=category.id,
                allocated_amount=amount,
            )
        )

    dependent = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.household_id == household.id,
            HouseholdMember.member_type == "dependent",
            HouseholdMember.deleted_at.is_(None),
        )
        .first()
    )
    if dependent is None:
        _seed_recurring(db, household)
        return
    member_budget = Budget(
        household_id=household.id,
        name=f"{dependent.display_name} budget",
        period_type="monthly",
        start_date=start,
        end_date=end,
        member_id=dependent.id,
        status="active",
    )
    db.add(member_budget)
    db.flush()
    for name, amount in DEPENDENT_LINES:
        category = _category(db, household.id, name)
        db.add(
            BudgetCategory(
                household_id=household.id,
                budget_id=member_budget.id,
                category_id=category.id,
                allocated_amount=amount,
            )
        )
    _seed_recurring(db, household)


def _seed_recurring(db: Session, household: Household) -> None:
    existing = (
        db.query(RecurringTransaction)
        .filter(
            RecurringTransaction.household_id == household.id,
            RecurringTransaction.deleted_at.is_(None),
        )
        .first()
    )
    if existing:
        return
    account = (
        db.query(Account)
        .filter(
            Account.household_id == household.id,
            Account.name == "Household current",
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        return
    utilities = _category(db, household.id, "Utilities")
    db.add(
        RecurringTransaction(
            household_id=household.id,
            account_id=account.id,
            category_id=utilities.id,
            amount=Decimal("40000.00"),
            currency="NGN",
            type="expense",
            frequency="monthly",
            next_date=date.today(),
            merchant="Utility company",
            description="Monthly utilities",
            is_active=True,
        )
    )
