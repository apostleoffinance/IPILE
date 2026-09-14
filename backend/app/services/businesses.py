from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.business import Business, BusinessEmployee, BusinessTransaction
from app.money import quantize_money
from app.schemas.business import (
    BusinessEmployeeOut,
    BusinessOut,
    BusinessPnLOut,
    BusinessTxOut,
)
from app.services.business_engine import BusinessLine, BusinessPnL, compute_pnl


def _lines(rows: list[BusinessTransaction]) -> list[BusinessLine]:
    return [
        BusinessLine(type=row.type, amount=quantize_money(Decimal(str(row.amount))))
        for row in rows
        if row.deleted_at is None
    ]


def account_balance(db: Session, business: Business) -> Decimal | None:
    if business.account_id is None:
        return None
    account = db.get(Account, business.account_id)
    if account is None:
        return None
    return quantize_money(Decimal(str(account.current_balance)))


def business_pnl(db: Session, business: Business) -> BusinessPnL:
    rows = (
        db.query(BusinessTransaction)
        .filter(
            BusinessTransaction.business_id == business.id,
            BusinessTransaction.deleted_at.is_(None),
        )
        .all()
    )
    return compute_pnl(_lines(rows), account_balance(db, business))


def serialize_pnl(result: BusinessPnL) -> BusinessPnLOut:
    return BusinessPnLOut(
        revenue=result.revenue,
        expenses=result.expenses,
        profit=result.profit,
        family_invested=result.family_invested,
        family_withdrawn=result.family_withdrawn,
        current_business_equity=result.current_business_equity,
        family_return=result.family_return,
    )


def serialize_employee(row: BusinessEmployee) -> BusinessEmployeeOut:
    return BusinessEmployeeOut(
        id=row.id,
        business_id=row.business_id,
        name=row.name,
        role=row.role,
        compensation=quantize_money(Decimal(str(row.compensation)))
        if row.compensation is not None
        else None,
        status=row.status,
    )


def serialize_tx(row: BusinessTransaction) -> BusinessTxOut:
    return BusinessTxOut(
        id=row.id,
        business_id=row.business_id,
        type=row.type,
        amount=quantize_money(Decimal(str(row.amount))),
        date=row.date,
        description=row.description,
        employee_id=row.employee_id,
        household_transaction_id=row.household_transaction_id,
    )


def serialize_business(db: Session, business: Business) -> BusinessOut:
    employees = (
        db.query(BusinessEmployee)
        .filter(
            BusinessEmployee.business_id == business.id,
            BusinessEmployee.deleted_at.is_(None),
        )
        .order_by(BusinessEmployee.name)
        .all()
    )
    txs = (
        db.query(BusinessTransaction)
        .filter(
            BusinessTransaction.business_id == business.id,
            BusinessTransaction.deleted_at.is_(None),
        )
        .order_by(BusinessTransaction.date.desc(), BusinessTransaction.created_at.desc())
        .limit(50)
        .all()
    )
    return BusinessOut(
        id=business.id,
        household_id=business.household_id,
        name=business.name,
        type=business.type,
        account_id=business.account_id,
        status=business.status,
        pnl=serialize_pnl(business_pnl(db, business)),
        employees=[serialize_employee(row) for row in employees],
        transactions=[serialize_tx(row) for row in txs],
    )


def ensure_business_account(db: Session, business: Business) -> Account:
    if business.account_id:
        account = db.get(Account, business.account_id)
        if account:
            return account
    account = Account(
        household_id=business.household_id,
        name=business.name,
        type="business",
        currency="NGN",
        current_balance=Decimal("0.00"),
        available_balance=Decimal("0.00"),
        is_protected=True,
        include_in_safe_to_spend=False,
        include_in_net_worth=True,
        business_id=business.id,
        status="active",
    )
    db.add(account)
    db.flush()
    business.account_id = account.id
    db.add(business)
    return account


def get_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
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


def record_business_tx(
    db: Session,
    business: Business,
    *,
    tx_type: str,
    amount: Decimal,
    when: date,
    account_id: UUID | None,
    employee_id: UUID | None,
    description: str | None,
    household_transaction_id: UUID | None,
) -> BusinessTransaction:
    row = BusinessTransaction(
        household_id=business.household_id,
        business_id=business.id,
        employee_id=employee_id,
        account_id=account_id or business.account_id,
        household_transaction_id=household_transaction_id,
        amount=quantize_money(amount),
        type=tx_type,
        date=when,
        description=description,
    )
    db.add(row)
    return row
