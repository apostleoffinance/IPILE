from datetime import date as Date
from uuid import UUID

from pydantic import BaseModel

from app.schemas.money import MoneyAmount


class CalendarEventOut(BaseModel):
    id: UUID
    kind: str
    title: str
    date: Date
    amount: MoneyAmount
    status: str
    coverage_label: str | None = None
    obligation_id: UUID | None = None
    occurrence_id: UUID | None = None
