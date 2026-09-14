from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.account import Account
from app.schemas.simulation import SimulationIn, SimulationRunOut
from app.services.simulations import get_run, run_simulation, serialize_run

router = APIRouter(tags=["simulations"])


@router.post("/simulations", response_model=SimulationRunOut, status_code=status.HTTP_201_CREATED)
def post_simulation(
    payload: SimulationIn,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    before = {
        row.id: str(row.current_balance)
        for row in db.query(Account).filter(
            Account.household_id == ctx.household.id, Account.deleted_at.is_(None)
        )
    }
    run = run_simulation(db, ctx.household, payload)
    db.commit()
    after = {
        row.id: str(row.current_balance)
        for row in db.query(Account).filter(
            Account.household_id == ctx.household.id, Account.deleted_at.is_(None)
        )
    }
    if before != after:
        raise HTTPException(status_code=500, detail="Simulation mutated live balances.")
    db.refresh(run)
    return serialize_run(db, run)


@router.get("/simulations/{run_id}", response_model=SimulationRunOut)
def read_simulation(
    run_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    run = get_run(db, ctx.household.id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found.")
    return serialize_run(db, run)
