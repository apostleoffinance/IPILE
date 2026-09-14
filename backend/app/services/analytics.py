from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.analytics import FinancialScore, FinancialSnapshot, Report
from app.models.household import Household
from app.models.obligation import Obligation, ObligationOccurrence
from app.money import format_money, quantize_money
from app.services.allocations import period_bounds
from app.services.health import (
    _spend_by_category,
    _top_overspend,
    compute_household_health,
    gather_period_activity,
    serialize_health,
    upsert_score,
)
from app.services.health_engine import HealthResult
from app.services.obligation_engine import coverage, coverage_label
from app.services.wealth import household_net_worth


def _get_snapshot(db: Session, household_id: UUID, start: date) -> FinancialSnapshot | None:
    return (
        db.query(FinancialSnapshot)
        .filter(
            FinancialSnapshot.household_id == household_id,
            FinancialSnapshot.period_start == start,
        )
        .first()
    )


def persist_snapshot(
    db: Session,
    household: Household,
    *,
    start: date,
    end: date,
    as_of: date,
    activity: dict[str, Decimal],
    net_worth: Decimal,
    health: HealthResult,
    extra: dict | None = None,
) -> FinancialSnapshot:
    row = _get_snapshot(db, household.id, start)
    if row is None:
        row = FinancialSnapshot(household_id=household.id, period_start=start)
        db.add(row)
    row.period_end = end
    row.as_of = as_of
    row.income = activity["income"]
    row.expenses = activity["expenses"]
    row.savings = activity["savings"]
    row.investments = activity["investments"]
    row.giving = activity["giving"]
    row.debt_reduction = activity["debt_reduction"]
    row.surplus = activity["surplus"]
    row.net_worth = net_worth
    row.health_score = health.score
    payload = {
        "income": format_money(activity["income"]),
        "expenses": format_money(activity["expenses"]),
        "savings": format_money(activity["savings"]),
        "investments": format_money(activity["investments"]),
        "giving": format_money(activity["giving"]),
        "debt_reduction": format_money(activity["debt_reduction"]),
        "surplus": format_money(activity["surplus"]),
        "net_worth": format_money(net_worth),
        "health": serialize_health(health, start, end),
    }
    if extra:
        payload.update(extra)
    row.payload = payload
    db.add(row)
    db.flush()
    upsert_score(db, household, health, start, end)
    return row


def freeze_current_snapshot(
    db: Session,
    household: Household,
    *,
    today: date | None = None,
    extra: dict | None = None,
) -> FinancialSnapshot:
    today = today or date.today()
    start, end = period_bounds(household, today)
    health, start, end = compute_household_health(db, household, today)
    activity = gather_period_activity(db, household, start, end)
    wealth = household_net_worth(db, household)
    return persist_snapshot(
        db,
        household,
        start=start,
        end=end,
        as_of=today,
        activity=activity,
        net_worth=wealth.net_worth,
        health=health,
        extra=extra,
    )


def list_snapshots(db: Session, household_id: UUID) -> list[FinancialSnapshot]:
    return (
        db.query(FinancialSnapshot)
        .filter(FinancialSnapshot.household_id == household_id)
        .order_by(FinancialSnapshot.period_start)
        .all()
    )


def _upcoming_risk(db: Session, household_id: UUID, today: date) -> dict | None:
    rows = (
        db.query(ObligationOccurrence, Obligation)
        .join(Obligation, Obligation.id == ObligationOccurrence.obligation_id)
        .filter(
            ObligationOccurrence.household_id == household_id,
            Obligation.deleted_at.is_(None),
            ObligationOccurrence.due_date >= today,
            ObligationOccurrence.status.in_(("upcoming", "due", "missed")),
        )
        .order_by(ObligationOccurrence.due_date)
        .all()
    )
    if not rows:
        return None
    occurrence, obligation = rows[0]
    ratio = coverage(occurrence.funded_amount, occurrence.amount)
    return {
        "title": obligation.name,
        "date": occurrence.due_date.isoformat(),
        "amount": format_money(occurrence.amount),
        "coverage_label": coverage_label(ratio),
    }


def _best_improvement(db: Session, household_id: UUID, start: date, health: dict) -> str:
    previous = (
        db.query(FinancialScore)
        .filter(FinancialScore.household_id == household_id, FinancialScore.period_start < start)
        .order_by(FinancialScore.period_start.desc())
        .first()
    )
    if previous is None:
        return "First scored period"
    prev_components = {row["key"]: Decimal(str(row["points"])) for row in previous.components}
    best_key = None
    best_delta = Decimal("0.00")
    for row in health["components"]:
        delta = Decimal(str(row["points"])) - prev_components.get(row["key"], Decimal("0.00"))
        if best_key is None or delta > best_delta:
            best_key = row["key"]
            best_delta = delta
    if best_key is None or best_delta <= 0:
        score_delta = Decimal(str(health["score"])) - Decimal(str(previous.score))
        if score_delta > 0:
            return f"Overall health +{format_money(score_delta)}"
        return "No component improved"
    return f"{best_key.replace('_', ' ')} +{format_money(best_delta)}"


