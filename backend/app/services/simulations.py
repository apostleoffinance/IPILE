from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.household import Household
from app.models.obligation import Obligation, ObligationOccurrence
from app.models.wealth import Liability
from app.models.simulation import Simulation, SimulationRun
from app.money import format_money, quantize_money
from app.schemas.simulation import SimulationIn
from app.services.allocations import active_rules, expected_income, period_bounds, to_spec
from app.services.budgets import serialize_budget
from app.services.debt_engine import DebtInput
from app.services.contribution_forecast import (
    contribution_forecast,
    monthly_expected_contributions,
)
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
        contribution_change_rate=Decimal(str(payload.contribution_change_rate)),
        debt_strategy=payload.debt_strategy,
        debt_extra_payment=Decimal(str(payload.debt_extra_payment)),
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
    liabilities = (
        db.query(Liability)
        .filter(
            Liability.household_id == household.id,
            Liability.deleted_at.is_(None),
            Liability.status != "paid_off",
        )
        .order_by(Liability.created_at)
        .all()
    )
    debts = tuple(
        DebtInput(
            id=row.id,
            name=row.name,
            balance=quantize_money(Decimal(str(row.current_balance))),
            interest_rate=Decimal(str(row.interest_rate or 0)),
            min_payment=quantize_money(Decimal(str(row.minimum_payment or 0))),
        )
        for row in liabilities
        if quantize_money(Decimal(str(row.current_balance))) > 0
    )
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
        expected_contributions=monthly_expected_contributions(
            db,
            household.id,
            household.base_currency,
            today=today,
        ),
        first_month_contributions=Decimal(
            str(
                contribution_forecast(
                    db,
                    household.id,
                    household.base_currency,
                    today=today,
                    horizon_days=max(1, (end - today).days),
                )["outstanding"]
            )
        ),
        minimum_buffer=quantize_money(Decimal(str(household.minimum_buffer_amount))),
        essentials=quantize_money(essentials),
        planned_investment=quantize_money(planned_investment),
        rules=rules,
        obligations=tuple(obligations),
        categories=tuple(categories),
        debts=debts,
    )


def _month_payload(month) -> dict:
    return {
        "month_index": month.month_index,
        "income": format_money(month.income),
        "contributions": format_money(month.contributions),
        "debt_payments": format_money(month.debt_payments),
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


def baseline_snapshot(state: SimState) -> dict:
    """Persist the exact inputs used by the pure scenario engine."""
    return {
        "cash": format_money(state.cash),
        "emergency": format_money(state.emergency),
        "investments": format_money(state.investments),
        "net_worth": format_money(state.net_worth),
        "expected_income": format_money(state.expected_income),
        "expected_contributions": format_money(state.expected_contributions),
        "first_month_contributions": format_money(state.first_month_contributions),
        "minimum_buffer": format_money(state.minimum_buffer),
        "essentials": format_money(state.essentials),
        "planned_investment": format_money(state.planned_investment),
        "rules": [
            {
                "id": str(row.id),
                "name": row.name,
                "type": row.type,
                "basis": row.basis,
                "rate": str(row.rate) if row.rate is not None else None,
                "amount": format_money(row.amount) if row.amount is not None else None,
                "priority": row.priority,
                "mandatory": row.mandatory,
                "destination_type": row.destination_type,
                "destination_id": str(row.destination_id) if row.destination_id else None,
            }
            for row in state.rules
        ],
        "obligations": [
            {
                "id": str(row.id),
                "name": row.name,
                "amount": format_money(row.amount),
                "frequency": row.frequency,
                "days_until_due": row.days_until_due,
                "funded_amount": format_money(row.funded_amount),
                "fund_id": str(row.fund_id) if row.fund_id else None,
            }
            for row in state.obligations
        ],
        "categories": [
            {
                "id": str(row.id),
                "name": row.name,
                "allocated": format_money(row.allocated),
                "kind": row.kind,
            }
            for row in state.categories
        ],
        "debts": [
            {
                "id": str(row.id),
                "name": row.name,
                "balance": format_money(row.balance),
                "interest_rate": str(row.interest_rate),
                "minimum_payment": format_money(row.min_payment),
            }
            for row in state.debts
        ],
    }


def parameters_payload(payload: SimulationIn, state: SimState) -> dict:
    return {
        **payload.model_dump(mode="json"),
        "engine_version": "phase3-v1",
        "baseline_snapshot": baseline_snapshot(state),
    }


def run_simulation(
    db: Session, household: Household, payload: SimulationIn, today: date | None = None
) -> SimulationRun:
    state = clone_state(db, household, today)
    params = params_from_payload(payload)
    result = project(state, params)
    stored_parameters = parameters_payload(payload, state)
    scenario = Simulation(
        household_id=household.id,
        name=payload.name,
        parameters=stored_parameters,
    )
    db.add(scenario)
    db.flush()
    run = SimulationRun(
        household_id=household.id,
        simulation_id=scenario.id,
        parameters=stored_parameters,
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
