from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.api.v1.transactions import create_transaction
from app.models.account import Account
from app.models.giving import GivingPolicy, GivingRecord
from app.schemas.giving import (
    GivingCreate,
    GivingPolicyCreate,
    GivingPolicyOut,
    GivingRecordOut,
    GivingSummaryOut,
)
from app.schemas.transaction import TransactionCreate
from app.services.giving_engine import (
    limit_warning_for,
    money,
    posted_records,
    serialize_policy,
    serialize_record,
)

router = APIRouter(prefix="/giving", tags=["giving"])


def _policies(db: Session, household_id: UUID):
    return db.query(GivingPolicy).filter(
        GivingPolicy.household_id == household_id,
        GivingPolicy.deleted_at.is_(None),
    )


def _records(db: Session, household_id: UUID):
    return db.query(GivingRecord).filter(
        GivingRecord.household_id == household_id,
        GivingRecord.deleted_at.is_(None),
    )


def _account(db: Session, household_id: UUID, account_id: UUID) -> Account:
    account = (
        db.query(Account)
        .filter(
            Account.id == account_id,
            Account.household_id == household_id,
            Account.deleted_at.is_(None),
        )
        .first()
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account


def _post_giving_transaction(
    *,
    ctx: HouseholdContext,
    db: Session,
    account: Account,
    amount,
    when: date,
    kind: str,
    beneficiary: str | None,
    category_id: UUID | None,
    notes: str | None,
    record_id: UUID,
):
    tx = create_transaction(
        TransactionCreate(
            account_id=account.id,
            amount=amount,
            type="giving",
            date=when,
            category_id=category_id,
            description=notes or f"Giving: {kind}",
            merchant=beneficiary,
            status="cleared",
        ),
        ctx,
        db,
    )
    if hasattr(tx, "giving_record_id"):
        tx.giving_record_id = record_id
        db.add(tx)
        db.commit()
        db.refresh(tx)
    return tx


@router.get("/policies", response_model=list[GivingPolicyOut])
def list_policies(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = _policies(db, ctx.household.id).order_by(GivingPolicy.name)
    return [serialize_policy(db, row) for row in rows]


@router.post("/policies", response_model=GivingPolicyOut, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: GivingPolicyCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    policy = GivingPolicy(
        household_id=ctx.household.id,
        name=payload.name,
        kind=payload.kind,
        monthly_limit=payload.monthly_limit,
        annual_limit=payload.annual_limit,
        requires_dual_approval=payload.requires_dual_approval,
        allocation_rule_id=payload.allocation_rule_id,
        status="active",
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return serialize_policy(db, policy)


@router.get("/summary", response_model=GivingSummaryOut)
def giving_summary(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    today = date.today()
    policies = [serialize_policy(db, row, today) for row in _policies(db, ctx.household.id)]
    records = [
        serialize_record(row)
        for row in _records(db, ctx.household.id).order_by(GivingRecord.date.desc()).limit(50)
    ]
    pending = [
        serialize_record(row)
        for row in _records(db, ctx.household.id)
        .filter(GivingRecord.status == "pending_approval")
        .order_by(GivingRecord.date.desc())
    ]
    month_total = posted_records(db, ctx.household.id).filter(
        extract("year", GivingRecord.date) == today.year,
        extract("month", GivingRecord.date) == today.month,
    ).with_entities(func.coalesce(func.sum(GivingRecord.amount), 0)).scalar()
    year_total = posted_records(db, ctx.household.id).filter(
        extract("year", GivingRecord.date) == today.year,
    ).with_entities(func.coalesce(func.sum(GivingRecord.amount), 0)).scalar()
    return GivingSummaryOut(
        period_month=today.strftime("%Y-%m"),
        policies=policies,
        records=records,
        pending_approvals=pending,
        total_posted_month=money(month_total),
        total_posted_year=money(year_total),
    )


@router.get("", response_model=list[GivingRecordOut])
def list_giving(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    rows = _records(db, ctx.household.id).order_by(GivingRecord.date.desc())
    return [serialize_record(row) for row in rows]


@router.post("", response_model=GivingRecordOut, status_code=status.HTTP_201_CREATED)
def create_giving(
    payload: GivingCreate,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner", "member")),
    db: Session = Depends(get_db),
):
    when = payload.date or date.today()
    account = _account(db, ctx.household.id, payload.account_id)
    policy = None
    if payload.policy_id:
        policy = (
            _policies(db, ctx.household.id)
            .filter(GivingPolicy.id == payload.policy_id)
            .first()
        )
        if policy is None:
            raise HTTPException(status_code=404, detail="Giving policy not found.")
    kind = policy.kind if policy else payload.kind
    warning = limit_warning_for(db, ctx.household.id, policy, kind, payload.amount, when)
    needs_approval = bool(policy and policy.requires_dual_approval)
    record = GivingRecord(
        household_id=ctx.household.id,
        policy_id=policy.id if policy else None,
        kind=kind,
        beneficiary=payload.beneficiary,
        amount=payload.amount,
        currency=account.currency,
        date=when,
        account_id=account.id,
        category_id=payload.category_id,
        allocation_rule_id=policy.allocation_rule_id if policy else None,
        status="pending_approval" if needs_approval else "posted",
        created_by_member_id=ctx.member.id,
        limit_warning=warning,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if not needs_approval:
        tx = _post_giving_transaction(
            ctx=ctx,
            db=db,
            account=account,
            amount=payload.amount,
            when=when,
            kind=kind,
            beneficiary=payload.beneficiary,
            category_id=payload.category_id,
            notes=payload.notes,
            record_id=record.id,
        )
        record.transaction_id = tx.id
        db.add(record)
        db.commit()
        db.refresh(record)
    return serialize_record(record)


@router.post("/{record_id}/approve", response_model=GivingRecordOut)
def approve_giving(
    record_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    record = _records(db, ctx.household.id).filter(GivingRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Giving record not found.")
    if record.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Record is not pending approval.")
    if record.created_by_member_id == ctx.member.id and ctx.role != "owner":
        raise HTTPException(status_code=400, detail="A second household member must approve.")

    account = _account(db, ctx.household.id, record.account_id)
    tx = _post_giving_transaction(
        ctx=ctx,
        db=db,
        account=account,
        amount=record.amount,
        when=record.date,
        kind=record.kind,
        beneficiary=record.beneficiary,
        category_id=record.category_id,
        notes=record.notes,
        record_id=record.id,
    )
    record.transaction_id = tx.id
    record.status = "approved"
    record.approved_by_member_id = ctx.member.id
    db.add(record)
    db.commit()
    db.refresh(record)
    return serialize_record(record)


@router.post("/{record_id}/reject", response_model=GivingRecordOut)
def reject_giving(
    record_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    record = _records(db, ctx.household.id).filter(GivingRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Giving record not found.")
    if record.status != "pending_approval":
        raise HTTPException(status_code=400, detail="Record is not pending approval.")
    record.status = "rejected"
    record.approved_by_member_id = ctx.member.id
    db.add(record)
    db.commit()
    db.refresh(record)
    return serialize_record(record)
