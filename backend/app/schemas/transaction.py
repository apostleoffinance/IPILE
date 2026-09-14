from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.money import MoneyAmount


class TransactionCreate(BaseModel):
    account_id: UUID
    amount: MoneyAmount
    type: str
    date: Date
    currency: str = "NGN"
    counterparty_account_id: UUID | None = None
    member_id: UUID | None = None
    category_id: UUID | None = None
    merchant: str | None = None
    description: str | None = None
    income_source_id: UUID | None = None
    obligation_id: UUID | None = None
    fund_id: UUID | None = None
    goal_id: UUID | None = None
    business_id: UUID | None = None
    status: str = "cleared"


class TransactionUpdate(BaseModel):
    merchant: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    date: Date | None = None
    member_id: UUID | None = None


class TransactionOut(BaseModel):
    id: UUID
    household_id: UUID
    account_id: UUID
    counterparty_account_id: UUID | None
    member_id: UUID | None
    amount: MoneyAmount
    currency: str
    type: str
    category_id: UUID | None
    date: Date
    merchant: str | None
    description: str | None
    income_source_id: UUID | None
    obligation_id: UUID | None = None
    fund_id: UUID | None = None
    goal_id: UUID | None = None
    business_id: UUID | None = None
    status: str
    import_source: str
    external_id: str | None = None

    model_config = {"from_attributes": True}
