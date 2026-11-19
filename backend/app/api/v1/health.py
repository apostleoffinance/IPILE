from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    """Process liveness; intentionally independent of external dependencies."""
    return {"status": "ok", "service": "ipile"}


@router.get("/health")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness check used by deployment platforms and uptime monitors."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return {"status": "ok", "service": "ipile", "database": "connected"}
