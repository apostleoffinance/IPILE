from datetime import date as Date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount


class ObligationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    amount: MoneyAmount
    frequency: str = "monthly"
    next_due_date: Date
    currency: str = "NGN"
    priority: str = "medium"
    sinking_fund: bool = False
    auto_allocate: bool = False
    category_id: UUID | None = None
    beneficiary_name: str | None = None
    beneficiary_member_id: UUID | None = None
    status: str = "active"


class ObligationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    amount: MoneyAmount | None = None
    frequency: str | None = None
    next_due_date: Date | None = None
    priority: str | None = None
    sinking_fund: bool | None = None
    auto_allocate: bool | None = None
    category_id: UUID | None = None
    beneficiary_name: str | None = None
    status: str | None = None


class OccurrenceOut(BaseModel):
    id: UUID
    obligation_id: UUID
    due_date: Date
    amount: MoneyAmount
    funded_amount: MoneyAmount
    coverage: str
    coverage_label: str
    status: str
    paid_at: datetime | None = None
    transaction_id: UUID | None = None


class ObligationPay(BaseModel):
    account_id: UUID
    date: Date | None = None


class ObligationOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    amount: MoneyAmount
    currency: str
    frequency: str
    next_due_date: Date
    priority: str
    sinking_fund: bool
    auto_allocate: bool
    category_id: UUID | None
    beneficiary_name: str | None
    beneficiary_member_id: UUID | None
    fund_id: UUID | None
    fund_name: str | None
    status: str
    required_monthly: MoneyAmount
    next_occurrence: OccurrenceOut | None
    occurrences: list[OccurrenceOut] = []
