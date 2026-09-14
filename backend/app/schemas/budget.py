from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount, MoneySigned


class BudgetCategoryIn(BaseModel):
    category_id: UUID
    allocated_amount: MoneyAmount
    rollover: bool = False


class BudgetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    period_type: str = "monthly"
    start_date: Date | None = None
    end_date: Date | None = None
    member_id: UUID | None = None
    status: str = "active"
    categories: list[BudgetCategoryIn] = []


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = None
    categories: list[BudgetCategoryIn] | None = None


class BudgetCategoryOut(BaseModel):
    id: UUID
    category_id: UUID
    category_name: str
    allocated_amount: MoneyAmount
    spent_amount: MoneySigned
    remaining_amount: MoneySigned
    utilization: str | None
    status: str
    rollover: bool


class BudgetOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    period_type: str
    start_date: Date
    end_date: Date
    member_id: UUID | None
    member_name: str | None
    status: str
    allocated_total: MoneyAmount
    spent_total: MoneySigned
    remaining_total: MoneySigned
    categories: list[BudgetCategoryOut]
