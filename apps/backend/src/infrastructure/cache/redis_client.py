"""
Redis infrastructure – connection pooling and cache utilities.

Provides:
- Async Redis connection factory
- Cache decorator
- FastAPI dependency
- Pub/Sub support
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncGenerator, Callable
from functools import wraps
from typing import Any, TypeVar

import redis.asyncio as aioredis
from loguru import logger
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from src.core.config import settings


# ==============================================================================
# CONNECTION
# ==============================================================================


_redis_pool: ConnectionPool | None = None


def get_redis_pool() -> ConnectionPool:
    """Return singleton Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
            encoding="utf-8",
        )
    return _redis_pool


def get_redis_client() -> Redis:
    """Return a Redis client using the singleton connection pool."""
    return aioredis.Redis(connection_pool=get_redis_pool())


async def close_redis_pool() -> None:
    """Close Redis connection pool. Called on application shutdown."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("Redis connection pool closed")


async def check_redis_connection() -> bool:
    """Verify that Redis is reachable. Used for health checks."""
    try:
        client = get_redis_client()
        await client.ping()
        return True
    except Exception as exc:
        logger.error(f"Redis connection check failed: {exc}")
        return False


# ==============================================================================
# FASTAPI DEPENDENCY
# ==============================================================================


async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI dependency providing a Redis client.

    Usage::

        @router.get("/example")
        async def example(redis: Redis = Depends(get_redis)):
            await redis.set("key", "value")
    """
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


# ==============================================================================
# CACHE SERVICE
# ==============================================================================


class CacheService:
    """
    High-level cache service wrapping Redis operations.

    Provides typed get/set/delete with automatic JSON serialisation,
    namespaced keys, and configurable TTLs.
    """

    def __init__(self, redis: Redis) -> None:
        """Initialize with a Redis client."""
        self._redis = redis

    def _make_key(self, namespace: str, key: str) -> str:
        """Build a namespaced cache key."""
        return f"saints:{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Any | None:
        """
        Get a cached value.

        Returns:
            Deserialised value, or None if not found/expired.
        """
        cache_key = self._make_key(namespace, key)
        try:
            raw = await self._redis.get(cache_key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning(f"Cache GET failed for {cache_key}: {exc}")
            return None

    async def set(
        self,
        namespace: str,
        key: str,
        value: Any,
        ttl: int = settings.CACHE_TTL_DEFAULT,
    ) -> bool:
        """
        Set a cached value with expiry.

        Args:
            namespace: Logical grouping for the cache entry.
            key: Cache key within the namespace.
            value: Value to cache (must be JSON serialisable).
            ttl: Time-to-live in seconds.

        Returns:
            True if successfully cached.
        """
        cache_key = self._make_key(namespace, key)
        try:
            serialised = json.dumps(value, default=str, ensure_ascii=False)
            await self._redis.setex(cache_key, ttl, serialised)
            return True
        except Exception as exc:
            logger.warning(f"Cache SET failed for {cache_key}: {exc}")
            return False

    async def delete(self, namespace: str, key: str) -> int:
        """Delete a cached value. Returns number of keys deleted."""
        cache_key = self._make_key(namespace, key)
        try:
            return await self._redis.delete(cache_key)
        except Exception as exc:
            logger.warning(f"Cache DELETE failed for {cache_key}: {exc}")
            return 0

    async def invalidate_namespace(self, namespace: str) -> int:
        """
        Delete all cache entries in a namespace.

        Uses SCAN to avoid blocking Redis with a KEYS command.
        """
        pattern = f"saints:{namespace}:*"
        cursor = 0
        deleted = 0
        try:
            while True:
                cursor, keys = await self._redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += await self._redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning(f"Cache invalidation failed for namespace {namespace}: {exc}")
        return deleted

    async def exists(self, namespace: str, key: str) -> bool:
        """Check if a cache entry exists."""
        cache_key = self._make_key(namespace, key)
        try:
            return bool(await self._redis.exists(cache_key))
        except Exception:
            return False

    async def get_or_set(
        self,
        namespace: str,
        key: str,
        factory: Callable,
        ttl: int = settings.CACHE_TTL_DEFAULT,
    ) -> Any:
        """
        Get from cache or compute and store.

        Args:
            namespace: Cache namespace.
            key: Cache key.
            factory: Async callable that computes the value if not cached.
            ttl: Time-to-live in seconds.

        Returns:
            Cached or freshly computed value.
        """
        cached = await self.get(namespace, key)
        if cached is not None:
            return cached

        value = await factory()
        await self.set(namespace, key, value, ttl=ttl)
        return value


def make_cache_key_from_params(**kwargs: Any) -> str:
    """
    Generate a deterministic cache key from arbitrary parameters.

    Useful for caching query results with complex filter combinations.
    """
    serialised = json.dumps(kwargs, sort_keys=True, default=str)
    return hashlib.md5(serialised.encode()).hexdigest()  # noqa: S324


# ==============================================================================
# RATE LIMITER (Redis-backed sliding window)
# ==============================================================================


class RateLimiter:
    """
    Redis-backed sliding window rate limiter.

    Uses a sorted set to track request timestamps within a window.
    """

    def __init__(self, redis: Redis) -> None:
        """Initialize with Redis client."""
        self._redis = redis

    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if a request is within the rate limit.

        Args:
            identifier: Unique client identifier (e.g. IP or user ID).
            limit: Maximum number of requests allowed in the window.
            window_seconds: Time window in seconds.

        Returns:
            Tuple of (is_allowed, remaining_requests).
        """
        import time

        key = f"saints:ratelimit:{identifier}"
        now = time.time()
        window_start = now - window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        current_count = results[2]
        remaining = max(0, limit - current_count)
        is_allowed = current_count <= limit

        return is_allowed, remaining
