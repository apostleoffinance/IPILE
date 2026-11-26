from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.models.currency import ExchangeRate
from app.services.currencies import (
    CurrencyError,
    convert_amount,
    currency_catalog,
    validate_currency,
)

router = APIRouter(prefix="/currencies", tags=["currencies"])


class CurrencyConversionRequest(BaseModel):
    amount: Decimal = Field(ge=0)
    from_currency: str = Field(min_length=3, max_length=3)
    to_currency: str = Field(min_length=3, max_length=3)
    rate_date: date


@router.get("")
def list_currencies():
    return {"currencies": currency_catalog(), "default": "NGN"}


@router.post("/convert")
def convert_currency(
    payload: CurrencyConversionRequest,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    try:
        result = convert_amount(
            db, ctx.household.id, payload.amount,
            validate_currency(payload.from_currency),
            validate_currency(payload.to_currency),
            payload.rate_date,
        )
        db.commit()
        return result
    except CurrencyError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class ExchangeRateCreate(BaseModel):
    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    rate: Decimal = Field(gt=0, max_digits=24, decimal_places=12)
    rate_date: date


@router.post("/rates")
def create_manual_rate(
    payload: ExchangeRateCreate,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    if ctx.role not in {"owner", "partner"}:
        raise HTTPException(status_code=403, detail=(
            "Only household administrators can add FX rates."
        ))
    try:
        base = validate_currency(payload.base_currency)
        quote = validate_currency(payload.quote_currency)
    except CurrencyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if base == quote:
        raise HTTPException(status_code=422, detail="Base and quote currencies must differ.")
    existing = db.query(ExchangeRate).filter(
        ExchangeRate.household_id == ctx.household.id,
        ExchangeRate.base_currency == base,
        ExchangeRate.quote_currency == quote,
        ExchangeRate.rate_date == payload.rate_date,
        ExchangeRate.source == "manual",
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "A manual rate already exists for this currency pair and date. "
                "Existing FX observations are immutable; use a new dated observation."
            ),
        )
    row = ExchangeRate(
        household_id=ctx.household.id,
        base_currency=base,
        quote_currency=quote,
        rate=payload.rate,
        rate_date=payload.rate_date,
        source="manual",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
