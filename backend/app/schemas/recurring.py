from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.money import MoneyAmount


class RecurringCreate(BaseModel):
    account_id: UUID
    amount: MoneyAmount
    type: str
    frequency: str = "monthly"
    next_date: Date
    currency: str = "NGN"
    counterparty_account_id: UUID | None = None
    member_id: UUID | None = None
    category_id: UUID | None = None
    merchant: str | None = None
    description: str | None = None


class RecurringOut(BaseModel):
    id: UUID
    household_id: UUID
    account_id: UUID
    counterparty_account_id: UUID | None
    member_id: UUID | None
    category_id: UUID | None
    amount: MoneyAmount
    currency: str
    type: str
    frequency: str
    next_date: Date
    merchant: str | None
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}
