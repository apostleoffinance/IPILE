from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.allocation import AllocationLine, AllocationRun
from app.models.analytics import FinancialSnapshot
from app.models.household import Household
from app.money import format_money
from app.services.allocations import period_bounds
from app.services.analytics import (
    annual_report,
    freeze_current_snapshot,
    giving_report,
    persist_snapshot,
    quarterly_report,
)
from app.services.health import _top_overspend, gather_period_activity
from app.services.health_engine import compute_health

PILOT_YEAR = 2026
LIVE_MONTH_INDEX = 6


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _health(**kwargs) -> dict:
    return kwargs


PILOT_SHOCKS = (
    {
        "month_index": 1,
        "month": 4,
        "shock": "Normal ₦2,000,000 income",
        "activity": {
            "income": Decimal("2000000.00"),
            "expenses": Decimal("1550000.00"),
            "savings": Decimal("350000.00"),
            "investments": Decimal("200000.00"),
            "giving": Decimal("250000.00"),
            "debt_reduction": Decimal("0.00"),
            "surplus": Decimal("200000.00"),
        },
        "net_worth": Decimal("4200000.00"),
        "giving_allocations": [
            {"name": "Giving share", "amount": "200000.00"},
            {"name": "Additional giving", "amount": "50000.00"},
        ],
        "health": _health(
            recognized_income=Decimal("2000000.00"),
            period_surplus=Decimal("200000.00"),
            funded_due_90=Decimal("300000.00"),
            due_90=Decimal("300000.00"),
            emergency_balance=Decimal("450000.00"),
            monthly_essentials=Decimal("670000.00"),
            total_liabilities=Decimal("0.00"),
            total_assets=Decimal("5000000.00"),
            missed_debt_payment=False,
            planned_savings=Decimal("350000.00"),
            actual_savings=Decimal("350000.00"),
            planned_investment=Decimal("200000.00"),
            actual_investment=Decimal("200000.00"),
            categories_ok=12,
            category_count=12,
            total_overspend=Decimal("0.00"),
            total_allocated=Decimal("820000.00"),
        ),
    },
    {
        "month_index": 2,
        "month": 5,
        "shock": "University fees due (₦450,000)",
        "activity": {
            "income": Decimal("2000000.00"),
            "expenses": Decimal("2000000.00"),
            "savings": Decimal("150000.00"),
            "investments": Decimal("200000.00"),
            "giving": Decimal("250000.00"),
            "debt_reduction": Decimal("0.00"),
            "surplus": Decimal("200000.00"),
        },
        "net_worth": Decimal("4100000.00"),
        "giving_allocations": [
            {"name": "Giving share", "amount": "200000.00"},
            {"name": "Additional giving", "amount": "50000.00"},
        ],
        "health": _health(
            recognized_income=Decimal("2000000.00"),
            period_surplus=Decimal("200000.00"),
            funded_due_90=Decimal("450000.00"),
            due_90=Decimal("750000.00"),
            emergency_balance=Decimal("450000.00"),
            monthly_essentials=Decimal("670000.00"),
            total_liabilities=Decimal("0.00"),
            total_assets=Decimal("4900000.00"),
            missed_debt_payment=False,
            planned_savings=Decimal("350000.00"),
            actual_savings=Decimal("150000.00"),
            planned_investment=Decimal("200000.00"),
            actual_investment=Decimal("200000.00"),
            categories_ok=11,
            category_count=12,
            total_overspend=Decimal("40000.00"),
            total_allocated=Decimal("820000.00"),
        ),
    },
    {
        "month_index": 3,
        "month": 6,
        "shock": "Income falls to ₦1,500,000",
        "activity": {
            "income": Decimal("1500000.00"),
            "expenses": Decimal("1500000.00"),
            "savings": Decimal("150000.00"),
            "investments": Decimal("0.00"),
            "giving": Decimal("150000.00"),
            "debt_reduction": Decimal("0.00"),
            "surplus": Decimal("0.00"),
        },
        "net_worth": Decimal("3950000.00"),
        "giving_allocations": [
            {"name": "Giving share", "amount": "150000.00"},
            {"name": "Additional giving", "amount": "0.00"},
        ],
        "health": _health(
            recognized_income=Decimal("1500000.00"),
            period_surplus=Decimal("0.00"),
            funded_due_90=Decimal("400000.00"),
            due_90=Decimal("750000.00"),
            emergency_balance=Decimal("300000.00"),
            monthly_essentials=Decimal("670000.00"),
            total_liabilities=Decimal("0.00"),
            total_assets=Decimal("4700000.00"),
            missed_debt_payment=False,
            planned_savings=Decimal("350000.00"),
            actual_savings=Decimal("150000.00"),
            planned_investment=Decimal("200000.00"),
            actual_investment=Decimal("0.00"),
            categories_ok=10,
            category_count=12,
            total_overspend=Decimal("80000.00"),
            total_allocated=Decimal("820000.00"),
        ),
    },
    {
        "month_index": 4,
        "month": 7,
        "shock": "Income increases to ₦2,800,000",
        "activity": {
            "income": Decimal("2800000.00"),
            "expenses": Decimal("1700000.00"),
            "savings": Decimal("350000.00"),
            "investments": Decimal("200000.00"),
            "giving": Decimal("280000.00"),
            "debt_reduction": Decimal("0.00"),
            "surplus": Decimal("280000.00"),
        },
        "net_worth": Decimal("4500000.00"),
        "giving_allocations": [
            {"name": "Giving share", "amount": "280000.00"},
            {"name": "Additional giving", "amount": "50000.00"},
        ],
        "health": _health(
            recognized_income=Decimal("2800000.00"),
            period_surplus=Decimal("280000.00"),
            funded_due_90=Decimal("600000.00"),
            due_90=Decimal("750000.00"),
            emergency_balance=Decimal("600000.00"),
            monthly_essentials=Decimal("670000.00"),
            total_liabilities=Decimal("0.00"),
            total_assets=Decimal("5400000.00"),
            missed_debt_payment=False,
            planned_savings=Decimal("350000.00"),
            actual_savings=Decimal("350000.00"),
            planned_investment=Decimal("200000.00"),
            actual_investment=Decimal("200000.00"),
            categories_ok=12,
            category_count=12,
            total_overspend=Decimal("0.00"),
            total_allocated=Decimal("820000.00"),
        ),
    },
    {
        "month_index": 5,
        "month": 8,
        "shock": "Parents' rent due (₦600,000)",
        "activity": {
            "income": Decimal("2000000.00"),
            "expenses": Decimal("2150000.00"),
            "savings": Decimal("200000.00"),
            "investments": Decimal("200000.00"),
            "giving": Decimal("250000.00"),
            "debt_reduction": Decimal("0.00"),
            "surplus": Decimal("200000.00"),
        },
        "net_worth": Decimal("4300000.00"),
        "giving_allocations": [
            {"name": "Giving share", "amount": "200000.00"},
            {"name": "Additional giving", "amount": "50000.00"},
        ],
        "health": _health(
            recognized_income=Decimal("2000000.00"),
            period_surplus=Decimal("200000.00"),
            funded_due_90=Decimal("400000.00"),
            due_90=Decimal("900000.00"),
            emergency_balance=Decimal("500000.00"),
            monthly_essentials=Decimal("670000.00"),
            total_liabilities=Decimal("0.00"),
            total_assets=Decimal("5200000.00"),
            missed_debt_payment=False,
            planned_savings=Decimal("350000.00"),
            actual_savings=Decimal("200000.00"),
            planned_investment=Decimal("200000.00"),
            actual_investment=Decimal("200000.00"),
            categories_ok=11,
            category_count=12,
            total_overspend=Decimal("30000.00"),
            total_allocated=Decimal("820000.00"),
        ),
    },
)


