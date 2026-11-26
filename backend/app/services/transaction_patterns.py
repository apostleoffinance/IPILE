"""Deterministic recurring-payment and transaction anomaly detection.

Signals are advisory only. This module never creates recurring templates,
changes balances, blocks transactions, or labels a transaction as fraud.
"""
from __future__ import annotations

import re
from calendar import monthrange
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal
from statistics import median


def _payee_key(transaction) -> str:
    merchant = (transaction.merchant or "").lower().strip()
    bank_sender_markers = (
        "gtbank", "gtco", "accessbank", "zenithbank", "firstbank",
        "ubagroup", "fidelitybank", "stanbicibtc", "fcmb", "sterling",
        "wemabank", "alat", "moniepoint", "kuda", "opay", "palmpay",
    )
    merchant_root = merchant.split(".", 1)[0]
    if any(marker in merchant_root for marker in bank_sender_markers):
        value = transaction.description or ""
    else:
        value = merchant or transaction.description or ""
    value = value.lower()
    value = re.sub(
        r"\b(?:ref|reference|transaction|session|auth|id)\s*[:#-]?\s*[a-z0-9/-]+",
        " ",
        value,
    )
    value = re.sub(r"\b\d{4,}\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    normalized = " ".join(value.split())
    if normalized in {
        "bank alert", "credit alert", "debit alert", "transaction alert",
        "payment alert", "transfer alert", "account alert",
    }:
        return ""
    return normalized


def _amount(transaction) -> Decimal:
    return Decimal(str(transaction.amount))


def _advance_expected_date(last_date: date, frequency: str) -> date:
    if frequency == "weekly":
        return last_date + timedelta(days=7)
    if frequency == "biweekly":
        return last_date + timedelta(days=14)
    months = {"monthly": 1, "quarterly": 3, "annual": 12}[frequency]
    month_index = last_date.month - 1 + months
    year = last_date.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(last_date.day, monthrange(year, month)[1]))


def _frequency(intervals: list[int]) -> str | None:
    if not intervals:
        return None
    typical = median(intervals)
    candidates = (
        ("weekly", 7, 2),
        ("biweekly", 14, 3),
        ("monthly", 30, 5),
        ("quarterly", 91, 9),
        ("annual", 365, 20),
    )
    for name, target, tolerance in candidates:
        if abs(typical - target) <= tolerance and all(
            abs(value - target) <= tolerance for value in intervals
        ):
            return name
    return None


