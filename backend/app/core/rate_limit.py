"""
Rate Limiting Dependency for ApplyFlow APIs.
Uses Redis / HybridProductionCache to enforce request quotas per user/IP.
"""

from fastapi import Depends, HTTPException, Request, status

from app.core.cache import cache
from app.core.dependencies import get_current_user


def rate_limit(limit_count: int, window_seconds: int = 60):
    """
    Dependency factory to rate limit endpoints per authenticated user (or client IP).
    """
    async def rate_limiter(request: Request, current_user=Depends(get_current_user)):
        user_identifier = str(current_user.id) if current_user else (request.client.host if request.client else "anon")
        route_path = request.url.path
        cache_key = f"ratelimit:{route_path}:{user_identifier}"

        curr = cache.get(cache_key)
        if curr is not None and int(curr) >= limit_count:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit_count} requests per {window_seconds}s.",
            )

        if curr is None:
            cache.set(cache_key, "1", ttl=window_seconds)
        else:
            cache.set(cache_key, str(int(curr) + 1), ttl=window_seconds)

        return True

    return rate_limiter