def _giving_allocations(db: Session, household: Household, start: date) -> list[dict]:
    run = (
        db.query(AllocationRun)
        .filter(AllocationRun.household_id == household.id, AllocationRun.period_start == start)
        .first()
    )
    if run is None:
        return []
    lines = (
        db.query(AllocationLine)
        .filter(AllocationLine.run_id == run.id, AllocationLine.destination_type == "giving")
        .all()
    )
    return [{"name": line.name, "amount": format_money(line.amount)} for line in lines]


def _seed_historical(db: Session, household: Household, spec: dict) -> None:
    start, end = _month_bounds(PILOT_YEAR, spec["month"])
    existing = (
        db.query(FinancialSnapshot)
        .filter(
            FinancialSnapshot.household_id == household.id,
            FinancialSnapshot.period_start == start,
        )
        .first()
    )
    if existing is not None:
        return
    health = compute_health(**spec["health"])
    persist_snapshot(
        db,
        household,
        start=start,
        end=end,
        as_of=end,
        activity=spec["activity"],
        net_worth=spec["net_worth"],
        health=health,
        extra={
            "shock": spec["shock"],
            "month_index": spec["month_index"],
            "giving_allocations": spec["giving_allocations"],
            "historical": True,
        },
    )


def _seed_live_month(db: Session, household: Household) -> None:
    today = date.today()
    start, end = period_bounds(household, today)
    extra = {
        "shock": "Unexpected ₦300,000 family expense",
        "month_index": LIVE_MONTH_INDEX,
        "historical": False,
        "top_overspend": _top_overspend(db, household, start, end),
        "giving_allocations": _giving_allocations(db, household, start),
        "live_activity": {
            key: format_money(value)
            for key, value in gather_period_activity(db, household, start, end).items()
        },
    }
    freeze_current_snapshot(db, household, today=today, extra=extra)


def seed_analytics(db: Session, household: Household) -> None:
    for spec in PILOT_SHOCKS:
        _seed_historical(db, household, spec)
    _seed_live_month(db, household)
    for quarter in (2, 3):
        quarterly_report(db, household, PILOT_YEAR, quarter)
    annual_report(db, household, PILOT_YEAR)
    giving_report(db, household, PILOT_YEAR)
    db.flush()


def shock_catalog() -> list[dict]:
    rows = [
        {
            "month_index": spec["month_index"],
            "period_start": date(PILOT_YEAR, spec["month"], 1).isoformat(),
            "shock": spec["shock"],
        }
        for spec in PILOT_SHOCKS
    ]
    rows.append(
        {
            "month_index": LIVE_MONTH_INDEX,
            "period_start": date(PILOT_YEAR, 9, 1).isoformat(),
            "shock": "Unexpected ₦300,000 family expense",
        }
    )
    return rows
