"""
ApplyFlow Production Multi-Worker Cache.
Provides sub-millisecond responses for read-heavy endpoints (dashboards, overviews, user lookups)
with deterministic tag-based invalidation across all workers via Redis or in-memory TTL fallback.
"""

import json
import logging
import time
from typing import Any

from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class TTLCache:
    """In-memory thread-safe TTL cache with tag tracking."""

    def __init__(self, default_ttl: float = 15.0):
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

    def set_nx(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """Sets key only if it does not exist or has expired. Returns True if key was set, False otherwise."""
        if key in self._cache:
            expires_at, _, _ = self._cache[key]
            if time.time() <= expires_at:
                return False
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl
        self._cache[key] = (expires_at, value, set())
        return True

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


class HybridProductionCache:
    """
    Production-ready hybrid cache:
    - Uses Redis when `REDIS_URL` is configured for cross-worker invalidation.
    - Transparently falls back to in-memory `TTLCache` in local/testing mode.
    """

    def __init__(self, default_ttl: float = 15.0):
        self.default_ttl = default_ttl
        self.local_cache = TTLCache(default_ttl=default_ttl)
        self._redis_client = None
        self._redis_available = False

        if settings.redis_url:
            try:
                import redis
                self._redis_client = redis.from_url(settings.redis_url, decode_responses=True)
                self._redis_client.ping()
                self._redis_available = True
                logger.info("Connected to Redis shared cache.")
            except Exception as exc:
                logger.warning(f"Redis unavailable ({exc}), falling back to in-memory TTL cache.")
                self._redis_available = False

    def _serialize(self, value: Any) -> str:
        if hasattr(value, "model_dump_json"):
            return value.model_dump_json()
        if hasattr(value, "dict"):
            return json.dumps(value.dict())
        return json.dumps(value)

    def get(self, key: str) -> Any | None:
        if self._redis_available and self._redis_client:
            try:
                raw = self._redis_client.get(f"applyflow:{key}")
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                logger.debug(f"Redis get failed ({exc}), checking local cache.")
        return self.local_cache.get(key)

    def set(self, key: str, value: Any, ttl: float | None = None, tags: set[str] | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self.default_ttl
        # Always set in local cache for speed
        self.local_cache.set(key, value, ttl=effective_ttl, tags=tags)

        if self._redis_available and self._redis_client:
            try:
                redis_key = f"applyflow:{key}"
                val_str = self._serialize(value)
                self._redis_client.setex(redis_key, int(effective_ttl), val_str)

                # Track tags in Redis sets for cross-worker invalidation
                if tags:
                    for tag in tags:
                        tag_key = f"applyflow:tag:{tag}"
                        self._redis_client.sadd(tag_key, redis_key)
                        self._redis_client.expire(tag_key, int(effective_ttl * 2))
            except Exception as exc:
                logger.debug(f"Redis set failed ({exc}).")

    def set_nx(self, key: str, value: Any, ttl: float | None = None) -> bool:
        """Atomic SETNX in Redis (or in-memory cache) with TTL. Returns True if set, False if already exists."""
        effective_ttl = ttl if ttl is not None else self.default_ttl
        if self._redis_available and self._redis_client:
            try:
                redis_key = f"applyflow:{key}"
                val_str = self._serialize(value)
                res = self._redis_client.set(redis_key, val_str, ex=int(effective_ttl), nx=True)
                if res:
                    self.local_cache.set_nx(key, value, ttl=effective_ttl)
                    return True
                return False
            except Exception as exc:
                logger.debug(f"Redis set_nx failed ({exc}), falling back to local.")
        return self.local_cache.set_nx(key, value, ttl=effective_ttl)

    def invalidate_key(self, key: str) -> None:
        self.local_cache.invalidate_key(key)
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.delete(f"applyflow:{key}")
            except Exception:
                pass

    def invalidate_tag(self, tag: str) -> int:
        local_count = self.local_cache.invalidate_tag(tag)
        if self._redis_available and self._redis_client:
            try:
                tag_key = f"applyflow:tag:{tag}"
                keys = self._redis_client.smembers(tag_key)
                if keys:
                    self._redis_client.delete(*keys)
                self._redis_client.delete(tag_key)
                return max(local_count, len(keys))
            except Exception as exc:
                logger.debug(f"Redis invalidate_tag failed ({exc}).")
        return local_count

    def rpush(self, key: str, value: Any) -> None:
        """Pushes an item to the tail of a list."""
        val_str = self._serialize(value)
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.rpush(f"applyflow:{key}", val_str)
                return
            except Exception as exc:
                logger.debug(f"Redis rpush failed ({exc}), falling back to local.")
        # Local fallback
        curr = self.local_cache.get(key) or []
        if not isinstance(curr, list):
            curr = []
        curr.append(json.loads(val_str) if isinstance(value, (dict, list, BaseModel)) else value)
        self.local_cache.set(key, curr, ttl=86400)

    def lrange(self, key: str, start: int = 0, end: int = -1) -> list[Any]:
        """Retrieves items from a list."""
        if self._redis_available and self._redis_client:
            try:
                items = self._redis_client.lrange(f"applyflow:{key}", start, end)
                return [json.loads(it) for it in items]
            except Exception as exc:
                logger.debug(f"Redis lrange failed ({exc}), falling back to local.")
        curr = self.local_cache.get(key)
        if isinstance(curr, list):
            if end == -1:
                return curr[start:]
            return curr[start:end + 1]
        return []

    def lrem(self, key: str, count: int, value: Any) -> int:
        """Removes element from list."""
        val_str = self._serialize(value)
        if self._redis_available and self._redis_client:
            try:
                return self._redis_client.lrem(f"applyflow:{key}", count, val_str)
            except Exception as exc:
                logger.debug(f"Redis lrem failed ({exc}).")
        curr = self.local_cache.get(key)
        if isinstance(curr, list):
            target = json.loads(val_str) if isinstance(value, (dict, list, BaseModel)) else value
            removed = 0
            new_list = []
            for item in curr:
                if item == target and (count == 0 or removed < abs(count)):
                    removed += 1
                else:
                    new_list.append(item)
            self.local_cache.set(key, new_list, ttl=86400)
            return removed
        return 0

    def clear(self) -> None:
        self.local_cache.clear()
        if self._redis_available and self._redis_client:
            try:
                self._redis_client.flushdb()
            except Exception:
                pass


# Global production cache instance
cache = HybridProductionCache(default_ttl=15.0)


# ---- Multi-Worker Shared Presence ----

def set_user_presence(user_id: str, room_id: str, ttl: int = 45) -> None:
    """Sets multi-worker active presence for a user in a room."""
    data = {"room": room_id, "last_seen": int(time.time())}
    cache.set(f"presence:user:{user_id}", data, ttl=ttl)


def get_user_presence(user_id: str) -> dict[str, Any] | None:
    """Gets multi-worker active presence for a user."""
    return cache.get(f"presence:user:{user_id}")


def remove_user_presence(user_id: str, room_id: str | None = None) -> None:
    """Removes active presence for a user."""
    curr = get_user_presence(user_id)
    if curr and (room_id is None or curr.get("room") == room_id):
        cache.invalidate_key(f"presence:user:{user_id}")


def is_user_in_room_shared(user_id: str, room_id: str) -> bool:
    """Checks if a user is currently active in a specific room across ALL workers."""
    pres = get_user_presence(user_id)
    if not pres:
        return False
    return str(pres.get("room")) == str(room_id)


# Specialized invalidation helpers
def invalidate_dashboard_cache() -> int:
    """Invalidates all cached dashboard variants when applications, resumes, clients, or targets mutate."""
    return cache.invalidate_tag("dashboard")

def invalidate_notifications_cache() -> int:
    """Invalidates notification caches."""
    return cache.invalidate_tag("notifications")

def invalidate_chat_cache() -> int:
    """Invalidates chat unread and room caches."""
    return cache.invalidate_tag("chat")

