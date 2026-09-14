"""Goal progress arithmetic. Never use float."""

from datetime import date
from decimal import Decimal

from app.money import quantize_money
from app.services.obligation_engine import coverage, months_between

GOAL_TYPES = frozenset(
    {
        "education",
        "housing",
        "relocation",
        "purchase",
        "retirement",
        "business",
        "emergency",
        "other",
    }
)
GOAL_STATUSES = frozenset({"active", "paused", "completed", "cancelled"})


def remaining(target_amount: Decimal, current_amount: Decimal) -> Decimal:
    gap = quantize_money(target_amount) - quantize_money(current_amount)
    return gap if gap > 0 else Decimal("0.00")


def months_left(today: date, deadline: date | None) -> int | None:
    if deadline is None:
        return None
    return max(1, months_between(today, deadline))


def required_monthly(
    target_amount: Decimal,
    current_amount: Decimal,
    deadline: date | None,
    today: date,
    explicit_monthly: Decimal | None = None,
) -> Decimal:
    left = remaining(target_amount, current_amount)
    if left == 0:
        return Decimal("0.00")
    if deadline is None:
        if explicit_monthly is None:
            return Decimal("0.00")
        return quantize_money(explicit_monthly)
    return quantize_money(left / Decimal(months_left(today, deadline) or 1))


def goal_progress(current_amount: Decimal, target_amount: Decimal) -> Decimal:
    return coverage(current_amount, target_amount)


def is_completed(current_amount: Decimal, target_amount: Decimal) -> bool:
    return quantize_money(current_amount) >= quantize_money(target_amount)


def apply_contribution(current_amount: Decimal, amount: Decimal) -> Decimal:
    return quantize_money(quantize_money(current_amount) + quantize_money(amount))


def resolve_status(current_amount: Decimal, target_amount: Decimal, status: str) -> str:
    if status in {"cancelled", "paused"}:
        return status
    if is_completed(current_amount, target_amount):
        return "completed"
    return status if status in GOAL_STATUSES else "active"
