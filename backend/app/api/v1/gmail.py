from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from email.utils import parseaddr

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import HouseholdContext, get_db, require_roles
from app.core.config import get_settings
from app.models.gmail import GmailConnection
from app.models.household import Household
from app.models.imports import ImportJob
from app.models.transaction import Transaction
from app.services.email_imports import apply_alert_automation, parse_bank_alert
from app.services.transaction_intelligence import enrich_bank_alert
from app.services.gmail import (
    authorization_url,
    decrypt_refresh_token,
    encrypt_refresh_token,
    exchange_code,
    extract_message,
    fetch_message,
    gmail_get,
    list_recent_messages,
    refresh_access_token,
    revoke_refresh_token,
)

router = APIRouter(prefix="/imports", tags=["imports"])


class PreferencesBody(BaseModel):
    automation_mode: str = Field(
        pattern="^(review_everything|auto_trusted|full_automation)$"
    )


def _frontend_redirect(result: str) -> RedirectResponse:
    origins = get_settings().cors_origin_list
    origin = origins[0] if origins else "https://ipile.app"
    return RedirectResponse(f"{origin.rstrip('/')}/money/import?gmail={result}", status_code=303)


def _sender_allowed(sender: str) -> bool:
    domain = sender.strip().lower().rsplit("@", 1)[-1].strip(" >")
    return bool(domain and any(
        domain == allowed or domain.endswith("." + allowed)
        for allowed in get_settings().gmail_sender_domain_list
    ))


def _gmail_dmarc_passes_for_sender(sender: str, authentication_results: str) -> bool:
    sender_address = parseaddr(sender)[1].lower()
    sender_domain = sender_address.rsplit("@", 1)[-1]
    match = re.search(
        r"\bdmarc=pass\b.*?\bheader\.from=([a-z0-9.-]+)",
        authentication_results,
        re.IGNORECASE,
    )
    return bool(match and sender_domain and match.group(1).lower() == sender_domain)


def _save_alert(db: Session, connection: GmailConnection, message: dict[str, str]) -> str:
    if not _sender_allowed(message["from"]):
        return "ignored"
    if not _gmail_dmarc_passes_for_sender(
        message["from"], message.get("authentication_results", "")
    ):
        return "ignored"
    if not message["body"]:
        return "ignored"
    duplicate = db.query(ImportJob).filter(
        ImportJob.household_id == connection.household_id,
        ImportJob.source == "email",
        ImportJob.result["message_id"].as_string() == message["message_id"],
    ).first()
    if duplicate:
        return "duplicate"
    try:
        row = parse_bank_alert(
            sender=message["from"],
            subject=message["subject"],
            body=message["body"],
            email_date=message["date"],
            message_id=message["message_id"],
        )
    except ValueError as exc:
        db.add(ImportJob(
            household_id=connection.household_id,
            source="email",
            filename=message["subject"][:200],
            status="rejected",
            error_count=1,
            result={
                "sender": message["from"][:200],
                "message_id": message["message_id"],
                "provider": "gmail",
                "errors": [str(exc)],
            },
        ))
        return "rejected"
    if db.query(Transaction.id).filter(
        Transaction.household_id == connection.household_id,
        Transaction.external_id == row.external_id,
        Transaction.deleted_at.is_(None),
    ).first():
        return "duplicate"
    pending = db.query(ImportJob).filter(
        ImportJob.household_id == connection.household_id,
        ImportJob.source == "email",
        ImportJob.status == "pending_review",
    ).all()
    if any(
        item.get("external_id") == row.external_id
        for job in pending
        for item in job.result.get("rows", [])
    ):
        return "duplicate"

    row, suggested, intelligence = enrich_bank_alert(
        db,
        connection.household_id,
        row,
        sender=message["from"],
        provider="gmail",
        provider_event_id=message["message_id"],
        sender_verified=True,
    )
    job = ImportJob(
        household_id=connection.household_id,
        source="email",
        filename=message["subject"][:200],
        status="pending_review",
        result={
            "sender": message["from"][:200],
            "message_id": message["message_id"],
            "provider": "gmail",
            "suggested_account_id": str(suggested.id) if suggested else None,
            "account_match": intelligence["account_match"],
            "intelligence": intelligence,
            "rows": [{
                "date": row.date.isoformat(),
                "amount": str(row.amount),
                "currency": row.currency,
                "type": row.type,
                "description": row.description,
                "external_id": row.external_id,
                "merchant": row.merchant,
                "category_name": row.category_name,
            }],
        },
    )
    household = db.query(Household).filter(Household.id == connection.household_id).first()
    auto_posted = False
    if household is not None:
        auto_posted = apply_alert_automation(db, household, job, row, suggested)
    db.add(job)
    return "auto_posted" if auto_posted else "queued"


def _sync_connection(db: Session, row: GmailConnection) -> dict[str, int]:
    if not row.enabled or not row.refresh_token_encrypted:
        return {"scanned": 0, "queued": 0, "rejected": 0, "ignored": 0}
    token = refresh_access_token(decrypt_refresh_token(row.refresh_token_encrypted))
    counts = {"scanned": 0, "queued": 0, "auto_posted": 0, "rejected": 0, "ignored": 0}
    latest = row.last_message_internal_date or int(datetime.now(UTC).timestamp() * 1000)
    sender_domains = get_settings().gmail_sender_domain_list
    for item in list_recent_messages(token, row.last_message_internal_date, sender_domains):
        message = extract_message(fetch_message(token, str(item["id"])))
        counts["scanned"] += 1
        latest = max(latest, int(message.get("internal_date") or 0))
        result = _save_alert(db, row, message)
        if result in counts:
            counts[result] += 1
    row.last_message_internal_date = latest or None
    row.last_sync_at = datetime.now(UTC)
    row.last_error = None
    db.add(row)
    db.commit()
    return counts


