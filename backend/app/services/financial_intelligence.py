"""Persist proactive, explainable financial signals as household alerts."""
from __future__ import annotations

import hashlib
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.household import Household
from app.models.transaction import Transaction
from app.services.transaction_patterns import detect_transaction_patterns


_RECURRING_ALERT_TYPES = {
    "recurring_payment_upcoming",
    "recurring_payment_missed",
}


def _upsert_open_alert(
    db: Session,
    *,
    household_id: UUID,
    alert_type: str,
    severity: str,
    title: str,
    body: str,
    related_entity_type: str,
    related_entity_id: UUID,
    period_key: str,
) -> bool:
    """Create/update an open alert without resurrecting one a user has read."""
    existing = (
        db.query(Alert)
        .filter(
            Alert.household_id == household_id,
            Alert.type == alert_type,
            Alert.related_entity_id == related_entity_id,
            Alert.period_key == period_key,
        )
        .first()
    )
    if existing is not None:
        if existing.status != "open":
            return False
        existing.severity = severity
        existing.title = title
        existing.body = body[:500]
        db.add(existing)
        return False
    db.add(
        Alert(
            household_id=household_id,
            type=alert_type,
            severity=severity,
            title=title[:200],
            body=body[:500],
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            period_key=period_key[:80],
            status="open",
        )
    )
    return True


def run_financial_intelligence(
    db: Session,
    household: Household,
    *,
    today: date | None = None,
) -> dict:
    """Turn current transaction patterns into deduplicated household alerts.

    Only household-shared, cleared/reconciled transactions are considered.
    Alerts are advisory and never post or modify ledger transactions.
    """
    today = today or date.today()
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household.id,
            Transaction.access_scope == "shared",
            Transaction.status.in_(("cleared", "reconciled")),
            Transaction.deleted_at.is_(None),
            Transaction.date >= today - timedelta(days=800),
            Transaction.date <= today,
            Transaction.type.in_(("income", "expense")),
        )
        .order_by(Transaction.date.asc())
        .limit(5000)
        .all()
    )
    patterns = detect_transaction_patterns(transactions, today=today)
    active_recurring: set[tuple[str, UUID, str]] = set()
    active_anomalies: set[UUID] = set()
    created = 0

    for pattern in patterns:
        code = pattern["code"]
        evidence = pattern["evidence"]
        if code in _RECURRING_ALERT_TYPES:
            account_id = UUID(evidence["account_id"])
            payee_hash = hashlib.sha256(evidence["payee"].encode("utf-8")).hexdigest()[:12]
            period_key = f"{evidence['expected_next_date']}:{payee_hash}"
            active_recurring.add((code, account_id, period_key))
            created += int(
                _upsert_open_alert(
                    db,
                    household_id=household.id,
                    alert_type=code,
                    severity=pattern["severity"],
                    title=pattern["title"],
                    body=pattern["detail"],
                    related_entity_type="account",
                    related_entity_id=account_id,
                    period_key=period_key,
                )
            )
        elif code == "unusually_large_transaction":
            transaction_id = UUID(evidence["transaction_id"])
            active_anomalies.add(transaction_id)
            created += int(
                _upsert_open_alert(
                    db,
                    household_id=household.id,
                    alert_type=code,
                    severity=pattern["severity"],
                    title=pattern["title"],
                    body=pattern["detail"],
                    related_entity_type="transaction",
                    related_entity_id=transaction_id,
                    period_key=str(transaction_id),
                )
            )

    # A newly recorded payment advances the expected date. Close obsolete
    # recurring alerts so the household is not left with stale reminders.
    recurring_alerts = (
        db.query(Alert)
        .filter(
            Alert.household_id == household.id,
            Alert.type.in_(tuple(_RECURRING_ALERT_TYPES)),
            Alert.status == "open",
        )
        .all()
    )
    resolved_recurring = 0
    for alert in recurring_alerts:
        key = (alert.type, alert.related_entity_id, alert.period_key)
        if key not in active_recurring:
            alert.status = "resolved"
            db.add(alert)
            resolved_recurring += 1

    # Anomaly alerts remain visible until read while the transaction is recent.
    # Corrected, voided or aged-out signals are resolved on the next refresh.
    anomaly_alerts = (
        db.query(Alert)
        .filter(
            Alert.household_id == household.id,
            Alert.type == "unusually_large_transaction",
            Alert.status == "open",
        )
        .all()
    )
    resolved_anomalies = 0
    for alert in anomaly_alerts:
        if alert.related_entity_id not in active_anomalies:
            alert.status = "resolved"
            db.add(alert)
            resolved_anomalies += 1

    db.flush()
    return {
        "patterns_evaluated": len(patterns),
        "recurring_alerts": len(active_recurring),
        "anomaly_alerts": len(active_anomalies),
        "alerts_created": created,
        "recurring_alerts_resolved": resolved_recurring,
        "anomaly_alerts_resolved": resolved_anomalies,
    }
