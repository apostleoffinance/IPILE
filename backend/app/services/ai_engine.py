"""AI analyst over verified engine payloads only. Never invents figures."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Protocol

from app.money import format_money, quantize_money

MONEY_RE = re.compile(r"(?<![\w.])-?\d{1,3}(?:,\d{3})*\.\d{2}(?![\w.])|-?\d+\.\d{2}")
PERCENT_RE = re.compile(r"-?\d+(?:\.\d+)?%")


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class TemplateModel:
    """Deterministic local model used when no external AI key is configured."""

    def complete(self, system: str, user: str) -> str:
        # user payload is JSON-like text; pick verified facts already listed
        lines = [line.strip("- ").strip() for line in user.splitlines() if line.strip()]
        facts = [line for line in lines if line and not line.startswith("{")]
        if not facts:
            return "I can only explain verified household metrics provided in this request."
        return "Based on verified engine metrics: " + " ".join(facts[:4])


class InventingModel:
    """Test double that invents figures — must be rejected by the analyst."""

    def complete(self, system: str, user: str) -> str:
        return "Your household spent ₦999999.99 on food and health is 12.34."


def flatten_allowed_numbers(payload: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
            return
        if isinstance(value, list):
            for child in value:
                walk(child)
            return
        if isinstance(value, bool):
            return
        if isinstance(value, int | float | Decimal):
            amount = quantize_money(Decimal(str(value)))
            allowed.add(format_money(amount))
            allowed.add(str(amount))
            return
        if isinstance(value, str):
            text = value.strip()
            if re.fullmatch(r"-?\d+(\.\d{1,2})?", text):
                amount = quantize_money(Decimal(text))
                allowed.add(format_money(amount))
                allowed.add(text)
                allowed.add(f"{amount:.2f}")

    walk(payload)
    return allowed


def extract_money_mentions(text: str) -> list[str]:
    found: list[str] = []
    for match in MONEY_RE.findall(text.replace("₦", "").replace(",", "")):
        try:
            found.append(format_money(Decimal(match)))
        except Exception:
            continue
    return found


def validate_response(text: str, payload: dict[str, Any]) -> str:
    allowed = flatten_allowed_numbers(payload)
    invented = []
    for mention in extract_money_mentions(text):
        if mention not in allowed and mention.replace("-", "") not in {
            item.replace("-", "") for item in allowed
        }:
            # allow integers that appear as whole amounts without cents in payload
            whole = mention.split(".")[0] + ".00"
            if whole not in allowed and mention not in allowed:
                invented.append(mention)
    if invented:
        raise ValueError(
            "AI response invented figures not present in verified payload: "
            + ", ".join(sorted(set(invented)))
        )
    return text


def build_prompt(payload: dict[str, Any]) -> tuple[str, str]:
    system = (
        "You are the Family Finance OS analyst. Explain only verified metrics. "
        "Do not invent any financial figures. Every amount you mention must appear "
        "exactly in the verified payload."
    )
    facts: list[str] = []
    health = payload.get("health") or {}
    if health:
        facts.append(f"Financial health score is {health.get('score')} ({health.get('label')}).")
    sts = payload.get("safe_to_spend") or {}
    if sts:
        facts.append(f"Current Safe to Spend is {sts.get('current')}.")
    wealth = payload.get("wealth") or {}
    if wealth:
        facts.append(f"Net worth is {wealth.get('net_worth')}.")
    budgets = payload.get("budgets") or []
    for row in budgets[:5]:
        facts.append(
            f"{row.get('name')} budget spent {row.get('spent_total')} "
            f"of {row.get('allocated_total')}."
        )
    obligations = payload.get("obligations") or []
    for row in obligations[:5]:
        facts.append(
            f"{row.get('name')} next due {row.get('next_due_date')} amount {row.get('amount')} "
            f"coverage {row.get('coverage')}."
        )
    funds = payload.get("funds") or []
    for row in funds[:5]:
        facts.append(
            f"{row.get('name')} fund has {row.get('current_amount')} of {row.get('target_amount')}."
        )
    user = "Verified facts:\n" + "\n".join(f"- {fact}" for fact in facts)
    user += "\n\nPayload:\n" + str(payload)
    return system, user


def explain(payload: dict[str, Any], model: ModelClient | None = None) -> str:
    client = model or TemplateModel()
    system, user = build_prompt(payload)
    raw = client.complete(system, user)
    return validate_response(raw, payload)
