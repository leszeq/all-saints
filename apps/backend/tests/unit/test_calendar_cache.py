"""Unit tests for public calendar response cache scoping and failure handling."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.cache.calendar_cache import CalendarResponseCache


def test_keys_are_scoped_by_version_period_calendar_and_layers() -> None:
    cache = CalendarResponseCache(None, ttl_seconds=60)

    day_key = cache.day_key(date(2026, 8, 23), "roman_pl", True, True)
    other_calendar_key = cache.day_key(date(2026, 8, 23), "roman_martyrology", True, True)
    other_layers_key = cache.day_key(date(2026, 8, 23), "roman_pl", False, True)
    month_key = cache.month_key(2026, 8, "roman_pl", True, True)

    assert ":v" in day_key
    assert "day:2026-08-23:roman_pl:u1:m1" in day_key
    assert other_calendar_key != day_key
    assert other_layers_key != day_key
    assert month_key != day_key
    assert "month:2026-08:roman_pl:u1:m1" in month_key


@pytest.mark.asyncio
async def test_cache_round_trip_serializes_json_with_ttl() -> None:
    redis = MagicMock()
    redis.get = AsyncMock(return_value='{"date":"2026-08-23","total":1}')
    redis.setex = AsyncMock()
    cache = CalendarResponseCache(redis, ttl_seconds=42)

    assert await cache.get("calendar-key") == {"date": "2026-08-23", "total": 1}
    await cache.set("calendar-key", {"date": "2026-08-23", "total": 1})

    redis.setex.assert_awaited_once()
    key, ttl, raw_payload = redis.setex.call_args.args
    assert (key, ttl) == ("calendar-key", 42)
    assert json.loads(raw_payload) == {"date": "2026-08-23", "total": 1}


@pytest.mark.asyncio
async def test_cache_fails_open_when_redis_is_unavailable() -> None:
    redis = MagicMock()
    redis.get = AsyncMock(side_effect=ConnectionError("redis unavailable"))
    redis.setex = AsyncMock(side_effect=ConnectionError("redis unavailable"))
    cache = CalendarResponseCache(redis)

    assert await cache.get("calendar-key") is None
    await cache.set("calendar-key", {"total": 0})


@pytest.mark.asyncio
async def test_invalidate_all_deletes_only_calendar_namespace_in_batches() -> None:
    redis = MagicMock()

    async def scan_iter(*, match: str):
        assert match == "saints:calendar:*"
        for key in ("saints:calendar:v1:day:a", "saints:calendar:v1:month:b"):
            yield key

    redis.scan_iter = scan_iter
    redis.delete = AsyncMock(return_value=2)
    cache = CalendarResponseCache(redis)

    assert await cache.invalidate_all() == 2
    redis.delete.assert_awaited_once_with(
        "saints:calendar:v1:day:a",
        "saints:calendar:v1:month:b",
    )


@pytest.mark.asyncio
async def test_invalidate_all_fails_open_when_redis_is_unavailable() -> None:
    redis = MagicMock()

    async def scan_iter(*, match: str):
        raise ConnectionError("redis unavailable")
        yield match  # pragma: no cover - keeps this an async generator

    redis.scan_iter = scan_iter
    cache = CalendarResponseCache(redis)

    assert await cache.invalidate_all() == 0
