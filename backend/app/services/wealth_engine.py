"""Net worth arithmetic. Never use float. Never double-count linked accounts."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.money import quantize_money

ASSET_TYPES = frozenset(
    {"cash", "savings", "investment", "business", "property", "vehicle", "other"}
)
LIABILITY_TYPES = frozenset({"loan", "credit", "mortgage", "other"})
INVESTMENT_TYPES = frozenset({"equity", "fund", "bond", "treasury", "other"})
INVESTMENT_TX_TYPES = frozenset({"buy", "sell", "dividend", "adjustment"})
ACCOUNT_ASSET_BUCKET = {
    "bank": "cash",
    "cash": "cash",
    "wallet": "cash",
    "savings": "savings",
    "investment": "investments",
    "business": "business",
    "other": "other",
}
LIABILITY_BUCKET = {
    "loan": "loans",
    "mortgage": "loans",
    "credit": "credit",
    "other": "other_debt",
}


@dataclass(frozen=True)
class AccountSpec:
    id: UUID
    type: str
    current_balance: Decimal
    include_in_net_worth: bool
    is_emergency: bool
    status: str = "active"


@dataclass(frozen=True)
class AssetSpec:
    type: str
    current_value: Decimal
    include_in_net_worth: bool
    account_id: UUID | None = None
    is_emergency: bool = False


@dataclass(frozen=True)
class InvestmentSpec:
    current_value: Decimal
    include_in_net_worth: bool
    account_id: UUID | None = None


@dataclass(frozen=True)
class GoalSpec:
    current_amount: Decimal
    is_emergency: bool
    account_id: UUID | None = None


@dataclass(frozen=True)
class LiabilitySpec:
    type: str
    current_balance: Decimal
    include_in_net_worth: bool
    status: str = "active"
    account_id: UUID | None = None


@dataclass
class AssetBuckets:
    cash: Decimal = field(default_factory=lambda: Decimal("0.00"))
    savings: Decimal = field(default_factory=lambda: Decimal("0.00"))
    investments: Decimal = field(default_factory=lambda: Decimal("0.00"))
    business: Decimal = field(default_factory=lambda: Decimal("0.00"))
    property: Decimal = field(default_factory=lambda: Decimal("0.00"))
    vehicle: Decimal = field(default_factory=lambda: Decimal("0.00"))
    other: Decimal = field(default_factory=lambda: Decimal("0.00"))

    def total(self) -> Decimal:
        return quantize_money(
            self.cash
            + self.savings
            + self.investments
            + self.business
            + self.property
            + self.vehicle
            + self.other
        )


@dataclass
class LiabilityBuckets:
    loans: Decimal = field(default_factory=lambda: Decimal("0.00"))
    credit: Decimal = field(default_factory=lambda: Decimal("0.00"))
    other_debt: Decimal = field(default_factory=lambda: Decimal("0.00"))

    def total(self) -> Decimal:
        return quantize_money(self.loans + self.credit + self.other_debt)


@dataclass(frozen=True)
class NetWorthResult:
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    emergency_fund: Decimal
    investments: Decimal
    debt: Decimal
    assets: AssetBuckets
    liabilities: LiabilityBuckets


def net_worth(total_assets: Decimal, total_liabilities: Decimal) -> Decimal:
    return quantize_money(quantize_money(total_assets) - quantize_money(total_liabilities))


def _add_asset(buckets: AssetBuckets, kind: str, amount: Decimal) -> None:
    amount = quantize_money(amount)
    if kind == "cash":
        buckets.cash += amount
    elif kind == "savings":
        buckets.savings += amount
    elif kind in {"investment", "investments"}:
        buckets.investments += amount
    elif kind == "business":
        buckets.business += amount
    elif kind == "property":
        buckets.property += amount
    elif kind == "vehicle":
        buckets.vehicle += amount
    else:
        buckets.other += amount


def _add_liability(buckets: LiabilityBuckets, kind: str, amount: Decimal) -> None:
    amount = quantize_money(amount)
    bucket = LIABILITY_BUCKET.get(kind, "other_debt")
    if bucket == "loans":
        buckets.loans += amount
    elif bucket == "credit":
        buckets.credit += amount
    else:
        buckets.other_debt += amount


def compute_net_worth(
    accounts: list[AccountSpec],
    assets: list[AssetSpec],
    investments: list[InvestmentSpec],
    liabilities: list[LiabilitySpec],
    goals: list[GoalSpec] | None = None,
) -> NetWorthResult:
    asset_buckets = AssetBuckets()
    liability_buckets = LiabilityBuckets()
    linked: set[UUID] = set()
    emergency = Decimal("0.00")

    for asset in assets:
        if asset.account_id is not None:
            linked.add(asset.account_id)
        if not asset.include_in_net_worth:
            continue
        _add_asset(asset_buckets, asset.type, asset.current_value)
        if asset.is_emergency:
            emergency += quantize_money(asset.current_value)

    for row in investments:
        if row.account_id is not None:
            linked.add(row.account_id)
        if not row.include_in_net_worth:
            continue
        _add_asset(asset_buckets, "investments", row.current_value)

    for account in accounts:
        if account.status != "active":
            continue
        if account.is_emergency and account.id not in linked:
            emergency += quantize_money(account.current_balance)
        if not account.include_in_net_worth:
            continue
        if account.id in linked:
            continue
        bucket = ACCOUNT_ASSET_BUCKET.get(account.type)
        if bucket is None:
            continue
        _add_asset(asset_buckets, bucket, account.current_balance)

    for goal in goals or []:
        if not goal.is_emergency:
            continue
        if goal.account_id is not None:
            continue
        emergency += quantize_money(goal.current_amount)

    for liability in liabilities:
        if liability.status == "paid_off":
            continue
        if not liability.include_in_net_worth:
            continue
        _add_liability(liability_buckets, liability.type, liability.current_balance)

    total_assets = asset_buckets.total()
    total_liabilities = liability_buckets.total()
    return NetWorthResult(
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=net_worth(total_assets, total_liabilities),
        emergency_fund=quantize_money(emergency),
        investments=quantize_money(asset_buckets.investments),
        debt=total_liabilities,
        assets=asset_buckets,
        liabilities=liability_buckets,
    )


def apply_investment_tx(
    current_value: Decimal,
    cost_basis: Decimal,
    tx_type: str,
    amount: Decimal,
) -> tuple[Decimal, Decimal]:
    amount = quantize_money(amount)
    value = quantize_money(current_value)
    basis = quantize_money(cost_basis)
    if tx_type == "buy":
        return quantize_money(value + amount), quantize_money(basis + amount)
    if tx_type == "sell":
        return quantize_money(max(Decimal("0.00"), value - amount)), basis
    if tx_type == "dividend":
        return quantize_money(value + amount), basis
    if tx_type == "adjustment":
        return amount, basis
    raise ValueError(f"Unsupported investment transaction type: {tx_type}")


def apply_liability_payment(current_balance: Decimal, amount: Decimal) -> tuple[Decimal, str]:
    remaining = quantize_money(quantize_money(current_balance) - quantize_money(amount))
    if remaining < 0:
        remaining = Decimal("0.00")
    status = "paid_off" if remaining == Decimal("0.00") else "active"
    return remaining, status
