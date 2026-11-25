"""Unit tests for debt snowball / avalanche engine."""

from decimal import Decimal
from uuid import uuid4

from app.services.debt_engine import (
    DebtInput,
    amortize_strategy,
    avalanche_order,
    compare_strategies,
    snowball_order,
)


def _debt(name: str, balance: str, rate: str, min_payment: str) -> DebtInput:
    return DebtInput(
        id=uuid4(),
        name=name,
        balance=Decimal(balance),
        interest_rate=Decimal(rate),
        min_payment=Decimal(min_payment),
    )


def test_snowball_orders_smallest_balance_first() -> None:
    a = _debt("Car", "500000.00", "0.120000", "25000.00")
    b = _debt("Card", "80000.00", "0.240000", "5000.00")
    c = _debt("Loan", "200000.00", "0.080000", "10000.00")
    ordered = snowball_order([a, b, c])
    assert [d.name for d in ordered] == ["Card", "Loan", "Car"]


def test_avalanche_orders_highest_rate_first() -> None:
    a = _debt("Car", "500000.00", "0.120000", "25000.00")
    b = _debt("Card", "80000.00", "0.240000", "5000.00")
    c = _debt("Loan", "200000.00", "0.080000", "10000.00")
    ordered = avalanche_order([a, b, c])
    assert [d.name for d in ordered] == ["Card", "Car", "Loan"]


def test_amortize_pays_off_and_summarizes_schedule() -> None:
    debts = [
        _debt("Small", "1000.00", "0.000000", "200.00"),
        _debt("Large", "2000.00", "0.000000", "200.00"),
    ]
    snow = amortize_strategy(debts, strategy="snowball", extra_payment=Decimal("100.00"))
    assert snow.months > 0
    assert snow.total_interest == Decimal("0.00")
    assert snow.schedule[-1].remaining_balance == Decimal("0.00")
    assert snow.schedule_summary[0].month == 1
    assert snow.schedule_summary[-1].remaining_balance == Decimal("0.00")
    # first 3 + last when long enough
    long = amortize_strategy(
        [_debt("Slow", "5000.00", "0.00", "100.00")],
        strategy="snowball",
        extra_payment=Decimal("0.00"),
    )
    assert long.months == 50
    assert len(long.schedule_summary) == 4
    assert long.schedule_summary[0].month == 1
    assert long.schedule_summary[2].month == 3
    assert long.schedule_summary[3].month == 50


def test_avalanche_saves_interest_vs_snowball_when_rates_differ() -> None:
    debts = [
        _debt("Cheap small", "800.00", "0.050000", "40.00"),
        _debt("Expensive big", "3000.00", "0.220000", "80.00"),
    ]
    compared = compare_strategies(debts, extra_payment=Decimal("100.00"))
    assert compared["snowball"].order[0]["name"] == "Cheap small"
    assert compared["avalanche"].order[0]["name"] == "Expensive big"
    assert compared["avalanche"].total_interest <= compared["snowball"].total_interest


def test_empty_debts() -> None:
    result = compare_strategies([], extra_payment=Decimal("50.00"))
    assert result["snowball"].months == 0
    assert result["avalanche"].months == 0
    assert result["snowball"].paid_off is True
    assert result["snowball"].remaining_balance == Decimal("0.00")


def test_debt_strategies_api(client) -> None:
    from tests.conftest import register

    register(client, "debt-strat@example.com")
    client.post(
        "/api/v1/liabilities",
        json={
            "name": "Card",
            "type": "credit",
            "current_balance": "1000.00",
            "interest_rate": "0.240000",
            "minimum_payment": "50.00",
        },
    )
    client.post(
        "/api/v1/liabilities",
        json={
            "name": "Loan",
            "type": "loan",
            "current_balance": "5000.00",
            "interest_rate": "0.080000",
            "minimum_payment": "100.00",
        },
    )
    body = client.get("/api/v1/debts/strategies", params={"extra_payment": "50"}).json()
    assert body["liabilities_considered"] == 2
    assert body["snowball"]["order"][0]["name"] == "Card"
    assert body["avalanche"]["order"][0]["name"] == "Card"
    assert body["snowball"]["months"] > 0
    assert body["snowball"]["paid_off"] is True
    assert body["snowball"]["remaining_balance"] == "0.00"
    assert body["avalanche"]["schedule_summary"]
    assert "total_interest" in body["snowball"]


def test_non_amortizing_debt_is_not_reported_as_paid_off() -> None:
    debt = _debt("High-interest debt", "1000.00", "0.24", "10.00")
    result = amortize_strategy([debt], strategy="avalanche")
    assert result.months == 600
    assert result.paid_off is False
    assert result.remaining_balance > Decimal("1000.00")


def test_debt_with_no_payment_capacity_reports_remaining_balance() -> None:
    debt = _debt("No payment", "1000.00", "0.12", "0.00")
    result = amortize_strategy([debt], strategy="snowball")
    assert result.months == 0
    assert result.paid_off is False
    assert result.remaining_balance == Decimal("1000.00")


def test_debt_engine_rejects_invalid_strategy_and_payment_inputs() -> None:
    import pytest

    debt = _debt("Loan", "1000.00", "0.12", "50.00")
    with pytest.raises(ValueError):
        amortize_strategy([debt], strategy="random")
    with pytest.raises(ValueError):
        amortize_strategy([debt], strategy="avalanche", extra_payment=Decimal("-1.00"))
    too_high = _debt("Invalid APR", "1000.00", "600.00", "50.00")
    with pytest.raises(ValueError):
        amortize_strategy([too_high], strategy="avalanche")


def test_liability_api_rejects_percentage_not_fraction_apr(client) -> None:
    from tests.conftest import register

    register(client, "debt-apr-validation@example.com")
    invalid = client.post(
        "/api/v1/liabilities",
        json={
            "name": "Invalid APR",
            "type": "credit",
            "current_balance": "1000.00",
            "interest_rate": "18",
            "minimum_payment": "50.00",
        },
    )
    assert invalid.status_code == 422
    valid = client.post(
        "/api/v1/liabilities",
        json={
            "name": "Valid APR",
            "type": "credit",
            "current_balance": "1000.00",
            "interest_rate": "0.18",
            "minimum_payment": "50.00",
        },
    )
    assert valid.status_code == 201, valid.text


def test_legacy_whole_percentage_apr_is_normalized() -> None:
    legacy = _debt("Legacy APR", "1000.00", "18", "100.00")
    result = amortize_strategy([legacy], strategy="avalanche")
    assert result.order[0]["interest_rate"] == "0.18"


def test_avalanche_ranks_legacy_and_fractional_apr_consistently() -> None:
    legacy_eighteen = _debt("Legacy 18%", "1000.00", "18", "100.00")
    modern_twenty_four = _debt("Modern 24%", "1000.00", "0.24", "100.00")
    ordered = avalanche_order([legacy_eighteen, modern_twenty_four])
    assert [row.name for row in ordered] == ["Modern 24%", "Legacy 18%"]
