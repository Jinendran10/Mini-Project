"""
Rate limiting for JIE API.
"""

import time
from collections import defaultdict
from fastapi import HTTPException
import logging
import os

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    What: Tracks requests per client and enforces limits
    Why: Prevents API abuse and overload
    Impact: Protects service from excessive requests
    """
    
    def __init__(self, requests_per_minute: int = 10):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per client per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
    
    async def check_rate_limit(self, api_key: str):
        """
        Check if request is within rate limit.
        
        Args:
            api_key: Client API key
        
        Raises:
            HTTPException: If rate limit exceeded
        """
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[api_key] = [
            req_time for req_time in self.requests[api_key]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[api_key]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for key: {api_key[:10]}...")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute.",
            )
        
        # Record this request
        self.requests[api_key].append(now)


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
)
