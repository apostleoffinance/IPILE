from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.money import MoneySigned


class SimulationIn(BaseModel):
    name: str = Field(default="Scenario", min_length=1, max_length=100)
    monthly_income: MoneySigned | None = None
    income_change_rate: str = "0"
    contribution_change_rate: str = "0"
    debt_strategy: Literal["snowball", "avalanche"] = "avalanche"
    debt_extra_payment: MoneySigned = Decimal("0.00")
    expense_category_deltas: dict[str, str] = Field(default_factory=dict)
    obligation_deltas: dict[str, str] = Field(default_factory=dict)
    investment_override: MoneySigned | None = None
    unexpected_expense: MoneySigned | None = None
    horizon_months: int = Field(default=12, ge=1, le=60)

    @field_validator(
        "monthly_income",
        "investment_override",
        "unexpected_expense",
        "debt_extra_payment",
    )
    @classmethod
    def hypothetical_amounts_must_be_non_negative(cls, value):
        if value is not None and value < 0:
            raise ValueError("Scenario amounts cannot be negative.")
        return value

    @field_validator("income_change_rate", "contribution_change_rate")
    @classmethod
    def validate_income_change_rates(cls, value):
        try:
            rate = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Income change rates must be decimals.") from exc
        if not rate.is_finite() or rate < -1:
            raise ValueError("Income change rates cannot reduce income below zero.")
        return value

    @field_validator("expense_category_deltas", "obligation_deltas")
    @classmethod
    def validate_scenario_deltas(cls, values):
        for key, raw in values.items():
            try:
                rate = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError(f"Scenario delta for {key} must be a decimal.") from exc
            if not rate.is_finite() or rate < -1:
                raise ValueError("Scenario deltas cannot reduce amounts below zero.")
        return values


class MonthOut(BaseModel):
    month_index: int
    income: MoneySigned
    contributions: MoneySigned
    debt_payments: MoneySigned
    debt_interest: MoneySigned
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
