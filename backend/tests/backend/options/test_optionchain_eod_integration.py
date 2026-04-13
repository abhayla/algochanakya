"""
Integration tests for EOD snapshot fallback in the option chain route.

TDD: Written FIRST, before modifying the route.
Tests verify that EOD snapshot data is used when market is closed and broker OI is zero.
"""
import pytest
import pytest_asyncio
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.market_hours import IST


def _make_strikes_data():
    """Build minimal strikes_data dict as produced by the route."""
    return {
        24000: {
            "strike": 24000,
            "ce": {"instrument_token": 100, "tradingsymbol": "NIFTY2641624000CE", "lot_size": 75},
            "pe": {"instrument_token": 101, "tradingsymbol": "NIFTY2641624000PE", "lot_size": 75},
        },
        24100: {
            "strike": 24100,
            "ce": {"instrument_token": 102, "tradingsymbol": "NIFTY2641624100CE", "lot_size": 75},
            "pe": {"instrument_token": 103, "tradingsymbol": "NIFTY2641624100PE", "lot_size": 75},
        },
        24200: {
            "strike": 24200,
            "ce": {"instrument_token": 104, "tradingsymbol": "NIFTY2641624200CE", "lot_size": 75},
            "pe": {"instrument_token": 105, "tradingsymbol": "NIFTY2641624200PE", "lot_size": 75},
        },
    }


def _make_zero_oi_quotes():
    """Quotes with zero OI (typical closed-market response)."""
    return {
        "NFO:NIFTY2641624000CE": {"last_price": 0, "oi": 0, "volume": 0, "ohlc": {"close": 150}, "depth": {}},
        "NFO:NIFTY2641624000PE": {"last_price": 0, "oi": 0, "volume": 0, "ohlc": {"close": 140}, "depth": {}},
        "NFO:NIFTY2641624100CE": {"last_price": 0, "oi": 0, "volume": 0, "ohlc": {"close": 100}, "depth": {}},
        "NFO:NIFTY2641624100PE": {"last_price": 0, "oi": 0, "volume": 0, "ohlc": {"close": 180}, "depth": {}},
        "NFO:NIFTY2641624200CE": {"last_price": 0, "oi": 0, "volume": 0, "ohlc": {"close": 60}, "depth": {}},
        "NFO:NIFTY2641624200PE": {"last_price": 0, "oi": 0, "volume": 0, "ohlc": {"close": 220}, "depth": {}},
    }


def _make_nonzero_oi_quotes():
    """Quotes with non-zero OI (broker still has data)."""
    return {
        "NFO:NIFTY2641624000CE": {"last_price": 150, "oi": 500000, "volume": 12000, "ohlc": {"close": 150}, "depth": {}},
        "NFO:NIFTY2641624000PE": {"last_price": 140, "oi": 300000, "volume": 8000, "ohlc": {"close": 140}, "depth": {}},
        "NFO:NIFTY2641624100CE": {"last_price": 100, "oi": 400000, "volume": 10000, "ohlc": {"close": 100}, "depth": {}},
        "NFO:NIFTY2641624100PE": {"last_price": 180, "oi": 350000, "volume": 9000, "ohlc": {"close": 180}, "depth": {}},
        "NFO:NIFTY2641624200CE": {"last_price": 60, "oi": 200000, "volume": 5000, "ohlc": {"close": 60}, "depth": {}},
        "NFO:NIFTY2641624200PE": {"last_price": 220, "oi": 250000, "volume": 6000, "ohlc": {"close": 220}, "depth": {}},
    }


def _make_eod_snapshot():
    """EOD snapshot dict as returned by EODSnapshotService.get_snapshot()."""
    return {
        Decimal("24000"): {"ce_oi": 500000, "ce_volume": 12000, "ce_ltp": Decimal("150"), "ce_iv": Decimal("18.5"),
                           "pe_oi": 300000, "pe_volume": 8000, "pe_ltp": Decimal("140"), "pe_iv": Decimal("22.1")},
        Decimal("24100"): {"ce_oi": 400000, "ce_volume": 10000, "ce_ltp": Decimal("100"), "ce_iv": Decimal("17.8"),
                           "pe_oi": 350000, "pe_volume": 9000, "pe_ltp": Decimal("180"), "pe_iv": Decimal("21.5")},
        Decimal("24200"): {"ce_oi": 200000, "ce_volume": 5000, "ce_ltp": Decimal("60"), "ce_iv": Decimal("16.2"),
                           "pe_oi": 250000, "pe_volume": 6000, "pe_ltp": Decimal("220"), "pe_iv": Decimal("20.8")},
    }


