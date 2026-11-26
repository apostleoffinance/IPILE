import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["health"])


def _expected_migration_heads() -> set[str]:
    backend_dir = Path(__file__).resolve().parents[3]
    alembic_config = Config(str(backend_dir / "alembic.ini"))
    return set(ScriptDirectory.from_config(alembic_config).get_heads())


@router.get("/health/live")
def liveness() -> dict[str, str]:
    """Process liveness; intentionally independent of external dependencies."""
    return {"status": "ok", "service": "ipile"}


@router.get("/health")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness check for database connectivity and schema migration state."""
    try:
        db.execute(text("SELECT 1"))
        applied_heads = set(db.execute(text("SELECT version_num FROM alembic_version")).scalars())
        expected_heads = _expected_migration_heads()
    except (SQLAlchemyError, OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database or migration state is unavailable.",
        ) from exc

    if not expected_heads or applied_heads != expected_heads:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database migrations are not current.",
        )

    return {
        "status": "ok",
        "service": "ipile",
        "database": "connected",
        "migrations": "current",
        "release": os.getenv("RENDER_GIT_COMMIT", "unknown"),
    }
