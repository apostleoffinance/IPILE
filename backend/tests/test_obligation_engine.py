from datetime import date
from decimal import Decimal

from app.services.fund_engine import (
    expected_funded_by,
    fund_progress,
    on_track,
    required_monthly,
    shortfall,
)
from app.services.obligation_engine import (
    coverage,
    coverage_label,
    due_dates_through_horizon,
    obligation_monthly,
    occurrence_status,
)


def test_quarterly_450000_requires_150000_a_month() -> None:
    assert obligation_monthly(Decimal("450000.00"), "quarterly") == Decimal("150000.00")


def test_annual_600000_requires_50000_a_month() -> None:
    assert obligation_monthly(Decimal("600000.00"), "annual") == Decimal("50000.00")


def test_monthly_and_weekly_and_one_time() -> None:
    assert obligation_monthly(Decimal("100000.00"), "monthly") == Decimal("100000.00")
    assert obligation_monthly(Decimal("10000.00"), "weekly") == Decimal("43333.33")
    assert obligation_monthly(
        Decimal("120000.00"),
        "one_time",
        today=date(2026, 9, 1),
        next_due_date=date(2026, 12, 1),
        already_funded=Decimal("0.00"),
    ) == Decimal("40000.00")


def test_occurrence_generation_is_idempotent_dates() -> None:
    first = due_dates_through_horizon(
        date(2026, 10, 15),
        "quarterly",
        today=date(2026, 9, 14),
    )
    second = due_dates_through_horizon(
        date(2026, 10, 15),
        "quarterly",
        today=date(2026, 9, 14),
    )
    assert first == second
    assert first[0] == date(2026, 10, 15)
    assert date(2028, 10, 15) not in first


def test_late_occurrence_becomes_missed() -> None:
    assert occurrence_status(date(2026, 9, 1), date(2026, 9, 14), "upcoming") == "missed"
    assert occurrence_status(date(2026, 9, 14), date(2026, 9, 14), "upcoming") == "due"
    assert occurrence_status(date(2026, 9, 1), date(2026, 9, 14), "paid") == "paid"


def test_coverage_and_fund_progress() -> None:
    assert coverage(Decimal("450000.00"), Decimal("450000.00")) == Decimal("1.00")
    assert coverage_label(Decimal("1.00")) == "Funded"
    assert coverage_label(Decimal("0.50")) == "50% funded"
    assert fund_progress(Decimal("150000.00"), Decimal("450000.00")) == Decimal("0.33")
    assert required_monthly(Decimal("150000.00"), Decimal("100000.00")) == Decimal("150000.00")
    expected = expected_funded_by(
        Decimal("150000.00"),
        start=date(2026, 7, 15),
        today=date(2026, 9, 14),
        target_date=date(2026, 10, 15),
    )
    assert expected == Decimal("300000.00")
    assert shortfall(expected, Decimal("150000.00")) == Decimal("150000.00")
    assert on_track(Decimal("300000.00"), expected) is True
