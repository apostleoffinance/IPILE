from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.models.wealth import Liability
from app.money import format_money, quantize_money
from app.schemas.debt import DebtStrategiesOut, DebtStrategyOut, ScheduleMonthOut
from app.services.debt_engine import DebtInput, compare_strategies

router = APIRouter(prefix="/debts", tags=["debts"])


def _serialize_strategy(result) -> DebtStrategyOut:
    return DebtStrategyOut(
        strategy=result.strategy,
        order=result.order,
        months=result.months,
        total_interest=format_money(result.total_interest),
        total_paid=format_money(result.total_paid),
        schedule_summary=[
            ScheduleMonthOut(
                month=row.month,
                total_payment=format_money(row.total_payment),
                total_interest=format_money(row.total_interest),
                remaining_balance=format_money(row.remaining_balance),
                debts_remaining=row.debts_remaining,
            )
            for row in result.schedule_summary
        ],
    )


@router.get("/strategies", response_model=DebtStrategiesOut)
def get_debt_strategies(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
    extra_payment: str = Query(default="0"),
):
    extra = quantize_money(Decimal(str(extra_payment or "0")))
    if extra < 0:
        extra = Decimal("0.00")
    rows = (
        db.query(Liability)
        .filter(
            Liability.household_id == ctx.household.id,
            Liability.deleted_at.is_(None),
            Liability.status != "paid_off",
        )
        .order_by(Liability.created_at)
        .all()
    )
    debts = [
        DebtInput(
            id=row.id,
            name=row.name,
            balance=quantize_money(Decimal(str(row.current_balance))),
            interest_rate=Decimal(str(row.interest_rate or 0)),
            min_payment=quantize_money(Decimal(str(row.minimum_payment or 0))),
        )
        for row in rows
        if quantize_money(Decimal(str(row.current_balance))) > 0
    ]
    compared = compare_strategies(debts, extra_payment=extra)
    return DebtStrategiesOut(
        extra_payment=format_money(extra),
        currency=ctx.household.base_currency,
        snowball=_serialize_strategy(compared["snowball"]),
        avalanche=_serialize_strategy(compared["avalanche"]),
        liabilities_considered=len(debts),
    )
