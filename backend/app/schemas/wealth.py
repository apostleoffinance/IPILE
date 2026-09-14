from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount, MoneySigned


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str
    current_value: MoneyAmount
    as_of: Date | None = None
    account_id: UUID | None = None
    include_in_net_worth: bool = True
    is_emergency: bool = False


class AssetOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    type: str
    current_value: MoneyAmount
    as_of: Date | None
    account_id: UUID | None
    include_in_net_worth: bool
    is_emergency: bool
    status: str

    model_config = {"from_attributes": True}


class LiabilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str
    current_balance: MoneyAmount
    interest_rate: str | None = None
    minimum_payment: MoneyAmount | None = None
    due_day: int | None = None
    account_id: UUID | None = None
    include_in_net_worth: bool = True


class LiabilityOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    type: str
    current_balance: MoneyAmount
    interest_rate: str | None
    minimum_payment: MoneyAmount | None
    due_day: int | None
    account_id: UUID | None
    include_in_net_worth: bool
    status: str

    model_config = {"from_attributes": True}


class LiabilityPaymentIn(BaseModel):
    account_id: UUID
    amount: MoneyAmount


class InvestmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = "other"
    current_value: MoneyAmount = "0.00"
    cost_basis: MoneyAmount = "0.00"
    institution: str | None = None
    account_id: UUID | None = None
    include_in_net_worth: bool = True


class InvestmentOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    type: str
    current_value: MoneyAmount
    cost_basis: MoneyAmount
    institution: str | None
    account_id: UUID | None
    include_in_net_worth: bool
    status: str

    model_config = {"from_attributes": True}


class InvestmentTxCreate(BaseModel):
    type: str
    amount: MoneyAmount
    date: Date
    account_id: UUID | None = None


class InvestmentTxOut(BaseModel):
    id: UUID
    investment_id: UUID
    account_id: UUID | None
    amount: MoneyAmount
    type: str
    date: Date


class WealthBuckets(BaseModel):
    cash: MoneySigned
    savings: MoneySigned
    investments: MoneySigned
    business: MoneySigned
    property: MoneySigned
    vehicle: MoneySigned
    other: MoneySigned
    loans: MoneySigned
    credit: MoneySigned
    other_debt: MoneySigned


class NetWorthSnapshotOut(BaseModel):
    period_start: Date
    period_end: Date
    as_of: Date
    net_worth: MoneySigned
    total_assets: MoneySigned
    total_liabilities: MoneySigned


class NetWorthOut(BaseModel):
    currency: str
    net_worth: MoneySigned
    total_assets: MoneySigned
    total_liabilities: MoneySigned
    emergency_fund: MoneySigned
    investments: MoneySigned
    debt: MoneySigned
    buckets: WealthBuckets
    history: list[NetWorthSnapshotOut]
