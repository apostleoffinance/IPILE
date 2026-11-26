import re
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.household import Household
from app.models.member import HouseholdMember
from app.models.user import User
from app.services.categories import seed_default_categories


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "household"


def unique_slug(db: Session, base: str) -> str:
    candidate = base[:60]
    while db.query(Household).filter(Household.slug == candidate).first():
        candidate = f"{base[:50]}-{uuid.uuid4().hex[:6]}"
    return candidate


COUNTRY_TIMEZONES = {
    "NG": "Africa/Lagos", "GB": "Europe/London", "US": "America/New_York",
    "CA": "America/Toronto", "CH": "Europe/Zurich", "AU": "Australia/Sydney",
    "AE": "Asia/Dubai", "GH": "Africa/Accra", "KE": "Africa/Nairobi",
    "ZA": "Africa/Johannesburg", "DE": "Europe/Berlin", "FR": "Europe/Paris",
    "IN": "Asia/Kolkata", "SG": "Asia/Singapore", "SA": "Asia/Riyadh",
    "BR": "America/Sao_Paulo", "MX": "America/Mexico_City", "JP": "Asia/Tokyo",
    "HK": "Asia/Hong_Kong", "NZ": "Pacific/Auckland",
}


def create_household_for_owner(
    db: Session,
    user: User,
    name: str,
    *,
    minimum_buffer_amount: Decimal | None = None,
    slug: str | None = None,
    base_currency: str = "NGN",
    country: str = "NG",
) -> tuple[Household, HouseholdMember]:
    if minimum_buffer_amount is None:
        minimum_buffer_amount = (
            Decimal("90000.00")
            if base_currency.upper() == "NGN"
            else Decimal("0.00")
        )
    household = Household(
        name=name,
        slug=unique_slug(db, slug or slugify(name)),
        base_currency=base_currency.upper(),
        reporting_currency=base_currency.upper(),
        timezone=COUNTRY_TIMEZONES.get(country.upper(), "UTC"),
        country=country.upper(),
        fiscal_month_start_day=1,
        minimum_buffer_amount=minimum_buffer_amount,
        settings={},
    )
    db.add(household)
    db.flush()
    member = HouseholdMember(
        household_id=household.id,
        user_id=user.id,
        display_name=user.display_name,
        role="owner",
        relationship="self",
        member_type="adult",
        is_financial_contributor=True,
    )
    db.add(member)
    seed_default_categories(db, household.id)
    db.flush()
    return household, member
