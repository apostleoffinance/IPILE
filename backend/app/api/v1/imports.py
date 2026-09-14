from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.schemas.imports import ImportBody, ImportJobOut
from app.services.imports import run_import

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/csv", response_model=ImportJobOut, status_code=status.HTTP_201_CREATED)
def import_csv(
    payload: ImportBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    try:
        job = run_import(
            db,
            ctx.household,
            account_id=payload.account_id,
            source="csv",
            content=payload.content,
            filename=payload.filename or "upload.csv",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(job)
    return job


@router.post("/statement", response_model=ImportJobOut, status_code=status.HTTP_201_CREATED)
def import_statement(
    payload: ImportBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    try:
        job = run_import(
            db,
            ctx.household,
            account_id=payload.account_id,
            source="statement",
            content=payload.content,
            filename=payload.filename or "statement.txt",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(job)
    return job
