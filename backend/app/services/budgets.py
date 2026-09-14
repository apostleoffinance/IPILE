from calendar import monthrange
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.budget import Budget, BudgetCategory
from app.models.category import Category
from app.models.member import HouseholdMember
from app.models.transaction import Transaction
from app.money import format_money, quantize_money
from app.schemas.budget import BudgetCategoryOut, BudgetOut
from app.services.alerts import resolve_alert, upsert_alert
from app.services.budget_engine import (
    ACTIVE_STATUSES,
    REFUND_TYPE,
    SPEND_TYPES,
    line_status,
    remaining,
    spent_from_lines,
    utilization,
)


def current_month_bounds(today: date | None = None) -> tuple[date, date]:
    today = today or date.today()
    start = date(today.year, today.month, 1)
    end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    return start, end


def category_spent(
    db: Session,
    *,
    household_id: UUID,
    category_id: UUID,
    start_date: date,
    end_date: date,
    member_id: UUID | None,
) -> Decimal:
    query = db.query(Transaction).filter(
        Transaction.household_id == household_id,
        Transaction.category_id == category_id,
        Transaction.deleted_at.is_(None),
        Transaction.status.in_(tuple(ACTIVE_STATUSES)),
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.type.in_(tuple(SPEND_TYPES | {REFUND_TYPE})),
    )
    if member_id is not None:
        query = query.filter(Transaction.member_id == member_id)
    rows = [(row.type, quantize_money(Decimal(str(row.amount)))) for row in query.all()]
    return spent_from_lines(rows)


def serialize_budget(db: Session, budget: Budget) -> BudgetOut:
    member_name = None
    if budget.member_id:
        member = db.get(HouseholdMember, budget.member_id)
        member_name = member.display_name if member else None
    lines = (
        db.query(BudgetCategory)
        .filter(
            BudgetCategory.budget_id == budget.id,
            BudgetCategory.household_id == budget.household_id,
        )
        .all()
    )
    category_outs: list[BudgetCategoryOut] = []
    allocated_total = Decimal("0.00")
    spent_total = Decimal("0.00")
    for line in lines:
        category = db.get(Category, line.category_id)
        spent = category_spent(
            db,
            household_id=budget.household_id,
            category_id=line.category_id,
            start_date=budget.start_date,
            end_date=budget.end_date,
            member_id=budget.member_id,
        )
        allocated = quantize_money(Decimal(line.allocated_amount))
        ratio = utilization(allocated, spent)
        category_outs.append(
            BudgetCategoryOut(
                id=line.id,
                category_id=line.category_id,
                category_name=category.name if category else "Category",
                allocated_amount=allocated,
                spent_amount=spent,
                remaining_amount=remaining(allocated, spent),
                utilization=None if ratio is None else format_money(ratio),
                status=line_status(allocated, spent),
                rollover=line.rollover,
            )
        )
        allocated_total += allocated
        spent_total += spent
    return BudgetOut(
        id=budget.id,
        household_id=budget.household_id,
        name=budget.name,
        period_type=budget.period_type,
        start_date=budget.start_date,
        end_date=budget.end_date,
        member_id=budget.member_id,
        member_name=member_name,
        status=budget.status,
        allocated_total=quantize_money(allocated_total),
        spent_total=quantize_money(spent_total),
        remaining_total=remaining(allocated_total, spent_total),
        categories=category_outs,
    )


def evaluate_budget_alerts(db: Session, household_id: UUID) -> None:
    budgets = (
        db.query(Budget)
        .filter(
            Budget.household_id == household_id,
            Budget.deleted_at.is_(None),
            Budget.status == "active",
        )
        .all()
    )
    for budget in budgets:
        snapshot = serialize_budget(db, budget)
        period_key = f"{budget.id}:{budget.start_date.isoformat()}"
        for line in snapshot.categories:
            threshold_type = "budget_threshold"
            overspend_type = "budget_overspend"
            if line.status == "critical":
                upsert_alert(
                    db,
                    household_id=household_id,
                    alert_type=overspend_type,
                    severity="critical",
                    title=f"{line.category_name} budget exceeded",
                    body=(
                        f"{line.category_name} spent {format_money(line.spent_amount)} "
                        f"of {format_money(line.allocated_amount)}."
                    ),
                    related_entity_type="budget_category",
                    related_entity_id=line.id,
                    period_key=period_key,
                )
                resolve_alert(
                    db,
                    household_id=household_id,
                    alert_type=threshold_type,
                    related_entity_id=line.id,
                    period_key=period_key,
                )
            elif line.status == "warning":
                upsert_alert(
                    db,
                    household_id=household_id,
                    alert_type=threshold_type,
                    severity="warning",
                    title=f"{line.category_name} budget reached 80%",
                    body=(
                        f"{line.category_name} is "
                        f"{int(Decimal(line.utilization or '0') * 100)}% used."
                    ),
                    related_entity_type="budget_category",
                    related_entity_id=line.id,
                    period_key=period_key,
                )
                resolve_alert(
                    db,
                    household_id=household_id,
                    alert_type=overspend_type,
                    related_entity_id=line.id,
                    period_key=period_key,
                )
            else:
                resolve_alert(
                    db,
                    household_id=household_id,
                    alert_type=threshold_type,
                    related_entity_id=line.id,
                    period_key=period_key,
                )
                resolve_alert(
                    db,
                    household_id=household_id,
                    alert_type=overspend_type,
                    related_entity_id=line.id,
                    period_key=period_key,
                )
