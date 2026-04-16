"""
Tests for Option Chain Performance Optimization components.

Task 8: Unit tests for get_next_market_open() and cache TTL
Task 9: Integration tests for cache hit/miss + coalescing
"""
import asyncio
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.utils.market_hours import (
    get_next_market_open,
    IST,
)


# ---------------------------------------------------------------------------
# Task 8: get_next_market_open() unit tests
# ---------------------------------------------------------------------------

class TestGetNextMarketOpen:
    """Test get_next_market_open() edge cases."""

    def test_friday_evening_returns_monday(self):
        # Friday 2026-04-17 at 18:00 IST → Monday 2026-04-20 09:15
        friday_evening = datetime(2026, 4, 17, 18, 0, tzinfo=IST)
        result = get_next_market_open(friday_evening)
        assert result.weekday() == 0  # Monday
        assert result.day == 20
        assert result.hour == 9
        assert result.minute == 15

    def test_saturday_returns_monday(self):
        # Saturday 2026-04-18 10:00 IST → Monday 2026-04-20 09:15
        saturday = datetime(2026, 4, 18, 10, 0, tzinfo=IST)
        result = get_next_market_open(saturday)
        assert result.weekday() == 0
        assert result.day == 20

    def test_sunday_returns_monday(self):
        sunday = datetime(2026, 4, 19, 14, 0, tzinfo=IST)
        result = get_next_market_open(sunday)
        assert result.weekday() == 0
        assert result.day == 20

    def test_before_market_open_returns_same_day(self):
        # Monday 2026-04-20 08:00 IST → same day 09:15
        monday_early = datetime(2026, 4, 20, 8, 0, tzinfo=IST)
        result = get_next_market_open(monday_early)
        assert result.day == 20
        assert result.hour == 9
        assert result.minute == 15

    def test_during_market_returns_next_day(self):
        # Monday 2026-04-20 12:00 IST → Tuesday 2026-04-21 09:15
        monday_midday = datetime(2026, 4, 20, 12, 0, tzinfo=IST)
        result = get_next_market_open(monday_midday)
        # April 21 is a holiday (Ram Navami) — should skip to April 22
        assert result.day == 22
        assert result.hour == 9
        assert result.minute == 15

    def test_holiday_skipped(self):
        # 2026-01-26 is Republic Day (holiday)
        # Jan 25 (Sunday) — next open should skip both Sunday and holiday
        jan_25_sunday = datetime(2026, 1, 25, 10, 0, tzinfo=IST)
        result = get_next_market_open(jan_25_sunday)
        # Jan 26 = holiday, Jan 27 = Tuesday (first trading day)
        assert result.day == 27
        assert result.month == 1

    def test_returns_ist_timezone(self):
        now = datetime(2026, 4, 20, 8, 0, tzinfo=IST)
        result = get_next_market_open(now)
        assert result.tzinfo == IST

    def test_long_weekend_with_holiday(self):
        # 2026-08-15 (Saturday) is Independence Day — but it's already a weekend
        # Friday 2026-08-14 at 16:00 → Monday 2026-08-17 09:15
        friday = datetime(2026, 8, 14, 16, 0, tzinfo=IST)
        result = get_next_market_open(friday)
        assert result.day == 17
        assert result.weekday() == 0


# ---------------------------------------------------------------------------
# Task 8: Cache TTL unit tests
# ---------------------------------------------------------------------------

class TestCacheTTL:
    """Test get_cache_ttl_seconds() behavior."""

    @patch("app.services.options.option_chain_cache.is_market_open", return_value=True)
    def test_returns_none_during_market_hours(self, mock_open):
        from app.services.options.option_chain_cache import get_cache_ttl_seconds
        assert get_cache_ttl_seconds() is None

    @patch("app.services.options.option_chain_cache.is_market_open", return_value=False)
    @patch("app.services.options.option_chain_cache._ist_now")
    @patch("app.services.options.option_chain_cache.get_next_market_open")
    def test_returns_seconds_until_next_open(self, mock_next_open, mock_now, mock_open):
        from app.services.options.option_chain_cache import get_cache_ttl_seconds
        now = datetime(2026, 4, 17, 18, 0, tzinfo=IST)
        next_open = datetime(2026, 4, 20, 9, 15, tzinfo=IST)
        mock_now.return_value = now
        mock_next_open.return_value = next_open

        ttl = get_cache_ttl_seconds()
        expected = int((next_open - now).total_seconds())
        assert ttl == expected

    @patch("app.services.options.option_chain_cache.is_market_open", return_value=False)
    @patch("app.services.options.option_chain_cache._ist_now")
    @patch("app.services.options.option_chain_cache.get_next_market_open")
    def test_minimum_ttl_60_seconds(self, mock_next_open, mock_now, mock_open):
        from app.services.options.option_chain_cache import get_cache_ttl_seconds
        now = datetime(2026, 4, 20, 9, 14, 50, tzinfo=IST)
        next_open = datetime(2026, 4, 20, 9, 15, tzinfo=IST)
        mock_now.return_value = now
        mock_next_open.return_value = next_open

        ttl = get_cache_ttl_seconds()
        assert ttl == 60  # Floor at 60s


