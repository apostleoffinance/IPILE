from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, get_household_context, require_roles
from app.models.account import Account
from app.models.business import Business
from app.models.category import Category
from app.models.fund import SinkingFund
from app.models.goal import Goal
from app.models.income import IncomeSource
from app.models.member import HouseholdMember
from app.models.obligation import Obligation
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionCreate, TransactionOut, TransactionUpdate
from app.services.allocations import ensure_period_allocation
from app.services.audit import write_audit
from app.services.balances import TRANSFER_TYPE, apply_transaction_effect
from app.services.budgets import evaluate_budget_alerts
from app.services.currencies import CurrencyError, get_rate, validate_currency
from app.services.finance_access import account_visibility, transaction_visibility

router = APIRouter(prefix="/transactions", tags=["transactions"])
TX_TYPES = {
    "income",
    "expense",
    "transfer",
    "refund",
    "investment",
    "debt_payment",
    "capital_contribution",
    "withdrawal",
    "giving",
}
TX_STATUSES = {"pending", "cleared", "reconciled", "voided"}


def _scoped_accounts(db: Session, household_id: UUID):
    return db.query(Account).filter(
        Account.household_id == household_id,
        Account.deleted_at.is_(None),
    )


def _get_account(db: Session, household_id: UUID, account_id: UUID) -> Account:
    account = _scoped_accounts(db, household_id).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account


def _require_household_reference(
    db: Session, model, household_id: UUID, record_id: UUID | None, label: str
) -> None:
    if record_id is None:
        return
    query = db.query(model.id).filter(model.id == record_id, model.household_id == household_id)
    deleted_at = getattr(model, "deleted_at", None)
    if deleted_at is not None:
        query = query.filter(deleted_at.is_(None))
    if query.first() is None:
        raise HTTPException(status_code=404, detail=f"{label} not found in this household.")

def _visible_account(db: Session, ctx: HouseholdContext, account_id: UUID) -> Account:
    account = account_visibility(
        _scoped_accounts(db, ctx.household.id), Account, ctx
    ).filter(Account.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    return account


def _visible_account_ids(db: Session, ctx: HouseholdContext):
    return account_visibility(
        _scoped_accounts(db, ctx.household.id), Account, ctx
    ).with_entities(Account.id)


def _visible_transaction(db: Session, ctx: HouseholdContext, transaction_id: UUID) -> Transaction:
    query = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.household_id == ctx.household.id,
        Transaction.deleted_at.is_(None),
    )
    query = transaction_visibility(query, Transaction, ctx)
    transaction = query.filter(Transaction.account_id.in_(_visible_account_ids(db, ctx))).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    return transaction


