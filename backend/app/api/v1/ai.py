from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context
from app.services.ai_analyst import explain_household

router = APIRouter(tags=["ai"])


@router.post("/ai/explain")
def post_ai_explain(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    try:
        payload = explain_household(db, ctx.household)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return payload
