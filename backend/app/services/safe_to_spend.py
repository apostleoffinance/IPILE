from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget, BudgetCategory
from app.models.fund import FundContribution, SinkingFund
from app.models.household import Household
from app.models.obligation import Obligation, ObligationOccurrence
from app.models.recurring import RecurringTransaction
from app.models.transaction import Transaction
from app.money import quantize_money
from app.schemas.safe_to_spend import PurchaseCheckOut, SafeToSpendComponents, SafeToSpendOut
from app.services.allocations import (
    compute_allocation,
    expected_income,
    period_bounds,
    recognized_income,
)
from app.services.balances import OUTFLOW_TYPES
from app.services.budgets import category_spent
from app.services.obligation_engine import add_months
from app.services.safe_to_spend_engine import (
    current_safe_to_spend,
    forecast_safe_to_spend,
    period_safe_to_spend,
)
from app.services.safe_to_spend_engine import (
    purchase_check as evaluate_purchase,
)

LIQUID_TYPES = frozenset({"bank", "cash", "wallet"})
OPEN_OCCURRENCE = frozenset({"upcoming", "due", "missed"})
FORECAST_DAYS = 90


def counts_toward_current_sts(account: Account) -> bool:
    if account.status != "active":
        return False
    if account.type not in LIQUID_TYPES:
        return False
    if getattr(account, "business_id", None) is not None:
        return bool(account.include_in_safe_to_spend)
    return bool(account.include_in_safe_to_spend)


def _accounts(db: Session, household_id: UUID) -> list[Account]:
    return (
        db.query(Account)
        .filter(Account.household_id == household_id, Account.deleted_at.is_(None))
        .all()
    )


def liquid_cash(accounts: list[Account]) -> Decimal:
    total = Decimal("0.00")
    for account in accounts:
        if not counts_toward_current_sts(account):
            continue
        total += Decimal(str(account.available_balance))
    return quantize_money(total)


def protected_in_spendable(accounts: list[Account], funds: list[SinkingFund]) -> Decimal:
    spendable_ids = {
        account.id
        for account in accounts
        if counts_toward_current_sts(account)
    }
    total = Decimal("0.00")
    for account in accounts:
        if account.id in spendable_ids and account.is_protected:
            total += Decimal(str(account.available_balance))
    for fund in funds:
        if not fund.is_protected or fund.status != "active" or fund.deleted_at is not None:
            continue
        if fund.account_id in spendable_ids:
            total += Decimal(str(fund.current_amount))
    return quantize_money(total)


def protected_savings(accounts: list[Account], funds: list[SinkingFund]) -> Decimal:
    total = Decimal("0.00")
    for account in accounts:
        if account.status != "active":
            continue
        if account.is_protected or not account.include_in_safe_to_spend:
            if account.type in {"savings", "investment"} or account.is_protected:
                total += Decimal(str(account.available_balance))
    counted_accounts = {
        account.id
        for account in accounts
        if account.status == "active"
        and (account.is_protected or not account.include_in_safe_to_spend)
        and (account.type in {"savings", "investment"} or account.is_protected)
    }
    for fund in funds:
        if not fund.is_protected or fund.status != "active" or fund.deleted_at is not None:
            continue
        if fund.account_id in counted_accounts:
            continue
        total += Decimal(str(fund.current_amount))
    return quantize_money(total)


def unfunded_occurrences(
    db: Session,
    household_id: UUID,
    start: date,
    end: date,
) -> tuple[Decimal, list[ObligationOccurrence]]:
    rows = (
        db.query(ObligationOccurrence)
        .filter(
            ObligationOccurrence.household_id == household_id,
            ObligationOccurrence.status.in_(tuple(OPEN_OCCURRENCE)),
            ObligationOccurrence.due_date >= start,
            ObligationOccurrence.due_date <= end,
        )
        .all()
    )
    total = Decimal("0.00")
    open_rows: list[ObligationOccurrence] = []
    for row in rows:
        gap = quantize_money(Decimal(str(row.amount)) - Decimal(str(row.funded_amount)))
        if gap > 0:
            total += gap
            open_rows.append(row)
    return quantize_money(total), open_rows


def pending_outbound(db: Session, household_id: UUID) -> Decimal:
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household_id,
            Transaction.deleted_at.is_(None),
            Transaction.status == "pending",
            Transaction.type.in_(tuple(OUTFLOW_TYPES)),
        )
        .all()
    )
    return quantize_money(sum((Decimal(str(row.amount)) for row in rows), Decimal("0.00")))


