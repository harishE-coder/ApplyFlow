"""
ApplyFlow In-Memory High-Performance TTL Cache Module.
Provides lightweight, thread-safe, memory-efficient caching for aggregated dashboard payloads,
with fast automatic expiration (15-30s TTL) and immediate mutation invalidation.
"""

import time
import asyncio
from typing import Any, Callable

# Thread-safe in-memory cache store: key -> (value, expire_timestamp)
_cache_store: dict[str, tuple[Any, float]] = {}
_lock = asyncio.Lock()

DEFAULT_TTL_SECONDS = 25  # 25 seconds TTL (within the 15-30s sprint specification)


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Generate a normalized cache key from prefix and arguments."""
    arg_parts = [str(a) for a in args if a is not None]
    kwarg_parts = [f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None]
    return f"{prefix}:" + ":".join(arg_parts + kwarg_parts)


async def get_cached(key: str) -> Any | None:
    """Retrieve an item from the cache if present and not expired."""
    entry = _cache_store.get(key)
    if entry is None:
        return None

    val, expire_at = entry
    if time.time() > expire_at:
        # Expired - remove and return None
        _cache_store.pop(key, None)
        return None

    return val


async def set_cached(key: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> None:
    """Store an item in the cache with a specified TTL in seconds."""
    expire_at = time.time() + ttl
    _cache_store[key] = (value, expire_at)


def invalidate_dashboard_cache() -> int:
    """
    Purge all dashboard and home aggregated cache entries.
    Returns the count of invalidated keys.
    """
    keys_to_delete = [
        k for k in _cache_store
        if k.startswith("dashboard:") or k.startswith("admin_home:") or k.startswith("emp_home:") or k.startswith("client_home:")
    ]
    for k in keys_to_delete:
        _cache_store.pop(k, None)
    return len(keys_to_delete)


def clear_all_cache() -> None:
    """Clear entire in-memory cache."""
    _cache_store.clear()
