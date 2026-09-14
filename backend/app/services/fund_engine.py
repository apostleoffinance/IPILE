from datetime import date
from decimal import Decimal

from app.money import quantize_money
from app.services.obligation_engine import coverage, months_between


def required_monthly(obligation_monthly_amount: Decimal, explicit_monthly: Decimal) -> Decimal:
    return max(quantize_money(obligation_monthly_amount), quantize_money(explicit_monthly))


def expected_funded_by(
    monthly: Decimal,
    *,
    start: date,
    today: date,
    target_date: date | None = None,
) -> Decimal:
    monthly = quantize_money(monthly)
    elapsed = max(0, months_between(start, today))
    expected = quantize_money(monthly * Decimal(elapsed))
    if target_date is None:
        return expected
    total_months = max(0, months_between(start, target_date))
    cap = quantize_money(monthly * Decimal(total_months))
    return min(expected, cap)


def shortfall(required_to_date: Decimal, current_amount: Decimal) -> Decimal:
    gap = quantize_money(required_to_date) - quantize_money(current_amount)
    return gap if gap > 0 else Decimal("0.00")


def on_track(current_amount: Decimal, expected: Decimal) -> bool:
    return quantize_money(current_amount) >= quantize_money(expected)


def fund_progress(current_amount: Decimal, target_amount: Decimal) -> Decimal:
    return coverage(current_amount, target_amount)
