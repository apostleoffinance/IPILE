import logging
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("familyos.request")

_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-csrf-token",
    "x-billing-secret",
    "x-inbound-email-secret",
    "proxy-authorization",
}


def scrub_error_event(event: dict, hint: dict | None = None) -> dict:
    """Remove request payloads and credentials before an error event leaves the app."""
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        request.pop("query_string", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                key: value
                for key, value in headers.items()
                if key.lower() not in _SENSITIVE_HEADERS
            }
        url = request.get("url")
        if isinstance(url, str):
            parts = urlsplit(url)
            request["url"] = urlunsplit(
                (parts.scheme, parts.netloc, parts.path, "", "")
            )
    event.pop("user", None)
    return event


def initialize_error_reporting(
    *, dsn: str, environment: str, traces_sample_rate: float = 0.0
) -> bool:
    """Enable Sentry only when an operator explicitly configures a DSN."""
    if not dsn.strip():
        logger.info("error_reporting_disabled reason=missing_sentry_dsn")
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn.strip(),
        environment=environment,
        integrations=[FastApiIntegration(), StarletteIntegration()],
        send_default_pii=False,
        max_request_body_size="never",
        traces_sample_rate=max(0.0, min(float(traces_sample_rate), 0.2)),
        before_send=scrub_error_event,
    )
    logger.info("error_reporting_enabled provider=sentry environment=%s", environment)
    return True


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request id and emit structured access / error logs for monitoring."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "elapsed_ms": round(elapsed_ms, 2),
                },
            )
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-Id"] = request_id
        if request.url.path.startswith("/api/"):
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "elapsed_ms": round(elapsed_ms, 2),
                },
            )
        return response
