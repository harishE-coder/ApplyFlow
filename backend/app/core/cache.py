"""
ApplyFlow Backend In-Memory TTL Cache.
Provides sub-millisecond responses for read-heavy endpoints (dashboards, overviews, user lookups)
with deterministic tag-based invalidation upon data mutations.
"""

import time
import asyncio
from typing import Any

class TTLCache:
    def __init__(self, default_ttl: float = 20.0):
        self.default_ttl = default_ttl
        self._cache: dict[str, tuple[float, Any, set[str]]] = {}

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            return None
        expires_at, value, _ = self._cache[key]
        if time.time() > expires_at:
            self._cache.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl: float | None = None, tags: set[str] | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl
        self._cache[key] = (expires_at, value, tags or set())

    def invalidate_key(self, key: str) -> None:
        self._cache.pop(key, None)

    def invalidate_tag(self, tag: str) -> int:
        keys_to_remove = [
            k for k, (_, _, tags) in self._cache.items()
            if tag in tags
        ]
        for k in keys_to_remove:
            self._cache.pop(k, None)
        return len(keys_to_remove)

    def clear(self) -> None:
        self._cache.clear()


# Global cache instance
cache = TTLCache(default_ttl=15.0)

# Specialized invalidation helpers
def invalidate_dashboard_cache():
    """Invalidates all cached dashboard variants when applications, resumes, clients, or targets mutate."""
    return cache.invalidate_tag("dashboard")

def invalidate_notifications_cache():
    """Invalidates notification caches."""
    return cache.invalidate_tag("notifications")
