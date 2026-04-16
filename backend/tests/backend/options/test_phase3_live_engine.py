"""
Phase 3 Option Chain Performance — TDD RED Tests

Tests for the OptionChainLiveEngine: a ticker-fed in-memory cache that
maintains live option chain snapshots. Instead of fetching quotes from
SmartAPI on every request, the engine subscribes to TickerPool and
updates an in-memory dict with every tick. API responses are served
from memory in <10ms.

Architecture:
  TickerPool → OptionChainLiveEngine.on_tick() → in-memory snapshot
  API request → engine.get_snapshot(underlying, expiry) → dict (no I/O)

These tests MUST FAIL before implementation (module doesn't exist yet).
"""
import pytest
import sys
import os
import asyncio
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))


# ---------------------------------------------------------------------------
# Test that the live engine module exists
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestLiveEngineModuleExists:

    def test_module_importable(self):
        from app.services.options import option_chain_live_engine
        assert option_chain_live_engine is not None

    def test_has_engine_class(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine
        assert OptionChainLiveEngine is not None

    def test_engine_is_instantiable(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine
        engine = OptionChainLiveEngine()
        assert engine is not None


# ---------------------------------------------------------------------------
# Snapshot management
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSnapshotManagement:

    def test_subscribe_creates_snapshot_entry(self):
        """After subscribing to an underlying+expiry, a snapshot entry should exist."""
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine
        engine = OptionChainLiveEngine()
        engine.register_chain("NIFTY", "2026-04-24", _make_chain_tokens())
        assert engine.has_snapshot("NIFTY", "2026-04-24")

    def test_no_snapshot_before_registration(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine
        engine = OptionChainLiveEngine()
        assert not engine.has_snapshot("NIFTY", "2026-04-24")

    def test_get_snapshot_returns_none_before_registration(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine
        engine = OptionChainLiveEngine()
        assert engine.get_snapshot("NIFTY", "2026-04-24") is None

    def test_get_snapshot_returns_dict_after_registration(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine
        engine = OptionChainLiveEngine()
        engine.register_chain("NIFTY", "2026-04-24", _make_chain_tokens())
        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        assert isinstance(snap, dict)

    def test_unregister_removes_snapshot(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine
        engine = OptionChainLiveEngine()
        engine.register_chain("NIFTY", "2026-04-24", _make_chain_tokens())
        engine.unregister_chain("NIFTY", "2026-04-24")
        assert not engine.has_snapshot("NIFTY", "2026-04-24")


# ---------------------------------------------------------------------------
# Tick processing
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTickProcessing:

    def test_tick_updates_ltp_in_snapshot(self):
        """When a tick arrives for a registered token, LTP should update."""
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens()
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        # Simulate a tick for the first CE token
        tick = _make_tick(token=1001, ltp=Decimal("250.50"))
        engine.on_tick([tick])

        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        assert snap["tokens"][1001]["ltp"] == Decimal("250.50")

    def test_tick_updates_oi(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens()
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        tick = _make_tick(token=1001, ltp=Decimal("250"), oi=85000)
        engine.on_tick([tick])

        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        assert snap["tokens"][1001]["oi"] == 85000

    def test_tick_for_unknown_token_is_ignored(self):
        """Ticks for tokens not in any registered chain should be silently ignored."""
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        engine.register_chain("NIFTY", "2026-04-24", _make_chain_tokens())

        tick = _make_tick(token=99999, ltp=Decimal("100"))
        engine.on_tick([tick])  # Should not raise

    def test_multiple_ticks_batch_update(self):
        """A batch of ticks should update all matching tokens."""
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens()
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        ticks = [
            _make_tick(token=1001, ltp=Decimal("251")),
            _make_tick(token=2001, ltp=Decimal("12.5")),
        ]
        engine.on_tick(ticks)

        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        assert snap["tokens"][1001]["ltp"] == Decimal("251")
        assert snap["tokens"][2001]["ltp"] == Decimal("12.5")

    def test_tick_updates_volume(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens()
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        tick = _make_tick(token=1001, ltp=Decimal("250"), volume=150000)
        engine.on_tick([tick])

        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        assert snap["tokens"][1001]["volume"] == 150000


# ---------------------------------------------------------------------------
# Snapshot data structure
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSnapshotStructure:

    def test_snapshot_contains_all_registered_tokens(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens()
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        for t in tokens:
            assert t["token"] in snap["tokens"], f"Token {t['token']} missing from snapshot"

    def test_snapshot_token_has_required_fields(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens()
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        entry = snap["tokens"][1001]
        for field in ["ltp", "oi", "volume", "strike", "side", "tradingsymbol"]:
            assert field in entry, f"Token entry missing field: {field}"

    def test_snapshot_includes_metadata(self):
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens()
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        snap = engine.get_snapshot("NIFTY", "2026-04-24")
        assert "underlying" in snap
        assert "expiry" in snap
        assert snap["underlying"] == "NIFTY"
        assert snap["expiry"] == "2026-04-24"


# ---------------------------------------------------------------------------
# Performance: get_snapshot must be fast (<1ms)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSnapshotPerformance:

    def test_get_snapshot_under_1ms(self):
        """In-memory snapshot retrieval must complete in <1ms."""
        import time
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens(n_strikes=40)
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        # Warm up
        engine.get_snapshot("NIFTY", "2026-04-24")

        start = time.perf_counter()
        for _ in range(100):
            engine.get_snapshot("NIFTY", "2026-04-24")
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100

        assert elapsed_ms < 1.0, (
            f"get_snapshot should complete in <1ms, took {elapsed_ms:.3f}ms avg"
        )

    def test_on_tick_under_1ms(self):
        """Processing a batch of 10 ticks must complete in <1ms."""
        import time
        from app.services.options.option_chain_live_engine import OptionChainLiveEngine

        engine = OptionChainLiveEngine()
        tokens = _make_chain_tokens(n_strikes=40)
        engine.register_chain("NIFTY", "2026-04-24", tokens)

        ticks = [_make_tick(token=1001 + i, ltp=Decimal(f"{200 + i}.5")) for i in range(10)]

        # Warm up
        engine.on_tick(ticks)

        start = time.perf_counter()
        for _ in range(100):
            engine.on_tick(ticks)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100

        assert elapsed_ms < 1.0, (
            f"on_tick(10 ticks) should complete in <1ms, took {elapsed_ms:.3f}ms avg"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chain_tokens(n_strikes=5):
    """Create mock chain token entries for registration."""
    tokens = []
    base_strike = 24000
    for i in range(n_strikes):
        strike = base_strike + (i - n_strikes // 2) * 100
        tokens.append({
            "token": 1001 + i,
            "strike": strike,
            "side": "CE",
            "tradingsymbol": f"NIFTY{strike}CE",
        })
        tokens.append({
            "token": 2001 + i,
            "strike": strike,
            "side": "PE",
            "tradingsymbol": f"NIFTY{strike}PE",
        })
    return tokens


def _make_tick(token, ltp, oi=0, volume=0):
    """Create a mock NormalizedTick-like object."""
    return MagicMock(
        token=token,
        ltp=ltp,
        oi=oi,
        volume=volume,
        open=ltp,
        high=ltp,
        low=ltp,
        close=ltp,
        change=Decimal("0"),
        change_percent=Decimal("0"),
    )
