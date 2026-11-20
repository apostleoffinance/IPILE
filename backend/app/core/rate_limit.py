from collections import defaultdict
from time import time

from fastapi import HTTPException, Request, status

_hits: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits() -> None:
    _hits.clear()


def requester_key(request: Request, action: str) -> str:
    """Build a per-client auth throttle key behind Cloudflare/Render proxies."""
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-real-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    return f"{action}:{client_ip}"


def enforce_rate_limit(key: str, limit: int = 10, window_seconds: int = 60) -> None:
    now = time()
    recent = [stamp for stamp in _hits[key] if now - stamp < window_seconds]
    if len(recent) >= limit:
        _hits[key] = recent
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again shortly.",
            headers={"Retry-After": str(window_seconds)},
        )
    recent.append(now)
    _hits[key] = recent
