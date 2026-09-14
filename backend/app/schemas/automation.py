from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: UUID
    household_id: UUID
    alert_id: UUID | None
    channel: str
    title: str
    body: str
    severity: str
    status: str
    created_at: datetime
    read_at: datetime | None

    model_config = {"from_attributes": True}


class TickIn(BaseModel):
    tick_type: str = "daily"
    period_key: str | None = None


class TickOut(BaseModel):
    id: UUID
    household_id: UUID
    tick_type: str
    period_key: str
    status: str
    result: dict
    skipped: bool = False

    model_config = {"from_attributes": True}
