from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = "other"
    account_id: UUID | None = None


class BusinessEmployeeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str = "staff"
    compensation: MoneyAmount | None = None


class BusinessEmployeeOut(BaseModel):
    id: UUID
    business_id: UUID
    name: str
    role: str
    compensation: MoneyAmount | None
    status: str


class BusinessTxCreate(BaseModel):
    type: str
    amount: MoneyAmount
    date: Date
    account_id: UUID | None = None
    employee_id: UUID | None = None
    description: str | None = None


class BusinessTxOut(BaseModel):
    id: UUID
    business_id: UUID
    type: str
    amount: MoneyAmount
    date: Date
    description: str | None
    employee_id: UUID | None
    household_transaction_id: UUID | None


class BusinessPnLOut(BaseModel):
    revenue: MoneyAmount
    expenses: MoneyAmount
    profit: MoneyAmount
    family_invested: MoneyAmount
    family_withdrawn: MoneyAmount
    current_business_equity: MoneyAmount
    family_return: MoneyAmount


class BusinessOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    type: str
    account_id: UUID | None
    status: str
    pnl: BusinessPnLOut
    employees: list[BusinessEmployeeOut]
    transactions: list[BusinessTxOut]
