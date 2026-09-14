from decimal import Decimal

from app.services.budget_engine import line_status, remaining, spent_from_lines, utilization
from app.services.recurring import advance_next_date


def test_zero_allocation_and_zero_spend_is_zero_utilization() -> None:
    spent = spent_from_lines([])
    assert spent == Decimal("0.00")
    assert remaining(Decimal("0.00"), spent) == Decimal("0.00")
    assert utilization(Decimal("0.00"), spent) == Decimal("0.00")
    assert line_status(Decimal("0.00"), spent) == "healthy"


def test_zero_allocation_with_spend_is_infinite_and_overspend() -> None:
    spent = spent_from_lines([("expense", Decimal("25.00"))])
    assert spent == Decimal("25.00")
    assert remaining(Decimal("0.00"), spent) == Decimal("-25.00")
    assert utilization(Decimal("0.00"), spent) is None
    assert line_status(Decimal("0.00"), spent) == "critical"


def test_refund_reduces_spend() -> None:
    spent = spent_from_lines(
        [
            ("expense", Decimal("100000.00")),
            ("giving", Decimal("10000.00")),
            ("refund", Decimal("40000.00")),
        ]
    )
    assert spent == Decimal("70000.00")
    assert remaining(Decimal("100000.00"), spent) == Decimal("30000.00")
    assert utilization(Decimal("100000.00"), spent) == Decimal("0.70")
    assert line_status(Decimal("100000.00"), spent) == "healthy"


def test_overspend_and_eighty_percent_warning() -> None:
    warning_spent = spent_from_lines([("expense", Decimal("80000.00"))])
    assert utilization(Decimal("100000.00"), warning_spent) == Decimal("0.80")
    assert line_status(Decimal("100000.00"), warning_spent) == "warning"

    overspent = spent_from_lines([("expense", Decimal("100000.01"))])
    assert remaining(Decimal("100000.00"), overspent) == Decimal("-0.01")
    assert line_status(Decimal("100000.00"), overspent) == "critical"


def test_capital_contribution_does_not_count_as_spend() -> None:
    spent = spent_from_lines([("capital_contribution", Decimal("50000.00"))])
    assert spent == Decimal("0.00")


def test_advance_next_date_by_frequency() -> None:
    from datetime import date

    start = date(2026, 1, 31)
    assert advance_next_date(start, "weekly") == date(2026, 2, 7)
    assert advance_next_date(start, "biweekly") == date(2026, 2, 14)
    assert advance_next_date(start, "monthly") == date(2026, 2, 28)
    assert advance_next_date(start, "quarterly") == date(2026, 4, 30)
    assert advance_next_date(start, "annual") == date(2027, 1, 31)
