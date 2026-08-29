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
import secrets
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import redis.asyncio as aioredis
from loguru import logger
from redis.asyncio.connection import Connection, ConnectionPool

if TYPE_CHECKING:
    from redis.asyncio import Redis

    type RedisClient = Redis[str]
else:
    from redis.asyncio import Redis as RedisClient

from src.core.config import settings

# ==============================================================================
# CONNECTION
# ==============================================================================


_redis_pool: ConnectionPool[Connection] | None = None


def get_redis_pool() -> ConnectionPool[Connection]:
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


def get_redis_client() -> RedisClient:
    """Return a Redis client using the singleton connection pool."""
    # types-redis cannot infer decode_responses=True from the connection pool.
    return cast(RedisClient, aioredis.Redis(connection_pool=get_redis_pool()))


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


async def get_redis() -> AsyncGenerator[RedisClient, None]:
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
        # Runtime Redis 5 exposes aclose(), while the pinned types-redis stubs
        # still model only the deprecated close() method.
        aclose = cast(
            Callable[[], Awaitable[None]],
            object.__getattribute__(client, "aclose"),
        )
        await aclose()


# ==============================================================================
# CACHE SERVICE
# ==============================================================================


class CacheService:
    """
    High-level cache service wrapping Redis operations.

    Provides typed get/set/delete with automatic JSON serialisation,
    namespaced keys, and configurable TTLs.
    """

    def __init__(self, redis: RedisClient) -> None:
        """Initialize with a Redis client."""
        self._redis = redis

    def _make_key(self, namespace: str, key: str) -> str:
        """Build a namespaced cache key."""
        return f"saints:{namespace}:{key}"

    async def get(self, namespace: str, key: str) -> Any | None:  # noqa: ANN401
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
        value: Any,  # noqa: ANN401 - cache accepts any JSON-serialisable value
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
        factory: Callable[[], Awaitable[Any]],
        ttl: int = settings.CACHE_TTL_DEFAULT,
    ) -> Any:  # noqa: ANN401 - factory result is intentionally generic
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


def make_cache_key_from_params(**kwargs: Any) -> str:  # noqa: ANN401
    """
    Generate a deterministic cache key from arbitrary parameters.

    Useful for caching query results with complex filter combinations.
    """
    serialised = json.dumps(kwargs, sort_keys=True, default=str)
    return hashlib.md5(serialised.encode()).hexdigest()  # noqa: S324


# ==============================================================================
# RATE LIMITER (Redis-backed sliding window)
# ==============================================================================


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    """Outcome of one rate-limit check."""

    allowed: bool
    remaining: int
    retry_after: int


class RateLimiter:
    """
    Redis-backed sliding window rate limiter.

    The full read/trim/write/count operation is executed atomically in Redis.
    Redis server time is used so that multiple API instances share one clock.
    """

    _SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local request_limit = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local member = ARGV[3]

local redis_time = redis.call('TIME')
local now_ms = redis_time[1] * 1000 + math.floor(redis_time[2] / 1000)
local window_start = now_ms - window_ms

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
redis.call('ZADD', key, now_ms, member)
local current_count = redis.call('ZCARD', key)
redis.call('PEXPIRE', key, window_ms)

local retry_after_ms = 0
if current_count > request_limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    if oldest[2] then
        retry_after_ms = math.max(0, tonumber(oldest[2]) + window_ms - now_ms)
    end
end

return {current_count, math.ceil(retry_after_ms / 1000)}
"""

    def __init__(self, redis: RedisClient) -> None:
        """Initialize with Redis client."""
        self._redis = redis

    async def check(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """Atomically record a request and return the current window state."""
        if limit < 1 or window_seconds < 1:
            raise ValueError("Rate limit and window must be positive")

        key = f"saints:ratelimit:{identifier}"
        result = await self._redis.eval(  # type: ignore[no-untyped-call]
            self._SLIDING_WINDOW_SCRIPT,
            1,
            key,
            limit,
            window_seconds * 1000,
            secrets.token_urlsafe(18),
        )
        current_count = int(result[0])
        retry_after = int(result[1])
        allowed = current_count <= limit

        return RateLimitResult(
            allowed=allowed,
            remaining=max(0, limit - current_count),
            retry_after=max(1, retry_after) if not allowed else retry_after,
        )

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
        result = await self.check(identifier, limit, window_seconds)
        return result.allowed, result.remaining
