from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AlertOut(BaseModel):
    id: UUID
    household_id: UUID
    type: str
    severity: str
    title: str
    body: str
    related_entity_type: str
    related_entity_id: UUID
    period_key: str
    status: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
