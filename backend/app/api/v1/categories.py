from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])
KINDS = {"income", "expense", "transfer", "giving", "investment", "debt", "system"}


@router.get("", response_model=list[CategoryOut])
def list_categories(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Category)
        .filter(Category.household_id == ctx.household.id, Category.deleted_at.is_(None))
        .order_by(Category.sort_order, Category.name)
        .all()
    )


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.kind not in KINDS:
        raise HTTPException(status_code=400, detail="Invalid category kind.")
    category = Category(
        household_id=ctx.household.id,
        name=payload.name,
        kind=payload.kind,
        parent_id=payload.parent_id,
        is_system=False,
        sort_order=payload.sort_order,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
