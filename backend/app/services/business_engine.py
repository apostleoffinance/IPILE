"""Business P/L and family invested/return. Never use float."""

from dataclasses import dataclass
from decimal import Decimal

from app.money import quantize_money

BUSINESS_TX_TYPES = frozenset(
    {"revenue", "expense", "capital_contribution", "withdrawal", "payroll"}
)
BUSINESS_STATUSES = frozenset({"active", "paused", "closed"})


@dataclass(frozen=True)
class BusinessLine:
    type: str
    amount: Decimal


@dataclass(frozen=True)
class BusinessPnL:
    revenue: Decimal
    expenses: Decimal
    profit: Decimal
    family_invested: Decimal
    family_withdrawn: Decimal
    current_business_equity: Decimal
    family_return: Decimal


def sum_type(lines: list[BusinessLine], *types: str) -> Decimal:
    wanted = set(types)
    total = Decimal("0.00")
    for line in lines:
        if line.type in wanted:
            total += quantize_money(line.amount)
    return quantize_money(total)


def family_invested(lines: list[BusinessLine]) -> Decimal:
    return sum_type(lines, "capital_contribution")


def family_withdrawn(lines: list[BusinessLine]) -> Decimal:
    return sum_type(lines, "withdrawal")


def revenue_total(lines: list[BusinessLine]) -> Decimal:
    return sum_type(lines, "revenue")


def expense_total(lines: list[BusinessLine]) -> Decimal:
    return sum_type(lines, "expense", "payroll")


def profit(lines: list[BusinessLine]) -> Decimal:
    return quantize_money(revenue_total(lines) - expense_total(lines))


def ledger_equity(lines: list[BusinessLine]) -> Decimal:
    return quantize_money(
        family_invested(lines) + profit(lines) - family_withdrawn(lines)
    )


def family_return(withdrawn: Decimal, equity: Decimal, invested: Decimal) -> Decimal:
    return quantize_money(
        quantize_money(withdrawn) + quantize_money(equity) - quantize_money(invested)
    )


def compute_pnl(lines: list[BusinessLine], account_balance: Decimal | None = None) -> BusinessPnL:
    invested = family_invested(lines)
    withdrawn = family_withdrawn(lines)
    equity = (
        quantize_money(account_balance)
        if account_balance is not None
        else ledger_equity(lines)
    )
    return BusinessPnL(
        revenue=revenue_total(lines),
        expenses=expense_total(lines),
        profit=profit(lines),
        family_invested=invested,
        family_withdrawn=withdrawn,
        current_business_equity=equity,
        family_return=family_return(withdrawn, equity, invested),
    )
