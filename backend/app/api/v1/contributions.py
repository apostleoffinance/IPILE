from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import (
    HouseholdContext,
    get_db,
    get_household_context,
    require_roles,
)
from app.models.contribution import ContributionAgreement, ContributionRecord
from app.models.member import HouseholdMember
from app.models.transaction import Transaction
from app.schemas.contribution import (
    CADENCES,
    ContributionAgreementCreate,
    ContributionAgreementOut,
    ContributionAgreementUpdate,
    ContributionRecordCreate,
    ContributionRecordOut,
)
from app.services.audit import write_audit
from app.services.contribution_forecast import contribution_forecast as build_contribution_forecast
from app.services.contribution_schedule import build_contribution_schedule
from app.services.finance_access import has_member_permission

router = APIRouter(prefix="/contributions", tags=["household-governance"])


def _agreement(
    db: Session,
    household_id: UUID,
    agreement_id: UUID,
) -> ContributionAgreement:
    row = (
        db.query(ContributionAgreement)
        .filter(
            ContributionAgreement.id == agreement_id,
            ContributionAgreement.household_id == household_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Contribution agreement not found.",
        )
    return row


def _visible_agreement(
    db: Session,
    ctx: HouseholdContext,
    agreement_id: UUID,
) -> ContributionAgreement:
    query = db.query(ContributionAgreement).filter(
        ContributionAgreement.id == agreement_id,
        ContributionAgreement.household_id == ctx.household.id,
    )
    if ctx.role not in {"owner", "partner"}:
        if not has_member_permission(ctx, "view_all_contributions"):
            query = query.filter(ContributionAgreement.member_id == ctx.member.id)
    agreement = query.first()
    if agreement is None:
        raise HTTPException(status_code=404, detail="Contribution agreement not found.")
    return agreement



@router.get("", response_model=list[ContributionAgreementOut])
def list_agreements(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    query = db.query(ContributionAgreement).filter(
        ContributionAgreement.household_id == ctx.household.id
    )
    if ctx.role not in {"owner", "partner"}:
        if not has_member_permission(ctx, "view_all_contributions"):
            query = query.filter(ContributionAgreement.member_id == ctx.member.id)
    return query.order_by(ContributionAgreement.start_date.desc()).all()


@router.get("/schedule")
def contribution_schedule(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    today = date.today()
    start = from_date or today - timedelta(days=90)
    end = to_date or today + timedelta(days=90)
    if end < start:
        raise HTTPException(status_code=400, detail="to_date must be on or after from_date.")
    query = db.query(ContributionAgreement).filter(
        ContributionAgreement.household_id == ctx.household.id
    )
    if ctx.role not in {"owner", "partner"}:
        if not has_member_permission(ctx, "view_all_contributions"):
            query = query.filter(ContributionAgreement.member_id == ctx.member.id)
    agreements = query.order_by(ContributionAgreement.start_date).all()
    if not agreements:
        return []
    agreement_ids = [agreement.id for agreement in agreements]
    records = (
        db.query(ContributionRecord)
        .filter(
            ContributionRecord.household_id == ctx.household.id,
            ContributionRecord.agreement_id.in_(agreement_ids),
            ContributionRecord.contributed_on <= end,
        )
        .order_by(ContributionRecord.contributed_on, ContributionRecord.created_at)
        .all()
    )
    records_by_agreement = defaultdict(list)
    for record in records:
        records_by_agreement[record.agreement_id].append(record)
    return build_contribution_schedule(
        agreements,
        records_by_agreement,
        from_date=start,
        to_date=end,
        today=today,
    )



@router.get("/forecast")
def forecast_contributions(
    horizon_days: int = Query(default=90, ge=1, le=730),
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    """Forecast contributions without treating unverified receipts as available cash."""
    member_id = None
    if ctx.role not in {"owner", "partner"}:
        if not has_member_permission(ctx, "view_all_contributions"):
            if ctx.member is None:
                raise HTTPException(
                    status_code=403,
                    detail="Contribution visibility is not available.",
                )
            member_id = ctx.member.id
    return build_contribution_forecast(
        db,
        ctx.household.id,
        ctx.household.base_currency,
        horizon_days=horizon_days,
        member_id=member_id,
    )


@router.post(
    "",
    response_model=ContributionAgreementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_agreement(
    payload: ContributionAgreementCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    member = (
        db.query(HouseholdMember)
        .filter(
            HouseholdMember.id == payload.member_id,
            HouseholdMember.household_id == ctx.household.id,
            HouseholdMember.deleted_at.is_(None),
        )
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Household member not found.")
    agreement = ContributionAgreement(
        household_id=ctx.household.id,
        member_id=member.id,
        name=payload.name.strip(),
        amount=payload.amount,
        currency=payload.currency.upper(),
        cadence=payload.cadence,
        due_day=payload.due_day,
        start_date=payload.start_date,
        end_date=payload.end_date,
        notes=payload.notes,
    )
    member.is_financial_contributor = True
    db.add(agreement)
    db.flush()
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="create",
        entity_type="contribution_agreement",
        entity_id=agreement.id,
        detail={
            "member_id": str(member.id),
            "amount": str(agreement.amount),
            "cadence": agreement.cadence,
        },
    )
    db.commit()
    db.refresh(agreement)
    return agreement


@router.patch("/{agreement_id}", response_model=ContributionAgreementOut)
def update_agreement(
    agreement_id: UUID,
    payload: ContributionAgreementUpdate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    agreement = _agreement(db, ctx.household.id, agreement_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("cadence") is not None and data["cadence"] not in CADENCES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported contribution cadence.",
        )
    if data.get("status") is not None and data["status"] not in {
        "active",
        "paused",
        "completed",
        "cancelled",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid contribution agreement status.",
        )
    end = data.get("end_date", agreement.end_date)
    if end and end < agreement.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date.",
        )
    cadence = data.get("cadence", agreement.cadence)
    due_day = data.get("due_day", agreement.due_day)
    if cadence == "monthly" and due_day is None:
        raise HTTPException(
            status_code=400,
            detail="Monthly agreements require a due day.",
        )
    for key, value in data.items():
        setattr(agreement, key, value)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="update",
        entity_type="contribution_agreement",
        entity_id=agreement.id,
        detail={"fields": sorted(data)},
    )
    db.commit()
    db.refresh(agreement)
    return agreement


@router.post(
    "/{agreement_id}/records",
    response_model=ContributionRecordOut,
    status_code=status.HTTP_201_CREATED,
)
def record_contribution(
    agreement_id: UUID,
    payload: ContributionRecordCreate,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    if ctx.role not in {"owner", "partner", "member"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    agreement = _visible_agreement(db, ctx, agreement_id)
    if ctx.role == "member" and agreement.member_id != ctx.member.id:
        raise HTTPException(
            status_code=403,
            detail="Members may record contributions only for their own agreements.",
        )
    if agreement.status != "active":
        raise HTTPException(
            status_code=400,
            detail="Only active agreements can receive contributions.",
        )
    if payload.contributed_on < agreement.start_date or (
        agreement.end_date and payload.contributed_on > agreement.end_date
    ):
        raise HTTPException(
            status_code=400,
            detail="Contribution date is outside the agreement period.",
        )
    if payload.transaction_id:
        transaction = (
            db.query(Transaction)
            .filter(
                Transaction.id == payload.transaction_id,
                Transaction.household_id == ctx.household.id,
                Transaction.deleted_at.is_(None),
            )
            .first()
        )
        if transaction is None:
            raise HTTPException(status_code=404, detail="Linked transaction not found.")
        existing_record = (
            db.query(ContributionRecord)
            .filter(
                ContributionRecord.household_id == ctx.household.id,
                ContributionRecord.transaction_id == transaction.id,
            )
            .first()
        )
        if existing_record is not None:
            raise HTTPException(
                status_code=409,
                detail="Transaction is already linked to a contribution record.",
            )
        if transaction.type != "income":
            raise HTTPException(
                status_code=400,
                detail="A contribution must link to an income transaction.",
            )
        if transaction.status not in {"cleared", "reconciled"}:
            raise HTTPException(
                status_code=400,
                detail="Only cleared or reconciled income can verify a received contribution.",
            )
        if ctx.role == "member" and transaction.member_id != ctx.member.id:
            raise HTTPException(
                status_code=403,
                detail="Members may link only their own income transactions.",
            )
        if (
            transaction.amount != payload.amount
            or transaction.currency != agreement.currency
            or transaction.date != payload.contributed_on
        ):
            raise HTTPException(
                status_code=400,
                detail="Linked transaction amount, currency, or date does not match.",
            )
        if transaction.member_id and transaction.member_id != agreement.member_id:
            raise HTTPException(
                status_code=400,
                detail="Linked transaction belongs to another member.",
            )
    record = ContributionRecord(
        household_id=ctx.household.id,
        agreement_id=agreement.id,
        member_id=agreement.member_id,
        amount=payload.amount,
        currency=agreement.currency,
        contributed_on=payload.contributed_on,
        transaction_id=payload.transaction_id,
        note=payload.note,
        recorded_by_user_id=ctx.user.id,
    )
    db.add(record)
    db.flush()
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="create",
        entity_type="contribution_record",
        entity_id=record.id,
        detail={
            "agreement_id": str(agreement.id),
            "amount": str(record.amount),
        },
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This income transaction is already linked to a contribution.",
        ) from exc
    db.refresh(record)
    return record


@router.get(
    "/{agreement_id}/records",
    response_model=list[ContributionRecordOut],
)
def list_records(
    agreement_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    agreement = _visible_agreement(db, ctx, agreement_id)
    return (
        db.query(ContributionRecord)
        .filter(
            ContributionRecord.household_id == ctx.household.id,
            ContributionRecord.agreement_id == agreement.id,
        )
        .order_by(ContributionRecord.contributed_on.desc())
        .all()
    )
