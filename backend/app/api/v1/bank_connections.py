import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.models.account import Account
from app.models.banking import BankConnection, BankWebhookEvent
from app.services.bank_security import decrypt_provider_account_id, encrypt_provider_account_id, provider_account_hash
from app.services.mono import MonoAPIError, MonoClient, MonoReauthRequired
from app.services.reconciliation import create_mono_session, minor_to_major

router = APIRouter(prefix="/bank-connections", tags=["bank-connectivity"])
webhook_router = APIRouter(prefix="/webhooks", tags=["bank-webhooks"])


def _client():
    settings = get_settings()
    if not settings.mono_connect_configured:
        raise HTTPException(status_code=503, detail="Bank connectivity is not configured.")
    return settings, MonoClient(settings.mono_secret_key)


def _out(row):
    return {"id": str(row.id), "account_id": str(row.account_id), "provider": row.provider,
        "institution_name": row.institution_name, "masked_account_number": row.masked_account_number,
        "currency": row.currency, "status": row.status, "data_status": row.data_status,
        "provider_balance": str(row.provider_balance) if row.provider_balance is not None else None,
        "provider_balance_as_of": row.provider_balance_as_of.isoformat() if row.provider_balance_as_of else None,
        "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else None,
        "last_error": row.last_error, "created_at": row.created_at.isoformat() if row.created_at else None}


def _shared_account(db, household_id, account_id):
    account = db.query(Account).filter(Account.id == account_id, Account.household_id == household_id,
        Account.access_scope == "shared", Account.deleted_at.is_(None)).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Shared household account not found.")
    return account


