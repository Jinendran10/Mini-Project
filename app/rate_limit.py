"""
Simple in-process rate limiter using a sliding window per client IP.
"""

import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException
from .config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

# Maps client IP → deque of request timestamps within the current window.
_request_log: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(request: Request) -> None:
    """
    FastAPI dependency — raises HTTP 429 when the caller exceeds the limit.
    Constants are imported from app.config so they stay in sync with the rest
    of the app.
    """
    ip = _client_ip(request)
    now = time.time()
    window = _request_log[ip]

    # Evict timestamps outside the current window.
    while window and window[0] < now - RATE_LIMIT_WINDOW:
        window.popleft()

    if len(window) >= RATE_LIMIT_REQUESTS:
        retry_after = int(RATE_LIMIT_WINDOW - (now - window[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )

    window.append(now)