def _authorize_write(ctx: HouseholdContext, member_id: UUID | None) -> UUID | None:
    if ctx.role in {"viewer", "advisor"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    if ctx.role == "member":
        if member_id and member_id != ctx.member.id:
            raise HTTPException(
                status_code=403,
                detail="Members may only record their own transactions.",
            )
        return ctx.member.id
    return member_id


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
    type: str | None = Query(default=None),
    account_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, le=200),
    view: str | None = Query(default=None, pattern="^(household|personal)$"),
):
    query = db.query(Transaction).filter(
        Transaction.household_id == ctx.household.id,
        Transaction.deleted_at.is_(None),
    )
    if type:
        query = query.filter(Transaction.type == type)
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    query = transaction_visibility(query, Transaction, ctx)
    query = query.filter(Transaction.account_id.in_(_visible_account_ids(db, ctx)))
    if view == "household":
        query = query.filter(Transaction.access_scope == "shared")
    elif view == "personal":
        query = query.filter(
            Transaction.access_scope == "personal",
            Transaction.member_id == ctx.member.id,
        )
    return query.order_by(Transaction.date.desc(), Transaction.created_at.desc()).limit(limit).all()


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    member_id = _authorize_write(ctx, payload.member_id)
    if payload.access_scope not in {'shared', 'personal'}:
        raise HTTPException(status_code=400, detail='Invalid transaction access scope.')
    if payload.access_scope == 'personal' and member_id is None:
        raise HTTPException(status_code=400, detail='Personal transactions require a member owner.')
    if payload.access_scope == 'personal' and ctx.role == 'member' and member_id != ctx.member.id:
        raise HTTPException(
            status_code=403,
            detail="Members may only create their own personal transactions.",
        )
    if payload.type not in TX_TYPES:
        raise HTTPException(status_code=400, detail="Invalid transaction type.")
    if payload.status not in TX_STATUSES or payload.status == "voided":
        raise HTTPException(status_code=400, detail="Invalid transaction status.")
    paired = {TRANSFER_TYPE, "capital_contribution", "withdrawal"}
    if payload.type in paired and not payload.counterparty_account_id:
        raise HTTPException(status_code=400, detail="This type requires a counterparty account.")
    if payload.counterparty_account_id == payload.account_id:
        raise HTTPException(status_code=400, detail="Transfer accounts must be different.")

    account = _visible_account(db, ctx, payload.account_id)
    counterparty = None
    if payload.counterparty_account_id:
        counterparty = _visible_account(db, ctx, payload.counterparty_account_id)

    for model, record_id, label in (
        (HouseholdMember, member_id, "Member"),
        (Category, payload.category_id, "Category"),
        (IncomeSource, payload.income_source_id, "Income source"),
        (Obligation, payload.obligation_id, "Obligation"),
        (SinkingFund, payload.fund_id, "Fund"),
        (Goal, payload.goal_id, "Goal"),
        (Business, payload.business_id, "Business"),
    ):
        _require_household_reference(db, model, ctx.household.id, record_id, label)

    # A private transaction must never change a shared balance, and a shared
    # transaction must never mutate a personal balance. Cross-scope transfers
    # need a paired-entry model and are intentionally rejected for now.
    if payload.access_scope == "personal":
        if account.access_scope != "personal" or account.owner_member_id != member_id:
            raise HTTPException(
                status_code=400,
                detail="Personal transactions must use an account owned by that member.",
            )
        if counterparty and (
            counterparty.access_scope != "personal"
            or counterparty.owner_member_id != member_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Personal transfers must use accounts owned by the same member.",
            )
    elif account.access_scope != "shared" or (
        counterparty and counterparty.access_scope != "shared"
    ):
        raise HTTPException(
            status_code=400,
            detail="Shared transactions must use shared accounts.",
        )

    try:
        source_currency = validate_currency(account.currency or ctx.household.base_currency)
    except CurrencyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.currency and validate_currency(payload.currency) != source_currency:
        raise HTTPException(
            status_code=400,
            detail="Transaction currency must match its source account currency.",
        )

    counterparty_amount = None
    counterparty_base_amount = None
    counterparty_rate = None
    counterparty_rate_date = None
    counterparty_rate_source = None
    if counterparty:
        target_currency = validate_currency(counterparty.currency or ctx.household.base_currency)
        if source_currency == target_currency:
            counterparty_amount = payload.amount
            counterparty_rate = Decimal("1")
            counterparty_rate_date = payload.date
            counterparty_rate_source = "identity"
        else:
            try:
                counterparty_rate, counterparty_rate_date, counterparty_rate_source = get_rate(
                    db, ctx.household.id, source_currency, target_currency, payload.date
                )
            except CurrencyError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            counterparty_amount = (payload.amount * counterparty_rate).quantize(Decimal("0.01"))

    try:
        if source_currency == ctx.household.base_currency:
            base_amount = payload.amount
            base_rate = Decimal("1")
            base_rate_date = payload.date
            base_rate_source = "identity"
        else:
            base_rate, base_rate_date, base_rate_source = get_rate(
                db, ctx.household.id, source_currency, ctx.household.base_currency, payload.date
            )
            base_amount = (payload.amount * base_rate).quantize(Decimal("0.01"))
    except CurrencyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if counterparty_amount is not None:
        counterparty_base_amount = (
            (base_amount * counterparty_amount / payload.amount).quantize(Decimal("0.01"))
            if payload.amount else Decimal("0.00")
        )

    transaction = Transaction(
        household_id=ctx.household.id,
        account_id=account.id,
        counterparty_account_id=counterparty.id if counterparty else None,
        member_id=member_id,
        access_scope=payload.access_scope,
        amount=payload.amount,
        currency=source_currency,
        base_amount=base_amount,
        base_currency=ctx.household.base_currency,
        exchange_rate=base_rate,
        exchange_rate_date=base_rate_date,
        exchange_rate_source=base_rate_source,
        counterparty_amount=counterparty_amount,
        counterparty_currency=counterparty.currency if counterparty else None,
        counterparty_base_amount=counterparty_base_amount,
        counterparty_exchange_rate=counterparty_rate,
        counterparty_exchange_rate_date=counterparty_rate_date,
        counterparty_exchange_rate_source=counterparty_rate_source,
        type=payload.type,
        category_id=payload.category_id,
        date=payload.date,
        merchant=payload.merchant,
        description=payload.description,
        income_source_id=payload.income_source_id,
        obligation_id=payload.obligation_id,
        fund_id=payload.fund_id,
        goal_id=payload.goal_id,
        business_id=payload.business_id,
        status=payload.status,
        import_source="manual",
    )
    db.add(transaction)
    apply_transaction_effect(
        db,
        account=account,
        counterparty=counterparty,
        tx_type=transaction.type,
        amount=transaction.amount,
        status=transaction.status,
        counterparty_amount=transaction.counterparty_amount,
    )
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    if (
        transaction.access_scope == "shared"
        and transaction.type == "income"
        and transaction.status in {"cleared", "reconciled"}
    ):
        from app.services.automation import run_tick

        _, skipped = run_tick(db, ctx.household, tick_type="income_recognized")
        if skipped:
            from app.services.financial_intelligence import run_financial_intelligence
            from app.services.notifications import sync_notifications_from_alerts

            run_financial_intelligence(db, ctx.household)
            sync_notifications_from_alerts(db, ctx.household.id)
    elif (
        transaction.access_scope == "shared"
        and transaction.type == "expense"
        and transaction.status in {"cleared", "reconciled"}
    ):
        from app.services.financial_intelligence import run_financial_intelligence
        from app.services.notifications import sync_notifications_from_alerts

        run_financial_intelligence(db, ctx.household)
        sync_notifications_from_alerts(db, ctx.household.id)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="create",
        entity_type="transaction",
        entity_id=transaction.id,
        detail={"type": transaction.type, "amount": str(transaction.amount)},
    )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: UUID,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    return _visible_transaction(db, ctx, transaction_id)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: UUID,
    payload: TransactionUpdate,
    ctx: HouseholdContext = Depends(get_household_context),
    db: Session = Depends(get_db),
):
    transaction = _visible_transaction(db, ctx, transaction_id)
    _authorize_write(ctx, payload.member_id or transaction.member_id)
    if ctx.role == "member" and transaction.member_id != ctx.member.id:
        raise HTTPException(status_code=403, detail="Members may only edit their own transactions.")
    updates = payload.model_dump(exclude_unset=True)
    if "member_id" in updates:
        _require_household_reference(
            db, HouseholdMember, ctx.household.id, updates["member_id"], "Member"
        )
        if transaction.access_scope == "personal":
            account = _get_account(db, ctx.household.id, transaction.account_id)
            if updates["member_id"] != account.owner_member_id:
                raise HTTPException(
                    status_code=400,
                    detail="A personal transaction must remain assigned to its account owner.",
                )
    if "category_id" in updates:
        _require_household_reference(
            db, Category, ctx.household.id, updates["category_id"], "Category"
        )
    if "date" in updates and updates["date"] != transaction.date:
        new_date = updates["date"]
        source_currency = transaction.currency
        base_currency = ctx.household.base_currency
        try:
            if source_currency == base_currency:
                transaction.base_amount = transaction.amount
                transaction.exchange_rate = Decimal("1")
                transaction.exchange_rate_date = new_date
                transaction.exchange_rate_source = "identity"
            else:
                rate, rate_date, rate_source = get_rate(
                    db, ctx.household.id, source_currency, base_currency, new_date
                )
                transaction.base_amount = (
                    Decimal(str(transaction.amount)) * rate
                ).quantize(Decimal("0.01"))
                transaction.exchange_rate = rate
                transaction.exchange_rate_date = rate_date
                transaction.exchange_rate_source = rate_source
            if transaction.counterparty_account_id:
                target_currency = transaction.counterparty_currency or source_currency
                if source_currency == target_currency:
                    transaction.counterparty_amount = transaction.amount
                    counterparty_rate = Decimal("1")
                    counterparty_rate_date = new_date
                    counterparty_rate_source = "identity"
                else:
                    counterparty_rate, counterparty_rate_date, counterparty_rate_source = get_rate(
                        db, ctx.household.id, source_currency, target_currency, new_date
                    )
                    transaction.counterparty_amount = (
                        Decimal(str(transaction.amount)) * counterparty_rate
                    ).quantize(Decimal("0.01"))
                transaction.counterparty_exchange_rate = counterparty_rate
                transaction.counterparty_exchange_rate_date = counterparty_rate_date
                transaction.counterparty_exchange_rate_source = counterparty_rate_source
                transaction.counterparty_base_amount = (
                    Decimal(str(transaction.base_amount))
                    * Decimal(str(transaction.counterparty_amount))
                    / Decimal(str(transaction.amount))
                ).quantize(Decimal("0.01")) if transaction.amount else Decimal("0.00")
        except CurrencyError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    for key, value in updates.items():
        setattr(transaction, key, value)
    db.add(transaction)
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    if (
        transaction.access_scope == "shared"
        and transaction.type in {"income", "expense"}
    ):
        from app.services.financial_intelligence import run_financial_intelligence
        from app.services.notifications import sync_notifications_from_alerts

        run_financial_intelligence(db, ctx.household)
        sync_notifications_from_alerts(db, ctx.household.id)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="update",
        entity_type="transaction",
        entity_id=transaction.id,
        detail={"fields": sorted(payload.model_dump(exclude_unset=True).keys())},
    )
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/{transaction_id}/void", response_model=TransactionOut)
def void_transaction(
    transaction_id: UUID,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    transaction = _visible_transaction(db, ctx, transaction_id)
    if transaction.status == "voided":
        raise HTTPException(status_code=400, detail="Transaction is already voided.")
    account = _visible_account(db, ctx, transaction.account_id)
    counterparty = None
    if transaction.counterparty_account_id:
        counterparty = _visible_account(db, ctx, transaction.counterparty_account_id)
    apply_transaction_effect(
        db,
        account=account,
        counterparty=counterparty,
        tx_type=transaction.type,
        amount=transaction.amount,
        status=transaction.status,
        reverse=True,
        counterparty_amount=transaction.counterparty_amount,
    )
    was_income = transaction.type == "income"
    transaction.status = "voided"
    db.add(transaction)
    db.flush()
    evaluate_budget_alerts(db, ctx.household.id)
    if was_income:
        ensure_period_allocation(db, ctx.household)
    if transaction.access_scope == "shared":
        from app.services.financial_intelligence import run_financial_intelligence
        from app.services.notifications import sync_notifications_from_alerts

        run_financial_intelligence(db, ctx.household)
        sync_notifications_from_alerts(db, ctx.household.id)
    write_audit(
        db,
        household_id=ctx.household.id,
        user_id=ctx.user.id,
        action="void",
        entity_type="transaction",
        entity_id=transaction.id,
        detail={"type": transaction.type, "amount": str(transaction.amount)},
    )
    db.commit()
    db.refresh(transaction)
    return transaction
