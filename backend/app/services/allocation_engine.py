"""Deterministic allocation. Rule names and destinations are household data."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.money import quantize_money

RULE_TYPES = frozenset({"percentage", "fixed", "remainder"})
BASES = frozenset({"recognized_income", "remaining", "specific_source"})
DESTINATIONS = frozenset({"fund", "budget", "account", "obligation", "goal", "giving"})


@dataclass(frozen=True)
class AllocationRuleSpec:
    id: UUID | None
    name: str
    type: str
    basis: str
    rate: Decimal | None
    amount: Decimal | None
    priority: int
    mandatory: bool
    destination_type: str
    destination_id: UUID | None = None
    income_source_id: UUID | None = None
    created_at: str = ""


@dataclass(frozen=True)
class AllocationLineResult:
    rule_id: UUID | None
    name: str
    requested: Decimal
    amount: Decimal
    destination_type: str
    destination_id: UUID | None
    mandatory: bool
    funded: bool


@dataclass(frozen=True)
class AllocationResult:
    recognized_income: Decimal
    lines: tuple[AllocationLineResult, ...]
    total_allocated: Decimal
    surplus: Decimal
    unfunded_mandatory: tuple[AllocationLineResult, ...]


def requested_amount(
    rule: AllocationRuleSpec,
    *,
    recognized_income: Decimal,
    remaining: Decimal,
    source_amounts: dict[UUID, Decimal] | None = None,
) -> Decimal:
    if rule.type == "remainder":
        return quantize_money(remaining)
    if rule.type == "fixed":
        return quantize_money(rule.amount or Decimal("0.00"))
    rate = rule.rate or Decimal("0")
    if rule.basis == "remaining":
        pool = remaining
    elif rule.basis == "specific_source":
        amounts = source_amounts or {}
        if rule.income_source_id:
            pool = amounts.get(rule.income_source_id, Decimal("0.00"))
        else:
            pool = Decimal("0.00")
    else:
        pool = recognized_income
    return quantize_money(pool * rate)


def allocate(
    recognized_income: Decimal,
    rules: list[AllocationRuleSpec],
    source_amounts: dict[UUID, Decimal] | None = None,
) -> AllocationResult:
    income = quantize_money(recognized_income)
    remaining = income
    ordered = sorted(rules, key=lambda rule: (rule.priority, rule.created_at, rule.name))
    lines: list[AllocationLineResult] = []
    for rule in ordered:
        requested = requested_amount(
            rule,
            recognized_income=income,
            remaining=remaining,
            source_amounts=source_amounts,
        )
        if requested < 0:
            requested = Decimal("0.00")
        amount = min(requested, remaining)
        amount = quantize_money(amount)
        remaining = quantize_money(remaining - amount)
        funded = amount == requested
        lines.append(
            AllocationLineResult(
                rule_id=rule.id,
                name=rule.name,
                requested=requested,
                amount=amount,
                destination_type=rule.destination_type,
                destination_id=rule.destination_id,
                mandatory=rule.mandatory,
                funded=funded,
            )
        )
    unfunded = tuple(line for line in lines if line.mandatory and not line.funded)
    total = quantize_money(sum((line.amount for line in lines), Decimal("0.00")))
    return AllocationResult(
        recognized_income=income,
        lines=tuple(lines),
        total_allocated=total,
        surplus=remaining,
        unfunded_mandatory=unfunded,
    )
