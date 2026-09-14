from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.wealth import Asset, Investment, Liability
from app.schemas.wealth import (
    AssetCreate,
    AssetOut,
    InvestmentCreate,
    InvestmentOut,
    InvestmentTxCreate,
    InvestmentTxOut,
    LiabilityCreate,
    LiabilityOut,
    LiabilityPaymentIn,
    NetWorthOut,
)
from app.services.wealth import (
    create_asset,
    create_investment,
    create_liability,
    pay_liability,
    record_investment_tx,
    serialize_investment,
    serialize_investment_tx,
    serialize_liability,
    serialize_net_worth,
)

router = APIRouter(tags=["wealth"])


@router.get("/net-worth", response_model=NetWorthOut)
def get_net_worth(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    payload = serialize_net_worth(db, ctx.household)
    db.commit()
    return payload


@router.get("/assets", response_model=list[AssetOut])
def list_assets(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Asset)
        .filter(Asset.household_id == ctx.household.id, Asset.deleted_at.is_(None))
        .order_by(Asset.created_at)
        .all()
    )


@router.post("/assets", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def post_asset(
    payload: AssetCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = create_asset(db, ctx.household, payload)
    db.commit()
    db.refresh(row)
    return row


@router.get("/liabilities", response_model=list[LiabilityOut])
def list_liabilities(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Liability)
        .filter(Liability.household_id == ctx.household.id, Liability.deleted_at.is_(None))
        .order_by(Liability.created_at)
        .all()
    )
    return [serialize_liability(row) for row in rows]


@router.post("/liabilities", response_model=LiabilityOut, status_code=status.HTTP_201_CREATED)
def post_liability(
    payload: LiabilityCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = create_liability(db, ctx.household, payload)
    db.commit()
    db.refresh(row)
    return serialize_liability(row)


@router.post("/liabilities/{liability_id}/payments", response_model=LiabilityOut)
def post_liability_payment(
    liability_id: UUID,
    payload: LiabilityPaymentIn,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Liability)
        .filter(
            Liability.id == liability_id,
            Liability.household_id == ctx.household.id,
            Liability.deleted_at.is_(None),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Liability not found.")
    updated = pay_liability(
        db, ctx.household, row, account_id=payload.account_id, amount=payload.amount
    )
    db.commit()
    db.refresh(updated)
    return serialize_liability(updated)


@router.get("/investments", response_model=list[InvestmentOut])
def list_investments(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return (
        db.query(Investment)
        .filter(Investment.household_id == ctx.household.id, Investment.deleted_at.is_(None))
        .order_by(Investment.created_at)
        .all()
    )


@router.post("/investments", response_model=InvestmentOut, status_code=status.HTTP_201_CREATED)
def post_investment(
    payload: InvestmentCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = create_investment(db, ctx.household, payload)
    db.commit()
    db.refresh(row)
    return serialize_investment(row)


@router.post(
    "/investments/{investment_id}/transactions",
    response_model=InvestmentTxOut,
    status_code=status.HTTP_201_CREATED,
)
def post_investment_tx(
    investment_id: UUID,
    payload: InvestmentTxCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = (
        db.query(Investment)
        .filter(
            Investment.id == investment_id,
            Investment.household_id == ctx.household.id,
            Investment.deleted_at.is_(None),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Investment not found.")
    created = record_investment_tx(
        db,
        ctx.household,
        row,
        tx_type=payload.type,
        amount=payload.amount,
        tx_date=payload.date,
        account_id=payload.account_id,
    )
    db.commit()
    db.refresh(created)
    return serialize_investment_tx(created)