# ---------------------------------------------------------------------------
# Task 9: Request coalescing integration tests
# ---------------------------------------------------------------------------

class TestRequestCoalescing:
    """Test get_or_compute() coalescing behavior."""

    @pytest.mark.asyncio
    async def test_cache_miss_calls_compute(self):
        from app.services.options.option_chain_cache import get_or_compute, _inflight

        mock_result = {"chain": [{"strike": 25000}]}

        async def compute():
            return mock_result

        with patch(
            "app.services.options.option_chain_cache.get_cached_response",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.options.option_chain_cache.store_cached_response",
            new_callable=AsyncMock,
        ) as mock_store:
            result = await get_or_compute("NIFTY", "2026-04-30", compute)
            assert result == mock_result
            mock_store.assert_called_once_with("NIFTY", "2026-04-30", mock_result)

    @pytest.mark.asyncio
    async def test_cache_hit_skips_compute(self):
        from app.services.options.option_chain_cache import get_or_compute

        cached_data = {"chain": [{"strike": 25000}], "cached": True}
        compute_called = False

        async def compute():
            nonlocal compute_called
            compute_called = True
            return {"should": "not be returned"}

        with patch(
            "app.services.options.option_chain_cache.get_cached_response",
            new_callable=AsyncMock,
            return_value=cached_data,
        ):
            result = await get_or_compute("NIFTY", "2026-04-30", compute)
            assert result == cached_data
            assert not compute_called

    @pytest.mark.asyncio
    async def test_concurrent_requests_coalesce(self):
        """Multiple concurrent requests for same key should result in only one compute call."""
        from app.services.options.option_chain_cache import get_or_compute, _inflight

        # Clear any leftover state
        _inflight.clear()

        compute_count = 0
        mock_result = {"chain": [{"strike": 25000}]}

        async def slow_compute():
            nonlocal compute_count
            compute_count += 1
            await asyncio.sleep(0.1)  # Simulate slow computation
            return mock_result

        with patch(
            "app.services.options.option_chain_cache.get_cached_response",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.options.option_chain_cache.store_cached_response",
            new_callable=AsyncMock,
        ):
            # Fire 5 concurrent requests for the same key
            results = await asyncio.gather(
                get_or_compute("NIFTY", "2026-05-01", slow_compute),
                get_or_compute("NIFTY", "2026-05-01", slow_compute),
                get_or_compute("NIFTY", "2026-05-01", slow_compute),
                get_or_compute("NIFTY", "2026-05-01", slow_compute),
                get_or_compute("NIFTY", "2026-05-01", slow_compute),
            )

            # All should get the same result
            for r in results:
                assert r == mock_result

            # But compute should only have been called ONCE
            assert compute_count == 1

    @pytest.mark.asyncio
    async def test_different_keys_compute_independently(self):
        from app.services.options.option_chain_cache import get_or_compute, _inflight
        _inflight.clear()

        compute_count = 0

        async def compute():
            nonlocal compute_count
            compute_count += 1
            return {"count": compute_count}

        with patch(
            "app.services.options.option_chain_cache.get_cached_response",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.options.option_chain_cache.store_cached_response",
            new_callable=AsyncMock,
        ):
            r1 = await get_or_compute("NIFTY", "2026-04-30", compute)
            r2 = await get_or_compute("BANKNIFTY", "2026-04-30", compute)

            assert compute_count == 2
            assert r1 != r2

    @pytest.mark.asyncio
    async def test_compute_exception_propagates_and_cleans_up(self):
        from app.services.options.option_chain_cache import get_or_compute, _inflight
        _inflight.clear()

        async def failing_compute():
            raise ValueError("Broker API failed")

        with patch(
            "app.services.options.option_chain_cache.get_cached_response",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.services.options.option_chain_cache.store_cached_response",
            new_callable=AsyncMock,
        ):
            with pytest.raises(ValueError, match="Broker API failed"):
                await get_or_compute("NIFTY", "2026-04-30", failing_compute)

            # Inflight should be cleaned up
            assert "optionchain:NIFTY:2026-04-30" not in _inflight


