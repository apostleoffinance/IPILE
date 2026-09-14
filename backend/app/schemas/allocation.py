from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneyAmount, MoneySigned


class AllocationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str
    basis: str = "recognized_income"
    rate: str | None = None
    amount: MoneyAmount | None = None
    priority: int = 0
    mandatory: bool = True
    destination_type: str
    destination_id: UUID | None = None
    income_source_id: UUID | None = None
    is_active: bool = True
    effective_from: Date | None = None
    effective_to: Date | None = None


class AllocationRuleOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    type: str
    basis: str
    rate: str | None
    amount: MoneyAmount | None
    priority: int
    mandatory: bool
    destination_type: str
    destination_id: UUID | None
    income_source_id: UUID | None
    is_active: bool
    effective_from: Date | None
    effective_to: Date | None

    model_config = {"from_attributes": True}


class AllocationLineOut(BaseModel):
    id: UUID
    rule_id: UUID | None
    name: str
    requested_amount: MoneyAmount
    amount: MoneyAmount
    destination_type: str
    destination_id: UUID | None
    mandatory: bool
    funded: bool


class UnfundedMandatoryOut(BaseModel):
    rule_id: UUID | None
    name: str
    requested_amount: MoneyAmount
    amount: MoneyAmount


class AllocationRunOut(BaseModel):
    id: UUID
    household_id: UUID
    period_start: Date
    period_end: Date
    recognized_income: MoneyAmount
    total_allocated: MoneyAmount
    surplus: MoneySigned
    status: str
    lines: list[AllocationLineOut]
    unfunded_mandatory: list[UnfundedMandatoryOut]
