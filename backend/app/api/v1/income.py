from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.api.v1.transactions import create_transaction
from app.models.income import IncomeSource
from app.models.transaction import Transaction
from app.schemas.income import IncomeCreate, IncomeSourceCreate, IncomeSourceOut
from app.schemas.transaction import TransactionCreate, TransactionOut

router = APIRouter(tags=["income"])


@router.get("/income/sources", response_model=list[IncomeSourceOut])
def list_income_sources(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(IncomeSource)
        .filter(IncomeSource.household_id == ctx.household.id, IncomeSource.deleted_at.is_(None))
        .order_by(IncomeSource.created_at)
        .all()
    )


@router.post("/income/sources", response_model=IncomeSourceOut, status_code=status.HTTP_201_CREATED)
def create_income_source(
    payload: IncomeSourceCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    source = IncomeSource(
        household_id=ctx.household.id,
        member_id=payload.member_id,
        name=payload.name,
        type=payload.type,
        expected_amount=payload.expected_amount,
        frequency=payload.frequency,
        next_expected_date=payload.next_expected_date,
        is_active=payload.is_active,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/income", response_model=list[TransactionOut])
def list_income(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Transaction)
        .filter(
            Transaction.household_id == ctx.household.id,
            Transaction.type == "income",
            Transaction.deleted_at.is_(None),
        )
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .all()
    )


@router.post("/income", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def record_income(
    payload: IncomeCreate,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    if payload.income_source_id:
        source = (
            db.query(IncomeSource)
            .filter(
                IncomeSource.id == payload.income_source_id,
                IncomeSource.household_id == ctx.household.id,
                IncomeSource.deleted_at.is_(None),
            )
            .first()
        )
        if source is None:
            raise HTTPException(status_code=404, detail="Income source not found.")
    return create_transaction(
        TransactionCreate(
            account_id=payload.account_id,
            amount=payload.amount,
            type="income",
            date=payload.date,
            currency=ctx.household.base_currency,
            member_id=payload.member_id,
            category_id=payload.category_id,
            description=payload.description,
            income_source_id=payload.income_source_id,
            status=payload.status,
        ),
        ctx,
        db,
    )
