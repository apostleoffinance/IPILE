from uuid import UUID

from pydantic import BaseModel

from app.schemas.money import MoneyAmount, MoneySigned


class SafeToSpendComponents(BaseModel):
    liquid_cash: MoneySigned
    expected_income: MoneySigned
    committed_obligations: MoneySigned
    upcoming_bills: MoneySigned
    sinking_fund_requirements: MoneySigned
    protected_savings: MoneySigned
    pending_transactions: MoneySigned


class SafeToSpendOut(BaseModel):
    currency: str
    current: MoneySigned
    period: MoneySigned
    forecast: MoneySigned
    horizon_days: int
    minimum_buffer_amount: MoneyAmount
    components: SafeToSpendComponents


class PurchaseCheckIn(BaseModel):
    amount: MoneyAmount
    category_id: UUID | None = None
    account_id: UUID | None = None


class PurchaseCheckOut(BaseModel):
    amount: MoneyAmount
    affordable: bool
    severity: str
    remaining_current_sts: MoneySigned
    obligations_affected: list[str]
    buffer_breached: bool
    recommended_action: str
