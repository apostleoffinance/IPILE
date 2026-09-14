from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.household import Household
from app.models.wealth import Asset, Investment
from app.money import quantize_money


def _account(db: Session, household_id, name: str) -> Account | None:
    return (
        db.query(Account)
        .filter(
            Account.household_id == household_id,
            Account.name == name,
            Account.deleted_at.is_(None),
        )
        .first()
    )


def seed_wealth(db: Session, household: Household) -> None:
    emergency = _account(db, household.id, "Emergency savings")
    if emergency is not None:
        emergency.is_emergency = True
        emergency.is_protected = True
        emergency.include_in_safe_to_spend = False
        db.add(emergency)
        existing_asset = (
            db.query(Asset)
            .filter(
                Asset.household_id == household.id,
                Asset.account_id == emergency.id,
                Asset.deleted_at.is_(None),
            )
            .first()
        )
        if existing_asset is None:
            db.add(
                Asset(
                    household_id=household.id,
                    name="Emergency fund",
                    type="savings",
                    current_value=quantize_money(Decimal(str(emergency.current_balance))),
                    account_id=emergency.id,
                    include_in_net_worth=True,
                    is_emergency=True,
                    status="active",
                )
            )

    brokerage = _account(db, household.id, "Investments")
    if brokerage is not None:
        existing_inv = (
            db.query(Investment)
            .filter(
                Investment.household_id == household.id,
                Investment.account_id == brokerage.id,
                Investment.deleted_at.is_(None),
            )
            .first()
        )
        if existing_inv is None:
            db.add(
                Investment(
                    household_id=household.id,
                    name="Family investments",
                    type="equity",
                    current_value=quantize_money(Decimal(str(brokerage.current_balance))),
                    cost_basis=quantize_money(Decimal(str(brokerage.current_balance))),
                    institution="Seed Broker",
                    account_id=brokerage.id,
                    include_in_net_worth=True,
                    status="active",
                )
            )
    db.flush()
