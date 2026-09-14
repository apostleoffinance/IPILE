from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.allocation import AllocationRule
from app.models.budget import Budget
from app.models.fund import SinkingFund
from app.models.household import Household
from app.models.obligation import Obligation
from app.services.allocations import ensure_period_allocation


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


def _obligation(db: Session, household_id, name: str) -> Obligation | None:
    return (
        db.query(Obligation)
        .filter(
            Obligation.household_id == household_id,
            Obligation.name == name,
            Obligation.deleted_at.is_(None),
        )
        .first()
    )


def _fund(db: Session, household_id, name: str) -> SinkingFund | None:
    return (
        db.query(SinkingFund)
        .filter(
            SinkingFund.household_id == household_id,
            SinkingFund.name == name,
            SinkingFund.deleted_at.is_(None),
        )
        .first()
    )


def _budget(db: Session, household_id, name: str) -> Budget | None:
    return (
        db.query(Budget)
        .filter(
            Budget.household_id == household_id,
            Budget.name == name,
            Budget.deleted_at.is_(None),
        )
        .first()
    )


def seed_allocation(db: Session, household: Household) -> None:
    existing = (
        db.query(AllocationRule)
        .filter(AllocationRule.household_id == household.id, AllocationRule.deleted_at.is_(None))
        .first()
    )
    if existing:
        ensure_period_allocation(db, household)
        return

    stipend = _obligation(db, household.id, "Parents' stipend")
    university = _fund(db, household.id, "University fund")
    rent = _fund(db, household.id, "Parents Rent Fund")
    essentials = _budget(db, household.id, "Household essentials")
    emergency = _account(db, household.id, "Emergency savings")
    investments = _account(db, household.id, "Investments")
    current = _account(db, household.id, "Household current")

    rows = [
        {
            "name": "Tithe",
            "type": "percentage",
            "basis": "recognized_income",
            "rate": Decimal("0.10"),
            "amount": None,
            "priority": 0,
            "mandatory": True,
            "destination_type": "giving",
            "destination_id": None,
        },
        {
            "name": "Parents' stipend",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("100000.00"),
            "priority": 1,
            "mandatory": True,
            "destination_type": "obligation",
            "destination_id": stipend.id if stipend else None,
        },
        {
            "name": "University fund",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("150000.00"),
            "priority": 2,
            "mandatory": True,
            "destination_type": "fund",
            "destination_id": university.id if university else None,
        },
        {
            "name": "Parents' rent fund",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("50000.00"),
            "priority": 3,
            "mandatory": True,
            "destination_type": "fund",
            "destination_id": rent.id if rent else None,
        },
        {
            "name": "Household essentials",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("670000.00"),
            "priority": 4,
            "mandatory": True,
            "destination_type": "budget",
            "destination_id": essentials.id if essentials else None,
        },
        {
            "name": "Emergency fund",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("150000.00"),
            "priority": 5,
            "mandatory": True,
            "destination_type": "account",
            "destination_id": emergency.id if emergency else None,
        },
        {
            "name": "Investments",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("200000.00"),
            "priority": 6,
            "mandatory": True,
            "destination_type": "account",
            "destination_id": investments.id if investments else None,
        },
        {
            "name": "Personal allowances",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("140000.00"),
            "priority": 7,
            "mandatory": True,
            "destination_type": "budget",
            "destination_id": None,
        },
        {
            "name": "Additional giving",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("50000.00"),
            "priority": 8,
            "mandatory": True,
            "destination_type": "giving",
            "destination_id": None,
        },
        {
            "name": "Buffer",
            "type": "fixed",
            "basis": "recognized_income",
            "rate": None,
            "amount": Decimal("90000.00"),
            "priority": 9,
            "mandatory": True,
            "destination_type": "account",
            "destination_id": current.id if current else None,
        },
        {
            "name": "Family surplus",
            "type": "remainder",
            "basis": "remaining",
            "rate": None,
            "amount": None,
            "priority": 10,
            "mandatory": False,
            "destination_type": "account",
            "destination_id": current.id if current else None,
        },
    ]
    for payload in rows:
        db.add(AllocationRule(household_id=household.id, is_active=True, **payload))
    db.flush()
    ensure_period_allocation(db, household)
