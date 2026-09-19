from datetime import date as Date

from pydantic import BaseModel

from app.schemas.money import MoneySigned


class CashFlowDayOut(BaseModel):
    date: Date
    income: MoneySigned
    expenses: MoneySigned
    giving: MoneySigned
    transfers_net: MoneySigned
    net: MoneySigned
    closing_cash: MoneySigned


class CashFlowOut(BaseModel):
    period_start: Date
    period_end: Date
    opening_cash: MoneySigned
    closing_cash: MoneySigned
    income: MoneySigned
    expenses: MoneySigned
    giving: MoneySigned
    transfers_net: MoneySigned
    surplus: MoneySigned
    daily: list[CashFlowDayOut]
