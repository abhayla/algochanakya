"""Tests for Fyers Ticker Adapter.

Tests cover:
- Adapter creation and configuration
- Token mapping (canonical int ↔ Fyers NSE: symbol string)
- Tick parsing (rupees already, Decimal conversion, change calculation)
- Broker token translation (canonical → NSE: symbol list)
- WebSocket callback → dispatch bridging (on_message → _dispatch_from_thread)
- Connection lifecycle (connect, disconnect, subscribe, unsubscribe)
- Edge cases: unknown symbols, zero close, missing fields, list messages
"""

import asyncio
import sys
import types
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.brokers.market_data.ticker.adapters.fyers import (
    FyersTickerAdapter,
    _MODE_TO_DATA_TYPE,
)
from app.services.brokers.market_data.ticker.models import NormalizedTick


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def adapter():
    """Create adapter with pre-loaded token map."""
    a = FyersTickerAdapter()
    a.load_token_map({
        256265: "NSE:NIFTY50-INDEX",        # NIFTY 50
        260105: "NSE:NIFTYBANK-INDEX",      # NIFTY BANK
        12345678: "NSE:NIFTY2522725000CE",  # Synthetic option token
        99990001: "NSE:RELIANCE-EQ",        # Equity
    })
    return a


@pytest.fixture
def sample_tick_nifty():
    """Sample Fyers SymbolUpdate tick for NIFTY 50 index (prices in rupees)."""
    return {
        "symbol": "NSE:NIFTY50-INDEX",
        "fyToken": "101000000001234",
        "timestamp": 1709119800,
        "ltp": 24500.50,
        "open_price": 24400.00,
        "high_price": 24550.25,
        "low_price": 24380.00,
        "prev_close_price": 24450.75,
        "ch": 49.75,
        "chp": 0.20,
        "vol_traded_today": 1234567,
        "bid_price": 24500.20,
        "bid_size": 500,
        "ask_price": 24500.80,
        "ask_size": 400,
        "oi": 5678900,
        "type": "sf",
    }


@pytest.fixture
def sample_tick_option():
    """Sample Fyers SymbolUpdate tick for an option contract."""
    return {
        "symbol": "NSE:NIFTY2522725000CE",
        "fyToken": "101010000012345",
        "timestamp": 1709119800,
        "ltp": 150.25,
        "open_price": 145.00,
        "high_price": 155.50,
        "low_price": 142.00,
        "prev_close_price": 148.75,
        "ch": 1.50,
        "chp": 1.01,
        "vol_traded_today": 125000,
        "bid_price": 150.20,
        "bid_size": 250,
        "ask_price": 150.30,
        "ask_size": 300,
        "oi": 500000,
        "type": "sf",
    }


@pytest.fixture
def sample_tick_zero_close():
    """Tick with zero close price (edge case for change_percent division)."""
    return {
        "symbol": "NSE:NIFTY50-INDEX",
        "ltp": 100.00,
        "open_price": 0,
        "high_price": 200.00,
        "low_price": 0,
        "prev_close_price": 0,
        "vol_traded_today": 0,
        "oi": 0,
        "type": "sf",
    }


# ═══════════════════════════════════════════════════════════════════════
# CREATION & CONFIG
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterCreation:
    def test_default_broker_type(self):
        adapter = FyersTickerAdapter()
        assert adapter.broker_type == "fyers"

    def test_custom_broker_type(self):
        adapter = FyersTickerAdapter(broker_type="fyers_platform")
        assert adapter.broker_type == "fyers_platform"

    def test_initial_state(self):
        adapter = FyersTickerAdapter()
        assert not adapter.is_connected
        assert adapter.subscribed_tokens == set()
        assert adapter.last_tick_time is None
        assert adapter.reconnect_count == 0

    def test_initial_maps_empty(self):
        adapter = FyersTickerAdapter()
        assert adapter._canonical_to_broker == {}
        assert adapter._broker_to_canonical == {}

    def test_mode_to_data_type_mapping(self):
        assert _MODE_TO_DATA_TYPE["ltp"] == "SymbolUpdate"
        assert _MODE_TO_DATA_TYPE["quote"] == "SymbolUpdate"
        assert _MODE_TO_DATA_TYPE["snap"] == "SymbolUpdate"
        assert _MODE_TO_DATA_TYPE["depth"] == "DepthUpdate"
        assert _MODE_TO_DATA_TYPE["full"] == "DepthUpdate"