@router.post("/initiate", status_code=201)
def initiate(account_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    settings, client = _client()
    account = _shared_account(db, ctx.household.id, account_id)
    reference = secrets.token_urlsafe(32)
    row = BankConnection(household_id=ctx.household.id, account_id=account.id,
        created_by_member_id=ctx.member.id, provider="mono", link_reference=reference)
    db.add(row)
    db.flush()
    try:
        url = client.initiate_linking(customer_name=ctx.user.display_name, customer_email=ctx.user.email,
            reference=reference, redirect_url=settings.mono_redirect_url)
        db.commit()
        db.refresh(row)
    except MonoAPIError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        client.close()
    return {"connection": _out(row), "mono_url": url}


@router.get("", response_model=list[dict])
def list_connections(ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    rows = db.query(BankConnection).filter(BankConnection.household_id == ctx.household.id).order_by(BankConnection.created_at.desc()).limit(100).all()
    return [_out(row) for row in rows]


@router.post("/{connection_id}/reauthorize")
def reauthorize(connection_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    settings, client = _client()
    row = db.query(BankConnection).filter(BankConnection.id == connection_id,
        BankConnection.household_id == ctx.household.id, BankConnection.provider == "mono").with_for_update().first()
    if row is None:
        client.close()
        raise HTTPException(status_code=404, detail="Bank connection not found.")
    if row.status != "reauth_required" or not row.provider_account_id_encrypted:
        client.close()
        raise HTTPException(status_code=409, detail="This connection cannot be re-authorised.")
    reference = secrets.token_urlsafe(32)
    try:
        url = client.initiate_reauthorization(account_id=decrypt_provider_account_id(row.provider_account_id_encrypted),
            reference=reference, redirect_url=settings.mono_redirect_url)
        row.link_reference, row.status, row.data_status, row.last_error = reference, "reauthorizing", "PROCESSING", None
        db.add(row)
        db.commit()
        db.refresh(row)
    except (MonoAPIError, RuntimeError) as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        client.close()
    return {"connection": _out(row), "mono_url": url}


@router.post("/{connection_id}/sync")
def sync(connection_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    _settings, client = _client()
    row = db.query(BankConnection).filter(BankConnection.id == connection_id,
        BankConnection.household_id == ctx.household.id, BankConnection.provider == "mono").with_for_update().first()
    if row is None:
        client.close()
        raise HTTPException(status_code=404, detail="Bank connection not found.")
    if row.status != "active" or row.data_status not in {"AVAILABLE", "PARTIAL"}:
        client.close()
        raise HTTPException(status_code=409, detail="Bank transaction data is not available yet.")
    account = _shared_account(db, ctx.household.id, row.account_id)
    try:
        session = create_mono_session(db, connection=row, account=account, client=client)
        db.commit()
        db.refresh(session)
    except MonoReauthRequired as exc:
        db.rollback()
        row = db.query(BankConnection).filter(BankConnection.id == connection_id, BankConnection.household_id == ctx.household.id).first()
        if row:
            row.status, row.last_error = "reauth_required", "The bank requires renewed customer authorisation."
            db.add(row)
            db.commit()
        raise HTTPException(status_code=409, detail="Bank authorisation must be renewed.") from exc
    except (MonoAPIError, RuntimeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        client.close()
    return {"session_id": str(session.id), "total_rows": session.total_rows,
        "duplicate_rows": session.duplicate_rows, "matched_count": session.matched_count,
        "suggested_count": session.suggested_count, "unmatched_count": session.unmatched_count,
        "conflict_count": session.conflict_count}


@router.post("/{connection_id}/disconnect")
def disconnect(connection_id: UUID, ctx: HouseholdContext = Depends(require_roles("owner", "partner")), db: Session = Depends(get_db)):
    _settings, client = _client()
    row = db.query(BankConnection).filter(BankConnection.id == connection_id,
        BankConnection.household_id == ctx.household.id, BankConnection.provider == "mono").with_for_update().first()
    if row is None:
        client.close()
        raise HTTPException(status_code=404, detail="Bank connection not found.")
    if row.status != "unlinked":
        if not row.provider_account_id_encrypted:
            client.close()
            raise HTTPException(status_code=409, detail="No active provider account to disconnect.")
        try:
            client.unlink_account(decrypt_provider_account_id(row.provider_account_id_encrypted))
        except (MonoAPIError, RuntimeError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        finally:
            client.close()
        row.status, row.data_status = "unlinked", "UNAVAILABLE"
        row.provider_account_id_encrypted = row.provider_account_id_hash = None
        row.provider_balance = row.provider_balance_as_of = None
        row.revoked_at = datetime.now(UTC)
        db.add(row)
        db.commit()
        db.refresh(row)
    else:
        client.close()
    return _out(row)


@webhook_router.post("/mono")
async def mono_webhook(request: Request, mono_webhook_secret: str | None = Header(default=None, alias="mono-webhook-secret"), db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.mono_webhook_secret:
        raise HTTPException(status_code=503, detail="Mono webhooks are not configured.")
    if not mono_webhook_secret or not hmac.compare_digest(mono_webhook_secret, settings.mono_webhook_secret):
        raise HTTPException(status_code=401, detail="Invalid webhook credentials.")
    raw = await request.body()
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload.")
    event_type = str(payload.get("event") or "")
    if not event_type.startswith("mono.events."):
        raise HTTPException(status_code=400, detail="Unsupported webhook event.")
    event_id = str(payload.get("event_id") or hashlib.sha256(raw).hexdigest())
    digest = hashlib.sha256(raw).hexdigest()
    if db.query(BankWebhookEvent.id).filter(BankWebhookEvent.provider == "mono", BankWebhookEvent.event_id == event_id).first():
        return {"received": True, "duplicate": True}
    db.add(BankWebhookEvent(provider="mono", event_id=event_id[:160], event_type=event_type[:120], payload_sha256=digest))
    data = payload["data"]
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    reference = str(meta.get("ref") or "")
    now = datetime.now(UTC)

    if event_type == "mono.events.account_connected":
        provider_id = str(data.get("id") or "")
        row = db.query(BankConnection).filter(BankConnection.provider == "mono",
            BankConnection.link_reference == reference, BankConnection.status == "pending").with_for_update().first()
        if row and provider_id:
            account_hash = provider_account_hash(provider_id)
            already = db.query(BankConnection.id).filter(BankConnection.household_id == row.household_id,
                BankConnection.provider == "mono", BankConnection.provider_account_id_hash == account_hash,
                BankConnection.id != row.id, BankConnection.status != "unlinked").first()
            if already:
                row.status, row.last_error = "error", "This bank account is already connected to this household."
            else:
                row.provider_account_id_encrypted = encrypt_provider_account_id(provider_id)
                row.provider_account_id_hash = account_hash
                row.data_status, row.status = str(meta.get("data_status") or "PROCESSING").upper(), "pending_data"
            db.add(row)

    elif event_type == "mono.events.account_updated":
        bank = data.get("account") if isinstance(data.get("account"), dict) else {}
        provider_id = str(bank.get("_id") or bank.get("id") or "")
        row = db.query(BankConnection).filter(BankConnection.provider == "mono", BankConnection.link_reference == reference).with_for_update().first() if reference else None
        if row is None and provider_id:
            row = db.query(BankConnection).filter(BankConnection.provider == "mono", BankConnection.provider_account_id_hash == provider_account_hash(provider_id)).with_for_update().first()
        if row and row.status not in {"unlinked", "error"}:
            currency = str(bank.get("currency") or row.currency or "").upper()
            account = db.query(Account).filter(Account.id == row.account_id, Account.household_id == row.household_id, Account.access_scope == "shared").first()
            institution = bank.get("institution") if isinstance(bank.get("institution"), dict) else {}
            row.institution_name = str(institution.get("name") or "")[:200] or None
            digits = "".join(c for c in str(bank.get("accountNumber") or bank.get("account_number") or "") if c.isdigit())
            row.masked_account_number = digits[-4:] if digits else None
            row.currency = currency or row.currency
            row.data_status = str(meta.get("data_status") or "PROCESSING").upper()
            if account is None or (currency and currency != account.currency.upper()):
                row.status, row.last_error = "error", "Connected bank currency does not match the selected household account."
            else:
                if bank.get("balance") is not None and currency:
                    try:
                        row.provider_balance = minor_to_major(bank["balance"], currency, allow_nonpositive=True)
                        row.provider_balance_as_of = now
                    except ValueError:
                        row.provider_balance = None
                retrieved = {str(x).lower() for x in (meta.get("retrieved_data") or [])}
                if row.data_status == "AVAILABLE" or (row.data_status == "PARTIAL" and "transactions" in retrieved):
                    row.status, row.last_error = "active", None
                elif row.data_status in {"FAILED", "UNAVAILABLE"}:
                    row.status, row.last_error = "error", "Mono could not retrieve usable bank data."
                else:
                    row.status = "pending_data"
            db.add(row)

    elif event_type == "mono.events.account_unlinked":
        bank = data.get("account") if isinstance(data.get("account"), dict) else {}
        provider_id = str(bank.get("_id") or bank.get("id") or data.get("id") or "")
        row = db.query(BankConnection).filter(BankConnection.provider == "mono",
            BankConnection.provider_account_id_hash == provider_account_hash(provider_id)).with_for_update().first() if provider_id else None
        if row:
            row.status, row.data_status = "unlinked", "UNAVAILABLE"
            row.provider_account_id_encrypted = row.provider_account_id_hash = None
            row.provider_balance = row.provider_balance_as_of = None
            row.revoked_at = now
            db.add(row)

    elif event_type == "mono.events.account_connected.failed":
        row = db.query(BankConnection).filter(BankConnection.provider == "mono",
            BankConnection.link_reference == reference, BankConnection.status == "pending").with_for_update().first()
        if row:
            row.status, row.last_error = "error", "Bank account authorisation was not completed."
            db.add(row)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.query(BankWebhookEvent.id).filter(BankWebhookEvent.provider == "mono", BankWebhookEvent.event_id == event_id).first():
            return {"received": True, "duplicate": True}
        raise
    return {"received": True, "duplicate": False}
