"""Provider-neutral intelligence for normalized bank-alert events.

This module is deliberately deterministic: it does not call an LLM, infer an
unknown currency, or post a transaction. It enriches a parsed event with
explainable category/account suggestions and a confidence assessment.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from email.utils import parseaddr
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.services.import_adapters import ImportRow


@dataclass(frozen=True)
class FinancialEvent:
    provider: str
    provider_event_id: str | None
    external_id: str
    occurred_on: str
    amount: str
    currency: str | None
    direction: str
    description: str | None
    merchant: str | None
    sender_verified: bool


# Bank sender domains are aliases, not an authorization list. Authorization
# remains the responsibility of the provider adapter before this module runs.
_INSTITUTION_ALIASES = {
    "gtbank": {"gtbank", "gtco", "guarantytrust"},
    "accessbank": {"accessbank", "accessbankplc"},
    "zenithbank": {"zenithbank"},
    "firstbank": {"firstbank", "firstbanknigeria"},
    "uba": {"uba", "ubagroup"},
    "fidelitybank": {"fidelitybank"},
    "stanbicibtc": {"stanbicibtc"},
    "fcmb": {"fcmb"},
    "sterling": {"sterling", "sterlingbank"},
    "wema": {"wema", "wemabank", "alat"},
    "moniepoint": {"moniepoint"},
    "kuda": {"kuda"},
    "opay": {"opay", "opayweb", "opayinc", "opaynigeria"},
    "palmpay": {"palmpay"},
}


def _token(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def sender_institution_key(sender: str) -> str:
    address = parseaddr(sender)[1] or sender
    domain = address.rsplit("@", 1)[-1].lower()
    root = domain.split(".", 1)[0]
    normalized = _token(root)
    for canonical, aliases in _INSTITUTION_ALIASES.items():
        if normalized in aliases:
            return canonical
    return normalized


def match_alert_account(
    accounts: list[Account], sender: str, currency: str | None
) -> tuple[Account | None, str]:
    """Return an account only for a unique institution match."""
    institution_key = sender_institution_key(sender)
    matches = [
        account for account in accounts
        if _token(account.institution) in _INSTITUTION_ALIASES.get(
            institution_key, {institution_key}
        )
    ]
    if len(matches) != 1:
        return None, "needs_selection" if not matches else "ambiguous_institution"
    account = matches[0]
    if currency and account.currency.upper() != currency.upper():
        return account, "currency_mismatch"
    if not currency:
        return account, "currency_unconfirmed"
    return account, "exact_institution"


_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    ("income", ("salary", "payroll", "wages"), ("salary", "income")),
    (
        "income",
        ("interest received", "dividend", "investment return"),
        ("investment income", "income"),
    ),
    ("expense", ("grocery", "supermarket", "market", "foodstuff"), ("groceries", "food")),
    ("expense", ("fuel", "petrol", "diesel", "uber", "bolt", "transport"), ("transport", "fuel")),
    (
        "expense",
        ("electricity", "water bill", "internet", "airtime", "utility"),
        ("utilities", "bills"),
    ),
    ("expense", ("rent", "landlord", "lease"), ("housing", "rent")),
    ("expense", ("hospital", "pharmacy", "clinic", "medical"), ("health", "healthcare")),
    ("expense", ("school", "tuition", "lesson", "university"), ("education",)),
    ("expense", ("restaurant", "cafe", "food delivery", "takeaway"), ("dining", "food")),
    ("expense", ("subscription", "netflix", "spotify", "icloud"), ("subscriptions",)),
    ("expense", ("pos purchase", "online purchase", "shopping"), ("shopping",)),
)


def suggest_category(
    db: Session,
    household_id: UUID,
    description: str | None,
    merchant: str | None,
    tx_type: str,
    classification_context: str | None = None,
) -> tuple[str | None, int, str | None]:
    """Suggest an existing household category; never create or hardcode one."""
    text = f"{merchant or ''} {description or ''} {classification_context or ''}".lower()
    categories = (
        db.query(Category)
        .filter(
            Category.household_id == household_id,
            Category.deleted_at.is_(None),
            Category.kind == tx_type,
        )
        .all()
    )
    for kind, needles, category_names in _CATEGORY_RULES:
        if kind != tx_type or not any(needle in text for needle in needles):
            continue
        wanted = {_token(name) for name in category_names}
        match = next((item for item in categories if _token(item.name) in wanted), None)
        if match:
            return match.name, 5, f"Matched description/merchant rule: {match.name}"
        return None, 0, "A likely category was detected, but no matching household category exists."
    return None, 0, "No reliable category rule matched; choose a category during review."


def assess_confidence(
    *,
    sender_verified: bool,
    amount_valid: bool,
    date_valid: bool,
    direction_valid: bool,
    currency_explicit: bool,
    account_match: str,
    category_points: int,
) -> dict[str, Any]:
    score = (
        (25 if sender_verified else 0)
        + (15 if amount_valid else 0)
        + (15 if date_valid else 0)
        + (15 if direction_valid else 0)
        + (15 if currency_explicit else 0)
        + (15 if account_match == "exact_institution" else 0)
        + category_points
    )
    score = min(score, 100)
    reasons: list[str] = []
    if not sender_verified:
        reasons.append("Sender authentication has not been verified.")
    if not currency_explicit:
        reasons.append("Currency is missing or ambiguous.")
    if account_match != "exact_institution":
        reasons.append(f"Account match requires attention: {account_match.replace('_', ' ')}.")
    if category_points == 0:
        reasons.append("Category is a suggestion only and needs user review.")
    band = "high" if score >= 85 else "medium" if score >= 65 else "low"
    return {"score": score, "band": band, "reasons": reasons}


def enrich_bank_alert(
    db: Session,
    household_id: UUID,
    row: ImportRow,
    *,
    sender: str,
    provider: str,
    provider_event_id: str | None,
    sender_verified: bool,
    classification_context: str | None = None,
) -> tuple[ImportRow, Account | None, dict[str, Any]]:
    """Normalize and enrich an alert from any trusted ingestion provider."""
    accounts = (
        db.query(Account)
        .filter(
            Account.household_id == household_id,
            Account.deleted_at.is_(None),
            Account.status == "active",
        )
        .all()
    )
    account, account_match = match_alert_account(accounts, sender, row.currency)
    category_name, category_points, category_reason = suggest_category(
        db,
        household_id,
        row.description,
        row.merchant,
        row.type,
        classification_context,
    )
    confidence = assess_confidence(
        sender_verified=sender_verified,
        amount_valid=row.amount > Decimal("0"),
        date_valid=row.date is not None,
        direction_valid=row.type in {"income", "expense"},
        currency_explicit=bool(row.currency),
        account_match=account_match,
        category_points=category_points,
    )
    enriched = replace(row, category_name=category_name)
    event = FinancialEvent(
        provider=provider,
        provider_event_id=provider_event_id,
        external_id=row.external_id,
        occurred_on=row.date.isoformat(),
        amount=str(row.amount),
        currency=row.currency,
        direction=row.type,
        description=row.description,
        merchant=row.merchant,
        sender_verified=sender_verified,
    )
    intelligence = {
        "confidence_score": confidence["score"],
        "confidence_band": confidence["band"],
        "review_reasons": confidence["reasons"],
        "category_suggestion": {
            "name": category_name,
            "confidence": "rule_match" if category_name else "unmatched",
            "reason": category_reason,
        },
        "account_match": account_match,
        "suggested_account_id": str(account.id) if account else None,
        "sender_verified": sender_verified,
        "normalized_event": asdict(event),
    }
    return enriched, account, intelligence
