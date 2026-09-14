from decimal import Decimal
from uuid import uuid4

from app.services.wealth_engine import (
    AccountSpec,
    AssetSpec,
    GoalSpec,
    InvestmentSpec,
    LiabilitySpec,
    apply_liability_payment,
    compute_net_worth,
    net_worth,
)


def test_net_worth_is_assets_minus_liabilities() -> None:
    assert net_worth(Decimal("1400000.00"), Decimal("400000.00")) == Decimal("1000000.00")


def test_linked_account_is_not_double_counted() -> None:
    account_id = uuid4()
    result = compute_net_worth(
        [
            AccountSpec(account_id, "bank", Decimal("1000000.00"), True, False),
            AccountSpec(uuid4(), "savings", Decimal("200000.00"), True, True),
        ],
        [AssetSpec("cash", Decimal("1000000.00"), True, account_id)],
        [],
        [],
    )
    assert result.total_assets == Decimal("1200000.00")
    assert result.assets.cash == Decimal("1000000.00")
    assert result.assets.savings == Decimal("200000.00")
    assert result.emergency_fund == Decimal("200000.00")
    assert result.net_worth == Decimal("1200000.00")


def test_investment_and_account_dedup() -> None:
    account_id = uuid4()
    result = compute_net_worth(
        [AccountSpec(account_id, "investment", Decimal("500000.00"), True, False)],
        [],
        [InvestmentSpec(Decimal("550000.00"), True, account_id)],
        [],
    )
    assert result.investments == Decimal("550000.00")
    assert result.total_assets == Decimal("550000.00")


def test_paid_off_liability_drops_out_of_debt() -> None:
    result = compute_net_worth(
        [AccountSpec(uuid4(), "bank", Decimal("1000000.00"), True, False)],
        [],
        [],
        [
            LiabilitySpec("loan", Decimal("400000.00"), True, "active"),
        ],
    )
    assert result.debt == Decimal("400000.00")
    assert result.net_worth == Decimal("600000.00")
    paid = compute_net_worth(
        [AccountSpec(uuid4(), "bank", Decimal("1000000.00"), True, False)],
        [],
        [],
        [LiabilitySpec("loan", Decimal("0.00"), True, "paid_off")],
    )
    assert paid.debt == Decimal("0.00")
    assert paid.net_worth == Decimal("1000000.00")
    remaining, status = apply_liability_payment(Decimal("400000.00"), Decimal("400000.00"))
    assert remaining == Decimal("0.00")
    assert status == "paid_off"


def test_unlinked_emergency_goal_counts_in_emergency() -> None:
    result = compute_net_worth(
        [AccountSpec(uuid4(), "bank", Decimal("1000000.00"), True, False)],
        [],
        [],
        [],
        [GoalSpec(Decimal("300000.00"), True)],
    )
    assert result.emergency_fund == Decimal("300000.00")
    assert result.net_worth == Decimal("1000000.00")


def test_linked_emergency_goal_is_not_double_counted() -> None:
    account_id = uuid4()
    result = compute_net_worth(
        [AccountSpec(account_id, "savings", Decimal("300000.00"), True, True)],
        [],
        [],
        [],
        [GoalSpec(Decimal("300000.00"), True, account_id)],
    )
    assert result.emergency_fund == Decimal("300000.00")
    assert result.net_worth == Decimal("300000.00")
