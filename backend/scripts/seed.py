from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.seed import seed_household


def main() -> None:
    settings = get_settings()
    if not settings.seed_on_start:
        print("SEED_ON_START disabled — skipping pilot seed.")
        return
    db = SessionLocal()
    try:
        household = seed_household(db)
        db.commit()
        if household is None:
            print("Seed household was deleted; not recreating (no code fork required).")
        else:
            print(f"Seed household ready: {household.name} ({household.slug})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
