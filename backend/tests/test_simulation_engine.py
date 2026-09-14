from decimal import Decimal
from uuid import uuid4

from app.services.allocation_engine import AllocationRuleSpec, allocate
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
    assert sts_status(Decimal("80000"), Decimal("90000")) == "critical"
    assert sts_status(Decimal("100000"), Decimal("90000")) == "warning"
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
