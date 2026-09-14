from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.household import Household
from app.models.obligation import Obligation, ObligationOccurrence
from app.models.simulation import Simulation, SimulationRun
from app.money import format_money, quantize_money
from app.schemas.simulation import SimulationIn
from app.services.allocations import active_rules, expected_income, period_bounds, to_spec
from app.services.budgets import serialize_budget
from app.services.simulation_engine import (
    SimCategory,
    SimObligation,
    SimParams,
    SimState,
    SimulationResult,
    project,
)
from app.services.wealth import household_net_worth


def _decimal_map(raw: dict[str, str]) -> dict[str, Decimal]:
    return {str(key): Decimal(str(value)) for key, value in raw.items()}


def params_from_payload(payload: SimulationIn) -> SimParams:
    unexpected = payload.unexpected_expense
    return SimParams(
        monthly_income=payload.monthly_income,
        income_change_rate=Decimal(str(payload.income_change_rate)),
        expense_category_deltas=_decimal_map(payload.expense_category_deltas),
        obligation_deltas=_decimal_map(payload.obligation_deltas),
        investment_override=payload.investment_override,
        unexpected_expense=unexpected,
        horizon_months=payload.horizon_months,
    )


def clone_state(db: Session, household: Household, today: date | None = None) -> SimState:
    today = today or date.today()
    start, end = period_bounds(household, today)
    accounts = (
        db.query(Account)
        .filter(Account.household_id == household.id, Account.deleted_at.is_(None))
        .all()
    )
    cash = quantize_money(
        sum(
            (
                Decimal(str(row.current_balance))
                for row in accounts
                if row.type in {"bank", "cash", "wallet"} and row.status == "active"
            ),
            Decimal("0.00"),
        )
    )
    wealth = household_net_worth(db, household)
    rules = tuple(to_spec(rule) for rule in active_rules(db, household.id, start, end))
    planned_investment = Decimal("0.00")
    for rule in rules:
        if rule.destination_type == "account" and rule.amount and "invest" in rule.name.lower():
            planned_investment += Decimal(str(rule.amount))
    obligations = []
    rows = (
        db.query(Obligation)
        .filter(Obligation.household_id == household.id, Obligation.deleted_at.is_(None))
        .all()
    )
    horizon = today + timedelta(days=90)
    for obligation in rows:
        occurrence = (
            db.query(ObligationOccurrence)
            .filter(
                ObligationOccurrence.obligation_id == obligation.id,
                ObligationOccurrence.due_date >= today,
                ObligationOccurrence.due_date <= horizon,
                ObligationOccurrence.status.in_(("upcoming", "due", "missed")),
            )
            .order_by(ObligationOccurrence.due_date)
            .first()
        )
        due = occurrence.due_date if occurrence else obligation.next_due_date
        funded = Decimal(str(occurrence.funded_amount)) if occurrence else Decimal("0.00")
        obligations.append(
            SimObligation(
                id=obligation.id,
                name=obligation.name,
                amount=quantize_money(Decimal(str(obligation.amount))),
                frequency=obligation.frequency,
                days_until_due=max(0, (due - today).days),
                funded_amount=quantize_money(funded),
                fund_id=obligation.fund_id,
            )
        )
    essentials = Decimal("0.00")
    categories: list[SimCategory] = []
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
    for budget in budgets:
        snapshot = serialize_budget(db, budget)
        essentials += snapshot.allocated_total
        for line in snapshot.categories:
            kind = "expense"
            category = db.get(Category, line.category_id)
            if category is not None:
                kind = category.kind
            categories.append(
                SimCategory(
                    id=line.category_id,
                    name=line.category_name,
                    allocated=line.allocated_amount,
                    kind=kind,
                )
            )
    return SimState(
        cash=cash,
        emergency=wealth.emergency_fund,
        investments=wealth.investments,
        net_worth=wealth.net_worth,
        expected_income=expected_income(db, household.id),
        minimum_buffer=quantize_money(Decimal(str(household.minimum_buffer_amount))),
        essentials=quantize_money(essentials),
        planned_investment=quantize_money(planned_investment),
        rules=rules,
        obligations=tuple(obligations),
        categories=tuple(categories),
    )


def _month_payload(month) -> dict:
    return {
        "month_index": month.month_index,
        "income": format_money(month.income),
        "surplus": format_money(month.surplus),
        "cash": format_money(month.cash),
        "emergency": format_money(month.emergency),
        "investments": format_money(month.investments),
        "net_worth": format_money(month.net_worth),
        "forecast_sts": format_money(month.forecast_sts),
        "cash_flow": month.cash_flow,
        "obligations": month.obligations,
        "emergency_fund": month.emergency_fund,
        "investments_status": month.investments_status,
        "safe_to_spend": month.safe_to_spend,
        "net_worth_delta": format_money(month.net_worth_delta),
    }


def serialize_result(result: SimulationResult) -> dict:
    months = [_month_payload(row) for row in result.months]
    return {"months": months, "summary": _month_payload(result.summary)}


def parameters_payload(payload: SimulationIn) -> dict:
    return payload.model_dump(mode="json")


def run_simulation(
    db: Session, household: Household, payload: SimulationIn, today: date | None = None
) -> SimulationRun:
    state = clone_state(db, household, today)
    params = params_from_payload(payload)
    result = project(state, params)
    scenario = Simulation(
        household_id=household.id,
        name=payload.name,
        parameters=parameters_payload(payload),
    )
    db.add(scenario)
    db.flush()
    run = SimulationRun(
        household_id=household.id,
        simulation_id=scenario.id,
        parameters=parameters_payload(payload),
        result=serialize_result(result),
        status="completed",
    )
    db.add(run)
    db.flush()
    return run


def get_run(db: Session, household_id: UUID, run_id: UUID) -> SimulationRun | None:
    return (
        db.query(SimulationRun)
        .filter(SimulationRun.id == run_id, SimulationRun.household_id == household_id)
        .first()
    )


def serialize_run(db: Session, run: SimulationRun) -> dict:
    scenario = db.get(Simulation, run.simulation_id) if run.simulation_id else None
    payload = run.result or {}
    return {
        "id": run.id,
        "household_id": run.household_id,
        "name": scenario.name if scenario else "Scenario",
        "parameters": run.parameters,
        "status": run.status,
        "months": payload.get("months", []),
        "summary": payload.get("summary"),
    }
