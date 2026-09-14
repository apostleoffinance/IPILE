from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneySigned


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str
    currency: str = "NGN"
    institution: str | None = None
    owner_member_id: UUID | None = None
    business_id: UUID | None = None
    current_balance: MoneySigned = "0.00"
    is_protected: bool = False
    is_emergency: bool = False
    include_in_safe_to_spend: bool = True
    include_in_net_worth: bool = True


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    institution: str | None = None
    is_protected: bool | None = None
    is_emergency: bool | None = None
    include_in_safe_to_spend: bool | None = None
    include_in_net_worth: bool | None = None
    status: str | None = None


class AccountOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    type: str
    currency: str
    institution: str | None
    owner_member_id: UUID | None
    business_id: UUID | None = None
    current_balance: MoneySigned
    available_balance: MoneySigned
    is_protected: bool
    is_emergency: bool
    include_in_safe_to_spend: bool
    include_in_net_worth: bool
    status: str

    model_config = {"from_attributes": True}
