from collections import defaultdict
from time import time

from fastapi import HTTPException, status

_hits: dict[str, list[float]] = defaultdict(list)


def reset_rate_limits() -> None:
    _hits.clear()


def enforce_rate_limit(key: str, limit: int = 10, window_seconds: int = 60) -> None:
    now = time()
    recent = [stamp for stamp in _hits[key] if now - stamp < window_seconds]
    if len(recent) >= limit:
        _hits[key] = recent
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again shortly.",
        )
    recent.append(now)
    _hits[key] = recent