def detect_recurring_payments(
    transactions: Iterable,
    *,
    today: date,
    lookahead_days: int = 45,
) -> list[dict]:
    """Find likely repeating income/expenses from at least three observations."""
    groups: dict[tuple, list] = defaultdict(list)
    for row in transactions:
        if row.type not in {"income", "expense"} or row.status not in {"cleared", "reconciled"}:
            continue
        if row.deleted_at is not None:
            continue
        payee = _payee_key(row)
        if not payee:
            continue
        key = (row.account_id, row.currency.upper(), row.type, row.category_id, payee)
        groups[key].append(row)

    candidates: list[dict] = []
    for (account_id, currency, tx_type, category_id, payee), rows in groups.items():
        # Collapse same-day repeats so a split/duplicate alert cannot fabricate cadence.
        by_day = {}
        for row in rows:
            by_day.setdefault(row.date, row)
        ordered = sorted(by_day.values(), key=lambda item: item.date)
        if len(ordered) < 3:
            continue
        intervals = [(right.date - left.date).days for left, right in zip(ordered, ordered[1:])]
        frequency = _frequency(intervals)
        if frequency is None:
            continue
        expected = _advance_expected_date(ordered[-1].date, frequency)
        overdue_days = (today - expected).days
        if overdue_days > 35:
            continue
        if overdue_days > 5:
            signal_code = "recurring_payment_missed"
            severity = "warning"
            title = "Expected recurring transaction not seen"
            detail = (
                f"{payee.title()} was expected on {expected.isoformat()}, but no "
                "matching transaction has been recorded."
            )
        elif expected <= today + timedelta(days=lookahead_days):
            signal_code = "recurring_payment_upcoming"
            severity = "info"
            title = "Expected recurring transaction"
            detail = (
                f"{payee.title()} is likely to repeat {frequency}; the next occurrence "
                f"is expected on {expected.isoformat()}."
            )
        else:
            signal_code = "recurring_payment_detected"
            severity = "info"
            title = "Recurring transaction pattern detected"
            detail = (
                f"{payee.title()} appears to repeat {frequency}; its next expected "
                f"date is {expected.isoformat()}."
            )
        amounts = [_amount(row) for row in ordered]
        typical_amount = Decimal(str(median(amounts)))
        stable = typical_amount > 0 and (
            max(abs(value - typical_amount) for value in amounts) / typical_amount
        ) <= Decimal("0.25")
        candidates.append({
            "code": signal_code,
            "severity": severity,
            "title": title,
            "detail": detail,
            "evidence": {
                "payee": payee,
                "transaction_type": tx_type,
                "frequency": frequency,
                "currency": currency,
                "typical_amount": str(typical_amount.quantize(Decimal("0.01"))),
                "amount_stable": stable,
                "observations": len(ordered),
                "last_seen": ordered[-1].date.isoformat(),
                "expected_next_date": expected.isoformat(),
                "account_id": str(account_id),
                "category_id": str(category_id) if category_id else None,
                "confidence": "high" if stable and len(ordered) >= 4 else "medium",
            },
        })
    return sorted(candidates, key=lambda item: item["evidence"]["expected_next_date"])


def detect_unusual_transactions(
    transactions: Iterable,
    *,
    today: date,
    lookback_days: int = 30,
    baseline_days: int = 180,
    minimum_history: int = 4,
    multiplier: Decimal = Decimal("3.0"),
) -> list[dict]:
    """Flag recent transactions materially above their own payee baseline."""
    rows = [
        row for row in transactions
        if row.type in {"income", "expense"}
        and row.status in {"cleared", "reconciled"}
        and row.deleted_at is None
        and row.currency
    ]
    signals: list[dict] = []
    for current in rows:
        if not (today - timedelta(days=lookback_days) <= current.date <= today):
            continue
        key = (
            current.account_id,
            current.currency.upper(),
            current.type,
            current.category_id,
            _payee_key(current),
        )
        if not key[-1]:
            continue
        history = [
            row for row in rows
            if row.id != current.id
            and row.date < current.date
            and row.date >= current.date - timedelta(days=baseline_days)
            and (
                row.account_id,
                row.currency.upper(),
                row.type,
                row.category_id,
                _payee_key(row),
            ) == key
        ]
        if len(history) < minimum_history:
            continue
        baseline = Decimal(str(median([_amount(row) for row in history])))
        amount = _amount(current)
        if baseline <= 0 or amount < baseline * multiplier:
            continue
        ratio = (amount / baseline).quantize(Decimal("0.01"))
        signals.append({
            "code": "unusually_large_transaction",
            "severity": "warning",
            "title": "Transaction is larger than usual",
            "detail": (
                f"{(current.merchant or current.description or 'This payee')} is "
                f"{ratio}× its historical typical amount. Check that this is expected."
            ),
            "evidence": {
                "transaction_id": str(current.id),
                "date": current.date.isoformat(),
                "amount": str(amount),
                "currency": current.currency.upper(),
                "historical_median": str(baseline.quantize(Decimal("0.01"))),
                "multiple": str(ratio),
                "history_count": len(history),
                "account_id": str(current.account_id),
                "category_id": str(current.category_id) if current.category_id else None,
            },
        })
    return sorted(signals, key=lambda item: Decimal(item["evidence"]["multiple"]), reverse=True)


def detect_transaction_patterns(transactions: Iterable, *, today: date) -> list[dict]:
    rows = list(transactions)
    return (
        detect_recurring_payments(rows, today=today)
        + detect_unusual_transactions(rows, today=today)
    )
