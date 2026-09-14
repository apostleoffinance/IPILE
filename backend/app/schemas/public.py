from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="partner")


class InviteOut(BaseModel):
    id: UUID
    household_id: UUID
    email: str
    role: str
    token: str
    status: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class InviteAccept(BaseModel):
    token: str = Field(min_length=8)


class BillingOut(BaseModel):
    household_id: str
    plan: str
    plan_name: str
    price_monthly: str
    currency: str
    billing_status: str
    plans: list[dict]


class BillingChange(BaseModel):
    plan: str


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=4000)


class SupportTicketOut(BaseModel):
    id: UUID
    household_id: UUID | None
    subject: str
    body: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OnboardingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    minimum_buffer_amount: str | None = None
