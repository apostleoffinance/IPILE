from decimal import Decimal

from app.services.health_engine import (
    WEIGHTS,
    budget_discipline_score,
    cash_flow_score,
    compute_health,
    debt_health_score,
    discipline_score,
    emergency_readiness_score,
    health_label,
    obligation_coverage_score,
)


def test_weights_sum_to_100() -> None:
    assert sum(WEIGHTS.values(), Decimal("0")) == Decimal("100")


def test_cash_flow_ten_percent_surplus_is_full_weight() -> None:
    row = cash_flow_score(Decimal("2000000.00"), Decimal("200000.00"))
    assert row.points == Decimal("20.00")
    assert row.inputs["surplus_ratio"] == Decimal("0.10")


def test_cash_flow_zero_income_cases() -> None:
    assert cash_flow_score(Decimal("0"), Decimal("0")).points == Decimal("0.00")
    assert cash_flow_score(Decimal("0"), Decimal("-10")).points == Decimal("0.00")
    assert cash_flow_score(Decimal("0"), Decimal("50")).points == Decimal("10.00")


def test_obligation_coverage_nothing_due_is_full() -> None:
    row = obligation_coverage_score(Decimal("0"), Decimal("0"))
    assert row.points == Decimal("20.00")


def test_obligation_coverage_partial() -> None:
    row = obligation_coverage_score(Decimal("225000.00"), Decimal("450000.00"))
    assert row.points == Decimal("10.00")


def test_emergency_three_months_is_full() -> None:
    row = emergency_readiness_score(Decimal("2010000.00"), Decimal("670000.00"))
    assert row.points == Decimal("15.00")
    assert row.inputs["months"] == Decimal("3.00")


def test_debt_zero_liabilities_is_full() -> None:
    row = debt_health_score(Decimal("0"), Decimal("1000000.00"), False)
    assert row.points == Decimal("15.00")


def test_debt_forty_percent_leverage_with_missed_payment() -> None:
    row = debt_health_score(Decimal("400000.00"), Decimal("1000000.00"), True)
    assert row.inputs["debt_to_asset"] == Decimal("0.40")
    assert row.points == Decimal("0.00")


def test_savings_and_investment_discipline() -> None:
    full = discipline_score("savings_discipline", Decimal("350000.00"), Decimal("350000.00"))
    assert full.points == Decimal("10.00")
    none_planned = discipline_score("investment_discipline", Decimal("0"), Decimal("0"))
    assert none_planned.points == Decimal("10.00")
    half = discipline_score("investment_discipline", Decimal("200000.00"), Decimal("100000.00"))
    assert half.points == Decimal("5.00")


def test_budget_discipline_all_ok() -> None:
    row = budget_discipline_score(12, 12, Decimal("0"), Decimal("820000.00"))
    assert row.points == Decimal("10.00")


def test_labels() -> None:
    assert health_label(Decimal("80.00")) == "Healthy"
    assert health_label(Decimal("79.99")) == "Watch"
    assert health_label(Decimal("60.00")) == "Watch"
    assert health_label(Decimal("59.99")) == "Strained"
    assert health_label(Decimal("40.00")) == "Strained"
    assert health_label(Decimal("39.99")) == "Critical"
    assert health_label(Decimal("0")) == "Critical"


def test_components_sum_to_total() -> None:
    result = compute_health(
        recognized_income=Decimal("2000000.00"),
        period_surplus=Decimal("200000.00"),
        funded_due_90=Decimal("300000.00"),
        due_90=Decimal("300000.00"),
        emergency_balance=Decimal("450000.00"),
        monthly_essentials=Decimal("670000.00"),
        total_liabilities=Decimal("0"),
        total_assets=Decimal("5000000.00"),
        missed_debt_payment=False,
        planned_savings=Decimal("350000.00"),
        actual_savings=Decimal("350000.00"),
        planned_investment=Decimal("200000.00"),
        actual_investment=Decimal("200000.00"),
        categories_ok=12,
        category_count=12,
        total_overspend=Decimal("0"),
        total_allocated=Decimal("820000.00"),
    )
    assert result.score == result.points_total()
    assert result.score == Decimal("88.36")
    assert result.label == "Healthy"
    assert [row.weight for row in result.components] == list(WEIGHTS.values())
    assert {row.key for row in result.components} == set(WEIGHTS)
