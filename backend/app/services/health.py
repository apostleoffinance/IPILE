from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.allocation import AllocationLine, AllocationRule, AllocationRun
from app.models.analytics import FinancialScore
from app.models.budget import Budget
from app.models.category import Category
from app.models.fund import FundContribution, SinkingFund
from app.models.goal import Goal, GoalContribution
from app.models.household import Household
from app.models.obligation import ObligationOccurrence
from app.models.transaction import Transaction
from app.models.wealth import InvestmentTransaction, Liability
from app.money import format_money, quantize_money
from app.services.allocations import period_bounds, recognized_income
from app.services.budgets import serialize_budget
from app.services.health_engine import HealthResult, compute_health
from app.services.wealth import household_net_worth

ACTIVE_TX = ("cleared", "reconciled")
SAVINGS_GOAL_TYPES = frozenset({"savings", "emergency"})
MISSED_LIABILITY = frozenset({"delinquent", "missed", "past_due"})


def _money_input(value: Decimal | int | bool | str) -> Decimal | int | bool | str:
    if isinstance(value, Decimal):
        return format_money(value)
    return value


def serialize_health(result: HealthResult, start: date, end: date) -> dict:
    components = [
        {
            "key": row.key,
            "weight": format_money(row.weight),
            "points": format_money(row.points),
            "inputs": {key: _money_input(value) for key, value in row.inputs.items()},
        }
        for row in result.components
    ]
    return {
        "score": format_money(result.score),
        "label": result.label,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "components": components,
    }


def _run_for_period(db: Session, household_id: UUID, start: date) -> AllocationRun | None:
    return (
        db.query(AllocationRun)
        .filter(AllocationRun.household_id == household_id, AllocationRun.period_start == start)
        .first()
    )


def _lines(db: Session, run: AllocationRun | None) -> list[AllocationLine]:
    if run is None:
        return []
    return db.query(AllocationLine).filter(AllocationLine.run_id == run.id).all()


def _period_surplus(
    db: Session, run: AllocationRun | None, income: Decimal, expenses: Decimal
) -> Decimal:
    if run is None:
        return quantize_money(income - expenses)
    remainder = Decimal("0.00")
    for line in _lines(db, run):
        if line.rule_id is None:
            continue
        rule = db.get(AllocationRule, line.rule_id)
        if rule is not None and rule.type == "remainder":
            remainder += Decimal(str(line.amount))
    return quantize_money(Decimal(str(run.surplus)) + remainder)


def _period_sum(
    db: Session,
    household_id: UUID,
    start: date,
    end: date,
    types: set[str],
) -> Decimal:
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household_id,
            Transaction.type.in_(tuple(types)),
            Transaction.status.in_(ACTIVE_TX),
            Transaction.deleted_at.is_(None),
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .all()
    )
    return quantize_money(sum((Decimal(str(row.amount)) for row in rows), Decimal("0.00")))


def _obligation_coverage(db: Session, household_id: UUID, today: date) -> tuple[Decimal, Decimal]:
    horizon = today + timedelta(days=90)
    rows = (
        db.query(ObligationOccurrence)
        .filter(
            ObligationOccurrence.household_id == household_id,
            ObligationOccurrence.due_date >= today,
            ObligationOccurrence.due_date <= horizon,
            ObligationOccurrence.status.in_(("upcoming", "due", "missed")),
        )
        .all()
    )
    due = Decimal("0.00")
    funded = Decimal("0.00")
    for row in rows:
        amount = quantize_money(Decimal(str(row.amount)))
        due += amount
        funded += min(quantize_money(Decimal(str(row.funded_amount))), amount)
    return quantize_money(funded), quantize_money(due)


def _monthly_essentials(db: Session, household: Household, start: date, end: date) -> Decimal:
    budgets = (
        db.query(Budget)
        .filter(
            Budget.household_id == household.id,
            Budget.deleted_at.is_(None),
            Budget.status == "active",
            Budget.member_id.is_(None),
            Budget.start_date <= end,
            Budget.end_date >= start,
        )
        .all()
    )
    total = Decimal("0.00")
    for budget in budgets:
        total += serialize_budget(db, budget).allocated_total
    return quantize_money(total)


def _budget_discipline(
    db: Session, household: Household, start: date, end: date
) -> tuple[int, int, Decimal, Decimal]:
    budgets = (
        db.query(Budget)
        .filter(
            Budget.household_id == household.id,
            Budget.deleted_at.is_(None),
            Budget.status == "active",
            Budget.start_date <= end,
            Budget.end_date >= start,
        )
        .all()
    )
    ok = 0
    count = 0
    overspend = Decimal("0.00")
    allocated = Decimal("0.00")
    for budget in budgets:
        snapshot = serialize_budget(db, budget)
        for line in snapshot.categories:
            count += 1
            allocated += line.allocated_amount
            if line.spent_amount <= line.allocated_amount:
                ok += 1
            else:
                overspend += line.spent_amount - line.allocated_amount
    return ok, count, quantize_money(overspend), quantize_money(allocated)


