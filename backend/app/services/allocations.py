from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.allocation import AllocationLine, AllocationRule, AllocationRun
from app.models.household import Household
from app.models.income import IncomeSource
from app.models.transaction import Transaction
from app.money import format_money, quantize_money
from app.schemas.allocation import (
    AllocationLineOut,
    AllocationRuleOut,
    AllocationRunOut,
    UnfundedMandatoryOut,
)
from app.services.alerts import resolve_alert, upsert_alert
from app.services.allocation_engine import (
    BASES,
    DESTINATIONS,
    RULE_TYPES,
    AllocationResult,
    AllocationRuleSpec,
    allocate,
)
from app.services.obligation_engine import add_months


def period_bounds(household: Household, today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    start_day = household.fiscal_month_start_day or 1
    if today.day >= start_day:
        year, month = today.year, today.month
    else:
        previous = add_months(date(today.year, today.month, 1), -1)
        year, month = previous.year, previous.month
    start_day = min(start_day, monthrange(year, month)[1])
    start = date(year, month, start_day)
    end = add_months(start, 1) - timedelta(days=1)
    return start, end


def recognized_income(
    db: Session,
    household_id: UUID,
    start: date,
    end: date,
    income_source_id: UUID | None = None,
) -> Decimal:
    query = db.query(Transaction).filter(
        Transaction.household_id == household_id,
        Transaction.type == "income",
        Transaction.status.in_(("cleared", "reconciled")),
        Transaction.deleted_at.is_(None),
        Transaction.date >= start,
        Transaction.date <= end,
    )
    if income_source_id is not None:
        query = query.filter(Transaction.income_source_id == income_source_id)
    return quantize_money(
        sum((Decimal(str(row.amount)) for row in query.all()), Decimal("0.00"))
    )


def source_amounts(
    db: Session, household_id: UUID, start: date, end: date
) -> dict[UUID, Decimal]:
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.household_id == household_id,
            Transaction.type == "income",
            Transaction.status.in_(("cleared", "reconciled")),
            Transaction.deleted_at.is_(None),
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.income_source_id.is_not(None),
        )
        .all()
    )
    totals: dict[UUID, Decimal] = {}
    for row in rows:
        if row.income_source_id is None:
            continue
        totals[row.income_source_id] = quantize_money(
            totals.get(row.income_source_id, Decimal("0.00")) + Decimal(str(row.amount))
        )
    return totals


def expected_income(db: Session, household_id: UUID) -> Decimal:
    sources = (
        db.query(IncomeSource)
        .filter(
            IncomeSource.household_id == household_id,
            IncomeSource.is_active.is_(True),
            IncomeSource.deleted_at.is_(None),
        )
        .all()
    )
    total = Decimal("0.00")
    for source in sources:
        amount = quantize_money(Decimal(str(source.expected_amount)))
        if source.frequency == "weekly":
            amount = quantize_money(amount * Decimal(52) / Decimal(12))
        elif source.frequency == "biweekly":
            amount = quantize_money(amount * Decimal(26) / Decimal(12))
        elif source.frequency == "quarterly":
            amount = quantize_money(amount / Decimal(3))
        elif source.frequency == "annual":
            amount = quantize_money(amount / Decimal(12))
        elif source.frequency == "irregular":
            amount = Decimal("0.00")
        total += amount
    return quantize_money(total)


def _rule_effective(rule: AllocationRule, start: date, end: date) -> bool:
    if rule.effective_from and rule.effective_from > end:
        return False
    if rule.effective_to and rule.effective_to < start:
        return False
    return True


def active_rules(db: Session, household_id: UUID, start: date, end: date) -> list[AllocationRule]:
    rows = (
        db.query(AllocationRule)
        .filter(
            AllocationRule.household_id == household_id,
            AllocationRule.is_active.is_(True),
            AllocationRule.deleted_at.is_(None),
        )
        .all()
    )
    return [row for row in rows if _rule_effective(row, start, end)]


def to_spec(rule: AllocationRule) -> AllocationRuleSpec:
    created = ""
    if rule.created_at is not None:
        created = rule.created_at.isoformat()
    return AllocationRuleSpec(
        id=rule.id,
        name=rule.name,
        type=rule.type,
        basis=rule.basis,
        rate=Decimal(str(rule.rate)) if rule.rate is not None else None,
        amount=quantize_money(Decimal(str(rule.amount))) if rule.amount is not None else None,
        priority=rule.priority,
        mandatory=rule.mandatory,
        destination_type=rule.destination_type,
        destination_id=rule.destination_id,
        income_source_id=rule.income_source_id,
        created_at=created,
    )


def compute_allocation(
    db: Session,
    household: Household,
    *,
    today: date | None = None,
    income_override: Decimal | None = None,
) -> tuple[tuple[date, date], AllocationResult]:
    start, end = period_bounds(household, today)
    income = (
        quantize_money(income_override)
        if income_override is not None
        else recognized_income(db, household.id, start, end)
    )
    rules = [to_spec(rule) for rule in active_rules(db, household.id, start, end)]
    result = allocate(income, rules, source_amounts(db, household.id, start, end))
    return (start, end), result


def persist_run(
    db: Session,
    household: Household,
    start: date,
    end: date,
    result: AllocationResult,
) -> AllocationRun:
    run = (
        db.query(AllocationRun)
        .filter(
            AllocationRun.household_id == household.id,
            AllocationRun.period_start == start,
            AllocationRun.period_end == end,
        )
        .first()
    )
    if run is None:
        run = AllocationRun(
            household_id=household.id,
            period_start=start,
            period_end=end,
        )
        db.add(run)
        db.flush()
    else:
        db.query(AllocationLine).filter(AllocationLine.run_id == run.id).delete()
    run.recognized_income = result.recognized_income
    run.total_allocated = result.total_allocated
    run.surplus = result.surplus
    run.status = "computed"
    db.add(run)
    db.flush()
    for line in result.lines:
        db.add(
            AllocationLine(
                household_id=household.id,
                run_id=run.id,
                rule_id=line.rule_id,
                name=line.name,
                requested_amount=line.requested,
                amount=line.amount,
                destination_type=line.destination_type,
                destination_id=line.destination_id,
                mandatory=line.mandatory,
                funded=line.funded,
            )
        )
    period_key = f"{start.isoformat()}:{end.isoformat()}"
    funded_ids = {line.rule_id for line in result.lines if line.funded and line.rule_id}
    for line in result.unfunded_mandatory:
        if line.rule_id is None:
            continue
        upsert_alert(
            db,
            household_id=household.id,
            alert_type="underfunded_mandatory_allocation",
            severity="critical",
            title=f"{line.name} is underfunded",
            body=(
                f"Mandatory allocation {line.name} requested "
                f"{format_money(line.requested)} and received {format_money(line.amount)}."
            ),
            related_entity_type="allocation_rule",
            related_entity_id=line.rule_id,
            period_key=period_key,
        )
    for rule_id in funded_ids:
        resolve_alert(
            db,
            household_id=household.id,
            alert_type="underfunded_mandatory_allocation",
            related_entity_id=rule_id,
            period_key=period_key,
        )
    db.flush()
    return run


def ensure_period_allocation(
    db: Session, household: Household, *, today: date | None = None
) -> AllocationRun:
    (start, end), result = compute_allocation(db, household, today=today)
    return persist_run(db, household, start, end, result)


def latest_run(db: Session, household_id: UUID) -> AllocationRun | None:
    return (
        db.query(AllocationRun)
        .filter(AllocationRun.household_id == household_id)
        .order_by(AllocationRun.period_start.desc(), AllocationRun.created_at.desc())
        .first()
    )


def serialize_rule(rule: AllocationRule) -> AllocationRuleOut:
    rate = None
    if rule.rate is not None:
        rate = format(Decimal(str(rule.rate)), "f")
    amount = None
    if rule.amount is not None:
        amount = quantize_money(Decimal(str(rule.amount)))
    return AllocationRuleOut(
        id=rule.id,
        household_id=rule.household_id,
        name=rule.name,
        type=rule.type,
        basis=rule.basis,
        rate=rate,
        amount=amount,
        priority=rule.priority,
        mandatory=rule.mandatory,
        destination_type=rule.destination_type,
        destination_id=rule.destination_id,
        income_source_id=rule.income_source_id,
        is_active=rule.is_active,
        effective_from=rule.effective_from,
        effective_to=rule.effective_to,
    )


def serialize_run(db: Session, run: AllocationRun) -> AllocationRunOut:
    lines = (
        db.query(AllocationLine)
        .filter(AllocationLine.run_id == run.id)
        .order_by(AllocationLine.created_at)
        .all()
    )
    line_outs = [
        AllocationLineOut(
            id=line.id,
            rule_id=line.rule_id,
            name=line.name,
            requested_amount=quantize_money(Decimal(str(line.requested_amount))),
            amount=quantize_money(Decimal(str(line.amount))),
            destination_type=line.destination_type,
            destination_id=line.destination_id,
            mandatory=line.mandatory,
            funded=line.funded,
        )
        for line in lines
    ]
    unfunded = [
        UnfundedMandatoryOut(
            rule_id=line.rule_id,
            name=line.name,
            requested_amount=line.requested_amount,
            amount=line.amount,
        )
        for line in line_outs
        if line.mandatory and not line.funded
    ]
    return AllocationRunOut(
        id=run.id,
        household_id=run.household_id,
        period_start=run.period_start,
        period_end=run.period_end,
        recognized_income=quantize_money(Decimal(str(run.recognized_income))),
        total_allocated=quantize_money(Decimal(str(run.total_allocated))),
        surplus=quantize_money(Decimal(str(run.surplus))),
        status=run.status,
        lines=line_outs,
        unfunded_mandatory=unfunded,
    )


def validate_rule_payload(
    *,
    rule_type: str,
    basis: str,
    destination_type: str,
    rate: str | None,
    amount: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    if rule_type not in RULE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid allocation rule type.")
    if basis not in BASES:
        raise HTTPException(status_code=400, detail="Invalid allocation basis.")
    if destination_type not in DESTINATIONS:
        raise HTTPException(status_code=400, detail="Invalid destination type.")
    parsed_rate = None
    if rule_type == "percentage":
        if rate is None:
            raise HTTPException(status_code=400, detail="Percentage rules require a rate.")
        try:
            parsed_rate = Decimal(str(rate))
        except InvalidOperation as exc:
            raise HTTPException(status_code=400, detail="Rate must be a decimal.") from exc
        if parsed_rate < 0 or parsed_rate > 1:
            raise HTTPException(status_code=400, detail="Rate must be between 0 and 1 inclusive.")
    if rule_type == "fixed" and amount is None:
        raise HTTPException(status_code=400, detail="Fixed rules require an amount.")
    return parsed_rate, amount
