from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.models.account import Account
from app.models.goal import Goal
from app.models.obligation import Obligation, ObligationOccurrence
from app.models.transaction import Transaction
from app.money import format_money, quantize_money
from app.schemas.account import AccountOut
from app.schemas.calendar import CalendarEventOut
from app.schemas.household import HouseholdOut
from app.schemas.transaction import TransactionOut
from app.services.allocations import latest_run, serialize_run
from app.services.health import household_health
from app.services.obligation_engine import coverage, coverage_label
from app.services.safe_to_spend import compute_safe_to_spend
from app.services.wealth import household_net_worth

router = APIRouter(tags=["overview"])


@router.get("/overview")
def overview(ctx: HouseholdContext = Depends(get_household_context), db: Session = Depends(get_db)):
    accounts = (
        db.query(Account)
        .filter(Account.household_id == ctx.household.id, Account.deleted_at.is_(None))
        .order_by(Account.created_at)
        .all()
    )
    transactions = (
        db.query(Transaction)
        .filter(Transaction.household_id == ctx.household.id, Transaction.deleted_at.is_(None))
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(10)
        .all()
    )
    today = date.today()
    start = date(today.year, today.month, 1)
    end_day = monthrange(today.year, today.month)[1]
    end = date(today.year, today.month, end_day)
    income_rows = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == ctx.household.id,
            Transaction.type == "income",
            Transaction.status.in_(("cleared", "reconciled")),
            Transaction.deleted_at.is_(None),
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .all()
    )
    cash_accounts = [
        account
        for account in accounts
        if account.type in {"bank", "cash", "wallet", "savings"} and account.status == "active"
    ]
    cash_total = quantize_money(
        sum((Decimal(account.current_balance) for account in cash_accounts), Decimal("0.00"))
    )
    period_income = quantize_money(
        sum((Decimal(row.amount) for row in income_rows), Decimal("0.00"))
    )
    horizon = today + timedelta(days=30)
    upcoming_rows = (
        db.query(ObligationOccurrence, Obligation)
        .join(Obligation, Obligation.id == ObligationOccurrence.obligation_id)
        .filter(
            ObligationOccurrence.household_id == ctx.household.id,
            Obligation.deleted_at.is_(None),
            ObligationOccurrence.due_date >= today,
            ObligationOccurrence.due_date <= horizon,
            ObligationOccurrence.status.in_(("upcoming", "due", "missed")),
        )
        .order_by(ObligationOccurrence.due_date)
        .all()
    )
    upcoming = [
        CalendarEventOut(
            id=occurrence.id,
            kind="obligation",
            title=obligation.name,
            date=occurrence.due_date,
            amount=quantize_money(occurrence.amount),
            status=occurrence.status,
            coverage_label=coverage_label(coverage(occurrence.funded_amount, occurrence.amount)),
            obligation_id=obligation.id,
            occurrence_id=occurrence.id,
        )
        for occurrence, obligation in upcoming_rows
    ]
    run = latest_run(db, ctx.household.id)
    allocation = serialize_run(db, run) if run else None
    allocated_total = allocation.total_allocated if allocation else Decimal("0.00")
    surplus = allocation.surplus if allocation else Decimal("0.00")
    sts = compute_safe_to_spend(db, ctx.household)
    wealth = household_net_worth(db, ctx.household)
    has_baseline = len(accounts) > 0 and (
        len(transactions) > 0
        or period_income > Decimal("0.00")
        or cash_total != Decimal("0.00")
    )
    health = household_health(db, ctx.household) if has_baseline else None
    foundation = {
        "household": True,
        "accounts": len(accounts) > 0,
        "income": period_income > Decimal("0.00")
        or any(row.type == "income" for row in transactions),
        "obligations": len(upcoming) > 0
        or db.query(Obligation)
        .filter(Obligation.household_id == ctx.household.id, Obligation.deleted_at.is_(None))
        .count()
        > 0,
        "budget": run is not None,
        "goals": db.query(Goal)
        .filter(Goal.household_id == ctx.household.id, Goal.deleted_at.is_(None))
        .count()
        > 0,
    }
    completed = sum(1 for value in foundation.values() if value)
    db.commit()
    return {
        "household": HouseholdOut.model_validate(ctx.household),
        "currency": ctx.household.base_currency,
        "cash_total": format_money(cash_total),
        "period_income": format_money(period_income),
        "allocated_total": format_money(allocated_total),
        "surplus": format_money(surplus),
        "allocation": allocation,
        "safe_to_spend": sts,
        "wealth": {
            "net_worth": format_money(wealth.net_worth),
            "investments": format_money(wealth.investments),
            "emergency_fund": format_money(wealth.emergency_fund),
            "debt": format_money(wealth.debt),
        },
        "health": health,
        "health_ready": has_baseline,
        "foundation": {**foundation, "completed": completed, "total": len(foundation)},
        "accounts": [AccountOut.model_validate(account) for account in accounts],
        "recent_transactions": [TransactionOut.model_validate(row) for row in transactions],
        "upcoming_obligations": upcoming,
    }
