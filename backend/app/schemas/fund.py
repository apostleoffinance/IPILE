from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount


class FundCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    target_amount: MoneyAmount
    target_date: Date | None = None
    obligation_id: UUID | None = None
    monthly_contribution: MoneyAmount = "0.00"
    account_id: UUID | None = None
    is_protected: bool = True


class FundContributionCreate(BaseModel):
    account_id: UUID
    amount: MoneyAmount
    date: Date | None = None


class FundContributionOut(BaseModel):
    id: UUID
    fund_id: UUID
    account_id: UUID
    amount: MoneyAmount
    date: Date
    transaction_id: UUID | None


class FundOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    target_amount: MoneyAmount
    current_amount: MoneyAmount
    target_date: Date | None
    obligation_id: UUID | None
    obligation_name: str | None
    monthly_contribution: MoneyAmount
    required_monthly: MoneyAmount
    expected_amount: MoneyAmount
    shortfall: MoneyAmount
    on_track: bool
    progress: str
    coverage_label: str
    account_id: UUID | None
    is_protected: bool
    status: str
