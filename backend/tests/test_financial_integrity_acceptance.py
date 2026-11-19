"""Independent acceptance vectors for household financial arithmetic.

Expected values below are calculated from the stated inputs, not by calling
production orchestration helpers to derive the expected result.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.services.allocation_engine import AllocationRuleSpec, allocate
from app.services.balances import account_delta, apply_flags, counterparty_delta
from app.services.budget_engine import line_status, remaining, spent_from_lines, utilization
from app.services.obligation_engine import add_months, obligation_monthly
from app.services.safe_to_spend import protected_in_spendable
from app.services.safe_to_spend_engine import (
    current_safe_to_spend,
    forecast_safe_to_spend,
    period_safe_to_spend,
    purchase_check,
)
from app.services.wealth_engine import (
    AccountSpec,
    AssetSpec,
    InvestmentSpec,
    LiabilitySpec,
    compute_net_worth,
)


D = Decimal


def _rule(name: str, kind: str, priority: int, *, amount: str | None = None,
          rate: str | None = None, basis: str = "recognized_income",
          source_id: UUID | None = None) -> AllocationRuleSpec:
    return AllocationRuleSpec(
        id=None, name=name, type=kind, basis=basis,
        rate=D(rate) if rate is not None else None,
        amount=D(amount) if amount is not None else None,
        priority=priority, mandatory=True, destination_type="fund",
        income_source_id=source_id,
    )


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("income", "2000000.00"),
        ("refund", "2000000.00"),
        ("expense", "-150000.00"),
        ("giving", "-100000.00"),
        ("investment", "-250000.00"),
        ("debt_payment", "-50000.00"),
    ],
)
def test_balance_deltas_match_independent_ledger(kind: str, expected: str) -> None:
    amount = D("2000000.00") if kind in {"income", "refund"} else D("150000.00")
    if kind == "giving":
        amount = D("100000.00")
    if kind == "investment":
        amount = D("250000.00")
    if kind == "debt_payment":
        amount = D("50000.00")
    assert account_delta(kind, amount) == D(expected)


def test_transfer_is_balance_neutral_across_two_accounts() -> None:
    opening_a, opening_b, transfer = D("1000000.00"), D("500000.00"), D("200000.00")
    closing_a = opening_a + account_delta("transfer", transfer)
    closing_b = opening_b + counterparty_delta("transfer", transfer)
    assert (closing_a, closing_b) == (D("800000.00"), D("700000.00"))
    assert closing_a + closing_b == opening_a + opening_b


def test_pending_and_cleared_balance_policies_are_distinct() -> None:
    assert apply_flags("pending") == (False, True)
    assert apply_flags("cleared") == (True, True)
    assert apply_flags("reconciled") == (True, True)
    assert apply_flags("void") == (False, False)


def test_allocation_percentage_fixed_and_remainder_reconcile_exactly() -> None:
    # 10% giving = 200,000; fixed obligations = 300,000; remainder = 1,500,000.
    rules = [
        _rule("Giving", "percentage", 1, rate="0.10"),
        _rule("Obligations", "fixed", 2, amount="300000.00"),
        _rule("Remaining", "remainder", 3, basis="remaining"),
    ]
    result = allocate(D("2000000.00"), rules)
    assert [line.amount for line in result.lines] == [
        D("200000.00"), D("300000.00"), D("1500000.00")
    ]
    assert result.total_allocated == D("2000000.00")
    assert result.surplus == D("0.00")
    assert result.total_allocated + result.surplus == D("2000000.00")


def test_allocation_caps_later_rules_at_available_cash() -> None:
    result = allocate(
        D("100000.00"),
        [
            _rule("Priority one", "fixed", 1, amount="80000.00"),
            _rule("Priority two", "fixed", 2, amount="50000.00"),
        ],
    )
    assert [line.amount for line in result.lines] == [D("80000.00"), D("20000.00")]
    assert result.total_allocated == D("100000.00")
    assert result.surplus == D("0.00")
    assert result.unfunded_mandatory[0].requested == D("50000.00")


def test_specific_source_allocation_uses_only_that_source() -> None:
    source_a, source_b = uuid4(), uuid4()
    result = allocate(
        D("300000.00"),
        [_rule("Source allocation", "percentage", 1, rate="0.50",
               basis="specific_source", source_id=source_a)],
        {source_a: D("100000.00"), source_b: D("200000.00")},
    )
    assert result.lines[0].amount == D("50000.00")
    assert result.surplus == D("250000.00")


def test_safe_to_spend_reconciles_all_deductions() -> None:
    # 1.4m liquid - 850k obligations - 50k pending outflows - 150k protected.
    current = current_safe_to_spend(D("1400000"), D("850000"), D("50000"), D("150000"))
    assert current == D("350000.00")
    period = period_safe_to_spend(current, D("400000"), D("100000"), D("50000"), D("25000"))
    assert period == D("575000.00")
    forecast = forecast_safe_to_spend(D("1800000"), D("1100000"), D("90000"))
    assert forecast == D("610000.00")


def test_purchase_check_boundaries_are_exact() -> None:
    healthy = purchase_check(D("260000"), D("350000"), D("90000"))
    assert healthy.affordable and healthy.remaining_current_sts == D("90000.00")
    assert healthy.severity == "healthy"
    breached = purchase_check(D("260001"), D("350000"), D("90000"))
    assert breached.affordable and breached.buffer_breached
    assert breached.remaining_current_sts == D("89999.00")
    impossible = purchase_check(D("350001"), D("350000"), D("0"))
    assert not impossible.affordable
    assert impossible.remaining_current_sts == D("-1.00")


def test_budget_refunds_reduce_net_spend_and_overspend_is_negative_remaining() -> None:
    spend = spent_from_lines([
        ("expense", D("125000.00")),
        ("giving", D("25000.00")),
        ("refund", D("10000.00")),
    ])
    assert spend == D("140000.00")
    assert remaining(D("150000.00"), spend) == D("10000.00")
    assert utilization(D("150000.00"), spend) == D("0.93")
    assert line_status(D("150000.00"), spend) == "warning"
    assert remaining(D("100000.00"), spend) == D("-40000.00")
    assert line_status(D("100000.00"), spend) == "critical"


@pytest.mark.parametrize(
    ("amount", "frequency", "expected"),
    [
        ("450000.00", "quarterly", "150000.00"),
        ("600000.00", "annual", "50000.00"),
        ("10000.00", "weekly", "43333.33"),
        ("75000.00", "monthly", "75000.00"),
    ],
)
def test_obligation_monthly_equivalents(amount: str, frequency: str, expected: str) -> None:
    assert obligation_monthly(D(amount), frequency) == D(expected)


def test_calendar_month_rollover_clamps_end_of_month() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)


def test_wealth_rollup_matches_independent_assets_minus_liabilities() -> None:
    cash_id, investment_id = uuid4(), uuid4()
    result = compute_net_worth(
        [
            AccountSpec(cash_id, "bank", D("1400000.00"), True, False),
            AccountSpec(investment_id, "investment", D("300000.00"), True, False),
        ],
        [AssetSpec("property", D("2500000.00"), True)],
        [InvestmentSpec(D("350000.00"), True, investment_id)],
        [
            LiabilitySpec("loan", D("500000.00"), True),
            LiabilitySpec("credit", D("150000.00"), True),
        ],
    )
    # Linked investment account is replaced by its investment valuation (350k).
    assert result.total_assets == D("4250000.00")
    assert result.total_liabilities == D("650000.00")
    assert result.net_worth == D("3600000.00")
    assert result.investments == D("350000.00")



def test_protected_fund_inside_protected_spendable_account_is_not_double_counted() -> None:
    account_id = uuid4()
    account = SimpleNamespace(
        id=account_id,
        status="active",
        type="bank",
        include_in_safe_to_spend=True,
        business_id=None,
        is_protected=True,
        available_balance=D("100000.00"),
    )
    fund = SimpleNamespace(
        id=uuid4(),
        account_id=account_id,
        is_protected=True,
        status="active",
        deleted_at=None,
        current_amount=D("25000.00"),
    )
    # The whole account balance already includes and protects the fund balance.
    assert protected_in_spendable([account], [fund]) == D("100000.00")
