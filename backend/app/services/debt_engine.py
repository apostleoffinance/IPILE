"""Debt payoff strategies: snowball and avalanche. Decimal only — never float."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.money import format_money, quantize_money

ZERO = Decimal("0.00")
TWELVE = Decimal("12")
MAX_MONTHS = 600


@dataclass(frozen=True)
class DebtInput:
    id: UUID | str
    name: str
    balance: Decimal
    interest_rate: Decimal  # APR as decimal fraction (0.18 = 18%)
    min_payment: Decimal


@dataclass(frozen=True)
class ScheduleMonth:
    month: int
    total_payment: Decimal
    total_interest: Decimal
    remaining_balance: Decimal
    debts_remaining: int


@dataclass
class StrategyResult:
    strategy: str
    order: list[dict]
    months: int
    total_interest: Decimal
    total_paid: Decimal
    schedule: list[ScheduleMonth] = field(default_factory=list)
    schedule_summary: list[ScheduleMonth] = field(default_factory=list)


def _money(value: Decimal | None) -> Decimal:
    return quantize_money(Decimal(str(value or 0)))


def snowball_order(debts: list[DebtInput]) -> list[DebtInput]:
    """Smallest balance first; ties by name."""
    return sorted(debts, key=lambda d: (_money(d.balance), d.name.lower(), str(d.id)))


def avalanche_order(debts: list[DebtInput]) -> list[DebtInput]:
    """Highest interest rate first; ties by balance then name."""

    def sort_key(d: DebtInput):
        return (-Decimal(str(d.interest_rate or 0)), _money(d.balance), d.name.lower(), str(d.id))

    return sorted(debts, key=sort_key)


def _order_payload(ordered: list[DebtInput]) -> list[dict]:
    return [
        {
            "id": str(debt.id),
            "name": debt.name,
            "balance": format_money(debt.balance),
            "interest_rate": format(Decimal(str(debt.interest_rate or 0)), "f"),
            "min_payment": format_money(debt.min_payment),
            "position": index + 1,
        }
        for index, debt in enumerate(ordered)
    ]


def _summarize_schedule(schedule: list[ScheduleMonth]) -> list[ScheduleMonth]:
    if not schedule:
        return []
    if len(schedule) <= 4:
        return list(schedule)
    return [*schedule[:3], schedule[-1]]


def _empty_result(strategy: str, ordered: list[DebtInput]) -> StrategyResult:
    return StrategyResult(
        strategy=strategy,
        order=_order_payload(ordered),
        months=0,
        total_interest=ZERO,
        total_paid=ZERO,
        schedule=[],
        schedule_summary=[],
    )


def amortize_strategy(
    debts: list[DebtInput],
    *,
    strategy: str,
    extra_payment: Decimal = ZERO,
) -> StrategyResult:
    """Monthly amortization for snowball or avalanche with optional extra payment.

    Each month: accrue interest, pay minimums on all open debts, then apply
    extra_payment (plus any leftover from overpaying a paid-off debt) to the
    first open debt in strategy order.
    """
    active = [
        DebtInput(
            id=d.id,
            name=d.name,
            balance=_money(d.balance),
            interest_rate=Decimal(str(d.interest_rate or 0)),
            min_payment=_money(d.min_payment),
        )
        for d in debts
        if _money(d.balance) > ZERO
    ]
    ordered = snowball_order(active) if strategy == "snowball" else avalanche_order(active)
    if not active:
        return _empty_result(strategy, ordered)

    extra = _money(extra_payment)
    monthly_capacity = quantize_money(sum((d.min_payment for d in ordered), ZERO) + extra)
    if monthly_capacity <= ZERO:
        return _empty_result(strategy, ordered)

    balances = {str(d.id): _money(d.balance) for d in ordered}
    rates = {str(d.id): Decimal(str(d.interest_rate or 0)) for d in ordered}
    mins = {str(d.id): _money(d.min_payment) for d in ordered}
    order_ids = [str(d.id) for d in ordered]
    paid_off: set[str] = set()

    total_interest = ZERO
    total_paid = ZERO
    schedule: list[ScheduleMonth] = []

    for month in range(1, MAX_MONTHS + 1):
        month_interest = ZERO
        for debt_id in order_ids:
            bal = balances[debt_id]
            if bal <= ZERO:
                continue
            interest = quantize_money(bal * (rates[debt_id] / TWELVE))
            balances[debt_id] = quantize_money(bal + interest)
            month_interest = quantize_money(month_interest + interest)
        total_interest = quantize_money(total_interest + month_interest)

        month_payment = ZERO
        # Mins of already-paid-off debts roll into the focus payment
        rolled = quantize_money(sum((mins[i] for i in paid_off), ZERO))
        leftover = ZERO

        for debt_id in order_ids:
            bal = balances[debt_id]
            if bal <= ZERO:
                continue
            pay = min(mins[debt_id], bal)
            balances[debt_id] = quantize_money(bal - pay)
            month_payment = quantize_money(month_payment + pay)
            if balances[debt_id] <= ZERO:
                balances[debt_id] = ZERO
                leftover = quantize_money(leftover + (mins[debt_id] - pay))
                paid_off.add(debt_id)

        pool = quantize_money(extra + rolled + leftover)
        for debt_id in order_ids:
            if pool <= ZERO:
                break
            bal = balances[debt_id]
            if bal <= ZERO:
                continue
            pay = min(pool, bal)
            balances[debt_id] = quantize_money(bal - pay)
            pool = quantize_money(pool - pay)
            month_payment = quantize_money(month_payment + pay)
            if balances[debt_id] <= ZERO:
                balances[debt_id] = ZERO
                paid_off.add(debt_id)

        total_paid = quantize_money(total_paid + month_payment)
        remaining = quantize_money(sum((balances[i] for i in order_ids), ZERO))
        debts_left = sum(1 for i in order_ids if balances[i] > ZERO)
        schedule.append(
            ScheduleMonth(
                month=month,
                total_payment=month_payment,
                total_interest=month_interest,
                remaining_balance=remaining,
                debts_remaining=debts_left,
            )
        )
        if remaining <= ZERO:
            break

    return StrategyResult(
        strategy=strategy,
        order=_order_payload(ordered),
        months=len(schedule),
        total_interest=total_interest,
        total_paid=total_paid,
        schedule=schedule,
        schedule_summary=_summarize_schedule(schedule),
    )


def compare_strategies(
    debts: list[DebtInput],
    *,
    extra_payment: Decimal = ZERO,
) -> dict[str, StrategyResult]:
    return {
        "snowball": amortize_strategy(debts, strategy="snowball", extra_payment=extra_payment),
        "avalanche": amortize_strategy(debts, strategy="avalanche", extra_payment=extra_payment),
    }
