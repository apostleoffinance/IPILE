from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.api.v1.transactions import create_transaction
from app.models.fund import SinkingFund
from app.models.obligation import Obligation, ObligationOccurrence
from app.schemas.obligation import ObligationCreate, ObligationOut, ObligationPay, ObligationUpdate
from app.schemas.transaction import TransactionCreate
from app.services.funds import apply_payment_from_fund, attach_fund, ensure_fund_account
from app.services.obligation_engine import FREQUENCIES
from app.services.obligations import (
    OBLIGATION_STATUSES,
    PRIORITIES,
    generate_occurrences,
    mark_paid,
    obligation_category,
    serialize_obligation,
)

router = APIRouter(prefix="/obligations", tags=["obligations"])


def _active(db: Session, household_id: UUID):
    return db.query(Obligation).filter(
        Obligation.household_id == household_id,
        Obligation.deleted_at.is_(None),
    )


def _get(db: Session, household_id: UUID, obligation_id: UUID) -> Obligation:
    obligation = _active(db, household_id).filter(Obligation.id == obligation_id).first()
    if obligation is None:
        raise HTTPException(status_code=404, detail="Obligation not found.")
    return obligation


@router.get("", response_model=list[ObligationOut])
def list_obligations(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = _active(db, ctx.household.id).order_by(Obligation.next_due_date).all()
    return [serialize_obligation(db, row) for row in rows]


@router.post("", response_model=ObligationOut, status_code=status.HTTP_201_CREATED)
def create_obligation(
    payload: ObligationCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    if payload.frequency not in FREQUENCIES:
        raise HTTPException(status_code=400, detail="Invalid frequency.")
    if payload.priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")
    if payload.status not in OBLIGATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid obligation status.")
    category_id = payload.category_id
    if category_id is None:
        category_id = obligation_category(db, ctx.household.id).id
    obligation = Obligation(
        household_id=ctx.household.id,
        name=payload.name,
        amount=payload.amount,
        currency=payload.currency,
        frequency=payload.frequency,
        next_due_date=payload.next_due_date,
        priority=payload.priority,
        sinking_fund=payload.sinking_fund,
        auto_allocate=payload.auto_allocate,
        category_id=category_id,
        beneficiary_name=payload.beneficiary_name,
        beneficiary_member_id=payload.beneficiary_member_id,
        status=payload.status,
    )
    db.add(obligation)
    db.flush()
    attach_fund(db, obligation)
    generate_occurrences(db, obligation)
    db.commit()
    db.refresh(obligation)
    return serialize_obligation(db, obligation)


@router.get("/{obligation_id}", response_model=ObligationOut)
def get_obligation(
    obligation_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return serialize_obligation(db, _get(db, ctx.household.id, obligation_id))


@router.patch("/{obligation_id}", response_model=ObligationOut)
def update_obligation(
    obligation_id: UUID,
    payload: ObligationUpdate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    obligation = _get(db, ctx.household.id, obligation_id)
    data = payload.model_dump(exclude_unset=True)
    if "frequency" in data and data["frequency"] not in FREQUENCIES:
        raise HTTPException(status_code=400, detail="Invalid frequency.")
    if "priority" in data and data["priority"] not in PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid priority.")
    if "status" in data and data["status"] not in OBLIGATION_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid obligation status.")
    for key, value in data.items():
        setattr(obligation, key, value)
    db.add(obligation)
    attach_fund(db, obligation)
    generate_occurrences(db, obligation)
    db.commit()
    db.refresh(obligation)
    return serialize_obligation(db, obligation)


@router.post("/{obligation_id}/occurrences/{occurrence_id}/pay", response_model=ObligationOut)
def pay_occurrence(
    obligation_id: UUID,
    occurrence_id: UUID,
    payload: ObligationPay,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    obligation = _get(db, ctx.household.id, obligation_id)
    occurrence = (
        db.query(ObligationOccurrence)
        .filter(
            ObligationOccurrence.id == occurrence_id,
            ObligationOccurrence.obligation_id == obligation.id,
            ObligationOccurrence.household_id == ctx.household.id,
        )
        .first()
    )
    if occurrence is None:
        raise HTTPException(status_code=404, detail="Occurrence not found.")
    if occurrence.status == "paid":
        raise HTTPException(status_code=400, detail="Occurrence is already paid.")
    pay_date = payload.date or occurrence.due_date
    source_id = payload.account_id
    counterparty_id = None
    tx_type = "expense"
    fund = db.get(SinkingFund, obligation.fund_id) if obligation.fund_id else None
    if fund and fund.account_id:
        ensure_fund_account(db, fund)
        source_id = fund.account_id
        apply_payment_from_fund(fund, occurrence.amount)
        db.add(fund)
    transaction = create_transaction(
        TransactionCreate(
            account_id=source_id,
            amount=occurrence.amount,
            type=tx_type,
            date=pay_date,
            counterparty_account_id=counterparty_id,
            category_id=obligation.category_id,
            description=obligation.name,
            obligation_id=obligation.id,
            fund_id=fund.id if fund else None,
            status="cleared",
        ),
        ctx,
        db,
    )
    mark_paid(occurrence, transaction.id)
    db.add(occurrence)
    generate_occurrences(db, obligation)
    db.commit()
    db.refresh(obligation)
    return serialize_obligation(db, obligation)


@router.delete("/{obligation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_obligation(
    obligation_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    obligation = _get(db, ctx.household.id, obligation_id)
    obligation.deleted_at = datetime.now(UTC)
    db.add(obligation)
    db.commit()
