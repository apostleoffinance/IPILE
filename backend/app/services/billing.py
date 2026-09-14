from uuid import UUID

from sqlalchemy.orm import Session

from app.models.household import Household
from app.services.audit import write_audit

PLANS = {
    "pilot": {
        "name": "Pilot",
        "price_monthly": "0.00",
        "currency": "NGN",
        "description": "Private pilot household — full engines, no charge.",
    },
    "family": {
        "name": "Family",
        "price_monthly": "15000.00",
        "currency": "NGN",
        "description": "Public family plan — multi-member, export, support.",
    },
}


def list_plans() -> list[dict]:
    return [{"id": key, **value} for key, value in PLANS.items()]


def billing_snapshot(household: Household) -> dict:
    plan = PLANS.get(household.plan, PLANS["pilot"])
    return {
        "household_id": str(household.id),
        "plan": household.plan,
        "plan_name": plan["name"],
        "price_monthly": plan["price_monthly"],
        "currency": plan["currency"],
        "billing_status": household.billing_status,
        "plans": list_plans(),
    }


def change_plan(
    db: Session,
    household: Household,
    *,
    user_id: UUID,
    plan: str,
) -> Household:
    if plan not in PLANS:
        raise ValueError("Unknown plan.")
    household.plan = plan
    household.billing_status = "active"
    db.add(household)
    write_audit(
        db,
        household_id=household.id,
        user_id=user_id,
        action="update",
        entity_type="billing",
        entity_id=household.id,
        detail={"plan": plan},
    )
    db.flush()
    return household
