from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.money import MoneySigned


class SimulationIn(BaseModel):
    name: str = "Scenario"
    monthly_income: MoneySigned | None = None
    income_change_rate: str = "0"
    expense_category_deltas: dict[str, str] = Field(default_factory=dict)
    obligation_deltas: dict[str, str] = Field(default_factory=dict)
    investment_override: MoneySigned | None = None
    unexpected_expense: MoneySigned | None = None
    horizon_months: int = Field(default=12, ge=1, le=60)


class MonthOut(BaseModel):
    month_index: int
    income: MoneySigned
    surplus: MoneySigned
    cash: MoneySigned
    emergency: MoneySigned
    investments: MoneySigned
    net_worth: MoneySigned
    forecast_sts: MoneySigned
    cash_flow: str
    obligations: str
    emergency_fund: str
    investments_status: str
    safe_to_spend: str
    net_worth_delta: MoneySigned


class SimulationRunOut(BaseModel):
    id: UUID
    household_id: UUID
    name: str
    parameters: dict
    status: str
    months: list[MonthOut]
    summary: MonthOut

    model_config = {"from_attributes": True}
