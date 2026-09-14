from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount


class IncomeSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = "salary"
    expected_amount: MoneyAmount
    frequency: str = "monthly"
    next_expected_date: Date | None = None
    member_id: UUID | None = None
    is_active: bool = True


class IncomeSourceOut(BaseModel):
    id: UUID
    household_id: UUID
    member_id: UUID | None
    name: str
    type: str
    expected_amount: MoneyAmount
    frequency: str
    next_expected_date: Date | None
    is_active: bool

    model_config = {"from_attributes": True}


class IncomeCreate(BaseModel):
    account_id: UUID
    amount: MoneyAmount
    date: Date
    income_source_id: UUID | None = None
    member_id: UUID | None = None
    category_id: UUID | None = None
    description: str | None = None
    status: str = "cleared"
