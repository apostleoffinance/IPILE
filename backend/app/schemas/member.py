from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class MemberCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    role: str = Field(default="member")
    relationship: str = Field(default="other")
    member_type: str = Field(default="adult")
    date_of_birth: date | None = None
    is_financial_contributor: bool = False
    user_id: UUID | None = None
    email: str | None = None


class MemberUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    role: str | None = None
    relationship: str | None = None
    member_type: str | None = None
    is_financial_contributor: bool | None = None


class MemberOut(BaseModel):
    id: UUID
    household_id: UUID
    user_id: UUID | None
    display_name: str
    role: str
    relationship: str
    member_type: str
    date_of_birth: date | None
    is_financial_contributor: bool

    model_config = {"from_attributes": True}