class TestEODSnapshotFallback:
    """Test the EOD snapshot integration in _build_chain_response (the inner logic)."""

    def test_snapshot_used_when_closed_and_zero_oi(self):
        """When market is closed and all broker OI is zero, snapshot OI should be used."""
        from app.api.routes.optionchain import _apply_eod_fallback

        all_quotes = _make_zero_oi_quotes()
        eod_snapshot = _make_eod_snapshot()

        modified = _apply_eod_fallback(all_quotes, eod_snapshot, _make_strikes_data())

        # OI should now come from snapshot
        assert modified["NFO:NIFTY2641624000CE"]["oi"] == 500000
        assert modified["NFO:NIFTY2641624000PE"]["oi"] == 300000
        assert modified["NFO:NIFTY2641624100CE"]["oi"] == 400000
        assert modified["NFO:NIFTY2641624200PE"]["oi"] == 250000

    def test_volumes_also_filled(self):
        """Volume should also come from snapshot when OI is zero."""
        from app.api.routes.optionchain import _apply_eod_fallback

        all_quotes = _make_zero_oi_quotes()
        eod_snapshot = _make_eod_snapshot()

        modified = _apply_eod_fallback(all_quotes, eod_snapshot, _make_strikes_data())

        assert modified["NFO:NIFTY2641624000CE"]["volume"] == 12000
        assert modified["NFO:NIFTY2641624000PE"]["volume"] == 8000

    def test_no_change_when_broker_has_oi(self):
        """When broker already has OI, snapshot should NOT override."""
        from app.api.routes.optionchain import _apply_eod_fallback

        all_quotes = _make_nonzero_oi_quotes()
        eod_snapshot = _make_eod_snapshot()

        modified = _apply_eod_fallback(all_quotes, eod_snapshot, _make_strikes_data())

        # Should remain unchanged
        assert modified["NFO:NIFTY2641624000CE"]["oi"] == 500000
        assert modified["NFO:NIFTY2641624000PE"]["oi"] == 300000

    def test_no_change_when_snapshot_is_none(self):
        """When no snapshot available, quotes should be unchanged."""
        from app.api.routes.optionchain import _apply_eod_fallback

        all_quotes = _make_zero_oi_quotes()

        modified = _apply_eod_fallback(all_quotes, None, _make_strikes_data())

        assert modified["NFO:NIFTY2641624000CE"]["oi"] == 0

    def test_partial_match_fills_what_it_can(self):
        """Snapshot has only some strikes — fill those, leave others as-is."""
        from app.api.routes.optionchain import _apply_eod_fallback

        all_quotes = _make_zero_oi_quotes()
        # Snapshot only has 24000 strike
        partial_snapshot = {
            Decimal("24000"): {"ce_oi": 500000, "ce_volume": 12000, "ce_ltp": Decimal("150"), "ce_iv": Decimal("18.5"),
                               "pe_oi": 300000, "pe_volume": 8000, "pe_ltp": Decimal("140"), "pe_iv": Decimal("22.1")},
        }

        modified = _apply_eod_fallback(all_quotes, partial_snapshot, _make_strikes_data())

        assert modified["NFO:NIFTY2641624000CE"]["oi"] == 500000
        assert modified["NFO:NIFTY2641624100CE"]["oi"] == 0  # No snapshot for this strike


class TestShouldUseSnapshot:

    def test_all_zero_oi_returns_true(self):
        """All OI is zero → should use snapshot."""
        from app.api.routes.optionchain import _should_use_eod_snapshot

        all_quotes = _make_zero_oi_quotes()
        assert _should_use_eod_snapshot(all_quotes) is True

    def test_any_nonzero_oi_returns_false(self):
        """Any non-zero OI → should NOT use snapshot."""
        from app.api.routes.optionchain import _should_use_eod_snapshot

        all_quotes = _make_nonzero_oi_quotes()
        assert _should_use_eod_snapshot(all_quotes) is False

    def test_empty_quotes_returns_true(self):
        """Empty quotes dict → should use snapshot."""
        from app.api.routes.optionchain import _should_use_eod_snapshot

        assert _should_use_eod_snapshot({}) is True
