from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.money import MoneySigned


class HealthComponentOut(BaseModel):
    key: str
    weight: MoneySigned
    points: MoneySigned
    inputs: dict[str, Any]


class HealthOut(BaseModel):
    score: MoneySigned
    label: str
    period_start: date
    period_end: date
    components: list[HealthComponentOut]


class SnapshotOut(BaseModel):
    id: UUID
    household_id: UUID
    period_start: date
    period_end: date
    as_of: date
    income: MoneySigned
    expenses: MoneySigned
    savings: MoneySigned
    investments: MoneySigned
    giving: MoneySigned
    debt_reduction: MoneySigned
    surplus: MoneySigned
    net_worth: MoneySigned
    health_score: MoneySigned
    payload: dict[str, Any]

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: UUID
    household_id: UUID
    kind: str
    period_start: date
    period_end: date
    payload: dict[str, Any]

    model_config = {"from_attributes": True}