def upcoming_bills(db: Session, household_id: UUID, start: date, end: date) -> Decimal:
    rows = (
        db.query(RecurringTransaction)
        .filter(
            RecurringTransaction.household_id == household_id,
            RecurringTransaction.deleted_at.is_(None),
            RecurringTransaction.is_active.is_(True),
            RecurringTransaction.type.in_(("expense", "giving")),
            RecurringTransaction.next_date >= start,
            RecurringTransaction.next_date <= end,
        )
        .all()
    )
    return quantize_money(sum((Decimal(str(row.amount)) for row in rows), Decimal("0.00")))


def fund_contribution_remaining(
    db: Session,
    funds: list[SinkingFund],
    start: date,
    end: date,
    skip_ids: set[UUID],
) -> Decimal:
    total = Decimal("0.00")
    for fund in funds:
        if fund.id in skip_ids:
            continue
        if fund.status != "active" or fund.deleted_at is not None or not fund.is_protected:
            continue
        required = quantize_money(Decimal(str(fund.monthly_contribution)))
        posted = (
            db.query(FundContribution)
            .filter(
                FundContribution.fund_id == fund.id,
                FundContribution.date >= start,
                FundContribution.date <= end,
            )
            .all()
        )
        contributed = sum((Decimal(str(row.amount)) for row in posted), Decimal("0.00"))
        gap = required - quantize_money(contributed)
        if gap > 0:
            total += gap
    return quantize_money(total)


def remaining_mandatory_allocations(
    db: Session,
    household: Household,
    recognized: Decimal,
    remaining_expected: Decimal,
    today: date,
) -> Decimal:
    if remaining_expected <= 0:
        (_, _), current = compute_allocation(db, household, today=today)
        return quantize_money(
            sum(
                (line.requested - line.amount for line in current.unfunded_mandatory),
                Decimal("0.00"),
            )
        )
    (_, _), full = compute_allocation(
        db,
        household,
        today=today,
        income_override=quantize_money(recognized + remaining_expected),
    )
    (_, _), current = compute_allocation(db, household, today=today)
    funded = {line.rule_id: line.amount for line in current.lines}
    leftover = Decimal("0.00")
    for line in full.lines:
        if not line.mandatory:
            continue
        already = funded.get(line.rule_id, Decimal("0.00"))
        gap = line.amount - already
        if gap > 0:
            leftover += gap
    return quantize_money(leftover)


def expected_in_horizon(
    monthly_expected: Decimal,
    remaining_this_period: Decimal,
    period_start: date,
    horizon: date,
) -> Decimal:
    extra = Decimal("0.00")
    cursor = add_months(period_start, 1)
    while cursor <= horizon:
        extra += monthly_expected
        cursor = add_months(cursor, 1)
    return quantize_money(remaining_this_period + extra)


def compute_safe_to_spend(
    db: Session,
    household: Household,
    *,
    today: date | None = None,
    horizon_days: int = FORECAST_DAYS,
) -> SafeToSpendOut:
    today = today or date.today()
    start, end = period_bounds(household, today)
    horizon = today + timedelta(days=horizon_days)
    accounts = _accounts(db, household.id)
    funds = (
        db.query(SinkingFund)
        .filter(SinkingFund.household_id == household.id, SinkingFund.deleted_at.is_(None))
        .all()
    )
    liquid = liquid_cash(accounts)
    protected_held = protected_in_spendable(accounts, funds)
    pending = pending_outbound(db, household.id)
    due_now, _ = unfunded_occurrences(db, household.id, date(1970, 1, 1), today)
    current = current_safe_to_spend(liquid, due_now, pending, protected_held)

    recognized = recognized_income(db, household.id, start, end)
    monthly_expected = expected_income(db, household.id)
    remaining_expected = max(Decimal("0.00"), monthly_expected - recognized)
    (_, _), allocation = compute_allocation(db, household, today=today)
    skip_funds = {
        line.destination_id
        for line in allocation.lines
        if line.destination_type == "fund" and line.destination_id is not None
    }
    skip_obligations = {
        line.destination_id
        for line in allocation.lines
        if line.destination_type == "obligation" and line.destination_id is not None
    }
    remaining_mandatory = remaining_mandatory_allocations(
        db, household, recognized, remaining_expected, today
    )
    period_unfunded, period_rows = unfunded_occurrences(db, household.id, today, end)
    period_unfunded = _exclude_obligation_destinations(
        db, period_rows, skip_obligations, period_unfunded
    )
    remaining_funds = fund_contribution_remaining(db, funds, start, end, skip_funds)
    bills_period = upcoming_bills(db, household.id, today, end)
    period = period_safe_to_spend(
        current,
        remaining_expected,
        remaining_mandatory,
        period_unfunded,
        remaining_funds,
    )
    period = quantize_money(period - bills_period)

    horizon_unfunded, horizon_rows = unfunded_occurrences(db, household.id, today, horizon)
    horizon_unfunded = _exclude_obligation_destinations(
        db, horizon_rows, skip_obligations, horizon_unfunded
    )
    horizon_funds = fund_contribution_remaining(db, funds, today, horizon, skip_funds)
    horizon_bills = upcoming_bills(db, household.id, today, horizon)
    expected_horizon = expected_in_horizon(monthly_expected, remaining_expected, start, horizon)
    projected_liquid = quantize_money(liquid - protected_held - pending + expected_horizon)
    projected_commitments = quantize_money(horizon_unfunded + horizon_funds + horizon_bills)
    buffer = quantize_money(Decimal(str(household.minimum_buffer_amount)))
    forecast = forecast_safe_to_spend(projected_liquid, projected_commitments, buffer)

    return SafeToSpendOut(
        currency=household.base_currency,
        current=current,
        period=period,
        forecast=forecast,
        horizon_days=horizon_days,
        minimum_buffer_amount=buffer,
        components=SafeToSpendComponents(
            liquid_cash=liquid,
            expected_income=remaining_expected,
            committed_obligations=due_now,
            upcoming_bills=bills_period,
            sinking_fund_requirements=remaining_funds,
            protected_savings=protected_savings(accounts, funds),
            pending_transactions=pending,
        ),
    )


