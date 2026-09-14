from calendar import monthrange
from datetime import date, timedelta

from app.models.recurring import RecurringTransaction


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def advance_next_date(current: date, frequency: str) -> date:
    if frequency == "weekly":
        return current + timedelta(days=7)
    if frequency == "biweekly":
        return current + timedelta(days=14)
    if frequency == "monthly":
        return add_months(current, 1)
    if frequency == "quarterly":
        return add_months(current, 3)
    if frequency == "annual":
        return add_months(current, 12)
    raise ValueError(f"Unsupported frequency: {frequency}")


def advance_recurring(template: RecurringTransaction) -> None:
    template.next_date = advance_next_date(template.next_date, template.frequency)
