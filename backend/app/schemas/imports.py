from uuid import UUID

from pydantic import BaseModel, Field


class ImportBody(BaseModel):
    account_id: UUID
    content: str = Field(min_length=1)
    filename: str | None = None


class ImportJobOut(BaseModel):
    id: UUID
    household_id: UUID
    source: str
    filename: str | None
    status: str
    created_count: int
    skipped_count: int
    error_count: int
    result: dict

    model_config = {"from_attributes": True}
