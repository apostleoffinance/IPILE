from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models.giving import GivingPolicy, GivingRecord
from app.schemas.giving import GivingPolicyOut, GivingRecordOut


def money(value: Decimal | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def posted_records(db: Session, household_id: UUID):
    return db.query(GivingRecord).filter(
        GivingRecord.household_id == household_id,
        GivingRecord.deleted_at.is_(None),
        GivingRecord.status.in_(("posted", "approved")),
    )


def sum_for_policy(
    db: Session,
    household_id: UUID,
    policy_id: UUID | None,
    kind: str,
    *,
    year: int,
    month: int | None = None,
) -> Decimal:
    query = posted_records(db, household_id).filter(
        extract("year", GivingRecord.date) == year,
    )
    if policy_id:
        query = query.filter(GivingRecord.policy_id == policy_id)
    else:
        query = query.filter(GivingRecord.kind == kind, GivingRecord.policy_id.is_(None))
    if month is not None:
        query = query.filter(extract("month", GivingRecord.date) == month)
    total = query.with_entities(func.coalesce(func.sum(GivingRecord.amount), 0)).scalar()
    return money(total)


def limit_warning_for(
    db: Session,
    household_id: UUID,
    policy: GivingPolicy | None,
    kind: str,
    amount: Decimal,
    when: date,
) -> str | None:
    monthly_used = sum_for_policy(
        db, household_id, policy.id if policy else None, kind, year=when.year, month=when.month
    )
    annual_used = sum_for_policy(
        db, household_id, policy.id if policy else None, kind, year=when.year
    )
    projected_month = money(monthly_used + amount)
    projected_year = money(annual_used + amount)
    warnings: list[str] = []
    if (
        policy
        and policy.monthly_limit is not None
        and projected_month > money(policy.monthly_limit)
    ):
        warnings.append(
            f"Monthly limit exceeded: {projected_month} / "
            f"{money(policy.monthly_limit)} for {policy.name}."
        )
    if (
        policy
        and policy.annual_limit is not None
        and projected_year > money(policy.annual_limit)
    ):
        warnings.append(
            f"Annual limit exceeded: {projected_year} / "
            f"{money(policy.annual_limit)} for {policy.name}."
        )
    return " ".join(warnings) if warnings else None


def serialize_policy(
    db: Session, policy: GivingPolicy, today: date | None = None
) -> GivingPolicyOut:
    today = today or date.today()
    monthly_used = sum_for_policy(
        db, policy.household_id, policy.id, policy.kind, year=today.year, month=today.month
    )
    annual_used = sum_for_policy(db, policy.household_id, policy.id, policy.kind, year=today.year)
    breached = False
    if policy.monthly_limit is not None and monthly_used > money(policy.monthly_limit):
        breached = True
    if policy.annual_limit is not None and annual_used > money(policy.annual_limit):
        breached = True
    return GivingPolicyOut(
        id=policy.id,
        household_id=policy.household_id,
        name=policy.name,
        kind=policy.kind,
        monthly_limit=policy.monthly_limit,
        annual_limit=policy.annual_limit,
        requires_dual_approval=policy.requires_dual_approval,
        allocation_rule_id=policy.allocation_rule_id,
        status=policy.status,
        monthly_used=monthly_used,
        annual_used=annual_used,
        limit_breached=breached,
    )


def serialize_record(row: GivingRecord) -> GivingRecordOut:
    return GivingRecordOut.model_validate(row)