@router.get("/gmail/connection")
def gmail_status(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = db.query(GmailConnection).filter(
        GmailConnection.household_id == ctx.household.id
    ).first()
    return {
        "connected": bool(row and row.enabled),
        "email_address": row.email_address if row and row.enabled else None,
        "last_sync_at": row.last_sync_at if row and row.enabled else None,
        "last_error": row.last_error if row and row.enabled else None,
    }


@router.post("/gmail/connect")
def gmail_connect(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.gmail_connect_configured:
        raise HTTPException(status_code=503, detail="Gmail connection is not configured yet.")
    state = secrets.token_urlsafe(32)
    row = db.query(GmailConnection).filter(
        GmailConnection.household_id == ctx.household.id
    ).first()
    if row is None:
        row = GmailConnection(household_id=ctx.household.id)
    row.state_hash = hashlib.sha256(state.encode()).hexdigest()
    row.state_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    db.add(row)
    db.commit()
    return {"authorization_url": authorization_url(state)}


@router.get("/gmail/callback")
def gmail_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error or not code or not state:
        return _frontend_redirect("error")
    digest = hashlib.sha256(state.encode()).hexdigest()
    row = (
        db.query(GmailConnection)
        .filter(GmailConnection.state_hash == digest)
        .with_for_update()
        .first()
    )
    if row is None or row.state_expires_at is None:
        return _frontend_redirect("expired")
    expiry = row.state_expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    if expiry < datetime.now(UTC):
        row.state_hash = None
        row.state_expires_at = None
        db.add(row)
        db.commit()
        return _frontend_redirect("expired")
    try:
        token_data = exchange_code(code)
        refresh = token_data.get("refresh_token")
        if not refresh and row.refresh_token_encrypted:
            refresh = decrypt_refresh_token(row.refresh_token_encrypted)
        if not refresh:
            return _frontend_redirect("reauthorize")
        profile = gmail_get(str(token_data["access_token"]), "profile")
        row.email_address = str(profile.get("emailAddress") or "")[:320]
        row.google_subject = row.email_address
        row.refresh_token_encrypted = encrypt_refresh_token(str(refresh))
        row.enabled = True
        row.revoked_at = None
        row.state_hash = None
        row.state_expires_at = None
        row.last_error = None
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        return _frontend_redirect("error")
    return _frontend_redirect("connected")


@router.post("/gmail/disconnect")
def gmail_disconnect(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = db.query(GmailConnection).filter(
        GmailConnection.household_id == ctx.household.id
    ).first()
    if row:
        if row.refresh_token_encrypted:
            try:
                revoke_refresh_token(decrypt_refresh_token(row.refresh_token_encrypted))
            except Exception:
                # Local disconnect must still immediately stop all future reads.
                pass
        row.enabled = False
        row.refresh_token_encrypted = None
        row.state_hash = None
        row.state_expires_at = None
        row.revoked_at = datetime.now(UTC)
        row.last_error = None
        db.add(row)
        db.commit()
    return {"connected": False}


@router.post("/gmail/sync")
def gmail_sync_now(
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    row = db.query(GmailConnection).filter(
        GmailConnection.household_id == ctx.household.id,
        GmailConnection.enabled.is_(True),
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="No Gmail account is connected.")
    try:
        return _sync_connection(db, row)
    except Exception as exc:
        row.last_error = "Gmail sync failed. Reconnect your inbox if the problem continues."
        db.add(row)
        db.commit()
        raise HTTPException(status_code=502, detail=row.last_error) from exc


@router.post("/gmail/sync/cron")
def gmail_sync_cron(
    x_gmail_sync_secret: str | None = Header(default=None, alias="X-Gmail-Sync-Secret"),
    db: Session = Depends(get_db),
):
    secret = get_settings().gmail_sync_secret
    if (
        not secret
        or not x_gmail_sync_secret
        or not hmac.compare_digest(secret, x_gmail_sync_secret)
    ):
        raise HTTPException(status_code=401, detail="Invalid Gmail sync credentials.")
    rows = db.query(GmailConnection).filter(GmailConnection.enabled.is_(True)).all()
    total = {
        "connections": len(rows),
        "scanned": 0,
        "queued": 0,
        "auto_posted": 0,
        "rejected": 0,
        "failed": 0,
    }
    for row in rows:
        try:
            result = _sync_connection(db, row)
            for key in ("scanned", "queued", "auto_posted", "rejected"):
                total[key] += result[key]
        except Exception:
            db.rollback()
            row.last_error = "Gmail sync failed. Reconnect your inbox if the problem continues."
            db.add(row)
            db.commit()
            total["failed"] += 1
    return total


@router.get("/preferences")
def import_preferences(ctx: HouseholdContext = Depends(require_roles("owner", "partner"))):
    settings = ctx.household.settings or {}
    return {"automation_mode": settings.get("bank_alert_automation_mode", "review_everything")}


@router.put("/preferences")
def update_import_preferences(
    payload: PreferencesBody,
    ctx: HouseholdContext = Depends(require_roles("owner", "partner")),
    db: Session = Depends(get_db),
):
    settings = dict(ctx.household.settings or {})
    settings["bank_alert_automation_mode"] = payload.automation_mode
    ctx.household.settings = settings
    db.add(ctx.household)
    db.commit()
    return {"automation_mode": payload.automation_mode}
