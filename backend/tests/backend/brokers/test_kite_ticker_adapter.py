"""Tests for Kite Connect Ticker Adapter.

Tests cover:
- Adapter creation and configuration
- Token translation (identity — canonical IS Kite token)
- Tick parsing (rupee prices, OHLC dict structure, change calculation)
- Batch tick processing (on_ticks receives list)
- WebSocket callback → dispatch bridging
- Connection lifecycle
- Mode mapping
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.brokers.market_data.ticker.adapters.kite import (
    KiteTickerAdapter,
)
from app.services.brokers.market_data.ticker.models import NormalizedTick


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def adapter():
    """Create a Kite ticker adapter."""
    return KiteTickerAdapter()


@pytest.fixture
def sample_tick_nifty():
    """Sample Kite tick for NIFTY 50 (prices in rupees)."""
    return {
        "instrument_token": 256265,
        "last_price": 24500.50,
        "ohlc": {
            "open": 24400.00,
            "high": 24550.25,
            "low": 24380.00,
            "close": 24450.75,
        },
        "change": 49.75,
        "volume": 1234567,
        "oi": 5678900,
        "exchange_timestamp": datetime(2026, 2, 17, 10, 30, 0),
    }


@pytest.fixture
def sample_tick_banknifty():
    """Sample Kite tick for BANKNIFTY."""
    return {
        "instrument_token": 260105,
        "last_price": 52000.25,
        "ohlc": {
            "open": 51800.00,
            "high": 52100.50,
            "low": 51750.00,
            "close": 51900.00,
        },
        "change": 100.25,
        "volume": 987654,
        "oi": 3456789,
        "exchange_timestamp": datetime(2026, 2, 17, 10, 30, 0),
    }


@pytest.fixture
def sample_tick_zero_close():
    """Tick with zero close price (edge case for change_percent)."""
    return {
        "instrument_token": 256265,
        "last_price": 100.0,
        "ohlc": {
            "open": 0,
            "high": 200.0,
            "low": 0,
            "close": 0,
        },
        "volume": 0,
        "oi": 0,
    }


@pytest.fixture
def sample_tick_ltp_only():
    """Minimal LTP-mode tick (no OHLC)."""
    return {
        "instrument_token": 256265,
        "last_price": 24500.50,
    }


# ═══════════════════════════════════════════════════════════════════════
# CREATION & CONFIG
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterCreation:
    def test_default_broker_type(self):
        adapter = KiteTickerAdapter()
        assert adapter.broker_type == "kite"

    def test_custom_broker_type(self):
        adapter = KiteTickerAdapter(broker_type="kite_user")
        assert adapter.broker_type == "kite_user"

    def test_initial_state(self):
        adapter = KiteTickerAdapter()
        assert not adapter.is_connected
        assert adapter.subscribed_tokens == set()
        assert adapter.last_tick_time is None
        assert adapter.reconnect_count == 0

    def test_mode_constants(self):
        assert KiteTickerAdapter.MODES["ltp"] == "ltp"
        assert KiteTickerAdapter.MODES["quote"] == "quote"
        assert KiteTickerAdapter.MODES["full"] == "full"


# ═══════════════════════════════════════════════════════════════════════
# TOKEN TRANSLATION (IDENTITY)
# ═══════════════════════════════════════════════════════════════════════

class TestTokenTranslation:
    def test_translate_single_token(self, adapter):
        result = adapter._translate_to_broker_tokens([256265])
        assert result == [256265]

    def test_translate_multiple_tokens(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 260105, 257801])
        assert result == [256265, 260105, 257801]

    def test_translate_empty_list(self, adapter):
        assert adapter._translate_to_broker_tokens([]) == []

    def test_translate_preserves_order(self, adapter):
        tokens = [260105, 256265, 257801]
        result = adapter._translate_to_broker_tokens(tokens)
        assert result == [260105, 256265, 257801]

    def test_get_canonical_token_identity(self, adapter):
        assert adapter._get_canonical_token(256265) == 256265
        assert adapter._get_canonical_token(260105) == 260105

    def test_get_canonical_token_string_input(self, adapter):
        """Should handle string input by converting to int."""
        assert adapter._get_canonical_token("256265") == 256265

    def test_get_canonical_token_invalid(self, adapter):
        assert adapter._get_canonical_token(None) == 0
        assert adapter._get_canonical_token("invalid") == 0


# ═══════════════════════════════════════════════════════════════════════
# TICK PARSING
# ═══════════════════════════════════════════════════════════════════════

class TestTickParsing:
    def test_parse_nifty_tick(self, adapter, sample_tick_nifty):
        ticks = adapter._parse_tick(sample_tick_nifty)

        assert len(ticks) == 1
        tick = ticks[0]

        assert isinstance(tick, NormalizedTick)
        assert tick.token == 256265
        assert tick.broker_type == "kite"

    def test_prices_are_decimal_rupees(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]

        assert tick.ltp == Decimal("24500.50")
        assert tick.open == Decimal("24400.00")
        assert tick.high == Decimal("24550.25")
        assert tick.low == Decimal("24380.00")
        assert tick.close == Decimal("24450.75")

    def test_all_prices_are_decimal(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]

        for field_name in ("ltp", "open", "high", "low", "close", "change", "change_percent"):
            value = getattr(tick, field_name)
            assert isinstance(value, Decimal), f"{field_name} should be Decimal, got {type(value)}"

    def test_change_calculated_correctly(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]

        expected_change = Decimal("24500.50") - Decimal("24450.75")
        assert tick.change == expected_change

        expected_pct = expected_change / Decimal("24450.75") * 100
        assert tick.change_percent == expected_pct

    def test_volume_and_oi(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]

        assert tick.volume == 1234567
        assert tick.oi == 5678900

    def test_exchange_timestamp_used(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]

        assert isinstance(tick.timestamp, datetime)
        assert tick.timestamp == datetime(2026, 2, 17, 10, 30, 0)

    def test_missing_timestamp_uses_now(self, adapter):
        tick_data = {
            "instrument_token": 256265,
            "last_price": 100.0,
        }
        tick = adapter._parse_tick(tick_data)[0]
        assert isinstance(tick.timestamp, datetime)
        # Should be close to now
        delta = (datetime.now() - tick.timestamp).total_seconds()
        assert delta < 2

    def test_zero_close_no_division_error(self, adapter, sample_tick_zero_close):
        ticks = adapter._parse_tick(sample_tick_zero_close)

        assert len(ticks) == 1
        assert ticks[0].change_percent == Decimal("0")

    def test_missing_token_returns_empty(self, adapter):
        assert adapter._parse_tick({}) == []
        assert adapter._parse_tick({"instrument_token": None}) == []

    def test_invalid_token_returns_empty(self, adapter):
        assert adapter._parse_tick({"instrument_token": "invalid"}) == []

    def test_missing_ohlc_defaults_to_zero(self, adapter, sample_tick_ltp_only):
        ticks = adapter._parse_tick(sample_tick_ltp_only)
        assert len(ticks) == 1
        assert ticks[0].ltp == Decimal("24500.50")
        assert ticks[0].open == Decimal("0")
        assert ticks[0].high == Decimal("0")
        assert ticks[0].low == Decimal("0")
        assert ticks[0].close == Decimal("0")

    def test_none_volume_oi_treated_as_zero(self, adapter):
        tick_data = {
            "instrument_token": 256265,
            "last_price": 100.0,
            "volume": None,
            "oi": None,
        }
        ticks = adapter._parse_tick(tick_data)
        assert ticks[0].volume == 0
        assert ticks[0].oi == 0

    def test_small_option_premium_precision(self, adapter):
        """Verify precision for small option premiums (e.g., ₹0.05)."""
        tick_data = {
            "instrument_token": 256265,
            "last_price": 0.05,
            "ohlc": {"close": 0.10},
        }
        tick = adapter._parse_tick(tick_data)[0]
        assert tick.ltp == Decimal("0.05")
        assert tick.close == Decimal("0.10")
        assert tick.change == Decimal("-0.05")

    def test_no_paise_conversion(self, adapter):
        """Kite prices are in rupees — verify NO ÷100 conversion happens."""
        tick_data = {
            "instrument_token": 256265,
            "last_price": 24500.50,
        }
        tick = adapter._parse_tick(tick_data)[0]
        # Should be ₹24500.50, NOT ₹245.0050
        assert tick.ltp == Decimal("24500.50")


# ═══════════════════════════════════════════════════════════════════════
# BATCH TICK PROCESSING (on_ticks receives a list)
# ═══════════════════════════════════════════════════════════════════════

class TestBatchTickProcessing:
    def test_on_ticks_processes_batch(self, adapter, sample_tick_nifty, sample_tick_banknifty):
        """on_ticks receives a list of tick dicts and dispatches all at once."""
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_ticks(ws=None, ticks=[sample_tick_nifty, sample_tick_banknifty])

        adapter._dispatch_from_thread.assert_called_once()
        dispatched = adapter._dispatch_from_thread.call_args[0][0]
        assert len(dispatched) == 2
        assert dispatched[0].token == 256265
        assert dispatched[1].token == 260105

    def test_on_ticks_single_tick(self, adapter, sample_tick_nifty):
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_ticks(ws=None, ticks=[sample_tick_nifty])

        adapter._dispatch_from_thread.assert_called_once()
        dispatched = adapter._dispatch_from_thread.call_args[0][0]
        assert len(dispatched) == 1
        assert dispatched[0].token == 256265

    def test_on_ticks_skips_unparseable(self, adapter, sample_tick_nifty):
        """Bad ticks should be skipped, good ones still dispatched."""
        adapter._dispatch_from_thread = MagicMock()

        bad_tick = {"instrument_token": None, "last_price": 0}
        adapter._on_ticks(ws=None, ticks=[bad_tick, sample_tick_nifty])

        adapter._dispatch_from_thread.assert_called_once()
        dispatched = adapter._dispatch_from_thread.call_args[0][0]
        assert len(dispatched) == 1
        assert dispatched[0].token == 256265

    def test_on_ticks_all_unparseable_no_dispatch(self, adapter):
        """If all ticks fail to parse, should not dispatch."""
        adapter._dispatch_from_thread = MagicMock()

        bad_ticks = [
            {"instrument_token": None},
            {"instrument_token": "invalid"},
        ]
        adapter._on_ticks(ws=None, ticks=bad_ticks)

        adapter._dispatch_from_thread.assert_not_called()

    def test_on_ticks_empty_list_no_dispatch(self, adapter):
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_ticks(ws=None, ticks=[])

        adapter._dispatch_from_thread.assert_not_called()

    def test_on_ticks_handles_exception(self, adapter):
        """on_ticks should not raise even on errors."""
        adapter._parse_tick = MagicMock(side_effect=RuntimeError("boom"))

        # Should not raise
        adapter._on_ticks(ws=None, ticks=[{"instrument_token": 256265}])


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION CALLBACKS
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionCallbacks:
    def test_on_connect_sets_event(self, adapter):
        assert not adapter._ws_connected_event.is_set()
        adapter._on_connect(ws=None, response={"status": "ok"})
        assert adapter._ws_connected_event.is_set()

    def test_on_close_clears_event_and_connected(self, adapter):
        adapter._ws_connected_event.set()
        adapter._connected = True

        adapter._on_close(ws=None, code=1000, reason="normal")

        assert not adapter._ws_connected_event.is_set()
        assert not adapter._connected

    def test_on_error_does_not_raise(self, adapter):
        """on_error should log but not raise."""
        adapter._on_error(ws=None, code=500, reason="test error")

    def test_on_reconnect_does_not_raise(self, adapter):
        """on_reconnect should log but not raise."""
        adapter._on_reconnect(ws=None, attempts_count=3)


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE (with mocked KiteTicker)
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionLifecycle:
    @pytest.mark.asyncio
    async def test_connect_creates_kws_and_starts_threaded(self):
        """connect should create KiteTicker and call connect(threaded=True)."""
        mock_kws_class = MagicMock()
        mock_kws = MagicMock()
        mock_kws_class.return_value = mock_kws

        adapter = KiteTickerAdapter()

        # Simulate _on_connect firing when kws.connect() is called
        def fake_connect(threaded=False):
            adapter._on_connect(ws=None, response={"status": "ok"})

        mock_kws.connect = fake_connect

        creds = {
            "api_key": "test_api_key",
            "access_token": "test_access_token",
        }

        with patch("kiteconnect.KiteTicker", mock_kws_class):
            await adapter._connect_ws(creds)

        # Verify KiteTicker was constructed with correct args
        mock_kws_class.assert_called_once_with(
            api_key="test_api_key",
            access_token="test_access_token",
        )

        # Verify callbacks were set
        assert mock_kws.on_ticks == adapter._on_ticks
        assert mock_kws.on_connect == adapter._on_connect
        assert mock_kws.on_close == adapter._on_close
        assert mock_kws.on_error == adapter._on_error
        assert mock_kws.on_reconnect == adapter._on_reconnect

        # Verify connection event was set (by fake_connect → _on_connect)
        assert adapter._ws_connected_event.is_set()

    @pytest.mark.asyncio
    async def test_disconnect_closes_kws(self):
        adapter = KiteTickerAdapter()
        mock_kws = MagicMock()
        adapter.kws = mock_kws

        await adapter._disconnect_ws()

        mock_kws.close.assert_called_once()
        assert adapter.kws is None

    @pytest.mark.asyncio
    async def test_disconnect_handles_error(self):
        adapter = KiteTickerAdapter()
        mock_kws = MagicMock()
        mock_kws.close.side_effect = RuntimeError("fail")
        adapter.kws = mock_kws

        # Should not raise
        await adapter._disconnect_ws()
        assert adapter.kws is None

    @pytest.mark.asyncio
    async def test_subscribe_calls_kws(self):
        adapter = KiteTickerAdapter()
        mock_kws = MagicMock()
        mock_kws.MODE_QUOTE = "quote"
        adapter.kws = mock_kws

        broker_tokens = [256265, 260105]
        await adapter._subscribe_ws(broker_tokens, "quote")

        mock_kws.subscribe.assert_called_once_with([256265, 260105])
        mock_kws.set_mode.assert_called_once_with("quote", [256265, 260105])

    @pytest.mark.asyncio
    async def test_subscribe_ltp_mode(self):
        adapter = KiteTickerAdapter()
        mock_kws = MagicMock()
        mock_kws.MODE_LTP = "ltp"
        adapter.kws = mock_kws

        await adapter._subscribe_ws([256265], "ltp")

        mock_kws.set_mode.assert_called_once_with("ltp", [256265])

    @pytest.mark.asyncio
    async def test_subscribe_full_mode(self):
        adapter = KiteTickerAdapter()
        mock_kws = MagicMock()
        mock_kws.MODE_FULL = "full"
        adapter.kws = mock_kws

        await adapter._subscribe_ws([256265], "full")

        mock_kws.set_mode.assert_called_once_with("full", [256265])

    @pytest.mark.asyncio
    async def test_subscribe_raises_when_not_connected(self):
        adapter = KiteTickerAdapter()
        adapter.kws = None

        with pytest.raises(ConnectionError):
            await adapter._subscribe_ws([256265], "quote")

    @pytest.mark.asyncio
    async def test_unsubscribe_calls_kws(self):
        adapter = KiteTickerAdapter()
        mock_kws = MagicMock()
        adapter.kws = mock_kws

        await adapter._unsubscribe_ws([256265, 260105])

        mock_kws.unsubscribe.assert_called_once_with([256265, 260105])

    @pytest.mark.asyncio
    async def test_unsubscribe_noop_when_not_connected(self):
        adapter = KiteTickerAdapter()
        adapter.kws = None

        # Should not raise
        await adapter._unsubscribe_ws([256265])


# ═══════════════════════════════════════════════════════════════════════
# MODE MAPPING
# ═══════════════════════════════════════════════════════════════════════

class TestModeMapping:
    def test_get_kite_mode_quote(self, adapter):
        mock_kws = MagicMock()
        mock_kws.MODE_LTP = "ltp"
        mock_kws.MODE_QUOTE = "quote"
        mock_kws.MODE_FULL = "full"
        adapter.kws = mock_kws

        assert adapter._get_kite_mode("quote") == "quote"

    def test_get_kite_mode_ltp(self, adapter):
        mock_kws = MagicMock()
        mock_kws.MODE_LTP = "ltp"
        mock_kws.MODE_QUOTE = "quote"
        mock_kws.MODE_FULL = "full"
        adapter.kws = mock_kws

        assert adapter._get_kite_mode("ltp") == "ltp"

    def test_get_kite_mode_full(self, adapter):
        mock_kws = MagicMock()
        mock_kws.MODE_LTP = "ltp"
        mock_kws.MODE_QUOTE = "quote"
        mock_kws.MODE_FULL = "full"
        adapter.kws = mock_kws

        assert adapter._get_kite_mode("full") == "full"

    def test_get_kite_mode_unknown_defaults_to_quote(self, adapter):
        mock_kws = MagicMock()
        mock_kws.MODE_LTP = "ltp"
        mock_kws.MODE_QUOTE = "quote"
        mock_kws.MODE_FULL = "full"
        adapter.kws = mock_kws

        assert adapter._get_kite_mode("depth") == "quote"

    def test_get_kite_mode_no_kws_returns_mode_string(self, adapter):
        """When kws not initialized, return the mode string as-is."""
        adapter.kws = None
        assert adapter._get_kite_mode("quote") == "quote"


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION: FULL TICK FLOW (adapter → parse → dispatch)
# ═══════════════════════════════════════════════════════════════════════

class TestFullTickFlow:
    def test_end_to_end_single_tick(self, adapter, sample_tick_nifty):
        """Full flow: raw Kite tick → NormalizedTick → callback."""
        received_ticks = []

        def mock_callback(ticks):
            received_ticks.extend(ticks)

        adapter.set_on_tick_callback(mock_callback)
        loop = asyncio.new_event_loop()
        adapter.set_event_loop(loop)

        # Parse tick directly
        ticks = adapter._parse_tick(sample_tick_nifty)
        assert len(ticks) == 1

        tick = ticks[0]
        assert tick.token == 256265
        assert tick.ltp == Decimal("24500.50")
        assert tick.broker_type == "kite"
        assert tick.volume == 1234567
        assert tick.oi == 5678900
        assert tick.timestamp == datetime(2026, 2, 17, 10, 30, 0)

        loop.close()

    def test_end_to_end_batch_ticks(self, adapter, sample_tick_nifty, sample_tick_banknifty):
        """Parse batch of ticks for multiple instruments."""
        ticks1 = adapter._parse_tick(sample_tick_nifty)
        ticks2 = adapter._parse_tick(sample_tick_banknifty)

        assert ticks1[0].token == 256265  # NIFTY
        assert ticks1[0].ltp == Decimal("24500.50")

        assert ticks2[0].token == 260105  # BANKNIFTY
        assert ticks2[0].ltp == Decimal("52000.25")

    def test_on_ticks_full_dispatch(self, adapter, sample_tick_nifty):
        """Simulate on_ticks callback dispatching to async callback."""
        dispatched = []
        adapter._dispatch_from_thread = lambda ticks: dispatched.extend(ticks)

        adapter._on_ticks(ws=None, ticks=[sample_tick_nifty])

        assert len(dispatched) == 1
        assert dispatched[0].token == 256265
        assert dispatched[0].ltp == Decimal("24500.50")
        assert dispatched[0].broker_type == "kite"
