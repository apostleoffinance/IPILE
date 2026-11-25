from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.banking import BankConnection, ReconciliationItem, ReconciliationSession
from app.models.transaction import Transaction
from app.services.bank_security import decrypt_provider_account_id
from app.services.import_adapters import ImportRow
from app.services.mono import MonoClient

MINOR_UNITS = {"NGN": 2, "GHS": 2, "KES": 2, "ZAR": 2, "USD": 2, "GBP": 2, "EUR": 2, "EGP": 2, "UGX": 0, "JPY": 0, "KRW": 0, "XOF": 0, "XAF": 0, "RWF": 0}

def minor_to_major(value: object, currency: str, *, allow_nonpositive: bool = False) -> Decimal:
    exponent = MINOR_UNITS.get(currency.upper())
    if exponent is None:
        raise ValueError(f"Unsupported currency precision for {currency}.")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Bank provider returned an invalid transaction amount.") from exc
    if not allow_nonpositive and amount <= 0:
        raise ValueError("Bank provider returned a non-positive transaction amount.")
    return (amount / (Decimal(10) ** exponent)).quantize(Decimal("0.01"))

def parse_provider_date(value: str) -> date:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError as exc:
            raise ValueError("Bank provider returned an invalid transaction date.") from exc

def _normalise(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

def _types(direction: str) -> list[str]:
    return {"expense": ["expense", "debt_payment", "giving", "investment"], "income": ["income", "refund"]}.get(direction, [direction])

def suggest_match(db: Session, item: ReconciliationItem) -> None:
    used = [row[0] for row in db.query(ReconciliationItem.matched_transaction_id).filter(
        ReconciliationItem.household_id == item.household_id,
        ReconciliationItem.matched_transaction_id.is_not(None)).all()]
    query = db.query(Transaction).filter(
        Transaction.household_id == item.household_id, Transaction.account_id == item.account_id,
        Transaction.amount == item.amount, Transaction.currency == item.currency,
        Transaction.type.in_(_types(item.type)),
        Transaction.date >= date.fromordinal(item.date.toordinal() - 3),
        Transaction.date <= date.fromordinal(item.date.toordinal() + 3),
        Transaction.status.in_(["cleared", "reconciled"]), Transaction.deleted_at.is_(None))
    if used:
        query = query.filter(~Transaction.id.in_(used))
    candidates = query.limit(25).all()
    if not candidates:
        item.status = "unmatched"
        item.match_reason = "No cleared ledger transaction matches amount, currency, direction and date."
        return
    statement = _normalise(item.merchant or item.description)
    ranked = []
    for tx in candidates:
        ledger = _normalise(tx.merchant or tx.description)
        similarity = SequenceMatcher(None, statement, ledger).ratio() if statement and ledger else 0
        days = abs((tx.date - item.date).days)
        score = 0.82 + (3 - days) * 0.025 + similarity * 0.10
        if tx.external_id and tx.external_id == item.source_reference:
            score, similarity = 1.0, 1.0
        ranked.append((score, similarity, tx, days))
    ranked.sort(key=lambda v: v[0], reverse=True)
    if len(ranked) == 1 or (ranked[0][1] >= 0.75 and ranked[0][0] - ranked[1][0] >= 0.15):
        score, _, tx, days = ranked[0]
        item.suggested_transaction_id = tx.id
        item.match_score = Decimal(str(min(score, 0.99))).quantize(Decimal("0.0001"))
        item.status = "suggested"
        item.match_reason = f"Exact financial fields; date differs by {days} day(s)."
    else:
        item.status = "conflict"
        item.match_reason = "Multiple ledger transactions match the financial fields; choose manually."

def refresh_summary(db: Session, session: ReconciliationSession) -> None:
    rows = db.query(ReconciliationItem).filter(ReconciliationItem.session_id == session.id).all()
    session.total_rows = len(rows)
    session.matched_count = sum(x.status == "matched" for x in rows)
    session.suggested_count = sum(x.status == "suggested" for x in rows)
    session.unmatched_count = sum(x.status == "unmatched" for x in rows)
    session.conflict_count = sum(x.status == "conflict" for x in rows)

def create_statement_session(db: Session, *, household_id: UUID, member_id: UUID, account: Account, rows: list[ImportRow], opening_balance: Decimal | None = None, closing_balance: Decimal | None = None) -> ReconciliationSession:
    if not rows:
        raise ValueError("The statement contains no transaction rows.")
    session = ReconciliationSession(household_id=household_id, account_id=account.id, created_by_member_id=member_id, source="statement", status="review", statement_start=min(x.date for x in rows), statement_end=max(x.date for x in rows), opening_balance=opening_balance, closing_balance=closing_balance)
    db.add(session)
    db.flush()
    duplicates = 0
    seen_references: set[str] = set()
    for row in rows:
        if not row.external_id:
            raise ValueError("Every statement row must have a stable transaction reference.")
        if row.external_id in seen_references:
            duplicates += 1
            continue
        seen_references.add(row.external_id)
        exists = db.query(ReconciliationItem.id).filter(ReconciliationItem.household_id == household_id, ReconciliationItem.account_id == account.id, ReconciliationItem.source == "statement", ReconciliationItem.source_reference == row.external_id).first()
        if exists:
            duplicates += 1
            continue
        item = ReconciliationItem(household_id=household_id, session_id=session.id, account_id=account.id, source="statement", source_reference=row.external_id, date=row.date, amount=row.amount, currency=account.currency, type=row.type, description=row.description, merchant=row.merchant, status="unmatched")
        suggest_match(db, item)
        db.add(item)
    session.duplicate_rows = duplicates
    db.flush()
    refresh_summary(db, session)
    if opening_balance is not None and closing_balance is not None and all(x.type in {"income", "expense"} for x in rows):
        net = sum((x.amount if x.type == "income" else -x.amount for x in rows), Decimal("0.00"))
        session.calculated_closing_balance = opening_balance + net
        session.balance_difference = session.calculated_closing_balance - closing_balance
    return session

def create_mono_session(db: Session, *, connection: BankConnection, account: Account, client: MonoClient) -> ReconciliationSession:
    if not connection.provider_account_id_encrypted:
        raise ValueError("This bank connection has no active provider account reference.")
    provider_id = decrypt_provider_account_id(connection.provider_account_id_encrypted)
    currency = (connection.currency or account.currency).upper()
    if currency != account.currency.upper() or currency not in MINOR_UNITS:
        raise ValueError("Connected bank currency is unsupported or does not match the selected account.")
    raw_rows, meta = [], {}
    for page in range(1, 21):
        rows, meta = client.fetch_transactions(provider_id, page=page)
        raw_rows.extend(rows)
        if not rows or not meta.get("next"):
            break
    session = ReconciliationSession(household_id=connection.household_id, account_id=account.id, created_by_member_id=connection.created_by_member_id, source="mono", status="review")
    db.add(session)
    db.flush()
    dates, duplicates = [], 0
    seen_references: set[str] = set()
    for raw in raw_rows:
        reference, kind = str(raw.get("id") or raw.get("_id") or "").strip(), str(raw.get("type") or "").lower()
        if not reference or kind not in {"debit", "credit"}:
            continue
        if reference in seen_references:
            duplicates += 1
            continue
        seen_references.add(reference)
        try:
            amount = minor_to_major(raw.get("amount"), currency)
            tx_date = parse_provider_date(str(raw.get("date") or ""))
            balance = minor_to_major(raw["balance"], currency, allow_nonpositive=True) if raw.get("balance") is not None else None
        except ValueError:
            continue
        exists = db.query(ReconciliationItem.id).filter(ReconciliationItem.household_id == connection.household_id, ReconciliationItem.account_id == account.id, ReconciliationItem.source == "mono", ReconciliationItem.source_reference == reference).first()
        if exists:
            duplicates += 1
            continue
        description = str(raw.get("narration") or raw.get("description") or "")[:500] or None
        item = ReconciliationItem(household_id=connection.household_id, session_id=session.id, account_id=account.id, source="mono", source_reference=reference, date=tx_date, amount=amount, currency=currency, type="expense" if kind == "debit" else "income", description=description, merchant=description[:200] if description else None, provider_category=str(raw.get("category") or "")[:80] or None, provider_balance=balance, status="unmatched")
        suggest_match(db, item)
        db.add(item)
        dates.append(tx_date)
    session.duplicate_rows = duplicates
    if dates:
        session.statement_start, session.statement_end = min(dates), max(dates)
    db.flush()
    refresh_summary(db, session)
    connection.last_synced_at = datetime.now(UTC)
    connection.last_error = "Sync reached the 20-page safety limit." if meta.get("next") else None
    db.add(connection)
    return session
