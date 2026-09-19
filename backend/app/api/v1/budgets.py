from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.budget import Budget, BudgetCategory
from app.models.category import Category
from app.models.member import HouseholdMember
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate
from app.services.budgets import current_month_bounds, evaluate_budget_alerts, serialize_budget

router = APIRouter(tags=["budget"])
PERIOD_TYPES = {"monthly", "quarterly", "annual", "weekly", "custom"}
BUDGET_STATUSES = {"draft", "active", "closed"}


def _budget_period_bounds(payload: BudgetCreate) -> tuple[date, date]:
    today = date.today()
    if payload.period_type == "weekly":
        start = payload.start_date or today
        end = payload.end_date or (start + timedelta(days=6))
        return start, end
    if payload.period_type == "custom":
        if payload.start_date is None or payload.end_date is None:
            raise HTTPException(
                status_code=400,
                detail="Custom budgets require start_date and end_date.",
            )
        if payload.end_date < payload.start_date:
            raise HTTPException(status_code=400, detail="end_date must be on or after start_date.")
        return payload.start_date, payload.end_date
    start, end = current_month_bounds()
    return payload.start_date or start, payload.end_date or end


def _active_budgets(db: Session, household_id: UUID):
    return db.query(Budget).filter(Budget.household_id == household_id, Budget.deleted_at.is_(None))


def _replace_categories(db: Session, budget: Budget, lines) -> None:
    incoming = {line.category_id: line for line in lines}
    if len(incoming) != len(lines):
        raise HTTPException(status_code=400, detail="Duplicate category on budget.")
    existing = {
        row.category_id: row
        for row in db.query(BudgetCategory).filter(BudgetCategory.budget_id == budget.id).all()
    }
    for category_id, row in existing.items():
        if category_id not in incoming:
            db.delete(row)
    for line in incoming.values():
        category = (
            db.query(Category)
            .filter(
                Category.id == line.category_id,
                Category.household_id == budget.household_id,
                Category.deleted_at.is_(None),
            )
            .first()
        )
        if category is None:
            raise HTTPException(status_code=404, detail="Category not found.")
        current = existing.get(line.category_id)
        if current:
            current.allocated_amount = line.allocated_amount
            current.rollover = line.rollover
            db.add(current)
            continue
        db.add(
            BudgetCategory(
                household_id=budget.household_id,
                budget_id=budget.id,
                category_id=line.category_id,
                allocated_amount=line.allocated_amount,
                rollover=line.rollover,
            )
        )


@router.get("/budget", response_model=list[BudgetOut])
def list_budgets(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    budgets = _active_budgets(db, ctx.household.id).order_by(Budget.start_date.desc()).all()
    return [serialize_budget(db, budget) for budget in budgets]


@router.post("/budget", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.period_type not in PERIOD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid period type.")
    if payload.status not in BUDGET_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid budget status.")
    if payload.member_id:
        member = (
            db.query(HouseholdMember)
            .filter(
                HouseholdMember.id == payload.member_id,
                HouseholdMember.household_id == ctx.household.id,
                HouseholdMember.deleted_at.is_(None),
            )
            .first()
        )
        if member is None:
            raise HTTPException(status_code=404, detail="Member not found.")
    start, end = _budget_period_bounds(payload)
    budget = Budget(
        household_id=ctx.household.id,
        name=payload.name,
        period_type=payload.period_type,
        start_date=start,
        end_date=end,
        member_id=payload.member_id,
        status=payload.status,
    )
    db.add(budget)
    db.flush()
    _replace_categories(db, budget, payload.categories)
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    db.commit()
    db.refresh(budget)
    return serialize_budget(db, budget)


@router.get("/budget/{budget_id}", response_model=BudgetOut)
def get_budget(
    budget_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    budget = _active_budgets(db, ctx.household.id).filter(Budget.id == budget_id).first()
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found.")
    return serialize_budget(db, budget)


@router.patch("/budget/{budget_id}", response_model=BudgetOut)
def update_budget(
    budget_id: UUID,
    payload: BudgetUpdate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    budget = _active_budgets(db, ctx.household.id).filter(Budget.id == budget_id).first()
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found.")
    if payload.name is not None:
        budget.name = payload.name
    if payload.status is not None:
        if payload.status not in BUDGET_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid budget status.")
        budget.status = payload.status
    if payload.categories is not None:
        _replace_categories(db, budget, payload.categories)
    db.add(budget)
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    db.commit()
    db.refresh(budget)
    return serialize_budget(db, budget)


@router.delete("/budget/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    budget = _active_budgets(db, ctx.household.id).filter(Budget.id == budget_id).first()
    if budget is None:
        raise HTTPException(status_code=404, detail="Budget not found.")
    budget.deleted_at = datetime.now(UTC)
    db.add(budget)
    db.commit()