# ---------------------------------------------------------------------------
# Task 9: Redis cache read/write tests (mocked Redis)
# ---------------------------------------------------------------------------

class TestRedisCache:
    """Test Redis cache operations with mocked Redis client."""

    @pytest.mark.asyncio
    async def test_get_cached_response_hit(self):
        from app.services.options.option_chain_cache import get_cached_response

        cached = json.dumps({"chain": [{"strike": 25000}]})
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached)

        with patch(
            "app.services.options.option_chain_cache.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await get_cached_response("NIFTY", "2026-04-30")
            assert result == {"chain": [{"strike": 25000}]}

    @pytest.mark.asyncio
    async def test_get_cached_response_miss(self):
        from app.services.options.option_chain_cache import get_cached_response

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch(
            "app.services.options.option_chain_cache.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            result = await get_cached_response("NIFTY", "2026-04-30")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_response_redis_failure(self):
        """Redis failure should return None, not raise."""
        from app.services.options.option_chain_cache import get_cached_response

        with patch(
            "app.services.options.option_chain_cache.get_redis",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ):
            result = await get_cached_response("NIFTY", "2026-04-30")
            assert result is None

    @pytest.mark.asyncio
    async def test_store_skipped_during_market_hours(self):
        from app.services.options.option_chain_cache import store_cached_response

        with patch(
            "app.services.options.option_chain_cache.get_cache_ttl_seconds",
            return_value=None,
        ), patch(
            "app.services.options.option_chain_cache.get_redis",
            new_callable=AsyncMock,
        ) as mock_get_redis:
            await store_cached_response("NIFTY", "2026-04-30", {"data": True})
            mock_get_redis.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_writes_with_ttl(self):
        from app.services.options.option_chain_cache import store_cached_response

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        with patch(
            "app.services.options.option_chain_cache.get_cache_ttl_seconds",
            return_value=3600,
        ), patch(
            "app.services.options.option_chain_cache.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            await store_cached_response("NIFTY", "2026-04-30", {"chain": []})
            mock_redis.setex.assert_called_once()
            args = mock_redis.setex.call_args
            assert args[0][0] == "optionchain:NIFTY:2026-04-30"
            assert args[0][1] == 3600


# ---------------------------------------------------------------------------
# Task 9: Platform adapter singleton tests
# ---------------------------------------------------------------------------

class TestPlatformAdapterSingleton:
    """Test get_cached_platform_adapter() caching behavior."""

    @pytest.mark.asyncio
    async def test_returns_cached_adapter_within_ttl(self):
        import app.services.options.option_chain_cache as cache_mod

        mock_adapter = MagicMock()
        mock_adapter.is_connected = True

        # Seed the cache
        import time
        cache_mod._cached_adapter = (mock_adapter, time.time())

        with patch(
            "app.services.options.option_chain_cache.get_platform_market_data_adapter",
            new_callable=AsyncMock,
        ) as mock_factory:
            result = await cache_mod.get_cached_platform_adapter(MagicMock())
            assert result is mock_adapter
            mock_factory.assert_not_called()

        # Clean up
        cache_mod._cached_adapter = None

    @pytest.mark.asyncio
    async def test_refreshes_stale_adapter(self):
        import app.services.options.option_chain_cache as cache_mod
        import time

        old_adapter = MagicMock()
        old_adapter.is_connected = True
        # Set created_at to 2 hours ago (beyond 1-hour TTL)
        cache_mod._cached_adapter = (old_adapter, time.time() - 7200)

        new_adapter = MagicMock()
        new_adapter.is_connected = True

        with patch(
            "app.services.options.option_chain_cache.get_platform_market_data_adapter",
            new_callable=AsyncMock,
            return_value=new_adapter,
        ):
            result = await cache_mod.get_cached_platform_adapter(MagicMock())
            assert result is new_adapter

        cache_mod._cached_adapter = None

    @pytest.mark.asyncio
    async def test_refreshes_disconnected_adapter(self):
        import app.services.options.option_chain_cache as cache_mod
        import time

        disconnected = MagicMock()
        disconnected.is_connected = False
        cache_mod._cached_adapter = (disconnected, time.time())

        new_adapter = MagicMock()
        new_adapter.is_connected = True

        with patch(
            "app.services.options.option_chain_cache.get_platform_market_data_adapter",
            new_callable=AsyncMock,
            return_value=new_adapter,
        ):
            result = await cache_mod.get_cached_platform_adapter(MagicMock())
            assert result is new_adapter

        cache_mod._cached_adapter = None
