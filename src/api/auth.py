"""
Authentication for JIE API.
"""

from fastapi import Header, HTTPException
import os
import logging

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: str = Header(..., description="API key")):
    """
    Verify API key from header.
    
    What: Checks if provided API key matches configured key
    Why: Prevents unauthorized access
    Impact: Secures API endpoints
    
    Args:
        x_api_key: API key from X-API-Key header
    
    Returns:
        API key if valid
    
    Raises:
        HTTPException: If key is invalid
    """
    valid_key = os.getenv("API_KEY")
    
    if not valid_key:
        logger.warning("API_KEY not configured - authentication disabled")
        return x_api_key
    
    if x_api_key != valid_key:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return x_api_key
