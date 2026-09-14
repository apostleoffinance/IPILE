from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.fund import FundContribution, SinkingFund
from app.models.obligation import Obligation
from app.money import format_money, quantize_money
from app.schemas.fund import FundOut
from app.services.fund_engine import (
    expected_funded_by,
    fund_progress,
    on_track,
    required_monthly,
    shortfall,
)
from app.services.obligation_engine import coverage_label, obligation_monthly


def attach_fund(db: Session, obligation: Obligation) -> SinkingFund | None:
    if not obligation.sinking_fund or obligation.fund_id:
        if obligation.fund_id:
            return db.get(SinkingFund, obligation.fund_id)
        return None
    monthly = obligation_monthly(
        Decimal(str(obligation.amount)),
        obligation.frequency,
        today=obligation.next_due_date,
        next_due_date=obligation.next_due_date,
    )
    fund = SinkingFund(
        household_id=obligation.household_id,
        name=f"{obligation.name} fund",
        target_amount=obligation.amount,
        current_amount=Decimal("0.00"),
        target_date=obligation.next_due_date,
        obligation_id=obligation.id,
        monthly_contribution=monthly,
        is_protected=True,
        status="active",
    )
    db.add(fund)
    db.flush()
    ensure_fund_account(db, fund)
    obligation.fund_id = fund.id
    db.add(obligation)
    return fund


def serialize_fund(db: Session, fund: SinkingFund, today: date | None = None) -> FundOut:
    today = today or date.today()
    obligation = db.get(Obligation, fund.obligation_id) if fund.obligation_id else None
    obligation_name = obligation.name if obligation else None
    obligation_req = Decimal("0.00")
    if obligation:
        obligation_req = obligation_monthly(
            Decimal(str(obligation.amount)),
            obligation.frequency,
            today=today,
            next_due_date=obligation.next_due_date,
            already_funded=quantize_money(Decimal(str(fund.current_amount))),
        )
    monthly = required_monthly(obligation_req, Decimal(str(fund.monthly_contribution)))
    start = today
    if fund.created_at is not None:
        start = fund.created_at.date()
    if obligation is not None and obligation.created_at is not None:
        start = min(start, obligation.created_at.date())
    expected = expected_funded_by(
        monthly,
        start=start,
        today=today,
        target_date=fund.target_date,
    )
    current = quantize_money(Decimal(str(fund.current_amount)))
    target = quantize_money(Decimal(str(fund.target_amount)))
    progress = fund_progress(current, target)
    return FundOut(
        id=fund.id,
        household_id=fund.household_id,
        name=fund.name,
        target_amount=target,
        current_amount=current,
        target_date=fund.target_date,
        obligation_id=fund.obligation_id,
        obligation_name=obligation_name,
        monthly_contribution=quantize_money(Decimal(str(fund.monthly_contribution))),
        required_monthly=monthly,
        expected_amount=expected,
        shortfall=shortfall(expected, current),
        on_track=on_track(current, expected),
        progress=format_money(progress),
        coverage_label=coverage_label(progress),
        account_id=fund.account_id,
        is_protected=fund.is_protected,
        status=fund.status,
    )


def ensure_fund_account(db: Session, fund: SinkingFund) -> Account:
    if fund.account_id:
        account = db.get(Account, fund.account_id)
        if account:
            return account
    account = Account(
        household_id=fund.household_id,
        name=fund.name,
        type="savings",
        currency="NGN",
        current_balance=Decimal("0.00"),
        available_balance=Decimal("0.00"),
        is_protected=True,
        include_in_safe_to_spend=False,
        include_in_net_worth=True,
        status="active",
    )
    db.add(account)
    db.flush()
    fund.account_id = account.id
    db.add(fund)
    return account


def apply_contribution(fund: SinkingFund, amount: Decimal) -> None:
    fund.current_amount = quantize_money(Decimal(str(fund.current_amount)) + quantize_money(amount))


def apply_payment_from_fund(fund: SinkingFund, amount: Decimal) -> Decimal:
    current = quantize_money(Decimal(str(fund.current_amount)))
    drawn = min(current, quantize_money(amount))
    fund.current_amount = quantize_money(current - drawn)
    return drawn


def record_contribution(
    db: Session,
    fund: SinkingFund,
    *,
    account_id: UUID,
    amount: Decimal,
    contribution_date: date,
    transaction_id: UUID | None,
) -> FundContribution:
    apply_contribution(fund, amount)
    row = FundContribution(
        household_id=fund.household_id,
        fund_id=fund.id,
        account_id=account_id,
        amount=quantize_money(amount),
        date=contribution_date,
        transaction_id=transaction_id,
    )
    db.add(row)
    db.add(fund)
    return row