def _account_map(db: Session, household_id: UUID) -> dict[UUID, Account]:
    rows = (
        db.query(Account)
        .filter(Account.household_id == household_id, Account.deleted_at.is_(None))
        .all()
    )
    return {row.id: row for row in rows}


def _planned_savings_and_investment(
    db: Session, household_id: UUID, run: AllocationRun | None
) -> tuple[Decimal, Decimal]:
    accounts = _account_map(db, household_id)
    savings = Decimal("0.00")
    investment = Decimal("0.00")
    for line in _lines(db, run):
        amount = quantize_money(Decimal(str(line.amount)))
        if line.destination_type == "fund":
            savings += amount
            continue
        if line.destination_type == "goal" and line.destination_id:
            goal = db.get(Goal, line.destination_id)
            if goal is not None and goal.type in SAVINGS_GOAL_TYPES:
                savings += amount
            continue
        if line.destination_type == "account" and line.destination_id:
            account = accounts.get(line.destination_id)
            if account is None:
                continue
            if account.type == "investment":
                investment += amount
            elif account.is_emergency or account.type == "savings":
                savings += amount
    return quantize_money(savings), quantize_money(investment)


def _fund_account_ids(db: Session, household_id: UUID) -> set[UUID]:
    rows = (
        db.query(SinkingFund)
        .filter(SinkingFund.household_id == household_id, SinkingFund.deleted_at.is_(None))
        .all()
    )
    return {row.account_id for row in rows if row.account_id is not None}


def _goal_account_ids(db: Session, household_id: UUID) -> set[UUID]:
    rows = (
        db.query(Goal)
        .filter(Goal.household_id == household_id, Goal.deleted_at.is_(None))
        .all()
    )
    ids: set[UUID] = set()
    for row in rows:
        if row.account_id:
            ids.add(row.account_id)
    return ids


def _actual_savings(db: Session, household_id: UUID, start: date, end: date) -> Decimal:
    funds = (
        db.query(FundContribution)
        .filter(
            FundContribution.household_id == household_id,
            FundContribution.date >= start,
            FundContribution.date <= end,
        )
        .all()
    )
    total = sum((Decimal(str(row.amount)) for row in funds), Decimal("0.00"))
    goals = (
        db.query(GoalContribution, Goal)
        .join(Goal, Goal.id == GoalContribution.goal_id)
        .filter(
            GoalContribution.household_id == household_id,
            Goal.type.in_(tuple(SAVINGS_GOAL_TYPES)),
            GoalContribution.date >= start,
            GoalContribution.date <= end,
        )
        .all()
    )
    total += sum((Decimal(str(row.amount)) for row, _goal in goals), Decimal("0.00"))
    skip = _fund_account_ids(db, household_id) | _goal_account_ids(db, household_id)
    accounts = _account_map(db, household_id)
    transfers = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household_id,
            Transaction.type == "transfer",
            Transaction.status.in_(ACTIVE_TX),
            Transaction.deleted_at.is_(None),
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.counterparty_account_id.is_not(None),
        )
        .all()
    )
    for row in transfers:
        dest_id = row.counterparty_account_id
        if dest_id is None or dest_id in skip:
            continue
        dest = accounts.get(dest_id)
        if dest is None:
            continue
        if dest.is_emergency or dest.type == "savings":
            total += Decimal(str(row.amount))
    return quantize_money(total)


def _actual_investment(db: Session, household_id: UUID, start: date, end: date) -> Decimal:
    buys = (
        db.query(InvestmentTransaction)
        .filter(
            InvestmentTransaction.household_id == household_id,
            InvestmentTransaction.type == "buy",
            InvestmentTransaction.date >= start,
            InvestmentTransaction.date <= end,
        )
        .all()
    )
    total = sum((Decimal(str(row.amount)) for row in buys), Decimal("0.00"))
    linked = {row.transaction_id for row in buys if row.transaction_id is not None}
    accounts = _account_map(db, household_id)
    transfers = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household_id,
            Transaction.type == "transfer",
            Transaction.status.in_(ACTIVE_TX),
            Transaction.deleted_at.is_(None),
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.counterparty_account_id.is_not(None),
        )
        .all()
    )
    for row in transfers:
        if row.id in linked:
            continue
        dest = accounts.get(row.counterparty_account_id) if row.counterparty_account_id else None
        if dest is not None and dest.type == "investment":
            total += Decimal(str(row.amount))
    return quantize_money(total)


