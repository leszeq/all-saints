"""Redis cache for public calendar responses.

Cache failures are deliberately fail-open: a Redis outage must not make the
calendar API unavailable because the database remains the source of truth.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from loguru import logger

from src.core.config import settings
from src.infrastructure.cache.redis_client import RedisClient


class CalendarResponseCache:
    """Cache serialized public day and month responses in Redis."""

    NAMESPACE = "saints:calendar"
    INVALIDATION_BATCH_SIZE = 100

    def __init__(
        self,
        redis: RedisClient | None,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        self._redis = redis
        self._ttl_seconds = (
            ttl_seconds if ttl_seconds is not None else settings.CALENDAR_CACHE_TTL_SECONDS
        )

    @classmethod
    def day_key(
        cls,
        value: date,
        calendar_code: str,
        include_universal: bool,
        include_martyrology: bool,
    ) -> str:
        """Build a key scoped to every input that changes a day response."""
        return cls._key(
            "day",
            value.isoformat(),
            calendar_code,
            include_universal,
            include_martyrology,
        )

    @classmethod
    def month_key(
        cls,
        year: int,
        month: int,
        calendar_code: str,
        include_universal: bool,
        include_martyrology: bool,
    ) -> str:
        """Build a key scoped to every input that changes a month response."""
        return cls._key(
            "month",
            f"{year:04d}-{month:02d}",
            calendar_code,
            include_universal,
            include_martyrology,
        )

    @classmethod
    def _key(
        cls,
        kind: str,
        period: str,
        calendar_code: str,
        include_universal: bool,
        include_martyrology: bool,
    ) -> str:
        return (
            f"{cls.NAMESPACE}:v{settings.CALENDAR_DATA_VERSION}:{kind}:{period}:"
            f"{calendar_code}:u{int(include_universal)}:m{int(include_martyrology)}"
        )

    async def get(self, key: str) -> dict[str, Any] | None:
        """Read and decode a cached JSON object, returning a miss on failure."""
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(key)
            if raw is None:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else None
        except Exception as exc:
            logger.debug("Calendar cache read failed", key=key, error=str(exc))
            return None

    async def set(self, key: str, payload: dict[str, Any]) -> None:
        """Encode and store a response; silently skip writes on cache failure."""
        if self._redis is None:
            return
        try:
            await self._redis.setex(
                key,
                self._ttl_seconds,
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            )
        except Exception as exc:
            logger.debug("Calendar cache write failed", key=key, error=str(exc))

    async def invalidate_all(self) -> int:
        """Remove every cached public calendar response.

        Publication can change a person's name, image or featured flag in any
        day/month response, so there is no safe single-key invalidation. Redis
        failures remain fail-open: the database is authoritative and the
        short TTL still bounds stale data.
        """
        if self._redis is None:
            return 0
        try:
            keys: list[str] = []
            async for key in self._redis.scan_iter(match=f"{self.NAMESPACE}:*"):
                keys.append(key)

            deleted = 0
            for start in range(0, len(keys), self.INVALIDATION_BATCH_SIZE):
                batch = keys[start : start + self.INVALIDATION_BATCH_SIZE]
                if batch:
                    deleted += int(await self._redis.delete(*batch))
            return deleted
        except Exception as exc:
            logger.debug("Calendar cache invalidation failed", error=str(exc))
            return 0
