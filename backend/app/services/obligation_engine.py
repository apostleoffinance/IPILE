from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from app.money import quantize_money

FREQUENCIES = frozenset({"weekly", "monthly", "quarterly", "annual", "one_time"})
PAYABLE_SKIP = frozenset({"paid", "skipped"})


def months_between(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def next_due_after(current: date, frequency: str) -> date:
    if frequency == "weekly":
        return current + timedelta(days=7)
    if frequency == "monthly":
        return add_months(current, 1)
    if frequency == "quarterly":
        return add_months(current, 3)
    if frequency == "annual":
        return add_months(current, 12)
    if frequency == "one_time":
        return current
    raise ValueError(f"Unsupported frequency: {frequency}")


def obligation_monthly(
    amount: Decimal,
    frequency: str,
    *,
    today: date | None = None,
    next_due_date: date | None = None,
    already_funded: Decimal = Decimal("0.00"),
) -> Decimal:
    amount = quantize_money(amount)
    already_funded = quantize_money(already_funded)
    if frequency == "monthly":
        return amount
    if frequency == "weekly":
        return quantize_money(amount * Decimal(52) / Decimal(12))
    if frequency == "quarterly":
        return quantize_money(amount / Decimal(3))
    if frequency == "annual":
        return quantize_money(amount / Decimal(12))
    if frequency == "one_time":
        today = today or date.today()
        due = next_due_date or today
        months_left = max(1, months_between(today, due))
        remaining = amount - already_funded
        if remaining <= 0:
            return Decimal("0.00")
        return quantize_money(remaining / Decimal(months_left))
    raise ValueError(f"Unsupported frequency: {frequency}")


def coverage(funded_amount: Decimal, amount: Decimal) -> Decimal:
    amount = quantize_money(amount)
    funded_amount = quantize_money(funded_amount)
    if amount == 0:
        return Decimal("0.00")
    return quantize_money(funded_amount / amount)


def coverage_label(ratio: Decimal) -> str:
    if ratio >= Decimal("1.00"):
        return "Funded"
    return f"{int(ratio * 100)}% funded"


def occurrence_status(due_date: date, today: date, current: str) -> str:
    if current in PAYABLE_SKIP:
        return current
    if due_date < today:
        return "missed"
    if due_date == today:
        return "due"
    return "upcoming"


def due_dates_through_horizon(
    next_due_date: date,
    frequency: str,
    *,
    today: date | None = None,
    months: int = 24,
) -> list[date]:
    today = today or date.today()
    horizon = add_months(today, months)
    dates: list[date] = []
    cursor = next_due_date
    if frequency == "one_time":
        if cursor <= horizon:
            dates.append(cursor)
        return dates
    while cursor <= horizon:
        dates.append(cursor)
        nxt = next_due_after(cursor, frequency)
        if nxt == cursor:
            break
        cursor = nxt
    return dates
