from decimal import Decimal

from app.money import quantize_money

SPEND_TYPES = frozenset({"expense", "giving"})
REFUND_TYPE = "refund"
ACTIVE_STATUSES = frozenset({"pending", "cleared", "reconciled"})


def spent_from_lines(rows: list[tuple[str, Decimal]]) -> Decimal:
    total = Decimal("0.00")
    for tx_type, amount in rows:
        amount = quantize_money(amount)
        if tx_type in SPEND_TYPES:
            total += amount
        elif tx_type == REFUND_TYPE:
            total -= amount
    return quantize_money(total)


def remaining(allocated: Decimal, spent: Decimal) -> Decimal:
    return quantize_money(allocated) - quantize_money(spent)


def utilization(allocated: Decimal, spent: Decimal) -> Decimal | None:
    allocated = quantize_money(allocated)
    spent = quantize_money(spent)
    if allocated == 0 and spent == 0:
        return Decimal("0.00")
    if allocated == 0 and spent > 0:
        return None
    return quantize_money(spent / allocated)


def line_status(allocated: Decimal, spent: Decimal) -> str:
    allocated = quantize_money(allocated)
    spent = quantize_money(spent)
    if spent > allocated:
        return "critical"
    ratio = utilization(allocated, spent)
    if ratio is not None and ratio >= Decimal("0.80"):
        return "warning"
    return "healthy"
