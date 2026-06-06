"""
Redis Cache Service

Centralized caching layer with graceful fallback to in-memory dict
when Redis is unavailable (for local dev without Redis running).

Key namespace convention: serene:{domain}:{relationship_id}:{identifier}
"""
import json
import logging
import time
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-backed cache with in-memory fallback."""

    def __init__(self, redis_url: str = "redis://localhost:6380/0"):
        self._redis = None
        self._redis_url = redis_url
        self._fallback: Dict[str, tuple] = {}  # key -> (value_json, expire_at)
        self._using_fallback = False
        self._connect()

    def _connect(self):
        """Attempt to connect to Redis."""
        try:
            import redis
            self._redis = redis.Redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._redis.ping()
            self._using_fallback = False
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}), using in-memory fallback")
            self._redis = None
            self._using_fallback = True

    def get(self, key: str) -> Optional[Any]:
        """Get a value by key. Returns None on miss."""
        if self._using_fallback:
            return self._fallback_get(key)
        try:
            raw = self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"Redis GET error: {e}")
            return self._fallback_get(key)

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set a value with TTL (seconds). Returns True on success."""
        serialized = json.dumps(value, default=str)
        if self._using_fallback:
            return self._fallback_set(key, serialized, ttl)
        try:
            self._redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET error: {e}")
            return self._fallback_set(key, serialized, ttl)

    def delete(self, key: str) -> bool:
        """Delete a key."""
        if self._using_fallback:
            self._fallback.pop(key, None)
            return True
        try:
            self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE error: {e}")
            self._fallback.pop(key, None)
            return True

    def invalidate_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern. Returns count deleted."""
        if self._using_fallback:
            import fnmatch
            keys = [k for k in list(self._fallback.keys()) if fnmatch.fnmatch(k, pattern)]
            for k in keys:
                del self._fallback[k]
            return len(keys)
        try:
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    self._redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            return deleted
        except Exception as e:
            logger.warning(f"Redis SCAN/DELETE error: {e}")
            return 0

    def incr(self, key: str, ttl: int = 60) -> int:
        """Increment a counter (for rate limiting). Sets TTL on first call."""
        if self._using_fallback:
            entry = self._fallback.get(key)
            now = time.time()
            if entry and now < entry[1]:
                count = int(entry[0]) + 1
                self._fallback[key] = (str(count), entry[1])
                return count
            else:
                self._fallback[key] = ("1", now + ttl)
                return 1
        try:
            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.ttl(key)
            result = pipe.execute()
            count = result[0]
            current_ttl = result[1]
            if current_ttl == -1:  # No TTL set yet
                self._redis.expire(key, ttl)
            return count
        except Exception as e:
            logger.warning(f"Redis INCR error: {e}")
            return 1  # Allow on error

    # --- Fallback methods ---

    def _fallback_get(self, key: str) -> Optional[Any]:
        entry = self._fallback.get(key)
        if entry is None:
            return None
        value_json, expire_at = entry
        if time.time() >= expire_at:
            del self._fallback[key]
            return None
        return json.loads(value_json)

    def _fallback_set(self, key: str, serialized: str, ttl: int) -> bool:
        self._fallback[key] = (serialized, time.time() + ttl)
        return True


# --- Singleton instance ---
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        from app.config import settings
        _cache_instance = RedisCache(settings.REDIS_URL)
    return _cache_instance


cache_service = get_cache()
