from datetime import date as Date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class GivingPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str = Field(min_length=1, max_length=80)
    monthly_limit: Decimal | None = None
    annual_limit: Decimal | None = None
    requires_dual_approval: bool = False
    allocation_rule_id: UUID | None = None


class GivingPolicyOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    kind: str
    monthly_limit: Decimal | None
    annual_limit: Decimal | None
    requires_dual_approval: bool
    allocation_rule_id: UUID | None
    status: str
    monthly_used: Decimal = Decimal("0.00")
    annual_used: Decimal = Decimal("0.00")
    limit_breached: bool = False

    model_config = {"from_attributes": True}


class GivingCreate(BaseModel):
    kind: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0)
    account_id: UUID
    date: Date | None = None
    beneficiary: str | None = None
    policy_id: UUID | None = None
    category_id: UUID | None = None
    notes: str | None = None


class GivingRecordOut(BaseModel):
    id: UUID
    household_id: UUID
    policy_id: UUID | None
    kind: str
    beneficiary: str | None
    amount: Decimal
    currency: str
    date: Date
    account_id: UUID
    transaction_id: UUID | None
    status: str
    limit_warning: str | None
    notes: str | None
    created_by_member_id: UUID | None
    approved_by_member_id: UUID | None

    model_config = {"from_attributes": True}


class GivingSummaryOut(BaseModel):
    period_month: str
    policies: list[GivingPolicyOut]
    records: list[GivingRecordOut]
    pending_approvals: list[GivingRecordOut]
    total_posted_month: Decimal
    total_posted_year: Decimal
