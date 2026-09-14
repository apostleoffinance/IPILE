from sqlalchemy.orm import Session

from app.models.business import Business, BusinessEmployee
from app.models.household import Household
from app.services.businesses import ensure_business_account


def seed_business(db: Session, household: Household) -> None:
    existing = (
        db.query(Business)
        .filter(
            Business.household_id == household.id,
            Business.name == "Salon",
            Business.deleted_at.is_(None),
        )
        .first()
    )
    if existing is None:
        existing = Business(
            household_id=household.id,
            name="Salon",
            type="service",
            status="active",
        )
        db.add(existing)
        db.flush()
        account = ensure_business_account(db, existing)
        account.business_id = existing.id
        account.include_in_safe_to_spend = False
        db.add(account)
    staff = (
        db.query(BusinessEmployee)
        .filter(
            BusinessEmployee.business_id == existing.id,
            BusinessEmployee.name == "Stylist",
            BusinessEmployee.deleted_at.is_(None),
        )
        .first()
    )
    if staff is None:
        db.add(
            BusinessEmployee(
                household_id=household.id,
                business_id=existing.id,
                name="Stylist",
                role="stylist",
                status="active",
            )
        )
    db.flush()
