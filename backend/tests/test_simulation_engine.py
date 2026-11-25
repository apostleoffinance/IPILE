from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

from app.services.allocation_engine import AllocationRuleSpec, allocate
from app.services.debt_engine import DebtInput
from app.services.simulation_engine import (
    SimObligation,
    SimParams,
    SimState,
    apply_params,
    cash_flow_status,
    emergency_status,
    investment_status,
    obligation_status,
    project,
    sts_status,
)


def _rule(
    name: str,
    kind: str,
    *,
    amount: str | None = None,
    rate: str | None = None,
    priority: int,
    dest: str = "account",
    dest_id=None,
) -> AllocationRuleSpec:
    return AllocationRuleSpec(
        id=uuid4(),
        name=name,
        type=kind,
        basis="recognized_income" if kind != "remainder" else "remaining",
        rate=Decimal(rate) if rate else None,
        amount=Decimal(amount) if amount else None,
        priority=priority,
        mandatory=kind != "remainder",
        destination_type=dest,
        destination_id=dest_id,
        created_at=str(priority).zfill(2),
    )


def _seed_state(university_id=None, university_fund_id=None) -> SimState:
    university_id = university_id or uuid4()
    university_fund_id = university_fund_id or uuid4()
    return SimState(
        cash=Decimal("1760000.00"),
        emergency=Decimal("0.00"),
        investments=Decimal("0.00"),
        net_worth=Decimal("3760000.00"),
        expected_income=Decimal("2000000.00"),
        minimum_buffer=Decimal("90000.00"),
        essentials=Decimal("670000.00"),
        planned_investment=Decimal("200000.00"),
        rules=(
            _rule("Giving share", "percentage", rate="0.10", priority=0, dest="giving"),
            _rule("Parents stipend", "fixed", amount="100000.00", priority=1, dest="obligation"),
            _rule(
                "University fund",
                "fixed",
                amount="150000.00",
                priority=2,
                dest="fund",
                dest_id=university_fund_id,
            ),
            _rule("Rent fund", "fixed", amount="50000.00", priority=3, dest="fund"),
            _rule("Essentials", "fixed", amount="670000.00", priority=4, dest="budget"),
            _rule("Emergency", "fixed", amount="150000.00", priority=5),
            _rule("Investments", "fixed", amount="200000.00", priority=6),
            _rule("Personal", "fixed", amount="140000.00", priority=7, dest="budget"),
            _rule("More giving", "fixed", amount="50000.00", priority=8, dest="giving"),
            _rule("Buffer", "fixed", amount="90000.00", priority=9),
            _rule("Family surplus", "remainder", priority=10),
        ),
        obligations=(
            SimObligation(
                id=university_id,
                name="Sibling University Fees",
                amount=Decimal("450000.00"),
                frequency="quarterly",
                days_until_due=31,
                funded_amount=Decimal("0.00"),
                fund_id=university_fund_id,
            ),
            SimObligation(
                id=uuid4(),
                name="Parents stipend",
                amount=Decimal("100000.00"),
                frequency="monthly",
                days_until_due=17,
                funded_amount=Decimal("0.00"),
            ),
        ),
    )


def test_status_thresholds() -> None:
    assert cash_flow_status(Decimal("-1"), Decimal("100")) == "critical"
    assert cash_flow_status(Decimal("4"), Decimal("100")) == "warning"
    assert cash_flow_status(Decimal("10"), Decimal("100")) == "healthy"
    assert obligation_status(Decimal("1.00"), 1) == "funded"
    assert obligation_status(Decimal("0.50"), 10) == "unfunded"
    assert obligation_status(Decimal("0.90"), 20) == "at risk"
    assert emergency_status(Decimal("0.40")) == "critical"
    assert emergency_status(Decimal("0.80")) == "warning"
    assert emergency_status(Decimal("1.00")) == "healthy"
    assert sts_status(Decimal("-1"), Decimal("90000")) == "critical"
    assert sts_status(Decimal("80000"), Decimal("90000")) == "warning"
    assert sts_status(Decimal("90000"), Decimal("90000")) == "healthy"
    assert sts_status(Decimal("200000"), Decimal("90000")) == "healthy"
    assert investment_status(Decimal("200000"), Decimal("0")) == "paused"
    assert investment_status(Decimal("200000"), Decimal("100000")) == "reduced"
    assert investment_status(Decimal("200000"), Decimal("200000")) == "on plan"