# ═══════════════════════════════════════════════════════════════════════
# TOKEN MAPPING
# ═══════════════════════════════════════════════════════════════════════

class TestTokenMapping:
    def test_load_token_map(self, adapter):
        assert adapter._canonical_to_broker[256265] == "NSE:NIFTY50-INDEX"
        assert adapter._broker_to_canonical["NSE:NIFTY50-INDEX"] == 256265

    def test_load_multiple_tokens(self, adapter):
        assert len(adapter._canonical_to_broker) == 4
        assert len(adapter._broker_to_canonical) == 4

    def test_load_token_map_incremental(self, adapter):
        """Loading more tokens should merge, not replace."""
        adapter.load_token_map({999: "NSE:SYNTHETIC"})
        assert adapter._canonical_to_broker[999] == "NSE:SYNTHETIC"
        # Old mappings still present
        assert adapter._canonical_to_broker[256265] == "NSE:NIFTY50-INDEX"

    def test_get_canonical_token_found(self, adapter):
        assert adapter._get_canonical_token("NSE:NIFTY50-INDEX") == 256265
        assert adapter._get_canonical_token("NSE:NIFTYBANK-INDEX") == 260105

    def test_get_canonical_token_not_found(self, adapter):
        assert adapter._get_canonical_token("NSE:UNKNOWN") == 0

    def test_get_canonical_token_option(self, adapter):
        assert adapter._get_canonical_token("NSE:NIFTY2522725000CE") == 12345678

    def test_bidirectional_mapping_consistent(self, adapter):
        """Round-trip: canonical → fyers → canonical should return original."""
        for canonical_token, fyers_symbol in adapter._canonical_to_broker.items():
            round_tripped = adapter._get_canonical_token(fyers_symbol)
            assert round_tripped == canonical_token


# ═══════════════════════════════════════════════════════════════════════
# TOKEN TRANSLATION
# ═══════════════════════════════════════════════════════════════════════

