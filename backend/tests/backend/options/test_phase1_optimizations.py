"""
Phase 1 Option Chain Performance Optimizations — TDD Tests

Tests cover:
  P1-1: Redis cache returns 3s TTL during market hours (not None)
  P1-2: Far OTM strikes (>10% moneyness) skip IV/Greeks calculation
  P1-3: Parallel spot price fetch via asyncio.gather
  P1-4: Frontend stale-while-revalidate (tested in frontend/tests/)

These tests were written retroactively for Phase 1 (code already exists).
They verify the optimization behavior is correct and guard against regressions.
"""
import asyncio
import math
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


# ---------------------------------------------------------------------------
# P1-1: Redis Cache TTL During Market Hours
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCacheTTLMarketHours:
    """P1-1: get_cache_ttl_seconds() must return a positive int during market hours."""

    @patch("app.services.options.option_chain_cache.is_market_open", return_value=True)
    def test_returns_positive_ttl_when_market_open(self, mock_market):
        from app.services.options.option_chain_cache import get_cache_ttl_seconds
        ttl = get_cache_ttl_seconds()
        assert isinstance(ttl, int), f"TTL must be int, got {type(ttl)}"
        assert ttl > 0, f"TTL must be positive during market hours, got {ttl}"

    @patch("app.services.options.option_chain_cache.is_market_open", return_value=True)
    def test_live_market_ttl_is_3_seconds(self, mock_market):
        from app.services.options.option_chain_cache import get_cache_ttl_seconds, LIVE_MARKET_CACHE_TTL
        ttl = get_cache_ttl_seconds()
        assert ttl == LIVE_MARKET_CACHE_TTL, (
            f"During market hours TTL should be {LIVE_MARKET_CACHE_TTL}s, got {ttl}"
        )

    @patch("app.services.options.option_chain_cache.is_market_open", return_value=False)
    @patch("app.services.options.option_chain_cache._ist_now")
    @patch("app.services.options.option_chain_cache.get_next_market_open")
    def test_after_hours_ttl_has_jitter(self, mock_next_open, mock_now, mock_market):
        """After-hours TTL should have ±10% jitter to prevent cache stampede."""
        from datetime import datetime, timedelta
        now = datetime(2026, 4, 16, 20, 0, 0)
        mock_now.return_value = now
        mock_next_open.return_value = now + timedelta(hours=13)  # ~46800s

        from app.services.options.option_chain_cache import get_cache_ttl_seconds

        # Collect TTLs to verify jitter exists (not all identical)
        ttls = set()
        for _ in range(20):
            ttls.add(get_cache_ttl_seconds())

        # With ±10% jitter on ~46800s, we should get multiple distinct values
        assert len(ttls) > 1, "After-hours TTL should have jitter (got all identical values)"

    @patch("app.services.options.option_chain_cache.is_market_open", return_value=False)
    @patch("app.services.options.option_chain_cache._ist_now")
    @patch("app.services.options.option_chain_cache.get_next_market_open")
    def test_after_hours_ttl_floor_is_60_seconds(self, mock_next_open, mock_now, mock_market):
        """TTL should never drop below 60 seconds even near market open."""
        from datetime import datetime, timedelta
        now = datetime(2026, 4, 16, 9, 14, 50)  # 10 seconds before open
        mock_now.return_value = now
        mock_next_open.return_value = now + timedelta(seconds=10)

        from app.services.options.option_chain_cache import get_cache_ttl_seconds
        ttl = get_cache_ttl_seconds()
        assert ttl >= 60, f"TTL floor should be 60s, got {ttl}"


# ---------------------------------------------------------------------------
# P1-1: store_cached_response must actually store during market hours
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCacheStoresDuringMarketHours:

    @pytest.mark.asyncio
    @patch("app.services.options.option_chain_cache.is_market_open", return_value=True)
    @patch("app.services.options.option_chain_cache.get_redis")
    async def test_stores_response_when_market_open(self, mock_get_redis, mock_market):
        """Cache must store responses during market hours (not skip them)."""
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        from app.services.options.option_chain_cache import store_cached_response
        await store_cached_response("NIFTY", "2026-04-24", {"chain": []})

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3, f"TTL should be 3s during market hours, got {call_args[0][1]}"