def _month_label(start: date) -> str:
    return start.strftime("%B %Y")


def build_monthly_payload(
    db: Session,
    household: Household,
    snapshot: FinancialSnapshot,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    health = snapshot.payload.get("health") or {
        "score": format_money(snapshot.health_score),
        "label": "",
        "components": [],
    }
    previous = (
        db.query(FinancialSnapshot)
        .filter(
            FinancialSnapshot.household_id == household.id,
            FinancialSnapshot.period_start < snapshot.period_start,
        )
        .order_by(FinancialSnapshot.period_start.desc())
        .first()
    )
    nw_change = snapshot.net_worth
    if previous is not None:
        nw_change = quantize_money(
            Decimal(str(snapshot.net_worth)) - Decimal(str(previous.net_worth))
        )
    return {
        "title": "FAMILY FINANCIAL REPORT",
        "period_label": _month_label(snapshot.period_start),
        "income": format_money(snapshot.income),
        "expenses": format_money(snapshot.expenses),
        "savings": format_money(snapshot.savings),
        "investments": format_money(snapshot.investments),
        "giving": format_money(snapshot.giving),
        "debt_reduction": format_money(snapshot.debt_reduction),
        "surplus": format_money(snapshot.surplus),
        "net_worth_change": format_money(nw_change),
        "top_overspend": snapshot.payload.get("top_overspend")
        or _top_overspend(db, household, snapshot.period_start, snapshot.period_end),
        "best_improvement": snapshot.payload.get("best_improvement")
        or _best_improvement(db, household.id, snapshot.period_start, health),
        "upcoming_risk": snapshot.payload.get("upcoming_risk")
        or _upcoming_risk(db, household.id, today),
        "health_score": format_money(snapshot.health_score),
        "health_label": health.get("label", ""),
        "shock": snapshot.payload.get("shock"),
    }


def upsert_report(
    db: Session,
    household: Household,
    *,
    kind: str,
    start: date,
    end: date,
    payload: dict,
) -> Report:
    row = (
        db.query(Report)
        .filter(
            Report.household_id == household.id,
            Report.kind == kind,
            Report.period_start == start,
        )
        .first()
    )
    if row is None:
        row = Report(household_id=household.id, kind=kind, period_start=start)
        db.add(row)
    row.period_end = end
    row.payload = payload
    db.add(row)
    db.flush()
    return row


def monthly_report(
    db: Session, household: Household, period: date | None = None, today: date | None = None
) -> Report:
    today = today or date.today()
    start, end = period_bounds(household, period or today)
    snapshot = _get_snapshot(db, household.id, start)
    if snapshot is None:
        extra = {
            "top_overspend": _top_overspend(db, household, start, end),
        }
        snapshot = freeze_current_snapshot(db, household, today=period or today, extra=extra)
    payload = build_monthly_payload(db, household, snapshot, today)
    return upsert_report(db, household, kind="monthly", start=start, end=end, payload=payload)


def _aggregate_snapshots(rows: list[FinancialSnapshot]) -> dict:
    income = sum((Decimal(str(row.income)) for row in rows), Decimal("0.00"))
    expenses = sum((Decimal(str(row.expenses)) for row in rows), Decimal("0.00"))
    savings = sum((Decimal(str(row.savings)) for row in rows), Decimal("0.00"))
    investments = sum((Decimal(str(row.investments)) for row in rows), Decimal("0.00"))
    giving = sum((Decimal(str(row.giving)) for row in rows), Decimal("0.00"))
    debt = sum((Decimal(str(row.debt_reduction)) for row in rows), Decimal("0.00"))
    surplus = sum((Decimal(str(row.surplus)) for row in rows), Decimal("0.00"))
    first_nw = Decimal(str(rows[0].net_worth)) if rows else Decimal("0.00")
    last_nw = Decimal(str(rows[-1].net_worth)) if rows else Decimal("0.00")
    last_health = format_money(rows[-1].health_score) if rows else "0.00"
    last_label = ""
    if rows:
        last_label = (rows[-1].payload.get("health") or {}).get("label", "")
    return {
        "income": format_money(income),
        "expenses": format_money(expenses),
        "savings": format_money(savings),
        "investments": format_money(investments),
        "giving": format_money(giving),
        "debt_reduction": format_money(debt),
        "surplus": format_money(surplus),
        "net_worth_change": format_money(
            quantize_money(last_nw - first_nw) if rows else Decimal("0.00")
        ),
        "health_score": last_health,
        "health_label": last_label,
        "months": [
            {
                "period_start": row.period_start.isoformat(),
                "period_label": _month_label(row.period_start),
                "income": format_money(row.income),
                "expenses": format_money(row.expenses),
                "surplus": format_money(row.surplus),
                "health_score": format_money(row.health_score),
                "shock": row.payload.get("shock"),
            }
            for row in rows
        ],
    }


def quarterly_report(db: Session, household: Household, year: int, quarter: int) -> Report:
    month = (quarter - 1) * 3 + 1
    start = date(year, month, 1)
    end_month = month + 2
    end = date(year, end_month, monthrange(year, end_month)[1])
    rows = [
        row
        for row in list_snapshots(db, household.id)
        if start <= row.period_start <= end
    ]
    payload = {
        "title": "FAMILY QUARTERLY REPORT",
        "period_label": f"Q{quarter} {year}",
        **_aggregate_snapshots(rows),
    }
    return upsert_report(db, household, kind="quarterly", start=start, end=end, payload=payload)


def annual_report(db: Session, household: Household, year: int) -> Report:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    rows = [row for row in list_snapshots(db, household.id) if row.period_start.year == year]
    payload = {
        "title": "FAMILY ANNUAL REPORT",
        "period_label": str(year),
        **_aggregate_snapshots(rows),
    }
    return upsert_report(db, household, kind="annual", start=start, end=end, payload=payload)


def giving_report(db: Session, household: Household, year: int) -> Report:
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    rows = [row for row in list_snapshots(db, household.id) if row.period_start.year == year]
    giving = sum((Decimal(str(row.giving)) for row in rows), Decimal("0.00"))
    allocated = Decimal("0.00")
    for row in rows:
        for line in row.payload.get("giving_allocations") or []:
            allocated += Decimal(str(line.get("amount", "0")))
    today = date.today()
    period_start, period_end = period_bounds(household, today)
    live_giving = gather_period_activity(db, household, period_start, period_end)["giving"]
    if not rows:
        giving = live_giving
    categories = _spend_by_category(db, household.id, start, min(end, today))
    giving_cats = [row for row in categories]
    limit = allocated if allocated > 0 else giving
    payload = {
        "title": "GIVING REPORT",
        "period_label": str(year),
        "allocated": format_money(allocated),
        "actual": format_money(giving),
        "limit": format_money(limit),
        "vs_limit": format_money(quantize_money(giving - limit)),
        "categories": giving_cats,
        "months": [
            {
                "period_label": _month_label(row.period_start),
                "giving": format_money(row.giving),
            }
            for row in rows
        ],
    }
    return upsert_report(db, household, kind="giving", start=start, end=end, payload=payload)


def insights_payload(db: Session, household: Household, today: date | None = None) -> dict:
    today = today or date.today()
    result, start, end = compute_household_health(db, household, today)
    upsert_score(db, household, result, start, end)
    spend = _spend_by_category(db, household.id, start, end)
    overspend = _top_overspend(db, household, start, end)
    snapshots = list_snapshots(db, household.id)
    scores = (
        db.query(FinancialScore)
        .filter(FinancialScore.household_id == household.id)
        .order_by(FinancialScore.period_start)
        .all()
    )
    giving = giving_report(db, household, start.year).payload
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "spend": spend,
        "top_categories": spend[:5],
        "overspend": [overspend] if overspend else [],
        "cash_flow": [
            {
                "period_start": row.period_start.isoformat(),
                "period_label": _month_label(row.period_start),
                "income": format_money(row.income),
                "expenses": format_money(row.expenses),
                "surplus": format_money(row.surplus),
            }
            for row in snapshots
        ],
        "net_worth": [
            {
                "period_start": row.period_start.isoformat(),
                "period_label": _month_label(row.period_start),
                "net_worth": format_money(row.net_worth),
            }
            for row in snapshots
        ],
        "health_history": [
            {
                "period_start": row.period_start.isoformat(),
                "period_label": _month_label(row.period_start),
                "score": format_money(row.score),
                "label": row.label,
            }
            for row in scores
        ],
        "giving": {
            "allocated": giving.get("allocated"),
            "actual": giving.get("actual"),
            "limit": giving.get("limit"),
            "vs_limit": giving.get("vs_limit"),
        },
        "health": serialize_health(result, start, end),
    }
