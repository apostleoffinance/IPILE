from uuid import UUID

from sqlalchemy.orm import Session

from app.models.category import Category

DEFAULT_CATEGORIES: list[tuple[str, str, int]] = [
    ("Household income", "income", 10),
    ("Food", "expense", 20),
    ("Transport", "expense", 30),
    ("Utilities", "expense", 40),
    ("Personal", "expense", 50),
    ("Healthcare", "expense", 60),
    ("Clothing", "expense", 70),
    ("Other", "expense", 80),
    ("Tithe", "giving", 90),
    ("Church", "giving", 100),
    ("Family assistance", "giving", 110),
    ("Charity", "giving", 120),
    ("Gifts", "giving", 130),
    ("Spontaneous giving", "giving", 140),
    ("Transfer", "transfer", 150),
    ("Investment", "investment", 160),
    ("Obligation", "system", 170),
    ("University provision", "system", 180),
]


def seed_default_categories(db: Session, household_id: UUID) -> list[Category]:
    created: list[Category] = []
    for name, kind, sort_order in DEFAULT_CATEGORIES:
        category = Category(
            household_id=household_id,
            name=name,
            kind=kind,
            is_system=True,
            sort_order=sort_order,
        )
        db.add(category)
        created.append(category)
    db.flush()
    return created