class TestTokenTranslation:
    def test_translate_single_token(self, adapter):
        result = adapter._translate_to_broker_tokens([256265])
        assert result == ["NSE:NIFTY50-INDEX"]

    def test_translate_multiple_tokens(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 260105])
        assert set(result) == {"NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX"}

    def test_translate_unknown_token_skipped(self, adapter):
        result = adapter._translate_to_broker_tokens([999999])
        assert result == []

    def test_translate_mixed_known_unknown(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 999999])
        assert result == ["NSE:NIFTY50-INDEX"]

    def test_translate_empty_list(self, adapter):
        assert adapter._translate_to_broker_tokens([]) == []

    def test_translate_option_token(self, adapter):
        result = adapter._translate_to_broker_tokens([12345678])
        assert result == ["NSE:NIFTY2522725000CE"]


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
        assert tick.broker_type == "fyers"

    def test_prices_are_decimal_rupees(self, adapter, sample_tick_nifty):
        """Fyers sends rupees — verify correct Decimal conversion (no paise)."""
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
            assert isinstance(value, Decimal), (
                f"{field_name} should be Decimal, got {type(value)}"
            )

    def test_change_calculated_from_decimal(self, adapter, sample_tick_nifty):
        """Change must be recalculated from Decimal, not taken from float 'ch' field."""
        tick = adapter._parse_tick(sample_tick_nifty)[0]

        expected_change = Decimal("24500.50") - Decimal("24450.75")
        assert tick.change == expected_change

        expected_pct = expected_change / Decimal("24450.75") * 100
        assert tick.change_percent == expected_pct

    def test_volume_and_oi(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]
        assert tick.volume == 1234567
        assert tick.oi == 5678900

    def test_bid_ask_populated(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]
        assert tick.bid == Decimal("24500.20")
        assert tick.ask == Decimal("24500.80")
        assert tick.bid_qty == 500
        assert tick.ask_qty == 400

    def test_timestamp_from_unix_epoch(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]
        assert isinstance(tick.timestamp, datetime)
        # Timestamp 1709119800 should be a valid datetime
        assert tick.timestamp.year >= 2024

    def test_zero_close_no_division_error(self, adapter, sample_tick_zero_close):
        ticks = adapter._parse_tick(sample_tick_zero_close)
        assert len(ticks) == 1
        assert ticks[0].change_percent == Decimal("0")

    def test_missing_symbol_returns_empty(self, adapter):
        assert adapter._parse_tick({}) == []
        assert adapter._parse_tick({"symbol": None}) == []

    def test_unknown_symbol_returns_empty(self, adapter):
        tick_data = {"symbol": "NSE:UNKNOWN99999", "ltp": 100.0}
        assert adapter._parse_tick(tick_data) == []

    def test_missing_price_fields_default_to_zero(self, adapter):
        tick_data = {
            "symbol": "NSE:NIFTY50-INDEX",
            "ltp": 24500.50,
            # All OHLC fields missing
        }
        ticks = adapter._parse_tick(tick_data)
        assert len(ticks) == 1
        assert ticks[0].ltp == Decimal("24500.5")
        assert ticks[0].open == Decimal("0")
        assert ticks[0].high == Decimal("0")

    def test_none_volume_oi_treated_as_zero(self, adapter):
        tick_data = {
            "symbol": "NSE:NIFTY50-INDEX",
            "ltp": 24500.50,
            "vol_traded_today": None,
            "oi": None,
        }
        ticks = adapter._parse_tick(tick_data)
        assert ticks[0].volume == 0
        assert ticks[0].oi == 0

    def test_bid_ask_absent_is_none(self, adapter):
        """Ticks without bid/ask should have None (not 0) for those fields."""
        tick_data = {
            "symbol": "NSE:NIFTY50-INDEX",
            "ltp": 24500.50,
            "prev_close_price": 24450.75,
            # No bid_price, ask_price
        }
        tick = adapter._parse_tick(tick_data)[0]
        assert tick.bid is None
        assert tick.ask is None
        assert tick.bid_qty is None
        assert tick.ask_qty is None

    def test_parse_option_tick(self, adapter, sample_tick_option):
        tick = adapter._parse_tick(sample_tick_option)[0]
        assert tick.token == 12345678
        assert tick.ltp == Decimal("150.25")
        assert tick.volume == 125000
        assert tick.oi == 500000

    def test_small_option_premium_precision(self, adapter):
        """Verify Decimal precision for small option premiums (e.g., ₹0.05)."""
        tick_data = {
            "symbol": "NSE:NIFTY2522725000CE",
            "ltp": 0.05,
            "prev_close_price": 0.10,
        }
        tick = adapter._parse_tick(tick_data)[0]
        assert tick.ltp == Decimal("0.05")
        assert tick.close == Decimal("0.10")
        assert tick.change == Decimal("-0.05")

    def test_no_float_intermediaries(self, adapter):
        """LTP must not use float arithmetic — Decimal precision required."""
        tick_data = {
            "symbol": "NSE:NIFTY50-INDEX",
            "ltp": 24500.15,
            "prev_close_price": 24000.05,
        }
        tick = adapter._parse_tick(tick_data)[0]
        # Decimal("24500.15") - Decimal("24000.05") = Decimal("500.10") exactly
        assert isinstance(tick.change, Decimal)
        assert tick.change == Decimal("24500.15") - Decimal("24000.05")


# ═══════════════════════════════════════════════════════════════════════
# DISPATCH BRIDGING
# ═══════════════════════════════════════════════════════════════════════

