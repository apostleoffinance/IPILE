from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    display_name: str = Field(min_length=1, max_length=200)
    invite_token: str | None = None
    create_household: bool = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    status: str

    model_config = {"from_attributes": True}


class HouseholdSummary(BaseModel):
    id: UUID
    name: str
    role: str
    slug: str


class MeOut(UserOut):
    households: list[HouseholdSummary] = []


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorBody
