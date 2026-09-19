from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.schemas.cash_flow import CashFlowDayOut, CashFlowOut
from app.services.cash_flow import compute_cash_flow

router = APIRouter(prefix="/cash-flow", tags=["cash-flow"])


@router.get("", response_model=CashFlowOut)
def get_cash_flow(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
):
    try:
        payload = compute_cash_flow(
            db,
            ctx.household,
            period_start=period_start,
            period_end=period_end,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CashFlowOut(
        period_start=payload["period_start"],
        period_end=payload["period_end"],
        opening_cash=payload["opening_cash"],
        closing_cash=payload["closing_cash"],
        income=payload["income"],
        expenses=payload["expenses"],
        giving=payload["giving"],
        transfers_net=payload["transfers_net"],
        surplus=payload["surplus"],
        daily=[CashFlowDayOut(**row) for row in payload["daily"]],
    )
