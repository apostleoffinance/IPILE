"""Minimal Gmail API client for read-only bank-alert ingestion."""
from __future__ import annotations

import base64
from email.utils import formatdate
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_ROOT = "https://gmail.googleapis.com/gmail/v1/users/me"


def _fernet() -> Fernet:
    key = get_settings().gmail_token_encryption_key
    if not key:
        raise RuntimeError("Gmail token encryption is not configured. Set GMAIL_TOKEN_ENCRYPTION_KEY.")
    return Fernet(key.encode("ascii"))


def encrypt_refresh_token(token: str) -> str:
    return _fernet().encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Stored Gmail authorisation cannot be decrypted.") from exc


def authorization_url(state: str) -> str:
    from urllib.parse import urlencode

    settings = get_settings()
    query = urlencode({
        "client_id": settings.gmail_oauth_client_id,
        "redirect_uri": settings.gmail_oauth_redirect_uri,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    })
    return "https://accounts.google.com/o/oauth2/v2/auth?" + query


def exchange_code(code: str) -> dict[str, Any]:
    settings = get_settings()
    response = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.gmail_oauth_client_id,
            "client_secret": settings.gmail_oauth_client_secret,
            "redirect_uri": settings.gmail_oauth_redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str) -> str:
    settings = get_settings()
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": settings.gmail_oauth_client_id,
            "client_secret": settings.gmail_oauth_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Google did not return an access token.")
    return str(token)


def gmail_get(access_token: str, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = httpx.get(
        f"{API_ROOT}/{path.lstrip('/')}",
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def _decode_body(data: str | None) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")


def _walk_parts(part: dict[str, Any]) -> list[str]:
    mime = str(part.get("mimeType") or "").lower()
    body = part.get("body") if isinstance(part.get("body"), dict) else {}
    result = [_decode_body(body.get("data"))] if mime == "text/plain" else []
    for child in part.get("parts") or []:
        if isinstance(child, dict):
            result.extend(_walk_parts(child))
    return result


def extract_message(message: dict[str, Any]) -> dict[str, str]:
    payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
    headers = {
        str(item.get("name", "")).lower(): str(item.get("value", ""))
        for item in payload.get("headers", [])
        if isinstance(item, dict)
    }
    body_parts = _walk_parts(payload)
    body = "\n".join(part for part in body_parts if part).strip()
    if not body:
        body = _decode_body((payload.get("body") or {}).get("data"))
    internal_ms = int(message.get("internalDate") or 0)
    email_date = formatdate(internal_ms / 1000, usegmt=True) if internal_ms else headers.get("date", "")
    return {
        "from": headers.get("from", ""),
        "subject": headers.get("subject", "Bank transaction alert"),
        "body": body,
        "date": email_date,
        "message_id": str(message.get("id") or ""),
        "authentication_results": headers.get("authentication-results", "").lower(),
        "internal_date": str(internal_ms),
    }


def list_recent_messages(access_token: str, after_internal_ms: int | None) -> list[dict[str, Any]]:
    if after_internal_ms:
        query = f"after:{max(0, after_internal_ms // 1000 - 60)}"
    else:
        query = "newer_than:7d"
    messages: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        params: dict[str, Any] = {"q": query, "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        page = gmail_get(access_token, "messages", params)
        for item in page.get("messages", []):
            if isinstance(item, dict) and item.get("id"):
                messages.append(item)
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    return messages


def fetch_message(access_token: str, message_id: str) -> dict[str, Any]:
    return gmail_get(access_token, f"messages/{message_id}", {"format": "full"})
