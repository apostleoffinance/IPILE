"""Household cash-flow statement for a date range. Decimal only."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.household import Household
from app.models.transaction import Transaction
from app.money import quantize_money
from app.services.balances import account_delta, counterparty_delta

CASH_TYPES = frozenset({"bank", "cash", "wallet", "savings"})
ACTIVE_TX = ("cleared", "reconciled")
ZERO = Decimal("0.00")


def current_month_bounds(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    return start, end


def _cash_accounts(db: Session, household_id: UUID) -> list[Account]:
    return (
        db.query(Account)
        .filter(
            Account.household_id == household_id,
            Account.deleted_at.is_(None),
            Account.status == "active",
            Account.type.in_(tuple(CASH_TYPES)),
        )
        .all()
    )


def _cash_total(accounts: list[Account]) -> Decimal:
    return quantize_money(
        sum((Decimal(str(row.current_balance)) for row in accounts), ZERO)
    )


def _period_transactions(
    db: Session, household_id: UUID, start: date | None = None, end: date | None = None
) -> list[Transaction]:
    query = db.query(Transaction).filter(
        Transaction.household_id == household_id,
        Transaction.status.in_(ACTIVE_TX),
        Transaction.deleted_at.is_(None),
    )
    if start is not None:
        query = query.filter(Transaction.date >= start)
    if end is not None:
        query = query.filter(Transaction.date <= end)
    return query.order_by(Transaction.date, Transaction.created_at).all()


def _cash_impact(
    tx: Transaction,
    cash_ids: set[UUID],
    account_types: dict[UUID, str],
) -> Decimal:
    """Net effect of one transaction on the household cash pool."""
    amount = Decimal(str(tx.amount))
    impact = ZERO
    if tx.account_id in cash_ids:
        impact += account_delta(tx.type, amount)
    if tx.counterparty_account_id and tx.counterparty_account_id in cash_ids:
        other = counterparty_delta(tx.type, amount)
        if other is not None:
            impact += other
    # Internal cash↔cash transfers already cancel via account + counterparty deltas.
    _ = account_types
    return quantize_money(impact)


def cash_as_of(
    db: Session,
    household_id: UUID,
    *,
    as_of: date,
    accounts: list[Account] | None = None,
) -> Decimal:
    """Cash pool balance at end of ``as_of`` (undo later activity)."""
    accounts = accounts if accounts is not None else _cash_accounts(db, household_id)
    cash_ids = {row.id for row in accounts}
    account_types = {row.id: row.type for row in accounts}
    total = _cash_total(accounts)
    later = _period_transactions(db, household_id, start=as_of + timedelta(days=1))
    for tx in later:
        total -= _cash_impact(tx, cash_ids, account_types)
    return quantize_money(total)


def compute_cash_flow(
    db: Session,
    household: Household,
    *,
    period_start: date | None = None,
    period_end: date | None = None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    default_start, default_end = current_month_bounds(today)
    start = period_start or default_start
    end = period_end or default_end
    if end < start:
        raise ValueError("period_end must be on or after period_start")

    accounts = _cash_accounts(db, household.id)
    cash_ids = {row.id for row in accounts}
    account_types = {row.id: row.type for row in accounts}

    opening = cash_as_of(db, household.id, as_of=start - timedelta(days=1), accounts=accounts)
    closing = cash_as_of(db, household.id, as_of=end, accounts=accounts)

    rows = _period_transactions(db, household.id, start=start, end=end)
    income = ZERO
    expenses = ZERO
    giving = ZERO
    transfers_net = ZERO
    by_day: dict[date, dict[str, Decimal]] = {}

    cursor = start
    while cursor <= end:
        by_day[cursor] = {
            "income": ZERO,
            "expenses": ZERO,
            "giving": ZERO,
            "transfers_net": ZERO,
        }
        cursor += timedelta(days=1)

    for tx in rows:
        amount = quantize_money(Decimal(str(tx.amount)))
        day = by_day.get(tx.date)
        if day is None:
            continue
        if tx.type == "income":
            income += amount
            day["income"] += amount
        elif tx.type == "expense":
            expenses += amount
            day["expenses"] += amount
        elif tx.type == "giving":
            giving += amount
            day["giving"] += amount
        elif tx.type == "transfer":
            impact = _cash_impact(tx, cash_ids, account_types)
            transfers_net += impact
            day["transfers_net"] += impact

    income = quantize_money(income)
    expenses = quantize_money(expenses)
    giving = quantize_money(giving)
    transfers_net = quantize_money(transfers_net)
    surplus = quantize_money(income - expenses - giving)

    running = opening
    daily: list[dict] = []
    for day_date in sorted(by_day):
        bucket = by_day[day_date]
        day_income = quantize_money(bucket["income"])
        day_expenses = quantize_money(bucket["expenses"])
        day_giving = quantize_money(bucket["giving"])
        day_transfers = quantize_money(bucket["transfers_net"])
        # Full cash impact for the day (includes refunds, debt, etc.)
        day_txs = [tx for tx in rows if tx.date == day_date]
        day_cash_delta = quantize_money(
            sum((_cash_impact(tx, cash_ids, account_types) for tx in day_txs), ZERO)
        )
        running = quantize_money(running + day_cash_delta)
        daily.append(
            {
                "date": day_date,
                "income": day_income,
                "expenses": day_expenses,
                "giving": day_giving,
                "transfers_net": day_transfers,
                "net": quantize_money(day_income - day_expenses - day_giving),
                "closing_cash": running,
            }
        )

    return {
        "period_start": start,
        "period_end": end,
        "opening_cash": opening,
        "closing_cash": closing,
        "income": income,
        "expenses": expenses,
        "giving": giving,
        "transfers_net": transfers_net,
        "surplus": surplus,
        "daily": daily,
    }
