from datetime import date
from decimal import Decimal

from app.services.goal_engine import (
    apply_contribution,
    goal_progress,
    is_completed,
    remaining,
    required_monthly,
    resolve_status,
)


def test_required_monthly_is_remaining_over_months_left() -> None:
    monthly = required_monthly(
        Decimal("8000000.00"),
        Decimal("2100000.00"),
        date(2027, 6, 30),
        date(2026, 9, 14),
    )
    assert monthly == Decimal("655555.56")


def test_required_monthly_is_zero_when_funded() -> None:
    assert (
        required_monthly(
            Decimal("8000000.00"),
            Decimal("8000000.00"),
            date(2027, 6, 30),
            date(2026, 9, 14),
        )
        == Decimal("0.00")
    )


def test_required_monthly_without_deadline_uses_explicit() -> None:
    assert required_monthly(
        Decimal("150000.00"),
        Decimal("0.00"),
        None,
        date(2026, 9, 14),
        Decimal("150000.00"),
    ) == Decimal("150000.00")


def test_goal_completed_when_current_reaches_target() -> None:
    current = apply_contribution(Decimal("2100000.00"), Decimal("5900000.00"))
    assert current == Decimal("8000000.00")
    assert is_completed(current, Decimal("8000000.00"))
    assert resolve_status(current, Decimal("8000000.00"), "active") == "completed"
    assert remaining(Decimal("8000000.00"), current) == Decimal("0.00")
    assert goal_progress(Decimal("2100000.00"), Decimal("8000000.00")) == Decimal("0.26")
