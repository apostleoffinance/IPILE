from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account, AccountBalance
from app.money import quantize_money

INFLOW_TYPES = frozenset({"income", "refund", "withdrawal"})
OUTFLOW_TYPES = frozenset(
    {"expense", "investment", "debt_payment", "capital_contribution", "giving"}
)
TRANSFER_TYPE = "transfer"
ACTIVE_STATUSES = frozenset({"pending", "cleared", "reconciled"})


class BalanceError(ValueError):
    pass


def account_delta(tx_type: str, amount: Decimal) -> Decimal:
    amount = quantize_money(amount)
    if tx_type in INFLOW_TYPES:
        return amount
    if tx_type in OUTFLOW_TYPES:
        return -amount
    if tx_type == TRANSFER_TYPE:
        return -amount
    raise BalanceError(f"Unsupported transaction type: {tx_type}")


def counterparty_delta(tx_type: str, amount: Decimal) -> Decimal | None:
    amount = quantize_money(amount)
    if tx_type == TRANSFER_TYPE:
        return amount
    if tx_type == "capital_contribution":
        return amount
    if tx_type == "withdrawal":
        return -amount
    return None


def apply_flags(status: str) -> tuple[bool, bool]:
    if status == "pending":
        return False, True
    if status in {"cleared", "reconciled"}:
        return True, True
    return False, False


def apply_delta(account: Account, delta: Decimal, *, current: bool, available: bool) -> None:
    delta = quantize_money(delta)
    if current:
        account.current_balance = quantize_money(Decimal(account.current_balance) + delta)
    if available:
        account.available_balance = quantize_money(Decimal(account.available_balance) + delta)


def snapshot_balance(db: Session, account: Account) -> None:
    db.add(
        AccountBalance(
            household_id=account.household_id,
            account_id=account.id,
            balance=quantize_money(Decimal(account.current_balance)),
            as_of=datetime.now(UTC),
            source="computed",
        )
    )


def apply_transaction_effect(
    db: Session,
    *,
    account: Account,
    counterparty: Account | None,
    tx_type: str,
    amount: Decimal,
    status: str,
    reverse: bool = False,
) -> None:
    if status not in ACTIVE_STATUSES and not reverse:
        return
    current, available = apply_flags(status)
    if not current and not available:
        return
    delta = account_delta(tx_type, amount)
    other = counterparty_delta(tx_type, amount)
    if reverse:
        delta = -delta
        other = None if other is None else -other
    apply_delta(account, delta, current=current, available=available)
    snapshot_balance(db, account)
    if other is not None:
        if counterparty is None:
            raise BalanceError("Transfer requires a counterparty account.")
        apply_delta(counterparty, other, current=current, available=available)
        snapshot_balance(db, counterparty)
