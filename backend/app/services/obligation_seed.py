from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.household import Household
from app.models.obligation import Obligation
from app.services.funds import attach_fund
from app.services.obligation_engine import obligation_monthly
from app.services.obligations import generate_occurrences, obligation_category

UNIVERSITY_DUE = date(2026, 10, 15)
RENT_DUE = date(2027, 1, 15)


def seed_obligations(db: Session, household: Household) -> None:
    existing = (
        db.query(Obligation)
        .filter(Obligation.household_id == household.id, Obligation.deleted_at.is_(None))
        .first()
    )
    if existing:
        return

    obligation_cat = obligation_category(db, household.id)
    university_cat = obligation_category(db, household.id, "University provision")

    stipend = Obligation(
        household_id=household.id,
        name="Parents' stipend",
        amount=Decimal("100000.00"),
        currency="NGN",
        frequency="monthly",
        next_due_date=date(2026, 10, 1),
        priority="high",
        sinking_fund=False,
        auto_allocate=False,
        category_id=obligation_cat.id,
        beneficiary_name="Parents",
        status="active",
    )
    university = Obligation(
        household_id=household.id,
        name="Sibling University Fees",
        amount=Decimal("450000.00"),
        currency="NGN",
        frequency="quarterly",
        next_due_date=UNIVERSITY_DUE,
        priority="critical",
        sinking_fund=True,
        auto_allocate=True,
        category_id=university_cat.id,
        beneficiary_name="Sibling",
        status="active",
    )
    rent = Obligation(
        household_id=household.id,
        name="Parents' rent",
        amount=Decimal("600000.00"),
        currency="NGN",
        frequency="annual",
        next_due_date=RENT_DUE,
        priority="high",
        sinking_fund=True,
        auto_allocate=True,
        category_id=obligation_cat.id,
        beneficiary_name="Parents",
        status="active",
    )
    db.add_all([stipend, university, rent])
    db.flush()
    for row, fund_name in (
        (university, "University fund"),
        (rent, "Parents Rent Fund"),
    ):
        fund = attach_fund(db, row)
        if fund:
            fund.name = fund_name
            fund.monthly_contribution = obligation_monthly(row.amount, row.frequency)
            db.add(fund)
            if fund.account_id:
                account = db.get(Account, fund.account_id)
                if account:
                    account.name = fund_name
                    db.add(account)
    for row in (stipend, university, rent):
        generate_occurrences(db, row)