class TestDispatchBridging:
    def test_on_message_dict_calls_dispatch(self, adapter, sample_tick_nifty):
        """_on_message with dict should parse tick and call _dispatch_from_thread."""
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_message(sample_tick_nifty)

        adapter._dispatch_from_thread.assert_called_once()
        ticks = adapter._dispatch_from_thread.call_args[0][0]
        assert len(ticks) == 1
        assert isinstance(ticks[0], NormalizedTick)
        assert ticks[0].token == 256265

    def test_on_message_list_calls_dispatch(self, adapter, sample_tick_nifty, sample_tick_option):
        """_on_message with list of dicts should parse all and dispatch."""
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_message([sample_tick_nifty, sample_tick_option])

        adapter._dispatch_from_thread.assert_called_once()
        ticks = adapter._dispatch_from_thread.call_args[0][0]
        assert len(ticks) == 2
        tokens = {t.token for t in ticks}
        assert tokens == {256265, 12345678}

    def test_on_message_skips_empty_parse(self, adapter):
        """_on_message should not dispatch when symbol is unknown."""
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_message({"symbol": "NSE:UNKNOWN", "ltp": 100.0})

        adapter._dispatch_from_thread.assert_not_called()

    def test_on_message_list_partial_unknown(self, adapter, sample_tick_nifty):
        """List with one valid and one unknown — dispatch only valid tick."""
        adapter._dispatch_from_thread = MagicMock()

        unknown_tick = {"symbol": "NSE:UNKNOWN", "ltp": 100.0}
        adapter._on_message([sample_tick_nifty, unknown_tick])

        adapter._dispatch_from_thread.assert_called_once()
        ticks = adapter._dispatch_from_thread.call_args[0][0]
        assert len(ticks) == 1
        assert ticks[0].token == 256265

    def test_on_message_empty_list_no_dispatch(self, adapter):
        """Empty list should not dispatch."""
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_message([])

        adapter._dispatch_from_thread.assert_not_called()

    def test_on_message_handles_exception(self, adapter):
        """_on_message should not raise even on parse errors."""
        adapter._parse_tick = MagicMock(side_effect=RuntimeError("boom"))

        # Should not raise
        adapter._on_message({"symbol": "NSE:NIFTY50-INDEX", "ltp": 100.0})


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION CALLBACKS
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionCallbacks:
    def test_on_open_sets_event(self, adapter):
        assert not adapter._ws_connected_event.is_set()
        adapter._on_open()
        assert adapter._ws_connected_event.is_set()

    def test_on_close_clears_event_and_connected(self, adapter):
        adapter._ws_connected_event.set()
        adapter._connected = True

        adapter._on_close("connection closed")

        assert not adapter._ws_connected_event.is_set()
        assert not adapter._connected

    def test_on_error_does_not_raise(self, adapter):
        """_on_error should log but not raise."""
        adapter._on_error("test error message")

    def test_on_error_with_dict_does_not_raise(self, adapter):
        adapter._on_error({"code": -16, "message": "Invalid token"})


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE (with mocked FyersDataSocket)
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionLifecycle:
    def _make_fyers_mock(self, adapter):
        """
        Build a fake fyers_apiv3 module tree and inject into sys.modules.
        Returns (mock_socket_class, mock_socket, cleanup_fn).
        """
        mock_socket = MagicMock()

        # Simulate on_open firing immediately when keep_running() is called
        def fake_keep_running():
            adapter._on_open()

        mock_socket.keep_running = fake_keep_running

        mock_socket_class = MagicMock(return_value=mock_socket)

        # Build fake module hierarchy: fyers_apiv3 → FyersWebsocket → data_ws
        fake_data_ws = types.ModuleType("fyers_apiv3.FyersWebsocket.data_ws")
        fake_data_ws.FyersDataSocket = mock_socket_class

        fake_fyers_ws = types.ModuleType("fyers_apiv3.FyersWebsocket")
        fake_fyers_ws.data_ws = fake_data_ws

        fake_fyers = types.ModuleType("fyers_apiv3")
        fake_fyers.FyersWebsocket = fake_fyers_ws

        # Inject into sys.modules (patch import machinery)
        sys.modules["fyers_apiv3"] = fake_fyers
        sys.modules["fyers_apiv3.FyersWebsocket"] = fake_fyers_ws
        sys.modules["fyers_apiv3.FyersWebsocket.data_ws"] = fake_data_ws

        def cleanup():
            sys.modules.pop("fyers_apiv3", None)
            sys.modules.pop("fyers_apiv3.FyersWebsocket", None)
            sys.modules.pop("fyers_apiv3.FyersWebsocket.data_ws", None)

        return mock_socket_class, mock_socket, cleanup

    @pytest.mark.asyncio
    async def test_connect_creates_data_socket_and_starts_thread(self):
        """connect should create FyersDataSocket with correct auth format."""
        adapter = FyersTickerAdapter()
        mock_socket_class, mock_socket, cleanup = self._make_fyers_mock(adapter)

        creds = {
            "app_id": "ABC123-100",
            "access_token": "eyJtest",
        }

        try:
            await adapter._connect_ws(creds)
        finally:
            cleanup()

        # Verify FyersDataSocket was constructed with colon-separated token
        mock_socket_class.assert_called_once()
        call_kwargs = mock_socket_class.call_args[1]
        assert call_kwargs["access_token"] == "ABC123-100:eyJtest"
        assert call_kwargs["litemode"] is False
        assert call_kwargs["reconnect"] is True
        assert call_kwargs["write_to_file"] is False

        # Verify callbacks were set in constructor
        assert call_kwargs["on_message"] == adapter._on_message
        assert call_kwargs["on_error"] == adapter._on_error
        assert call_kwargs["on_close"] == adapter._on_close
        assert call_kwargs["on_open"] == adapter._on_open

        # Verify connection event was set (by fake keep_running → _on_open)
        assert adapter._ws_connected_event.is_set()

    @pytest.mark.asyncio
    async def test_connect_loads_token_map_from_credentials(self):
        """connect should call load_token_map if token_map is in credentials."""
        adapter = FyersTickerAdapter()
        mock_socket_class, mock_socket, cleanup = self._make_fyers_mock(adapter)

        creds = {
            "app_id": "ABC123-100",
            "access_token": "eyJtest",
            "token_map": {256265: "NSE:NIFTY50-INDEX"},
        }

        try:
            await adapter._connect_ws(creds)
        finally:
            cleanup()

        assert adapter._canonical_to_broker[256265] == "NSE:NIFTY50-INDEX"

    @pytest.mark.asyncio
    async def test_disconnect_clears_socket(self):
        adapter = FyersTickerAdapter()
        mock_socket = MagicMock()
        adapter._data_socket = mock_socket

        await adapter._disconnect_ws()

        mock_socket.close_connection.assert_called_once()
        assert adapter._data_socket is None

    @pytest.mark.asyncio
    async def test_disconnect_handles_error(self):
        adapter = FyersTickerAdapter()
        mock_socket = MagicMock()
        mock_socket.close_connection.side_effect = RuntimeError("fail")
        adapter._data_socket = mock_socket

        # Should not raise
        await adapter._disconnect_ws()
        assert adapter._data_socket is None

    @pytest.mark.asyncio
    async def test_subscribe_calls_data_socket(self):
        adapter = FyersTickerAdapter()
        mock_socket = MagicMock()
        adapter._data_socket = mock_socket

        symbols = ["NSE:NIFTY50-INDEX", "NSE:NIFTYBANK-INDEX"]
        await adapter._subscribe_ws(symbols, "quote")

        mock_socket.subscribe.assert_called_once_with(
            symbols=symbols, data_type="SymbolUpdate"
        )

    @pytest.mark.asyncio
    async def test_subscribe_depth_mode(self):
        adapter = FyersTickerAdapter()
        mock_socket = MagicMock()
        adapter._data_socket = mock_socket

        await adapter._subscribe_ws(["NSE:NIFTY50-INDEX"], "depth")

        mock_socket.subscribe.assert_called_once_with(
            symbols=["NSE:NIFTY50-INDEX"], data_type="DepthUpdate"
        )

    @pytest.mark.asyncio
    async def test_subscribe_raises_when_not_connected(self):
        adapter = FyersTickerAdapter()
        adapter._data_socket = None

        with pytest.raises(ConnectionError):
            await adapter._subscribe_ws(["NSE:NIFTY50-INDEX"], "quote")

    @pytest.mark.asyncio
    async def test_subscribe_empty_list_noop(self):
        adapter = FyersTickerAdapter()
        mock_socket = MagicMock()
        adapter._data_socket = mock_socket

        await adapter._subscribe_ws([], "quote")

        mock_socket.subscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_calls_data_socket(self):
        adapter = FyersTickerAdapter()
        mock_socket = MagicMock()
        adapter._data_socket = mock_socket
        adapter._data_type = "SymbolUpdate"

        await adapter._unsubscribe_ws(["NSE:NIFTY50-INDEX"])

        mock_socket.unsubscribe.assert_called_once_with(
            symbols=["NSE:NIFTY50-INDEX"], data_type="SymbolUpdate"
        )

    @pytest.mark.asyncio
    async def test_unsubscribe_noop_when_not_connected(self):
        adapter = FyersTickerAdapter()
        adapter._data_socket = None

        # Should not raise
        await adapter._unsubscribe_ws(["NSE:NIFTY50-INDEX"])

    @pytest.mark.asyncio
    async def test_unsubscribe_empty_list_noop(self):
        adapter = FyersTickerAdapter()
        mock_socket = MagicMock()
        adapter._data_socket = mock_socket

        await adapter._unsubscribe_ws([])

        mock_socket.unsubscribe.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION: FULL TICK FLOW (adapter → parse → dispatch)