def _missed_debt(db: Session, household_id: UUID) -> bool:
    row = (
        db.query(Liability)
        .filter(
            Liability.household_id == household_id,
            Liability.deleted_at.is_(None),
            Liability.status.in_(tuple(MISSED_LIABILITY)),
        )
        .first()
    )
    return row is not None


def _top_overspend(db: Session, household: Household, start: date, end: date) -> dict | None:
    budgets = (
        db.query(Budget)
        .filter(
            Budget.household_id == household.id,
            Budget.deleted_at.is_(None),
            Budget.status == "active",
            Budget.start_date <= end,
            Budget.end_date >= start,
        )
        .all()
    )
    worst: tuple[str, Decimal] | None = None
    for budget in budgets:
        snapshot = serialize_budget(db, budget)
        for line in snapshot.categories:
            extra = quantize_money(line.spent_amount - line.allocated_amount)
            if extra <= 0:
                continue
            if worst is None or extra > worst[1]:
                worst = (line.category_name, extra)
    if worst is None:
        return None
    return {"category": worst[0], "amount": format_money(worst[1])}


def _spend_by_category(db: Session, household_id: UUID, start: date, end: date) -> list[dict]:
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household_id,
            Transaction.type.in_(("expense", "giving")),
            Transaction.status.in_(ACTIVE_TX),
            Transaction.deleted_at.is_(None),
            Transaction.date >= start,
            Transaction.date <= end,
        )
        .all()
    )
    totals: dict[str, Decimal] = {}
    for row in rows:
        name = "Uncategorized"
        if row.category_id:
            category = db.get(Category, row.category_id)
            if category is not None:
                name = category.name
        totals[name] = quantize_money(totals.get(name, Decimal("0.00")) + Decimal(str(row.amount)))
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return [{"category": name, "amount": format_money(amount)} for name, amount in ordered]


def gather_period_activity(
    db: Session, household: Household, start: date, end: date
) -> dict[str, Decimal]:
    income = recognized_income(db, household.id, start, end)
    expenses = _period_sum(db, household.id, start, end, {"expense"})
    giving = _period_sum(db, household.id, start, end, {"giving"})
    debt_reduction = _period_sum(db, household.id, start, end, {"debt_payment"})
    run = _run_for_period(db, household.id, start)
    surplus = _period_surplus(db, run, income, expenses + giving)
    savings = _actual_savings(db, household.id, start, end)
    investments = _actual_investment(db, household.id, start, end)
    return {
        "income": income,
        "expenses": expenses,
        "giving": giving,
        "debt_reduction": debt_reduction,
        "surplus": surplus,
        "savings": savings,
        "investments": investments,
    }


def compute_household_health(
    db: Session, household: Household, today: date | None = None
) -> tuple[HealthResult, date, date]:
    today = today or date.today()
    start, end = period_bounds(household, today)
    run = _run_for_period(db, household.id, start)
    income = (
        quantize_money(Decimal(str(run.recognized_income)))
        if run is not None
        else recognized_income(db, household.id, start, end)
    )
    activity = gather_period_activity(db, household, start, end)
    surplus = _period_surplus(db, run, income, activity["expenses"] + activity["giving"])
    funded, due = _obligation_coverage(db, household.id, today)
    wealth = household_net_worth(db, household)
    planned_savings, planned_investment = _planned_savings_and_investment(db, household.id, run)
    ok, count, overspend, allocated = _budget_discipline(db, household, start, end)
    result = compute_health(
        recognized_income=income,
        period_surplus=surplus,
        funded_due_90=funded,
        due_90=due,
        emergency_balance=wealth.emergency_fund,
        monthly_essentials=_monthly_essentials(db, household, start, end),
        total_liabilities=wealth.total_liabilities,
        total_assets=wealth.total_assets,
        missed_debt_payment=_missed_debt(db, household.id),
        planned_savings=planned_savings,
        actual_savings=activity["savings"],
        planned_investment=planned_investment,
        actual_investment=activity["investments"],
        categories_ok=ok,
        category_count=count,
        total_overspend=overspend,
        total_allocated=allocated,
    )
    return result, start, end


def upsert_score(
    db: Session,
    household: Household,
    result: HealthResult,
    start: date,
    end: date,
) -> FinancialScore:
    row = (
        db.query(FinancialScore)
        .filter(FinancialScore.household_id == household.id, FinancialScore.period_start == start)
        .first()
    )
    if row is None:
        row = FinancialScore(household_id=household.id, period_start=start)
        db.add(row)
    payload = serialize_health(result, start, end)
    row.period_end = end
    row.score = result.score
    row.label = result.label
    row.components = payload["components"]
    db.add(row)
    db.flush()
    return row


def household_health(db: Session, household: Household, today: date | None = None) -> dict:
    result, start, end = compute_household_health(db, household, today)
    upsert_score(db, household, result, start, end)
    return serialize_health(result, start, end)
