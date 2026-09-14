"""Hypothetical scenarios. Never mutates live household balances."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from uuid import UUID

from app.money import quantize_money
from app.services.allocation_engine import AllocationRuleSpec, allocate
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


@dataclass(frozen=True)
class SimParams:
    monthly_income: Decimal | None = None
    income_change_rate: Decimal = Decimal("0")
    expense_category_deltas: dict[str, Decimal] | None = None
    obligation_deltas: dict[str, Decimal] | None = None
    investment_override: Decimal | None = None
    unexpected_expense: Decimal | None = None
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


@dataclass(frozen=True)
class MonthProjection:
    month_index: int
    income: Decimal
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
    categories = []
    for category in state.categories:
        rate = _delta_for(cat_deltas, str(category.id)) or _delta_for(cat_deltas, category.name)
        allocated = _scale(category.allocated, rate) if rate else category.allocated
        categories.append(replace(category, allocated=allocated))
        if rate and category.kind != "income":
            essentials = quantize_money(essentials + (allocated - category.allocated))
    income = state.expected_income
    if params.monthly_income is not None:
        income = quantize_money(params.monthly_income)
    income = _scale(income, params.income_change_rate)
    planned = state.planned_investment
    if params.investment_override is not None:
        planned = quantize_money(params.investment_override)
    return replace(
        state,
        expected_income=income,
        essentials=essentials,
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


def project(state: SimState, params: SimParams) -> SimulationResult:
    working = apply_params(state, params)
    cash = quantize_money(working.cash)
    emergency = quantize_money(working.emergency)
    investments = quantize_money(working.investments)
    net_worth = quantize_money(working.net_worth)
    months: list[MonthProjection] = []
    for index in range(1, max(1, params.horizon_months) + 1):
        unexpected = Decimal("0.00")
        if index == 1 and params.unexpected_expense:
            unexpected = quantize_money(params.unexpected_expense)
        allocation = allocate(working.expected_income, list(working.rules))
        surplus = quantize_money(allocation.surplus - unexpected)
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
        forecast = forecast_safe_to_spend(
            cash,
            sum(
                (
                    obligation_monthly(row.amount, row.frequency)
                    for row in working.obligations
                ),
                Decimal("0.00"),
            ),
            working.minimum_buffer,
        )
        net_worth = quantize_money(net_worth + surplus)
        month = MonthProjection(
            month_index=index,
            income=working.expected_income,
            surplus=surplus,
            cash=cash,
            emergency=emergency,
            investments=investments,
            net_worth=net_worth,
            forecast_sts=forecast,
            cash_flow=cash_flow_status(surplus, working.expected_income),
            obligations=_worst_obligation(working.obligations),
            emergency_fund=emergency_status(months_emergency),
            investments_status=investment_status(working.planned_investment, invested),
            safe_to_spend=sts_status(forecast, working.minimum_buffer),
            net_worth_delta=surplus,
        )
        months.append(month)
        # subsequent months have no one-time shock; funded amounts do not increase (clone only)
    summary = months[-1]
    return SimulationResult(months=tuple(months), summary=summary)
