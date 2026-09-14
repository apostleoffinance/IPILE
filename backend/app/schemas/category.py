from uuid import UUID

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str
    parent_id: UUID | None = None
    sort_order: int = 0


class CategoryOut(BaseModel):
    id: UUID
    household_id: UUID
    parent_id: UUID | None
    name: str
    kind: str
    is_system: bool
    sort_order: int

    model_config = {"from_attributes": True}
