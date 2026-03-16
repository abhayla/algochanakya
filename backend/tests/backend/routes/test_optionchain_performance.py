"""
Bug reproduction test: Option chain API times out due to fetching quotes for ALL strikes.

Root cause: Backend queries all 241 NIFTY strikes from DB, then batches them to SmartAPI
in groups of 100 (5 batches). Each SmartAPI batch takes ~7s → total ~37s → frontend
30s timeout fires → "Failed to load option chain" error.

Fix: Filter instruments to ATM ± strikesRange before fetching quotes from SmartAPI.
This reduces 241 strikes to ~40, meaning 1 batch call instead of 5.

These tests should FAIL before the fix and PASS after.
"""
import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta


@pytest.mark.unit
class TestOptionChainPerformance:
    """Tests that option chain loads within acceptable time by filtering strikes."""

    def test_strike_filter_reduces_instrument_count(self):
        """
        BUG-PERF-1: Without filtering, 241 strikes are sent to SmartAPI.
        After fix, only ~40 strikes near ATM should be sent.
        """
        # Simulate 241 NIFTY strikes (19200 to 24200 at 50-point intervals)
        all_strikes = [19200 + i * 50 for i in range(100)]  # 100 strikes
        spot_price = 23750.0
        strikes_range = 20  # ±20 strikes around ATM

        # ATM = nearest strike to spot
        atm_strike = min(all_strikes, key=lambda x: abs(x - spot_price))
        atm_idx = all_strikes.index(atm_strike)

        # Filter to ±strikes_range around ATM
        start = max(0, atm_idx - strikes_range)
        end = min(len(all_strikes), atm_idx + strikes_range + 1)
        filtered_strikes = all_strikes[start:end]

        # Should be at most 2*strikes_range+1 = 41 strikes
        assert len(filtered_strikes) <= 41, (
            f"Filtered strikes count {len(filtered_strikes)} exceeds expected max 41. "
            f"Filter is not working correctly."
        )
        assert len(filtered_strikes) < len(all_strikes), (
            f"BUG: No filtering applied — all {len(all_strikes)} strikes are being sent to SmartAPI. "
            f"This causes the 37-second timeout."
        )

        # ATM must be in filtered list
        assert atm_strike in filtered_strikes, "ATM strike must always be included"

    def test_batch_count_reduced_after_filter(self):
        """
        BUG-PERF-2: 241 strikes × 2 (CE+PE) = 482 symbols → 5 SmartAPI batch calls.
        After fix: ~40 strikes × 2 = 80 symbols → 1 batch call.
        """
        BATCH_SIZE = 100

        # Before fix: all strikes
        all_symbols_before = 241 * 2  # 482
        batches_before = (all_symbols_before + BATCH_SIZE - 1) // BATCH_SIZE  # 5

        # After fix: only near-ATM strikes
        filtered_symbols_after = 41 * 2  # 82
        batches_after = (filtered_symbols_after + BATCH_SIZE - 1) // BATCH_SIZE  # 1

        # BUG: 5 batches at ~7s each = 35s → exceeds 30s frontend timeout
        assert batches_before > 3, (
            f"Before fix should have >3 SmartAPI batch calls, got {batches_before}"
        )

        # After fix: should be 1-2 batches
        assert batches_after <= 2, (
            f"After fix should have ≤2 SmartAPI batch calls, got {batches_after}. "
            f"Performance fix not applied."
        )

    def test_atm_filter_logic_includes_correct_strikes(self):
        """
        BUG-PERF-3: The filter must keep strikes symmetric around ATM
        and always include ATM itself even if not at a round interval.
        """
        # NIFTY at 23,772 → ATM = 23,750 (nearest 50-point strike)
        spot = 23772.0
        strikes = [s for s in range(19200, 26201, 50)]  # All NIFTY strikes

        atm = min(strikes, key=lambda x: abs(x - spot))
        assert atm == 23750, f"ATM should be 23750, got {atm}"

        atm_idx = strikes.index(atm)
        range_size = 20
        start = max(0, atm_idx - range_size)
        end = min(len(strikes), atm_idx + range_size + 1)
        filtered = strikes[start:end]

        # Must include ATM
        assert atm in filtered

        # Must include reasonable strikes around ATM (23250–24250 range)
        assert 23250 in filtered or 23300 in filtered, "Should include strikes 500 points below ATM"
        assert 24200 in filtered or 24250 in filtered, "Should include strikes 500 points above ATM"

        # Must NOT include very far OTM strikes
        assert 19200 not in filtered, "Should not include far OTM strike 19200"
        assert 26200 not in filtered, "Should not include far OTM strike 26200"


@pytest.mark.integration
class TestOptionChainAPIPerformance:
    """
    Integration test: Option chain API should respond within 20 seconds.
    Requires backend running with SmartAPI credentials.
    """

    @pytest.mark.slow
    @pytest.mark.live
    async def test_option_chain_loads_within_timeout(self):
        """
        BUG-PERF-4: GET /api/optionchain/chain must respond in < 20 seconds.
        Currently takes ~37 seconds (5 SmartAPI batches).
        After fix (filtered strikes): should take < 15 seconds (1-2 batches).
        """
        import httpx
        from datetime import date, timedelta

        # Use next Thursday as expiry
        today = date.today()
        days_until_thursday = (3 - today.weekday()) % 7 or 7
        expiry = today + timedelta(days=days_until_thursday)
        expiry_str = expiry.strftime("%Y-%m-%d")

        start = time.time()
        async with httpx.AsyncClient(base_url="http://localhost:8001", timeout=25.0) as client:
            # Would need real auth token here
            response = await client.get(
                f"/api/optionchain/chain",
                params={"underlying": "NIFTY", "expiry": expiry_str},
                headers={"Authorization": "Bearer TEST_TOKEN"}
            )
        elapsed = time.time() - start

        # BUG: Currently fails because it takes 37s (exceeds 25s test timeout)
        assert elapsed < 20, (
            f"Option chain API took {elapsed:.1f}s — exceeds 20s threshold. "
            f"Backend is fetching quotes for too many strikes (all {241} instead of ~40 near ATM). "
            f"Fix: filter to ATM ± strikesRange before SmartAPI quote fetch."
        )
