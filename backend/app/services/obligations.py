from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.fund import SinkingFund
from app.models.obligation import Obligation, ObligationOccurrence
from app.money import format_money, quantize_money
from app.schemas.obligation import ObligationOut, OccurrenceOut
from app.services.alerts import upsert_alert
from app.services.obligation_engine import (
    PAYABLE_SKIP,
    coverage,
    coverage_label,
    due_dates_through_horizon,
    obligation_monthly,
    occurrence_status,
)

PRIORITIES = frozenset({"critical", "high", "medium", "low"})
OBLIGATION_STATUSES = frozenset({"active", "paused", "completed", "cancelled"})


def obligation_category(db: Session, household_id: UUID, name: str = "Obligation") -> Category:
    row = (
        db.query(Category)
        .filter(
            Category.household_id == household_id,
            Category.name == name,
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if row:
        return row
    row = Category(
        household_id=household_id,
        name=name,
        kind="system",
        is_system=True,
        sort_order=180,
    )
    db.add(row)
    db.flush()
    return row


def serialize_occurrence(row: ObligationOccurrence) -> OccurrenceOut:
    ratio = coverage(Decimal(str(row.funded_amount)), Decimal(str(row.amount)))
    return OccurrenceOut(
        id=row.id,
        obligation_id=row.obligation_id,
        due_date=row.due_date,
        amount=quantize_money(Decimal(str(row.amount))),
        funded_amount=quantize_money(Decimal(str(row.funded_amount))),
        coverage=format_money(ratio),
        coverage_label=coverage_label(ratio),
        status=row.status,
        paid_at=row.paid_at,
        transaction_id=row.transaction_id,
    )


def serialize_obligation(db: Session, obligation: Obligation) -> ObligationOut:
    fund_name = None
    already_funded = Decimal("0.00")
    if obligation.fund_id:
        fund = db.get(SinkingFund, obligation.fund_id)
        if fund:
            fund_name = fund.name
            already_funded = quantize_money(Decimal(str(fund.current_amount)))
    monthly = obligation_monthly(
        Decimal(str(obligation.amount)),
        obligation.frequency,
        today=date.today(),
        next_due_date=obligation.next_due_date,
        already_funded=already_funded,
    )
    occurrences = (
        db.query(ObligationOccurrence)
        .filter(ObligationOccurrence.obligation_id == obligation.id)
        .order_by(ObligationOccurrence.due_date)
        .all()
    )
    serialized = [serialize_occurrence(row) for row in occurrences]
    next_row = next(
        (row for row in serialized if row.status in {"upcoming", "due", "missed"}),
        None,
    )
    return ObligationOut(
        id=obligation.id,
        household_id=obligation.household_id,
        name=obligation.name,
        amount=quantize_money(Decimal(str(obligation.amount))),
        currency=obligation.currency,
        frequency=obligation.frequency,
        next_due_date=obligation.next_due_date,
        priority=obligation.priority,
        sinking_fund=obligation.sinking_fund,
        auto_allocate=obligation.auto_allocate,
        category_id=obligation.category_id,
        beneficiary_name=obligation.beneficiary_name,
        beneficiary_member_id=obligation.beneficiary_member_id,
        fund_id=obligation.fund_id,
        fund_name=fund_name,
        status=obligation.status,
        required_monthly=monthly,
        next_occurrence=next_row,
        occurrences=serialized,
    )


def generate_occurrences(db: Session, obligation: Obligation, today: date | None = None) -> None:
    today = today or date.today()
    existing = {
        row.due_date: row
        for row in db.query(ObligationOccurrence)
        .filter(ObligationOccurrence.obligation_id == obligation.id)
        .all()
    }
    for due in due_dates_through_horizon(
        obligation.next_due_date,
        obligation.frequency,
        today=today,
    ):
        row = existing.get(due)
        if row is None:
            row = ObligationOccurrence(
                household_id=obligation.household_id,
                obligation_id=obligation.id,
                due_date=due,
                amount=obligation.amount,
                funded_amount=Decimal("0.00"),
                status="upcoming",
            )
            db.add(row)
            db.flush()
            existing[due] = row
        elif row.status not in PAYABLE_SKIP:
            row.amount = obligation.amount
        row.status = occurrence_status(due, today, row.status)
        if row.status == "missed":
            upsert_alert(
                db,
                household_id=obligation.household_id,
                alert_type="obligation_missed",
                severity="critical",
                title=f"{obligation.name} is late",
                body=f"{obligation.name} was due {due.isoformat()} and is not paid.",
                related_entity_type="obligation_occurrence",
                related_entity_id=row.id,
                period_key=f"{obligation.id}:{due.isoformat()}",
            )
    db.flush()
    _allocate_fund_to_occurrences(db, obligation)
    _evaluate_coverage_alerts(db, obligation, today)


def _allocate_fund_to_occurrences(db: Session, obligation: Obligation) -> None:
    if not obligation.fund_id:
        return
    fund = db.get(SinkingFund, obligation.fund_id)
    if fund is None:
        return
    remaining = quantize_money(Decimal(str(fund.current_amount)))
    rows = (
        db.query(ObligationOccurrence)
        .filter(ObligationOccurrence.obligation_id == obligation.id)
        .order_by(ObligationOccurrence.due_date)
        .all()
    )
    for row in rows:
        if row.status in PAYABLE_SKIP:
            continue
        allocated = min(quantize_money(Decimal(str(row.amount))), remaining)
        row.funded_amount = allocated
        remaining -= allocated
        db.add(row)


def _evaluate_coverage_alerts(db: Session, obligation: Obligation, today: date) -> None:
    rows = (
        db.query(ObligationOccurrence)
        .filter(
            ObligationOccurrence.obligation_id == obligation.id,
            ObligationOccurrence.status.in_(("upcoming", "due", "missed")),
        )
        .order_by(ObligationOccurrence.due_date)
        .all()
    )
    row = rows[0] if rows else None
    if row is None:
        return
    ratio = coverage(Decimal(str(row.funded_amount)), Decimal(str(row.amount)))
    days_left = (row.due_date - today).days
    if ratio >= Decimal("1.00"):
        return
    severity = "warning"
    if days_left <= 14 and ratio < Decimal("0.80"):
        severity = "critical"
    upsert_alert(
        db,
        household_id=obligation.household_id,
        alert_type="obligation_underfunded",
        severity=severity,
        title=f"{obligation.name} is underfunded",
        body=f"{obligation.name} due {row.due_date.isoformat()} is {coverage_label(ratio)}.",
        related_entity_type="obligation_occurrence",
        related_entity_id=row.id,
        period_key=f"{obligation.id}:{row.due_date.isoformat()}",
    )


def mark_paid(occurrence: ObligationOccurrence, transaction_id: UUID) -> None:
    occurrence.status = "paid"
    occurrence.funded_amount = occurrence.amount
    occurrence.paid_at = datetime.now(UTC)
    occurrence.transaction_id = transaction_id
