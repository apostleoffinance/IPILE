"""Financial calendar event aggregation. Rules stay data-driven."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy.orm import Session

from app.models.fund import SinkingFund
from app.models.goal import Goal
from app.models.obligation import Obligation, ObligationOccurrence
from app.models.recurring import RecurringTransaction
from app.models.wealth import Liability
from app.money import quantize_money
from app.schemas.calendar import CalendarEventOut
from app.services.obligation_engine import coverage, coverage_label

ZERO = Decimal("0.00")


def _stable_id(kind: str, entity_id: UUID, on: date) -> UUID:
    return uuid5(NAMESPACE_URL, f"calendar:{kind}:{entity_id}:{on.isoformat()}")


def _next_due_day(today: date, due_day: int, horizon_end: date) -> date | None:
    day = max(1, min(due_day, 31))
    year, month = today.year, today.month
    while True:
        capped = min(day, monthrange(year, month)[1])
        candidate = date(year, month, capped)
        if candidate >= today and candidate <= horizon_end:
            return candidate
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        if date(year, month, 1) > horizon_end:
            return None


def _approx_next_month_contribution(today: date) -> date:
    if today.month == 12:
        return date(today.year + 1, 1, 1)
    return date(today.year, today.month + 1, 1)


def build_calendar_events(
    db: Session,
    household_id: UUID,
    *,
    days: int = 30,
    today: date | None = None,
) -> list[CalendarEventOut]:
    today = today or date.today()
    end = today + timedelta(days=days)
    events: list[CalendarEventOut] = []

    rows = (
        db.query(ObligationOccurrence, Obligation)
        .join(Obligation, Obligation.id == ObligationOccurrence.obligation_id)
        .filter(
            ObligationOccurrence.household_id == household_id,
            Obligation.deleted_at.is_(None),
            ObligationOccurrence.due_date >= today,
            ObligationOccurrence.due_date <= end,
        )
        .order_by(ObligationOccurrence.due_date)
        .all()
    )
    for occurrence, obligation in rows:
        ratio = coverage(occurrence.funded_amount, occurrence.amount)
        events.append(
            CalendarEventOut(
                id=occurrence.id,
                kind="obligation",
                title=obligation.name,
                date=occurrence.due_date,
                amount=quantize_money(occurrence.amount),
                status=occurrence.status,
                coverage_label=coverage_label(ratio),
                obligation_id=obligation.id,
                occurrence_id=occurrence.id,
            )
        )

    recurring = (
        db.query(RecurringTransaction)
        .filter(
            RecurringTransaction.household_id == household_id,
            RecurringTransaction.deleted_at.is_(None),
            RecurringTransaction.is_active.is_(True),
            RecurringTransaction.next_date >= today,
            RecurringTransaction.next_date <= end,
        )
        .order_by(RecurringTransaction.next_date)
        .all()
    )
    for row in recurring:
        events.append(
            CalendarEventOut(
                id=_stable_id("recurring", row.id, row.next_date),
                kind="recurring",
                title=row.merchant or row.description or "Recurring",
                date=row.next_date,
                amount=quantize_money(Decimal(str(row.amount))),
                status="scheduled",
            )
        )

    contrib_date = _approx_next_month_contribution(today)
    if today <= contrib_date <= end:
        funds = (
            db.query(SinkingFund)
            .filter(
                SinkingFund.household_id == household_id,
                SinkingFund.deleted_at.is_(None),
                SinkingFund.status == "active",
            )
            .all()
        )
        for fund in funds:
            monthly = quantize_money(Decimal(str(fund.monthly_contribution)))
            if monthly <= ZERO:
                continue
            events.append(
                CalendarEventOut(
                    id=_stable_id("fund", fund.id, contrib_date),
                    kind="fund_contribution",
                    title=f"{fund.name} contribution",
                    date=contrib_date,
                    amount=monthly,
                    status="planned",
                )
            )

    liabilities = (
        db.query(Liability)
        .filter(
            Liability.household_id == household_id,
            Liability.deleted_at.is_(None),
            Liability.status == "active",
            Liability.due_day.is_not(None),
        )
        .all()
    )
    for liability in liabilities:
        due = _next_due_day(today, int(liability.due_day), end)
        if due is None:
            continue
        events.append(
            CalendarEventOut(
                id=_stable_id("liability", liability.id, due),
                kind="liability",
                title=liability.name,
                date=due,
                amount=quantize_money(Decimal(str(liability.minimum_payment or ZERO))),
                status="due",
            )
        )

    goals = (
        db.query(Goal)
        .filter(
            Goal.household_id == household_id,
            Goal.deleted_at.is_(None),
            Goal.status == "active",
            Goal.monthly_contribution.is_not(None),
        )
        .all()
    )
    if today <= contrib_date <= end:
        for goal in goals:
            monthly = quantize_money(Decimal(str(goal.monthly_contribution)))
            if monthly <= ZERO:
                continue
            events.append(
                CalendarEventOut(
                    id=_stable_id("goal", goal.id, contrib_date),
                    kind="goal_contribution",
                    title=f"{goal.name} contribution",
                    date=contrib_date,
                    amount=monthly,
                    status="planned",
                )
            )

    events.sort(key=lambda row: (row.date, row.kind, row.title))
    return events
