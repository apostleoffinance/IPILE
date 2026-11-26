from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneySigned


class HouseholdCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    base_currency: str = Field(default="NGN", min_length=3, max_length=3)
    country: str = Field(default="NG", min_length=2, max_length=2)


class HouseholdUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    minimum_buffer_amount: MoneySigned | None = None
    fiscal_month_start_day: int | None = Field(default=None, ge=1, le=28)
    country: str | None = Field(default=None, min_length=2, max_length=2)\n    reporting_currency: str | None = Field(default=None, min_length=3, max_length=3)


class HouseholdOut(BaseModel):
    id: UUID
    name: str
    slug: str
    base_currency: str
    timezone: str
    country: str
    fiscal_month_start_day: int
    minimum_buffer_amount: MoneySigned
    plan: str = "pilot"
    billing_status: str = "active"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class HouseholdMembershipOut(BaseModel):
    id: UUID
    name: str
    role: str
    slug: str
