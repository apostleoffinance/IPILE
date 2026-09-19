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
    assert body["avalanche"]["schedule_summary"]
    assert "total_interest" in body["snowball"]