def test_income_cut_fee_hike_and_shock_bands() -> None:
    university_id = uuid4()
    fund_id = uuid4()
    state = _seed_state(university_id, fund_id)
    params = SimParams(
        income_change_rate=Decimal("-0.20"),
        obligation_deltas={str(university_id): Decimal("0.15")},
        unexpected_expense=Decimal("300000.00"),
        horizon_months=6,
    )
    scaled = apply_params(state, params)
    assert scaled.expected_income == Decimal("1600000.00")
    uni = next(row for row in scaled.obligations if row.id == university_id)
    assert uni.amount == Decimal("517500.00")
    result = project(state, params)
    first = result.months[0]
    assert first.income == Decimal("1600000.00")
    assert first.surplus < 0
    assert first.cash_flow == "critical"
    assert first.obligations == "unfunded"
    assert first.emergency_fund == "critical"
    assert first.investments_status in {"on plan", "reduced", "paused"}
    assert first.safe_to_spend in {"healthy", "warning", "critical"}
    assert len(result.months) == 6
    allocation = allocate(scaled.expected_income, list(scaled.rules))
    assert allocation.recognized_income == Decimal("1600000.00")


def test_simulation_rejects_inputs_that_create_negative_financial_values() -> None:
    import pytest
    from pydantic import ValidationError

    from app.schemas.simulation import SimulationIn

    with pytest.raises(ValidationError):
        SimulationIn(income_change_rate="-1.01")
    with pytest.raises(ValidationError):
        SimulationIn(expense_category_deltas={"food": "-1.1"})
    with pytest.raises(ValidationError):
        SimulationIn(unexpected_expense="-100.00")
    with pytest.raises(ValidationError):
        SimulationIn(debt_extra_payment="-1.00")
    with pytest.raises(ValidationError):
        SimulationIn(debt_strategy="unknown")
    valid = SimulationIn(
        income_change_rate="-0.25",
        expense_category_deltas={"food": "-0.10"},
        horizon_months=6,
    )
    assert valid.horizon_months == 6



def test_obligation_risk_advances_as_due_date_approaches() -> None:
    state = _seed_state()
    obligation = SimObligation(
        id=uuid4(),
        name="Quarterly fees",
        amount=Decimal("100.00"),
        frequency="quarterly",
        days_until_due=31,
        funded_amount=Decimal("50.00"),
    )
    state = replace(state, obligations=(obligation,))
    result = project(state, SimParams(horizon_months=2))
    assert result.months[0].obligations == "unfunded"
    assert result.months[1].obligations == "funded"



def test_simulation_models_debt_minimum_and_extra_payments() -> None:
    debt = DebtInput(
        id=uuid4(),
        name="Credit card",
        balance=Decimal("1000.00"),
        interest_rate=Decimal("0.12"),
        min_payment=Decimal("100.00"),
    )
    state = replace(_seed_state(), debts=(debt,))
    baseline = project(state, SimParams(horizon_months=2))
    accelerated = project(
        state,
        SimParams(
            horizon_months=2,
            debt_strategy="avalanche",
            debt_extra_payment=Decimal("50.00"),
        ),
    )
    assert baseline.months[0].debt_payments == Decimal("100.00")
    assert accelerated.months[0].debt_payments == Decimal("150.00")
    assert accelerated.months[0].debt_interest == Decimal("10.00")
    assert accelerated.months[0].cash == baseline.months[0].cash - Decimal("50.00")
    assert accelerated.months[0].forecast_sts == (
        baseline.months[0].forecast_sts - Decimal("50.00")
    )


def test_simulation_uses_remaining_income_in_first_month_then_full_run_rate() -> None:
    state = replace(
        _seed_state(),
        expected_income=Decimal("200.00"),
        first_month_income=Decimal("120.00"),
        expected_contributions=Decimal("0.00"),
        first_month_contributions=Decimal("0.00"),
    )
    result = project(state, SimParams(horizon_months=2))
    assert result.months[0].income == Decimal("120.00")
    assert result.months[1].income == Decimal("200.00")


