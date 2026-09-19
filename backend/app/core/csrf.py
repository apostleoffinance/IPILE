"""Double-submit CSRF for cookie-authenticated mutations."""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
EXEMPT_PREFIXES = (
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/csrf",
    "/docs",
    "/openapi.json",
    "/redoc",
)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    settings = get_settings()
    value = token or new_csrf_token()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=value,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=_cookie_samesite(),
        max_age=settings.session_absolute_days * 24 * 60 * 60,
        path="/",
    )
    return value


def _cookie_samesite() -> str:
    value = get_settings().cookie_samesite.lower()
    if value not in {"lax", "strict", "none"}:
        return "lax"
    return value


def csrf_exempt(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix + "/") for prefix in EXEMPT_PREFIXES)


class CsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if request.method.upper() in UNSAFE and not csrf_exempt(request.url.path):
            cookie_token = request.cookies.get(settings.csrf_cookie_name)
            header_token = request.headers.get("x-csrf-token")
            if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                return Response(
                    content='{"detail":"CSRF validation failed."}',
                    status_code=403,
                    media_type="application/json",
                )
        return await call_next(request)