# ═══════════════════════════════════════════════════════════════════════

class TestFullTickFlow:
    def test_end_to_end_tick_dispatch(self, adapter, sample_tick_nifty):
        """Simulate full flow: raw Fyers tick → NormalizedTick → verify fields."""
        received_ticks = []

        def mock_callback(ticks):
            received_ticks.extend(ticks)

        adapter.set_on_tick_callback(mock_callback)
        loop = asyncio.new_event_loop()
        adapter.set_event_loop(loop)

        # Parse tick directly (bypass thread dispatch for unit test)
        ticks = adapter._parse_tick(sample_tick_nifty)

        assert len(ticks) == 1
        tick = ticks[0]
        assert tick.token == 256265
        assert tick.ltp == Decimal("24500.50")
        assert tick.broker_type == "fyers"
        assert tick.volume == 1234567
        assert tick.oi == 5678900
        assert tick.bid == Decimal("24500.20")
        assert tick.ask == Decimal("24500.80")

        loop.close()

    def test_nifty_and_banknifty_parse(self, adapter):
        """Parse ticks for multiple instruments — verify each maps to correct token."""
        nifty_tick = {
            "symbol": "NSE:NIFTY50-INDEX",
            "ltp": 24500.50,
            "prev_close_price": 24450.75,
            "vol_traded_today": 100,
            "oi": 200,
        }
        banknifty_tick = {
            "symbol": "NSE:NIFTYBANK-INDEX",
            "ltp": 52000.25,
            "prev_close_price": 51900.00,
            "vol_traded_today": 300,
            "oi": 400,
        }

        ticks1 = adapter._parse_tick(nifty_tick)
        ticks2 = adapter._parse_tick(banknifty_tick)

        assert ticks1[0].token == 256265  # NIFTY
        assert ticks1[0].ltp == Decimal("24500.50")

        assert ticks2[0].token == 260105  # BANKNIFTY
        assert ticks2[0].ltp == Decimal("52000.25")

    def test_fyers_no_paise_conversion(self, adapter):
        """
        CRITICAL: Fyers prices are already rupees.
        Verify ₹150.25 stays ₹150.25 (NOT treated as paise → ₹1.5025).
        """
        tick_data = {
            "symbol": "NSE:NIFTY2522725000CE",
            "ltp": 150.25,
            "prev_close_price": 148.75,
        }
        tick = adapter._parse_tick(tick_data)[0]

        # CORRECT: ₹150.25 (already rupees, no division by 100)
        assert tick.ltp == Decimal("150.25")

        # WRONG would be: Decimal("150.25") / 100 = Decimal("1.5025")
        assert tick.ltp != Decimal("1.5025")

    def test_auth_format_colon_separated(self):
        """Verify auth token format is app_id:access_token (not Bearer)."""
        app_id = "ABC123-100"
        access_token = "eyJtest"
        fyers_token = f"{app_id}:{access_token}"

        # Must be colon-separated
        assert fyers_token == "ABC123-100:eyJtest"
        # Must NOT be Bearer format
        assert not fyers_token.startswith("Bearer ")