def test_simulation_uses_remaining_budget_in_first_month() -> None:
    state = replace(
        _seed_state(),
        cash=Decimal("1000.00"),
        expected_income=Decimal("200.00"),
        first_month_income=Decimal("200.00"),
        minimum_buffer=Decimal("0.00"),
        essentials=Decimal("100.00"),
        first_month_essentials=Decimal("60.00"),
        rules=(
            _rule("Budget", "fixed", amount="80.00", priority=0, dest="budget"),
        ),
        obligations=(),
        debts=(),
    )
    result = project(state, SimParams(horizon_months=2))
    assert result.months[0].surplus == Decimal("140.00")
    assert result.months[1].surplus == Decimal("100.00")


def test_one_time_obligation_is_reserved_until_due_not_repeated_forever() -> None:
    obligation = SimObligation(
        id=uuid4(),
        name="One-time school fee",
        amount=Decimal("120.00"),
        frequency="one_time",
        days_until_due=60,
        funded_amount=Decimal("0.00"),
    )
    state = replace(
        _seed_state(),
        cash=Decimal("1000.00"),
        expected_income=Decimal("0.00"),
        first_month_income=Decimal("0.00"),
        expected_contributions=Decimal("0.00"),
        first_month_contributions=Decimal("0.00"),
        minimum_buffer=Decimal("0.00"),
        essentials=Decimal("0.00"),
        first_month_essentials=Decimal("0.00"),
        rules=(),
        obligations=(obligation,),
        debts=(),
    )
    result = project(state, SimParams(horizon_months=3))
    assert [row.forecast_sts for row in result.months] == [
        Decimal("940.00"),
        Decimal("880.00"),
        Decimal("1000.00"),
    ]
    assert result.months[1].obligations == "funded"


def test_funded_obligation_amount_is_not_reserved_twice() -> None:
    obligation = SimObligation(
        id=uuid4(),
        name="Quarterly fees",
        amount=Decimal("120.00"),
        frequency="quarterly",
        days_until_due=30,
        funded_amount=Decimal("20.00"),
    )
    state = replace(
        _seed_state(),
        cash=Decimal("1000.00"),
        expected_income=Decimal("0.00"),
        first_month_income=Decimal("0.00"),
        expected_contributions=Decimal("0.00"),
        first_month_contributions=Decimal("0.00"),
        minimum_buffer=Decimal("0.00"),
        essentials=Decimal("0.00"),
        first_month_essentials=Decimal("0.00"),
        rules=(),
        obligations=(obligation,),
        debts=(),
    )
    result = project(state, SimParams(horizon_months=2))
    assert result.months[0].forecast_sts == Decimal("900.00")
    assert result.months[1].forecast_sts == Decimal("860.00")

def test_monthly_income_override_preserves_income_already_received() -> None:
    state = replace(
        _seed_state(),
        expected_income=Decimal("200.00"),
        first_month_income=Decimal("120.00"),
        recognized_income=Decimal("80.00"),
    )
    scaled = apply_params(state, SimParams(monthly_income=Decimal("300.00")))
    assert scaled.expected_income == Decimal("300.00")
    assert scaled.first_month_income == Decimal("220.00")


def test_simulation_projects_emergency_and_investment_transfers_into_net_worth() -> None:
    state = replace(
        _seed_state(),
        cash=Decimal("1000.00"),
        emergency=Decimal("0.00"),
        investments=Decimal("0.00"),
        net_worth=Decimal("1000.00"),
        expected_income=Decimal("1000.00"),
        first_month_income=Decimal("1000.00"),
        minimum_buffer=Decimal("0.00"),
        essentials=Decimal("100.00"),
        first_month_essentials=Decimal("0.00"),
        rules=(
            _rule("Emergency reserve", "fixed", amount="100.00", priority=0),
            _rule("Investments", "fixed", amount="200.00", priority=1),
            _rule("University fund", "fixed", amount="50.00", priority=2, dest="fund"),
            _rule("Parents stipend reserve", "fixed", amount="50.00", priority=3, dest="obligation"),
        ),
        obligations=(),
        debts=(),
    )
    month = project(state, SimParams(horizon_months=1)).months[0]
    assert month.cash == Decimal("1600.00")
    assert month.emergency == Decimal("100.00")
    assert month.investments == Decimal("200.00")
    assert month.net_worth_delta == Decimal("1000.00")
    assert month.net_worth == Decimal("2000.00")
