from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.money import MoneySigned


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str
    currency: str | None = None
    institution: str | None = None
    owner_member_id: UUID | None = None
    access_scope: str = "shared"
    business_id: UUID | None = None
    current_balance: MoneySigned = "0.00"
    is_protected: bool = False
    is_emergency: bool = False
    include_in_safe_to_spend: bool = True
    include_in_net_worth: bool = True

    @model_validator(mode="after")
    def validate_scope(self):
        if self.access_scope not in {"shared", "personal"}:
            raise ValueError("access_scope must be shared or personal.")
        if self.access_scope == "personal" and self.owner_member_id is None:
            raise ValueError("Personal accounts require an owner_member_id.")
        if self.access_scope == "shared" and self.owner_member_id is not None:
            raise ValueError("Shared accounts cannot have a personal owner.")
        return self


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
    access_scope: str
    business_id: UUID | None = None
    current_balance: MoneySigned
    available_balance: MoneySigned
    is_protected: bool
    is_emergency: bool
    include_in_safe_to_spend: bool
    include_in_net_worth: bool
    status: str

    model_config = {"from_attributes": True}
