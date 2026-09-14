"""Household automation chain. Scheduler ticks are idempotent by period_key."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.allocation import AllocationLine, AllocationRun
from app.models.automation import SchedulerTick
from app.models.fund import SinkingFund
from app.models.household import Household
from app.models.obligation import Obligation
from app.models.transaction import Transaction
from app.money import format_money, quantize_money
from app.services.alerts import upsert_alert
from app.services.allocations import (
    ensure_period_allocation,
    period_bounds,
)
from app.services.balances import apply_transaction_effect
from app.services.budgets import evaluate_budget_alerts
from app.services.funds import record_contribution
from app.services.notifications import sync_notifications_from_alerts
from app.services.obligations import generate_occurrences
from app.services.safe_to_spend import compute_safe_to_spend


def _liquid_source(db: Session, household_id: UUID) -> Account | None:
    return (
        db.query(Account)
        .filter(
            Account.household_id == household_id,
            Account.deleted_at.is_(None),
            Account.status == "active",
            Account.type.in_(("bank", "cash", "wallet")),
            Account.include_in_safe_to_spend.is_(True),
        )
        .order_by(Account.created_at)
        .first()
    )


def _fund_from_allocation_lines(
    db: Session,
    household: Household,
    run: AllocationRun,
    *,
    today: date,
) -> dict:
    """Apply fund destination lines once per allocation run (idempotent via period marker)."""
    source = _liquid_source(db, household.id)
    if source is None:
        return {"funded_lines": 0, "total": "0.00"}
    lines = (
        db.query(AllocationLine)
        .filter(
            AllocationLine.run_id == run.id,
            AllocationLine.destination_type == "fund",
            AllocationLine.destination_id.is_not(None),
        )
        .all()
    )
    funded = 0
    total = Decimal("0.00")
    period_tag = f"auto:{run.id}"
    for line in lines:
        amount = quantize_money(Decimal(str(line.amount)))
        if amount <= 0 or line.destination_id is None:
            continue
        fund = (
            db.query(SinkingFund)
            .filter(
                SinkingFund.id == line.destination_id,
                SinkingFund.household_id == household.id,
                SinkingFund.deleted_at.is_(None),
            )
            .first()
        )
        if fund is None:
            continue
        already = (
            db.query(Transaction)
            .filter(
                Transaction.household_id == household.id,
                Transaction.fund_id == fund.id,
                Transaction.type == "transfer",
                Transaction.description == period_tag,
                Transaction.deleted_at.is_(None),
            )
            .first()
        )
        if already is not None:
            continue
        if Decimal(str(source.current_balance)) < amount:
            continue
        dest = None
        if fund.account_id:
            dest = db.get(Account, fund.account_id)
        tx = Transaction(
            household_id=household.id,
            account_id=source.id,
            counterparty_account_id=dest.id if dest else None,
            amount=amount,
            currency=household.base_currency,
            type="transfer",
            date=today,
            description=period_tag,
            fund_id=fund.id,
            status="cleared",
            import_source="manual",
        )
        db.add(tx)
        db.flush()
        apply_transaction_effect(
            db,
            account=source,
            counterparty=dest,
            tx_type="transfer",
            amount=amount,
            status="cleared",
        )
        record_contribution(
            db,
            fund,
            account_id=source.id,
            amount=amount,
            contribution_date=today,
            transaction_id=tx.id,
        )
        funded += 1
        total += amount
        db.refresh(source)
    return {"funded_lines": funded, "total": format_money(total)}


def run_due_date_checks(db: Session, household: Household, today: date | None = None) -> dict:
    today = today or date.today()
    obligations = (
        db.query(Obligation)
        .filter(Obligation.household_id == household.id, Obligation.deleted_at.is_(None))
        .all()
    )
    checked = 0
    for obligation in obligations:
        generate_occurrences(db, obligation, today=today)
        checked += 1
        if obligation.fund_id:
            fund = db.get(SinkingFund, obligation.fund_id)
            if fund is None:
                continue
            # approaching due within 30 days with shortfall
            next_due = obligation.next_due_date
            if next_due and 0 <= (next_due - today).days <= 30:
                required = quantize_money(Decimal(str(obligation.amount)))
                current = quantize_money(Decimal(str(fund.current_amount)))
                if current < required:
                    upsert_alert(
                        db,
                        household_id=household.id,
                        alert_type="obligation_underfunded",
                        severity="warning" if current >= required * Decimal("0.80") else "critical",
                        title=f"{obligation.name} needs funding",
                        body=(
                            f"{obligation.name} due {next_due.isoformat()} has "
                            f"{format_money(current)} of {format_money(required)}."
                        ),
                        related_entity_type="obligation",
                        related_entity_id=obligation.id,
                        period_key=f"{obligation.id}:{next_due.isoformat()}:due",
                    )
    return {"obligations_checked": checked}


def run_income_recognized_chain(
    db: Session, household: Household, today: date | None = None
) -> dict:
    today = today or date.today()
    run = ensure_period_allocation(db, household, today=today)
    fund_result = _fund_from_allocation_lines(db, household, run, today=today)
    evaluate_budget_alerts(db, household.id)
    due = run_due_date_checks(db, household, today=today)
    sts = compute_safe_to_spend(db, household, today=today)
    notes = sync_notifications_from_alerts(db, household.id)
    return {
        "allocation_run_id": str(run.id),
        "recognized_income": format_money(run.recognized_income),
        "total_allocated": format_money(run.total_allocated),
        "funds": fund_result,
        "due": due,
        "safe_to_spend": format_money(sts.current),
        "notifications_created": len(notes),
    }


def run_daily_chain(db: Session, household: Household, today: date | None = None) -> dict:
    today = today or date.today()
    evaluate_budget_alerts(db, household.id)
    due = run_due_date_checks(db, household, today=today)
    compute_safe_to_spend(db, household, today=today)
    notes = sync_notifications_from_alerts(db, household.id)
    return {
        "due": due,
        "notifications_created": len(notes),
        "horizon": (today + timedelta(days=30)).isoformat(),
    }


def run_tick(
    db: Session,
    household: Household,
    *,
    tick_type: str,
    period_key: str | None = None,
    today: date | None = None,
) -> tuple[SchedulerTick, bool]:
    today = today or date.today()
    start, end = period_bounds(household, today)
    if period_key is None:
        if tick_type == "income_recognized":
            period_key = f"{start.isoformat()}:{end.isoformat()}"
        else:
            period_key = today.isoformat()
    existing = (
        db.query(SchedulerTick)
        .filter(
            SchedulerTick.household_id == household.id,
            SchedulerTick.tick_type == tick_type,
            SchedulerTick.period_key == period_key,
        )
        .first()
    )
    if existing is not None:
        return existing, True
    if tick_type == "income_recognized":
        result = run_income_recognized_chain(db, household, today=today)
    else:
        result = run_daily_chain(db, household, today=today)
    tick = SchedulerTick(
        household_id=household.id,
        tick_type=tick_type,
        period_key=period_key,
        status="completed",
        result=result,
    )
    db.add(tick)
    db.flush()
    return tick, False
