"""
API key authentication for the detection endpoint.

The expected key is read from the API_KEY environment variable.
If API_KEY is not set the server starts in open mode (dev/local use only).
"""

import os
from fastapi import Header, HTTPException

_API_KEY = os.environ.get("API_KEY", "")


def require_api_key(x_api_key: str = Header(default="")) -> None:
    """
    FastAPI dependency — inject into any route that needs authentication.

    Usage:
        from .auth import require_api_key
        from fastapi import Depends

        @app.post("/api/detect", dependencies=[Depends(require_api_key)])
        async def detect_poison(...):
            ...
    """
    if not _API_KEY:
        return  # No key configured → open mode (dev / local)

    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
