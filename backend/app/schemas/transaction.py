from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, model_validator

from app.schemas.money import MoneyAmount


class TransactionCreate(BaseModel):
    account_id: UUID
    amount: MoneyAmount
    type: str
    date: Date
    currency: str = "NGN"
    counterparty_account_id: UUID | None = None
    member_id: UUID | None = None
    access_scope: str = "shared"
    category_id: UUID | None = None
    merchant: str | None = None
    description: str | None = None
    income_source_id: UUID | None = None
    obligation_id: UUID | None = None
    fund_id: UUID | None = None
    goal_id: UUID | None = None
    business_id: UUID | None = None
    status: str = "cleared"

    @model_validator(mode="after")
    def validate_scope(self):
        if self.access_scope not in {"shared", "personal"}:
            raise ValueError("access_scope must be shared or personal.")
        if self.access_scope == "personal" and self.member_id is None:
            raise ValueError("Personal transactions require a member_id.")
        if self.access_scope == "shared" and self.member_id is not None:
            raise ValueError("Shared transactions cannot have a personal owner.")
        return self


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
    access_scope: str
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
