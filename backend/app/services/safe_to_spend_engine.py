"""Safe to Spend and purchase-check arithmetic. Never use float."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.money import quantize_money


@dataclass(frozen=True)
class PurchaseCheckResult:
    amount: Decimal
    affordable: bool
    severity: str
    remaining_current_sts: Decimal
    buffer_breached: bool
    recommended_action: str


def current_safe_to_spend(
    liquid_spendable: Decimal,
    unfunded_due_or_overdue: Decimal,
    pending_outbound: Decimal,
    protected_in_spendable: Decimal,
) -> Decimal:
    return quantize_money(
        quantize_money(liquid_spendable)
        - quantize_money(unfunded_due_or_overdue)
        - quantize_money(pending_outbound)
        - quantize_money(protected_in_spendable)
    )


def period_safe_to_spend(
    current: Decimal,
    remaining_expected_income: Decimal,
    remaining_mandatory_allocations: Decimal,
    remaining_unfunded_occurrences: Decimal,
    remaining_protected_fund_contributions: Decimal,
) -> Decimal:
    return quantize_money(
        quantize_money(current)
        + quantize_money(remaining_expected_income)
        - quantize_money(remaining_mandatory_allocations)
        - quantize_money(remaining_unfunded_occurrences)
        - quantize_money(remaining_protected_fund_contributions)
    )


def forecast_safe_to_spend(
    projected_liquid: Decimal,
    projected_commitments: Decimal,
    minimum_buffer: Decimal,
) -> Decimal:
    return quantize_money(
        quantize_money(projected_liquid)
        - quantize_money(projected_commitments)
        - quantize_money(minimum_buffer)
    )


def purchase_check(
    amount: Decimal,
    current_sts: Decimal,
    minimum_buffer: Decimal,
    *,
    budget_exceeded: bool = False,
    raids_protected: bool = False,
) -> PurchaseCheckResult:
    purchase = quantize_money(amount)
    remaining = quantize_money(quantize_money(current_sts) - purchase)
    buffer = quantize_money(minimum_buffer)
    buffer_breached = remaining < buffer
    if remaining < 0 or raids_protected:
        return PurchaseCheckResult(
            amount=purchase,
            affordable=False,
            severity="critical",
            remaining_current_sts=remaining,
            buffer_breached=True,
            recommended_action="delay",
        )
    if buffer_breached or budget_exceeded:
        action = "delay / reduce / use surplus" if buffer_breached else "review budget"
        return PurchaseCheckResult(
            amount=purchase,
            affordable=True,
            severity="warning",
            remaining_current_sts=remaining,
            buffer_breached=buffer_breached,
            recommended_action=action,
        )
    return PurchaseCheckResult(
        amount=purchase,
        affordable=True,
        severity="healthy",
        remaining_current_sts=remaining,
        buffer_breached=False,
        recommended_action="proceed",
    )