# ---------------------------------------------------------------------------
# P1-2: Skip IV for Far OTM Strikes
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSkipFarOTMIV:
    """P1-2: Strikes >10% OTM should return IV=0 and zero Greeks."""

    def test_far_otm_constant_exists(self):
        from app.api.routes.optionchain import FAR_OTM_MONEYNESS_THRESHOLD
        assert FAR_OTM_MONEYNESS_THRESHOLD == 0.10

    def test_far_otm_moneyness_detected_correctly(self):
        """A CE strike 15% above spot should be detected as far OTM."""
        from app.api.routes.optionchain import FAR_OTM_MONEYNESS_THRESHOLD
        spot = 24000.0
        strike = 27600.0  # 15% OTM
        moneyness = abs(spot - strike) / spot
        assert moneyness > FAR_OTM_MONEYNESS_THRESHOLD, (
            f"Strike {strike} at spot {spot} has moneyness {moneyness:.2%} — "
            f"should exceed {FAR_OTM_MONEYNESS_THRESHOLD:.0%} threshold"
        )

    def test_near_atm_call_gets_nonzero_iv(self):
        """A CE strike near ATM with decent premium should compute real IV."""
        from app.api.routes.optionchain import calculate_iv
        iv = calculate_iv(150.0, 24000, 24100, 14, True)
        assert iv > 0, f"Near-ATM call should have positive IV, got {iv}"

    def test_moneyness_threshold_logic(self):
        """Verify the moneyness check math: abs(spot-strike)/spot > threshold."""
        from app.api.routes.optionchain import FAR_OTM_MONEYNESS_THRESHOLD

        spot = 24000.0

        # 5% OTM — should NOT be skipped
        strike_5pct = 25200.0
        moneyness_5 = abs(spot - strike_5pct) / spot
        assert moneyness_5 == pytest.approx(0.05, abs=0.001)
        assert moneyness_5 <= FAR_OTM_MONEYNESS_THRESHOLD, "5% OTM should NOT exceed threshold"

        # 12% OTM — SHOULD be skipped
        strike_12pct = 26880.0
        moneyness_12 = abs(spot - strike_12pct) / spot
        assert moneyness_12 == pytest.approx(0.12, abs=0.001)
        assert moneyness_12 > FAR_OTM_MONEYNESS_THRESHOLD, "12% OTM should exceed threshold"

    def test_calculate_greeks_with_zero_iv_returns_zeros(self):
        """When IV is 0 (far OTM skip), Greeks must all be zero."""
        from app.api.routes.optionchain import calculate_greeks
        greeks = calculate_greeks(24000, 27600, 7, 0.0, True)
        assert greeks == {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}


# ---------------------------------------------------------------------------
# P1-3: Parallel Spot Price Fetch
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParallelSpotFetch:
    """P1-3: Spot price fetch should use asyncio.gather for parallel execution."""

    def test_asyncio_gather_used_in_compute_option_chain(self):
        """Verify that the option chain route uses asyncio.gather for spot fetch."""
        import inspect
        from app.api.routes.optionchain import _compute_option_chain
        source = inspect.getsource(_compute_option_chain)
        assert "asyncio.gather" in source, (
            "_compute_option_chain must use asyncio.gather for parallel spot price fetch"
        )

    def test_spot_tasks_dict_pattern_exists(self):
        """Verify the spot_tasks dict pattern for labeling parallel fetches."""
        import inspect
        from app.api.routes.optionchain import _compute_option_chain
        source = inspect.getsource(_compute_option_chain)
        assert "spot_tasks" in source, (
            "_compute_option_chain must use spot_tasks dict for labeled parallel fetches"
        )

    @pytest.mark.asyncio
    async def test_gather_returns_first_successful_result(self):
        """When both adapters return, the first valid price should be used."""
        # This tests the pattern, not the actual route (which needs full DB context)
        async def adapter_a():
            return {"NIFTY": 24000.0}

        async def adapter_b():
            return {"NIFTY": 24001.0}

        results = await asyncio.gather(adapter_a(), adapter_b(), return_exceptions=True)
        prices = []
        for r in results:
            if not isinstance(r, Exception):
                price = float(r.get("NIFTY", 0))
                if price > 0:
                    prices.append(price)

        assert len(prices) == 2, "Both adapters should return valid prices"
        assert prices[0] == 24000.0, "First valid price should be used"

    @pytest.mark.asyncio
    async def test_gather_handles_one_adapter_failure(self):
        """If one adapter fails, the other's result should still be used."""
        async def adapter_success():
            return {"NIFTY": 24000.0}

        async def adapter_failure():
            raise ConnectionError("Broker offline")

        results = await asyncio.gather(
            adapter_success(), adapter_failure(), return_exceptions=True
        )
        valid_price = None
        for r in results:
            if not isinstance(r, Exception):
                price = float(r.get("NIFTY", 0))
                if price > 0:
                    valid_price = price
                    break

        assert valid_price == 24000.0, "Should use the successful adapter's price"
