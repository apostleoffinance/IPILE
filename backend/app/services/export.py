from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.allocation import AllocationRule
from app.models.budget import Budget
from app.models.category import Category
from app.models.fund import SinkingFund
from app.models.goal import Goal
from app.models.household import Household
from app.models.income import IncomeSource
from app.models.member import HouseholdMember
from app.models.obligation import Obligation
from app.models.transaction import Transaction
from app.models.wealth import Asset, Investment, Liability
from app.money import quantize_money
from app.services.audit import write_audit


def _money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(quantize_money(Decimal(value)))


def _serialize_tx(row: Transaction) -> dict:
    return {
        "id": str(row.id),
        "account_id": str(row.account_id),
        "amount": _money(row.amount),
        "currency": row.currency,
        "type": row.type,
        "category_id": str(row.category_id) if row.category_id else None,
        "date": row.date.isoformat(),
        "merchant": row.merchant,
        "description": row.description,
        "status": row.status,
        "import_source": row.import_source,
        "external_id": row.external_id,
    }


def build_household_export(db: Session, household: Household) -> dict:
    hid = household.id
    members = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.household_id == hid, HouseholdMember.deleted_at.is_(None))
        .all()
    )
    accounts = (
        db.query(Account).filter(Account.household_id == hid, Account.deleted_at.is_(None)).all()
    )
    categories = (
        db.query(Category)
        .filter(Category.household_id == hid, Category.deleted_at.is_(None))
        .all()
    )
    transactions = (
        db.query(Transaction)
        .filter(Transaction.household_id == hid, Transaction.deleted_at.is_(None))
        .order_by(Transaction.date, Transaction.created_at)
        .all()
    )
    income_sources = (
        db.query(IncomeSource)
        .filter(IncomeSource.household_id == hid, IncomeSource.deleted_at.is_(None))
        .all()
    )
    budgets = db.query(Budget).filter(Budget.household_id == hid, Budget.deleted_at.is_(None)).all()
    obligations = (
        db.query(Obligation)
        .filter(Obligation.household_id == hid, Obligation.deleted_at.is_(None))
        .all()
    )
    funds = (
        db.query(SinkingFund)
        .filter(SinkingFund.household_id == hid, SinkingFund.deleted_at.is_(None))
        .all()
    )
    rules = (
        db.query(AllocationRule)
        .filter(AllocationRule.household_id == hid, AllocationRule.deleted_at.is_(None))
        .all()
    )
    goals = db.query(Goal).filter(Goal.household_id == hid, Goal.deleted_at.is_(None)).all()
    assets = db.query(Asset).filter(Asset.household_id == hid, Asset.deleted_at.is_(None)).all()
    liabilities = (
        db.query(Liability)
        .filter(Liability.household_id == hid, Liability.deleted_at.is_(None))
        .all()
    )
    investments = (
        db.query(Investment)
        .filter(Investment.household_id == hid, Investment.deleted_at.is_(None))
        .all()
    )
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "household": {
            "id": str(household.id),
            "name": household.name,
            "slug": household.slug,
            "base_currency": household.base_currency,
            "timezone": household.timezone,
            "country": household.country,
            "minimum_buffer_amount": _money(household.minimum_buffer_amount),
        },
        "members": [
            {
                "id": str(m.id),
                "display_name": m.display_name,
                "role": m.role,
                "relationship": m.relationship,
                "member_type": m.member_type,
            }
            for m in members
        ],
        "accounts": [
            {
                "id": str(a.id),
                "name": a.name,
                "type": a.type,
                "current_balance": _money(a.current_balance),
                "available_balance": _money(a.available_balance),
            }
            for a in accounts
        ],
        "categories": [{"id": str(c.id), "name": c.name, "kind": c.kind} for c in categories],
        "income_sources": [
            {
                "id": str(s.id),
                "name": s.name,
                "expected_amount": _money(s.expected_amount),
                "type": s.type,
            }
            for s in income_sources
        ],
        "transactions": [_serialize_tx(t) for t in transactions],
        "budgets": [{"id": str(b.id), "name": b.name} for b in budgets],
        "obligations": [
            {
                "id": str(o.id),
                "name": o.name,
                "amount": _money(o.amount),
                "frequency": o.frequency,
            }
            for o in obligations
        ],
        "funds": [
            {
                "id": str(f.id),
                "name": f.name,
                "target_amount": _money(f.target_amount),
                "current_amount": _money(f.current_amount),
            }
            for f in funds
        ],
        "allocation_rules": [
            {
                "id": str(r.id),
                "name": r.name,
                "type": r.type,
                "priority": r.priority,
                "mandatory": r.mandatory,
            }
            for r in rules
        ],
        "goals": [
            {
                "id": str(g.id),
                "name": g.name,
                "target_amount": _money(g.target_amount),
                "current_amount": _money(g.current_amount),
            }
            for g in goals
        ],
        "assets": [
            {"id": str(a.id), "name": a.name, "current_value": _money(a.current_value)}
            for a in assets
        ],
        "liabilities": [
            {
                "id": str(li.id),
                "name": li.name,
                "current_balance": _money(li.current_balance),
            }
            for li in liabilities
        ],
        "investments": [
            {
                "id": str(inv.id),
                "name": inv.name,
                "current_value": _money(inv.current_value),
            }
            for inv in investments
        ],
    }


def soft_delete_household(
    db: Session,
    household: Household,
    *,
    user_id: UUID,
) -> None:
    now = datetime.now(UTC)
    write_audit(
        db,
        household_id=household.id,
        user_id=user_id,
        action="delete",
        entity_type="household",
        entity_id=household.id,
        detail={"name": household.name, "slug": household.slug},
    )
    household.deleted_at = now
    db.add(household)
    members = (
        db.query(HouseholdMember)
        .filter(HouseholdMember.household_id == household.id, HouseholdMember.deleted_at.is_(None))
        .all()
    )
    for member in members:
        member.deleted_at = now
        db.add(member)
    db.flush()
