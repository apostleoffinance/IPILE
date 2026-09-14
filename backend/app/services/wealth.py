from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.goal import Goal
from app.models.household import Household
from app.models.transaction import Transaction
from app.models.wealth import Asset, Investment, InvestmentTransaction, Liability, NetWorthSnapshot
from app.money import format_money, quantize_money
from app.schemas.wealth import (
    InvestmentOut,
    InvestmentTxOut,
    LiabilityOut,
    NetWorthOut,
    NetWorthSnapshotOut,
    WealthBuckets,
)
from app.services.allocations import period_bounds
from app.services.balances import apply_transaction_effect
from app.services.obligation_engine import add_months
from app.services.wealth_engine import (
    ASSET_TYPES,
    INVESTMENT_TX_TYPES,
    INVESTMENT_TYPES,
    LIABILITY_TYPES,
    AccountSpec,
    AssetSpec,
    GoalSpec,
    InvestmentSpec,
    LiabilitySpec,
    NetWorthResult,
    apply_investment_tx,
    apply_liability_payment,
    compute_net_worth,
)


def _accounts(db: Session, household_id: UUID) -> list[Account]:
    return (
        db.query(Account)
        .filter(Account.household_id == household_id, Account.deleted_at.is_(None))
        .all()
    )


def _get_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
    account = (
        db.query(Account)
        .filter(
            Account.id == account_id,
            Account.household_id == household_id,
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account


def household_net_worth(db: Session, household: Household) -> NetWorthResult:
    accounts = [
        AccountSpec(
            id=row.id,
            type=row.type,
            current_balance=quantize_money(Decimal(str(row.current_balance))),
            include_in_net_worth=row.include_in_net_worth,
            is_emergency=bool(getattr(row, "is_emergency", False)),
            status=row.status,
        )
        for row in _accounts(db, household.id)
    ]
    assets = (
        db.query(Asset)
        .filter(
            Asset.household_id == household.id,
            Asset.deleted_at.is_(None),
            Asset.status == "active",
        )
        .all()
    )
    investments = (
        db.query(Investment)
        .filter(
            Investment.household_id == household.id,
            Investment.deleted_at.is_(None),
            Investment.status == "active",
        )
        .all()
    )
    liabilities = (
        db.query(Liability)
        .filter(Liability.household_id == household.id, Liability.deleted_at.is_(None))
        .all()
    )
    goals = (
        db.query(Goal)
        .filter(
            Goal.household_id == household.id,
            Goal.deleted_at.is_(None),
            Goal.status.in_(("active", "paused", "completed")),
        )
        .all()
    )
    return compute_net_worth(
        accounts,
        [
            AssetSpec(
                type=row.type,
                current_value=quantize_money(Decimal(str(row.current_value))),
                include_in_net_worth=row.include_in_net_worth,
                account_id=row.account_id,
                is_emergency=row.is_emergency,
            )
            for row in assets
        ],
        [
            InvestmentSpec(
                current_value=quantize_money(Decimal(str(row.current_value))),
                include_in_net_worth=row.include_in_net_worth,
                account_id=row.account_id,
            )
            for row in investments
        ],
        [
            LiabilitySpec(
                type=row.type,
                current_balance=quantize_money(Decimal(str(row.current_balance))),
                include_in_net_worth=row.include_in_net_worth,
                status=row.status,
                account_id=row.account_id,
            )
            for row in liabilities
        ],
        [
            GoalSpec(
                current_amount=quantize_money(Decimal(str(row.current_amount))),
                is_emergency=row.type == "emergency",
                account_id=row.account_id,
            )
            for row in goals
        ],
    )


def _breakdown(result: NetWorthResult) -> dict:
    return {
        "cash": format_money(result.assets.cash),
        "savings": format_money(result.assets.savings),
        "investments": format_money(result.assets.investments),
        "business": format_money(result.assets.business),
        "property": format_money(result.assets.property),
        "vehicle": format_money(result.assets.vehicle),
        "other": format_money(result.assets.other),
        "loans": format_money(result.liabilities.loans),
        "credit": format_money(result.liabilities.credit),
        "other_debt": format_money(result.liabilities.other_debt),
    }


def upsert_snapshot(
    db: Session,
    household: Household,
    result: NetWorthResult,
    *,
    period_start: date,
    period_end: date,
    as_of: date,
) -> NetWorthSnapshot:
    row = (
        db.query(NetWorthSnapshot)
        .filter(
            NetWorthSnapshot.household_id == household.id,
            NetWorthSnapshot.period_start == period_start,
        )
        .first()
    )
    if row is None:
        row = NetWorthSnapshot(household_id=household.id, period_start=period_start)
        db.add(row)
    row.period_end = period_end
    row.as_of = as_of
    row.total_assets = result.total_assets
    row.total_liabilities = result.total_liabilities
    row.net_worth = result.net_worth
    row.emergency_fund = result.emergency_fund
    row.investments = result.investments
    row.debt = result.debt
    row.breakdown = _breakdown(result)
    db.add(row)
    db.flush()
    return row


def close_period_if_needed(db: Session, household: Household, today: date | None = None) -> None:
    today = today or date.today()
    start, end = period_bounds(household, today)
    previous_start = add_months(start, -1)
    previous_end = start - timedelta(days=1)
    if today <= end:
        existing = (
            db.query(NetWorthSnapshot)
            .filter(
                NetWorthSnapshot.household_id == household.id,
                NetWorthSnapshot.period_start == previous_start,
            )
            .first()
        )
        if existing is None and today > previous_end:
            result = household_net_worth(db, household)
            upsert_snapshot(
                db,
                household,
                result,
                period_start=previous_start,
                period_end=previous_end,
                as_of=previous_end,
            )


def serialize_net_worth(db: Session, household: Household) -> NetWorthOut:
    today = date.today()
    close_period_if_needed(db, household, today)
    result = household_net_worth(db, household)
    start, end = period_bounds(household, today)
    upsert_snapshot(db, household, result, period_start=start, period_end=end, as_of=today)
    history = (
        db.query(NetWorthSnapshot)
        .filter(NetWorthSnapshot.household_id == household.id)
        .order_by(NetWorthSnapshot.period_start)
        .all()
    )
    return NetWorthOut(
        currency=household.base_currency,
        net_worth=result.net_worth,
        total_assets=result.total_assets,
        total_liabilities=result.total_liabilities,
        emergency_fund=result.emergency_fund,
        investments=result.investments,
        debt=result.debt,
        buckets=WealthBuckets(
            cash=result.assets.cash,
            savings=result.assets.savings,
            investments=result.assets.investments,
            business=result.assets.business,
            property=result.assets.property,
            vehicle=result.assets.vehicle,
            other=result.assets.other,
            loans=result.liabilities.loans,
            credit=result.liabilities.credit,
            other_debt=result.liabilities.other_debt,
        ),
        history=[
            NetWorthSnapshotOut(
                period_start=row.period_start,
                period_end=row.period_end,
                as_of=row.as_of,
                net_worth=quantize_money(Decimal(str(row.net_worth))),
                total_assets=quantize_money(Decimal(str(row.total_assets))),
                total_liabilities=quantize_money(Decimal(str(row.total_liabilities))),
            )
            for row in history
        ],
    )


def serialize_liability(row: Liability) -> LiabilityOut:
    rate = None
    if row.interest_rate is not None:
        rate = format(Decimal(str(row.interest_rate)), "f")
    minimum = None
    if row.minimum_payment is not None:
        minimum = quantize_money(Decimal(str(row.minimum_payment)))
    return LiabilityOut(
        id=row.id,
        household_id=row.household_id,
        name=row.name,
        type=row.type,
        current_balance=quantize_money(Decimal(str(row.current_balance))),
        interest_rate=rate,
        minimum_payment=minimum,
        due_day=row.due_day,
        account_id=row.account_id,
        include_in_net_worth=row.include_in_net_worth,
        status=row.status,
    )


def serialize_investment(row: Investment) -> InvestmentOut:
    return InvestmentOut.model_validate(row)


def create_asset(db: Session, household: Household, payload) -> Asset:
    if payload.type not in ASSET_TYPES:
        raise HTTPException(status_code=400, detail="Invalid asset type.")
    if payload.account_id:
        _get_account(db, household.id, payload.account_id)
    row = Asset(
        household_id=household.id,
        name=payload.name,
        type=payload.type,
        current_value=payload.current_value,
        as_of=payload.as_of,
        account_id=payload.account_id,
        include_in_net_worth=payload.include_in_net_worth,
        is_emergency=payload.is_emergency,
        status="active",
    )
    db.add(row)
    db.flush()
    return row


def create_liability(db: Session, household: Household, payload) -> Liability:
    if payload.type not in LIABILITY_TYPES:
        raise HTTPException(status_code=400, detail="Invalid liability type.")
    rate = None
    if payload.interest_rate is not None:
        rate = Decimal(str(payload.interest_rate))
    if payload.account_id:
        _get_account(db, household.id, payload.account_id)
    row = Liability(
        household_id=household.id,
        name=payload.name,
        type=payload.type,
        current_balance=payload.current_balance,
        interest_rate=rate,
        minimum_payment=payload.minimum_payment,
        due_day=payload.due_day,
        account_id=payload.account_id,
        include_in_net_worth=payload.include_in_net_worth,
        status="active",
    )
    db.add(row)
    db.flush()
    return row


def create_investment(db: Session, household: Household, payload) -> Investment:
    if payload.type not in INVESTMENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid investment type.")
    if payload.account_id:
        _get_account(db, household.id, payload.account_id)
    row = Investment(
        household_id=household.id,
        name=payload.name,
        type=payload.type,
        current_value=payload.current_value,
        cost_basis=payload.cost_basis,
        institution=payload.institution,
        account_id=payload.account_id,
        include_in_net_worth=payload.include_in_net_worth,
        status="active",
    )
    db.add(row)
    db.flush()
    return row


def record_investment_tx(
    db: Session,
    household: Household,
    investment: Investment,
    *,
    tx_type: str,
    amount: Decimal,
    tx_date: date,
    account_id: UUID | None,
) -> InvestmentTransaction:
    if tx_type not in INVESTMENT_TX_TYPES:
        raise HTTPException(status_code=400, detail="Invalid investment transaction type.")
    value, basis = apply_investment_tx(
        Decimal(str(investment.current_value)),
        Decimal(str(investment.cost_basis)),
        tx_type,
        amount,
    )
    investment.current_value = value
    investment.cost_basis = basis
    db.add(investment)
    money_tx_id = None
    account = None
    if account_id is not None:
        account = _get_account(db, household.id, account_id)
        effect_type = "investment" if tx_type == "buy" else None
        if tx_type == "sell":
            effect_type = "refund"
        if tx_type == "dividend":
            effect_type = "income"
        if effect_type is not None:
            money_tx = Transaction(
                household_id=household.id,
                account_id=account.id,
                amount=amount,
                currency=household.base_currency,
                type=effect_type,
                date=tx_date,
                description=f"{tx_type} {investment.name}",
                status="cleared",
                import_source="manual",
            )
            db.add(money_tx)
            apply_transaction_effect(
                db,
                account=account,
                counterparty=None,
                tx_type=effect_type,
                amount=amount,
                status="cleared",
            )
            db.flush()
            money_tx_id = money_tx.id
    row = InvestmentTransaction(
        household_id=household.id,
        investment_id=investment.id,
        account_id=account.id if account else None,
        amount=quantize_money(amount),
        type=tx_type,
        date=tx_date,
        transaction_id=money_tx_id,
    )
    db.add(row)
    db.flush()
    return row


def pay_liability(
    db: Session,
    household: Household,
    liability: Liability,
    *,
    account_id: UUID,
    amount: Decimal,
) -> Liability:
    if liability.status == "paid_off":
        raise HTTPException(status_code=400, detail="Liability is already paid off.")
    account = _get_account(db, household.id, account_id)
    remaining, status = apply_liability_payment(Decimal(str(liability.current_balance)), amount)
    money_tx = Transaction(
        household_id=household.id,
        account_id=account.id,
        amount=amount,
        currency=household.base_currency,
        type="debt_payment",
        date=date.today(),
        description=f"Payment {liability.name}",
        status="cleared",
        import_source="manual",
    )
    db.add(money_tx)
    apply_transaction_effect(
        db,
        account=account,
        counterparty=None,
        tx_type="debt_payment",
        amount=amount,
        status="cleared",
    )
    liability.current_balance = remaining
    liability.status = status
    db.add(liability)
    db.flush()
    return liability


def serialize_investment_tx(row: InvestmentTransaction) -> InvestmentTxOut:
    return InvestmentTxOut(
        id=row.id,
        investment_id=row.investment_id,
        account_id=row.account_id,
        amount=quantize_money(Decimal(str(row.amount))),
        type=row.type,
        date=row.date,
    )