def _exclude_obligation_destinations(
    db: Session,
    rows: list[ObligationOccurrence],
    skip_obligation_ids: set[UUID],
    total: Decimal,
) -> Decimal:
    if not skip_obligation_ids:
        return total
    reduced = total
    for row in rows:
        if row.obligation_id not in skip_obligation_ids:
            continue
        obligation = db.get(Obligation, row.obligation_id)
        if obligation is None:
            continue
        gap = quantize_money(Decimal(str(row.amount)) - Decimal(str(row.funded_amount)))
        if gap > 0:
            reduced -= gap
    return quantize_money(max(Decimal("0.00"), reduced))


def category_would_exceed(
    db: Session,
    household_id: UUID,
    category_id: UUID,
    amount: Decimal,
    start: date,
    end: date,
) -> bool:
    lines = (
        db.query(BudgetCategory, Budget)
        .join(Budget, Budget.id == BudgetCategory.budget_id)
        .filter(
            Budget.household_id == household_id,
            Budget.deleted_at.is_(None),
            Budget.status == "active",
            Budget.member_id.is_(None),
            Budget.start_date <= end,
            Budget.end_date >= start,
            BudgetCategory.category_id == category_id,
        )
        .all()
    )
    if not lines:
        return False
    for line, budget in lines:
        spent = category_spent(
            db,
            household_id=household_id,
            category_id=category_id,
            start_date=budget.start_date,
            end_date=budget.end_date,
            member_id=budget.member_id,
        )
        remaining = quantize_money(Decimal(str(line.allocated_amount))) - spent
        if amount > remaining:
            return True
    return False


def run_purchase_check(
    db: Session,
    household: Household,
    amount: Decimal,
    *,
    category_id: UUID | None = None,
    account_id: UUID | None = None,
    today: date | None = None,
) -> PurchaseCheckOut:
    today = today or date.today()
    start, end = period_bounds(household, today)
    sts = compute_safe_to_spend(db, household, today=today)
    raids_protected = False
    if account_id is not None:
        account = (
            db.query(Account)
            .filter(
                Account.id == account_id,
                Account.household_id == household.id,
                Account.deleted_at.is_(None),
            )
            .first()
        )
        if account is not None and (account.is_protected or not account.include_in_safe_to_spend):
            raids_protected = True
    budget_exceeded = False
    if category_id is not None:
        budget_exceeded = category_would_exceed(db, household.id, category_id, amount, start, end)
    result = evaluate_purchase(
        amount,
        Decimal(str(sts.current)),
        Decimal(str(household.minimum_buffer_amount)),
        budget_exceeded=budget_exceeded,
        raids_protected=raids_protected,
    )
    affected: list[str] = []
    if raids_protected:
        affected.append("protected_account")
    return PurchaseCheckOut(
        amount=result.amount,
        affordable=result.affordable,
        severity=result.severity,
        remaining_current_sts=result.remaining_current_sts,
        obligations_affected=affected,
        buffer_breached=result.buffer_breached,
        recommended_action=result.recommended_action,
    )
