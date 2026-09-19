from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount


class DebtOrderItem(BaseModel):
    id: str
    name: str
    balance: MoneyAmount
    interest_rate: str
    min_payment: MoneyAmount
    position: int


class ScheduleMonthOut(BaseModel):
    month: int
    total_payment: MoneyAmount
    total_interest: MoneyAmount
    remaining_balance: MoneyAmount
    debts_remaining: int


class DebtStrategyOut(BaseModel):
    strategy: str
    order: list[DebtOrderItem]
    months: int
    total_interest: MoneyAmount
    total_paid: MoneyAmount
    schedule_summary: list[ScheduleMonthOut]


class DebtStrategiesOut(BaseModel):
    extra_payment: MoneyAmount
    currency: str
    snowball: DebtStrategyOut
    avalanche: DebtStrategyOut
    liabilities_considered: int = Field(ge=0)
