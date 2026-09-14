from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.account import Account
from app.models.household import Household
from app.models.income import IncomeSource
from app.models.member import HouseholdMember
from app.models.user import User
from app.services.allocation_seed import seed_allocation
from app.services.analytics_seed import seed_analytics
from app.services.business_seed import seed_business
from app.services.goal_seed import seed_goals
from app.services.households import create_household_for_owner
from app.services.obligation_seed import seed_obligations
from app.services.planning_seed import seed_planning
from app.services.wealth_seed import seed_wealth

SEED_SLUG = "seed-household"
SEED_OWNER_EMAIL = "owner@seed.example.com"
SEED_PARTNER_EMAIL = "partner@seed.example.com"
SEED_OWNER_PASSWORD = "family-os-seed-owner"


def seed_household(db: Session) -> Household | None:
    """Idempotent pilot seed. Soft-deleted seed is never resurrected."""
    existing = db.query(Household).filter(Household.slug == SEED_SLUG).first()
    if existing is not None:
        if existing.deleted_at is not None:
            return None
        seed_planning(db, existing)
        seed_obligations(db, existing)
        seed_allocation(db, existing)
        seed_wealth(db, existing)
        seed_goals(db, existing)
        seed_business(db, existing)
        seed_analytics(db, existing)
        return existing

    owner = db.query(User).filter(User.email == SEED_OWNER_EMAIL).first()
    if owner is None:
        owner = User(
            email=SEED_OWNER_EMAIL,
            password_hash=hash_password(SEED_OWNER_PASSWORD),
            display_name="Partner A",
            status="active",
        )
        db.add(owner)
        db.flush()

    household, owner_member = create_household_for_owner(
        db,
        owner,
        "Seed Household",
        minimum_buffer_amount=Decimal("90000.00"),
        slug=SEED_SLUG,
    )
    owner_member.display_name = "Partner A"

    partner = db.query(User).filter(User.email == SEED_PARTNER_EMAIL).first()
    if partner is None:
        partner = User(
            email=SEED_PARTNER_EMAIL,
            password_hash=hash_password(SEED_OWNER_PASSWORD),
            display_name="Partner B",
            status="active",
        )
        db.add(partner)
        db.flush()

    db.add(
        HouseholdMember(
            household_id=household.id,
            user_id=partner.id,
            display_name="Partner B",
            role="partner",
            relationship="spouse",
            member_type="adult",
            is_financial_contributor=True,
        )
    )
    db.add(
        HouseholdMember(
            household_id=household.id,
            user_id=None,
            display_name="Baby",
            role="member",
            relationship="child",
            member_type="dependent",
            is_financial_contributor=False,
        )
    )

    current = Account(
        household_id=household.id,
        name="Household current",
        type="bank",
        currency="NGN",
        institution="Seed Bank",
        owner_member_id=owner_member.id,
        current_balance=Decimal("0.00"),
        available_balance=Decimal("0.00"),
        is_protected=False,
        include_in_safe_to_spend=True,
        include_in_net_worth=True,
        status="active",
    )
    emergency = Account(
        household_id=household.id,
        name="Emergency savings",
        type="savings",
        currency="NGN",
        current_balance=Decimal("0.00"),
        available_balance=Decimal("0.00"),
        is_protected=True,
        is_emergency=True,
        include_in_safe_to_spend=False,
        include_in_net_worth=True,
        status="active",
    )
    investment = Account(
        household_id=household.id,
        name="Investments",
        type="investment",
        currency="NGN",
        current_balance=Decimal("0.00"),
        available_balance=Decimal("0.00"),
        is_protected=True,
        include_in_safe_to_spend=False,
        include_in_net_worth=True,
        status="active",
    )
    db.add_all([current, emergency, investment])
    db.add(
        IncomeSource(
            household_id=household.id,
            member_id=owner_member.id,
            name="Household income",
            type="salary",
            expected_amount=Decimal("2000000.00"),
            frequency="monthly",
            is_active=True,
        )
    )
    db.flush()
    seed_planning(db, household)
    seed_obligations(db, household)
    seed_allocation(db, household)
    seed_wealth(db, household)
    seed_goals(db, household)
    seed_business(db, household)
    seed_analytics(db, household)
    return household
