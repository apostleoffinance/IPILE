from datetime import date as Date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str
    target_amount: MoneyAmount
    current_amount: MoneyAmount = Decimal("0.00")
    deadline: Date | None = None
    monthly_contribution: MoneyAmount | None = None
    priority: int = 100
    funding_source_account_id: UUID | None = None
    account_id: UUID | None = None


class GoalContributionCreate(BaseModel):
    account_id: UUID
    amount: MoneyAmount
    date: Date | None = None


class GoalOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    type: str
    target_amount: MoneyAmount
    current_amount: MoneyAmount
    remaining: MoneyAmount
    deadline: Date | None
    monthly_contribution: MoneyAmount | None
    required_monthly: MoneyAmount
    months_left: int | None
    priority: int
    funding_source_account_id: UUID | None
    account_id: UUID | None
    progress: str
    percent: int
    coverage_label: str
    status: str
