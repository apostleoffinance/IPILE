"""Hypothetical scenarios. Never mutates live household balances."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from app.money import quantize_money
from app.services.allocation_engine import AllocationRuleSpec, allocate
from app.services.debt_engine import DebtInput, amortize_strategy
from app.services.obligation_engine import obligation_monthly
from app.services.safe_to_spend_engine import forecast_safe_to_spend


def cash_flow_status(surplus: Decimal, income: Decimal) -> str:
    surplus = quantize_money(surplus)
    income = quantize_money(income)
    if surplus < 0:
        return "critical"
    if income <= 0:
        return "warning"
    if surplus / income < Decimal("0.05"):
        return "warning"
    return "healthy"


def obligation_status(coverage: Decimal, days_until_due: int) -> str:
    coverage = quantize_money(coverage)
    if coverage >= Decimal("1.00"):
        return "funded"
    if coverage < Decimal("0.80") and days_until_due <= 14:
        return "unfunded"
    if coverage <= 0:
        return "unfunded"
    return "at risk"


def emergency_status(months: Decimal) -> str:
    months = quantize_money(months)
    if months < Decimal("0.50"):
        return "critical"
    if months < Decimal("1.00"):
        return "warning"
    return "healthy"


def sts_status(forecast: Decimal, minimum_buffer: Decimal) -> str:
    forecast = quantize_money(forecast)
    buffer = quantize_money(minimum_buffer)
    if forecast < buffer:
        return "critical"
    if forecast < quantize_money(buffer * Decimal("2")):
        return "warning"
    return "healthy"


def investment_status(planned: Decimal, allocated: Decimal) -> str:
    planned = quantize_money(planned)
    allocated = quantize_money(allocated)
    if planned <= 0:
        return "on plan"
    if allocated <= 0:
        return "paused"
    if allocated < planned:
        return "reduced"
    return "on plan"


@dataclass(frozen=True)
class SimObligation:
    id: UUID
    name: str
    amount: Decimal
    frequency: str
    days_until_due: int
    funded_amount: Decimal
    fund_id: UUID | None = None


@dataclass(frozen=True)
class SimCategory:
    id: UUID
    name: str
    allocated: Decimal
    kind: str = "expense"
    remaining: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class SimParams:
    monthly_income: Decimal | None = None
    income_change_rate: Decimal = Decimal("0")
    expense_category_deltas: dict[str, Decimal] | None = None
    obligation_deltas: dict[str, Decimal] | None = None
    investment_override: Decimal | None = None
    unexpected_expense: Decimal | None = None
    contribution_change_rate: Decimal = Decimal("0")
    debt_strategy: str = "avalanche"
    debt_extra_payment: Decimal = Decimal("0.00")
    horizon_months: int = 12


@dataclass(frozen=True)
class SimState:
    cash: Decimal
    emergency: Decimal
    investments: Decimal
    net_worth: Decimal
    expected_income: Decimal
    minimum_buffer: Decimal
    essentials: Decimal
    planned_investment: Decimal
    rules: tuple[AllocationRuleSpec, ...]
    obligations: tuple[SimObligation, ...]
    categories: tuple[SimCategory, ...] = ()
    expected_contributions: Decimal = Decimal("0.00")
    first_month_contributions: Decimal = Decimal("0.00")
    debts: tuple[DebtInput, ...] = ()
    first_month_income: Decimal | None = None
    first_month_essentials: Decimal | None = None


@dataclass(frozen=True)
class MonthProjection:
    month_index: int
    income: Decimal
    contributions: Decimal
    debt_payments: Decimal
    debt_interest: Decimal
    surplus: Decimal
    cash: Decimal
    emergency: Decimal
    investments: Decimal
    net_worth: Decimal
    forecast_sts: Decimal
    cash_flow: str
    obligations: str
    emergency_fund: str
    investments_status: str
    safe_to_spend: str
    net_worth_delta: Decimal


@dataclass(frozen=True)
class SimulationResult:
    months: tuple[MonthProjection, ...]
    summary: MonthProjection


def _delta_for(deltas: dict[str, Decimal] | None, key: str) -> Decimal:
    if not deltas:
        return Decimal("0")
    return Decimal(str(deltas.get(key, Decimal("0"))))


def _scale(amount: Decimal, rate: Decimal) -> Decimal:
    return quantize_money(quantize_money(amount) * (Decimal("1") + rate))


def apply_params(state: SimState, params: SimParams) -> SimState:
    obl_deltas = {
        str(key): Decimal(str(value)) for key, value in (params.obligation_deltas or {}).items()
    }
    cat_deltas = {
        str(key): Decimal(str(value))
        for key, value in (params.expense_category_deltas or {}).items()
    }
    obligations = []
    scaled_ids: set[UUID] = set()
    for row in state.obligations:
        rate = _delta_for(obl_deltas, str(row.id))
        if rate == 0:
            rate = _delta_for(obl_deltas, row.name)
        scaled = replace(row, amount=_scale(row.amount, rate)) if rate else row
        obligations.append(scaled)
        if rate:
            scaled_ids.add(row.id)
            if row.fund_id:
                scaled_ids.add(row.fund_id)
    rules = []
    for rule in state.rules:
        amount = rule.amount
        dest = rule.destination_id
        if amount is not None and dest is not None and dest in scaled_ids:
            rate = Decimal("0")
            for row in state.obligations:
                if dest in {row.id, row.fund_id}:
                    rate = _delta_for(obl_deltas, str(row.id)) or _delta_for(obl_deltas, row.name)
                    break
            amount = _scale(amount, rate)
        if (
            params.investment_override is not None
            and rule.destination_type == "account"
            and amount is not None
            and rule.name.lower().startswith("invest")
        ):
            amount = quantize_money(params.investment_override)
        rules.append(replace(rule, amount=amount) if amount != rule.amount else rule)
    essentials = state.essentials
    first_month_essentials = (
        state.first_month_essentials
        if state.first_month_essentials is not None
        else state.essentials
    )
    categories = []
    for category in state.categories:
        rate = _delta_for(cat_deltas, str(category.id)) or _delta_for(cat_deltas, category.name)
        allocated = _scale(category.allocated, rate) if rate else category.allocated
        remaining = _scale(category.remaining, rate) if rate else category.remaining
        categories.append(replace(category, allocated=allocated, remaining=remaining))
        if rate and category.kind != "income":
            essentials = quantize_money(essentials + (allocated - category.allocated))
            first_month_essentials = quantize_money(
                first_month_essentials + (remaining - category.remaining)
            )
    income = state.expected_income
    first_month_income = (
        state.first_month_income
        if state.first_month_income is not None
        else state.expected_income
    )
    if params.monthly_income is not None:
        income = quantize_money(params.monthly_income)
        first_month_income = income
    income = _scale(income, params.income_change_rate)
    first_month_income = _scale(first_month_income, params.income_change_rate)
    contributions = _scale(state.expected_contributions, params.contribution_change_rate)
    first_month_contributions = _scale(
        state.first_month_contributions,
        params.contribution_change_rate,
    )
    planned = state.planned_investment
    if params.investment_override is not None:
        planned = quantize_money(params.investment_override)
    return replace(
        state,
        expected_income=income,
        expected_contributions=contributions,
        first_month_contributions=first_month_contributions,
        essentials=essentials,
        first_month_essentials=first_month_essentials,
        first_month_income=first_month_income,
        planned_investment=planned,
        rules=tuple(rules),
        obligations=tuple(obligations),
        categories=tuple(categories),
    )


def _coverage(row: SimObligation) -> Decimal:
    if row.amount <= 0:
        return Decimal("1.00")
    return quantize_money(min(Decimal("1.00"), row.funded_amount / row.amount))


def _worst_obligation(rows: tuple[SimObligation, ...]) -> str:
    if not rows:
        return "funded"
    ranks = {"funded": 0, "at risk": 1, "unfunded": 2}
    worst = "funded"
    for row in rows:
        label = obligation_status(_coverage(row), row.days_until_due)
        if ranks[label] > ranks[worst]:
            worst = label
    return worst


def _allocated_investment(lines, planned: Decimal) -> Decimal:
    total = Decimal("0.00")
    for line in lines:
        if line.destination_type == "account" and "invest" in line.name.lower():
            total += line.amount
    if total == 0 and planned:
        # destination_type account without invest in name still counts via planned match
        pass
    return quantize_money(total)



def _months_until_due(days_until_due: int) -> int:
    return max(1, (max(0, days_until_due) + 29) // 30)


def _monthly_obligation_commitment(row: SimObligation, month_index: int) -> Decimal:
    months_to_due = _months_until_due(row.days_until_due)
    remaining = max(Decimal("0.00"), quantize_money(row.amount - row.funded_amount))
    if month_index <= months_to_due:
        return quantize_money(remaining / Decimal(months_to_due))
    if row.frequency == "one_time":
        return Decimal("0.00")
    return obligation_monthly(row.amount, row.frequency)


def _projected_obligations(
    rows: tuple[SimObligation, ...],
    month_index: int,
) -> tuple[SimObligation, ...]:
    projected: list[SimObligation] = []
    period_days = {
        "weekly": 7,
        "monthly": 30,
        "quarterly": 90,
        "annual": 365,
    }
    for row in rows:
        months_to_due = _months_until_due(row.days_until_due)
        remaining = max(Decimal("0.00"), quantize_money(row.amount - row.funded_amount))
        if month_index <= months_to_due:
            reserve = quantize_money(remaining / Decimal(months_to_due))
            funded = min(row.amount, quantize_money(row.funded_amount + reserve * month_index))
            days = max(0, row.days_until_due - month_index * 30)
        elif row.frequency == "one_time":
            funded = row.amount
            days = 0
        else:
            elapsed_after_due = max(0, month_index * 30 - row.days_until_due)
            period = period_days.get(row.frequency, 30)
            days = period - (elapsed_after_due % period)
            if days == 0:
                days = period
            funded = Decimal("0.00")
        projected.append(
            replace(
                row,
                funded_amount=quantize_money(funded),
                days_until_due=days,
            )
        )
    return tuple(projected)


def project(state: SimState, params: SimParams) -> SimulationResult:
    working = apply_params(state, params)
    cash = quantize_money(working.cash)
    emergency = quantize_money(working.emergency)
    investments = quantize_money(working.investments)
    net_worth = quantize_money(working.net_worth)
    months: list[MonthProjection] = []
    debt_result = amortize_strategy(
        list(working.debts),
        strategy=params.debt_strategy,
        extra_payment=params.debt_extra_payment,
    )
    for index in range(1, max(1, params.horizon_months) + 1):
        unexpected = Decimal("0.00")
        if index == 1 and params.unexpected_expense:
            unexpected = quantize_money(params.unexpected_expense)
        contributions = (
            working.first_month_contributions
            if index == 1
            else working.expected_contributions
        )
        month_income = (
            working.first_month_income
            if index == 1 and working.first_month_income is not None
            else working.expected_income
        )
        total_income = quantize_money(month_income + contributions)
        allocation = allocate(total_income, list(working.rules))
        debt_month = (
            debt_result.schedule[index - 1]
            if index <= len(debt_result.schedule)
            else None
        )
        debt_payments = debt_month.total_payment if debt_month else Decimal("0.00")
        debt_interest = debt_month.total_interest if debt_month else Decimal("0.00")
        debt_principal = quantize_money(debt_payments - debt_interest)
        budget_allocated = quantize_money(
            sum(
                (
                    line.amount
                    for line in allocation.lines
                    if line.destination_type == "budget"
                ),
                Decimal("0.00"),
            )
        )
        month_essentials = (
            working.first_month_essentials
            if index == 1 and working.first_month_essentials is not None
            else working.essentials
        )
        # Replace planned budget allocations with the actual remaining budget
        # for month one; later months use the full monthly budget run rate.
        surplus = quantize_money(
            allocation.surplus + budget_allocated - month_essentials - unexpected - debt_payments
        )
        cash = quantize_money(cash + surplus)
        if unexpected:
            cash = quantize_money(cash)  # already in surplus
        invested = _allocated_investment(allocation.lines, working.planned_investment)
        if invested:
            investments = quantize_money(investments + invested)
        months_emergency = (
            Decimal("0.00")
            if working.essentials <= 0
            else quantize_money(emergency / working.essentials)
        )
        month_obligations = _projected_obligations(working.obligations, index)
        forecast = forecast_safe_to_spend(
            cash,
            sum(
                (
                    _monthly_obligation_commitment(row, index)
                    for row in working.obligations
                ),
                Decimal("0.00"),
            ),
            working.minimum_buffer,
        )
        net_worth_delta = quantize_money(surplus + debt_principal)
        net_worth = quantize_money(net_worth + net_worth_delta)
        month = MonthProjection(
            month_index=index,
            income=total_income,
            contributions=contributions,
            debt_payments=debt_payments,
            debt_interest=debt_interest,
            surplus=surplus,
            cash=cash,
            emergency=emergency,
            investments=investments,
            net_worth=net_worth,
            forecast_sts=forecast,
            cash_flow=cash_flow_status(surplus, total_income),
            obligations=_worst_obligation(month_obligations),
            emergency_fund=emergency_status(months_emergency),
            investments_status=investment_status(working.planned_investment, invested),
            safe_to_spend=sts_status(forecast, working.minimum_buffer),
            net_worth_delta=net_worth_delta,
        )
        months.append(month)
        # Later months have no one-time shock; live state remains untouched.
    summary = months[-1]
    return SimulationResult(months=tuple(months), summary=summary)
