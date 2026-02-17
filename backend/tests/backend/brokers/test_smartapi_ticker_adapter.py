"""Tests for SmartAPI Ticker Adapter.

Tests cover:
- Adapter creation and configuration
- Token mapping (canonical ↔ broker)
- Tick parsing (paise → Decimal rupees, change calculation)
- Broker token translation (grouping by exchange type)
- WebSocket callback → dispatch bridging
- Connection lifecycle
"""

import asyncio
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.brokers.market_data.ticker.adapters.smartapi import (
    SmartAPITickerAdapter,
)
from app.services.brokers.market_data.ticker.models import NormalizedTick


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def adapter():
    """Create adapter with pre-loaded token map."""
    a = SmartAPITickerAdapter()
    # Load well-known index token mappings
    a.load_token_map({
        256265: ("99926000", 1),   # NIFTY 50 → NSE
        260105: ("99926009", 1),   # NIFTY BANK → NSE
        257801: ("99926037", 1),   # NIFTY FIN SERVICE → NSE
        100001: ("12345", 2),     # Synthetic F&O token → NFO
    })
    return a


@pytest.fixture
def sample_tick_nifty():
    """Sample SmartAPI tick for NIFTY 50 (prices in paise)."""
    return {
        "token": "99926000",
        "last_traded_price": 2450050,      # ₹24500.50
        "open_price_of_the_day": 2440000,  # ₹24400.00
        "high_price_of_the_day": 2455025,  # ₹24550.25
        "low_price_of_the_day": 2438000,   # ₹24380.00
        "closed_price": 2445075,           # ₹24450.75 (prev close)
        "volume_trade_for_the_day": 1234567,
        "open_interest": 5678900,
        "exchange_timestamp": 1708070400000,
    }


@pytest.fixture
def sample_tick_zero_close():
    """Tick with zero close price (edge case for change_percent)."""
    return {
        "token": "99926000",
        "last_traded_price": 100,
        "open_price_of_the_day": 0,
        "high_price_of_the_day": 200,
        "low_price_of_the_day": 0,
        "closed_price": 0,
        "volume_trade_for_the_day": 0,
        "open_interest": 0,
    }


# ═══════════════════════════════════════════════════════════════════════
# CREATION & CONFIG
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterCreation:
    def test_default_broker_type(self):
        adapter = SmartAPITickerAdapter()
        assert adapter.broker_type == "smartapi"

    def test_custom_broker_type(self):
        adapter = SmartAPITickerAdapter(broker_type="smartapi_platform")
        assert adapter.broker_type == "smartapi_platform"

    def test_initial_state(self):
        adapter = SmartAPITickerAdapter()
        assert not adapter.is_connected
        assert adapter.subscribed_tokens == set()
        assert adapter.last_tick_time is None
        assert adapter.reconnect_count == 0

    def test_mode_constants(self):
        assert SmartAPITickerAdapter.MODES["ltp"] == 1
        assert SmartAPITickerAdapter.MODES["quote"] == 2
        assert SmartAPITickerAdapter.MODES["snap"] == 3
        assert SmartAPITickerAdapter.MODES["depth"] == 4

    def test_exchange_type_constants(self):
        assert SmartAPITickerAdapter.EXCHANGE_NSE == 1
        assert SmartAPITickerAdapter.EXCHANGE_NFO == 2
        assert SmartAPITickerAdapter.EXCHANGE_BSE == 3
        assert SmartAPITickerAdapter.EXCHANGE_BFO == 4
        assert SmartAPITickerAdapter.EXCHANGE_MCX == 5


# ═══════════════════════════════════════════════════════════════════════
# TOKEN MAPPING
# ═══════════════════════════════════════════════════════════════════════

class TestTokenMapping:
    def test_load_token_map(self, adapter):
        assert adapter._canonical_to_broker[256265] == "99926000"
        assert adapter._broker_to_canonical["99926000"] == 256265
        assert adapter._token_exchange_type[256265] == 1  # NSE

    def test_load_multiple_tokens(self, adapter):
        assert len(adapter._canonical_to_broker) == 4
        assert len(adapter._broker_to_canonical) == 4

    def test_get_canonical_token_found(self, adapter):
        assert adapter._get_canonical_token("99926000") == 256265
        assert adapter._get_canonical_token("99926009") == 260105

    def test_get_canonical_token_not_found(self, adapter):
        assert adapter._get_canonical_token("99999999") == 0

    def test_get_canonical_token_int_input(self, adapter):
        """_get_canonical_token should handle int input by converting to str."""
        assert adapter._get_canonical_token(99926000) == 256265

    def test_load_token_map_incremental(self, adapter):
        """Loading more tokens should merge, not replace."""
        adapter.load_token_map({999: ("55555", 5)})
        assert adapter._canonical_to_broker[999] == "55555"
        # Old mappings still present
        assert adapter._canonical_to_broker[256265] == "99926000"


# ═══════════════════════════════════════════════════════════════════════
# TOKEN TRANSLATION
# ═══════════════════════════════════════════════════════════════════════

class TestTokenTranslation:
    def test_translate_single_nse_token(self, adapter):
        result = adapter._translate_to_broker_tokens([256265])
        assert len(result) == 1
        assert result[0]["exchangeType"] == 1  # NSE
        assert "99926000" in result[0]["tokens"]

    def test_translate_multiple_same_exchange(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 260105])
        # Both are NSE, should be grouped
        assert len(result) == 1
        assert result[0]["exchangeType"] == 1
        assert set(result[0]["tokens"]) == {"99926000", "99926009"}

    def test_translate_multiple_different_exchanges(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 100001])
        # NSE + NFO = two groups
        assert len(result) == 2
        exchange_types = {r["exchangeType"] for r in result}
        assert exchange_types == {1, 2}

    def test_translate_unknown_token_skipped(self, adapter):
        result = adapter._translate_to_broker_tokens([999999])
        assert result == []

    def test_translate_mixed_known_unknown(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 999999])
        assert len(result) == 1
        assert result[0]["tokens"] == ["99926000"]

    def test_translate_empty_list(self, adapter):
        assert adapter._translate_to_broker_tokens([]) == []

    def test_translate_default_exchange_type(self):
        """Tokens without explicit exchange type default to NFO."""
        a = SmartAPITickerAdapter()
        a._canonical_to_broker[42] = "ABCDE"
        a._broker_to_canonical["ABCDE"] = 42
        # No exchange type set → defaults to NFO (2)
        result = a._translate_to_broker_tokens([42])
        assert result[0]["exchangeType"] == 2


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
        assert tick.broker_type == "smartapi"

    def test_prices_converted_to_decimal_rupees(self, adapter, sample_tick_nifty):
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

    def test_timestamp_set(self, adapter, sample_tick_nifty):
        tick = adapter._parse_tick(sample_tick_nifty)[0]
        assert isinstance(tick.timestamp, datetime)

    def test_zero_close_no_division_error(self, adapter, sample_tick_zero_close):
        ticks = adapter._parse_tick(sample_tick_zero_close)

        assert len(ticks) == 1
        assert ticks[0].change_percent == Decimal("0")

    def test_missing_token_returns_empty(self, adapter):
        assert adapter._parse_tick({}) == []
        assert adapter._parse_tick({"token": None}) == []

    def test_unknown_broker_token_returns_empty(self, adapter):
        tick_data = {
            "token": "99999999",
            "last_traded_price": 100,
        }
        assert adapter._parse_tick(tick_data) == []

    def test_missing_price_fields_default_to_zero(self, adapter):
        tick_data = {
            "token": "99926000",
            "last_traded_price": 100,
            # All other fields missing
        }
        ticks = adapter._parse_tick(tick_data)
        assert len(ticks) == 1
        assert ticks[0].ltp == Decimal("1")  # 100 paise = ₹1
        assert ticks[0].open == Decimal("0")
        assert ticks[0].high == Decimal("0")

    def test_none_volume_oi_treated_as_zero(self, adapter):
        tick_data = {
            "token": "99926000",
            "last_traded_price": 100,
            "volume_trade_for_the_day": None,
            "open_interest": None,
        }
        ticks = adapter._parse_tick(tick_data)
        assert ticks[0].volume == 0
        assert ticks[0].oi == 0

    def test_paise_precision_small_values(self, adapter):
        """Verify precision for small option premiums (e.g., ₹0.05)."""
        tick_data = {
            "token": "99926000",
            "last_traded_price": 5,  # ₹0.05 in paise
            "closed_price": 10,     # ₹0.10 prev close
        }
        tick = adapter._parse_tick(tick_data)[0]
        assert tick.ltp == Decimal("0.05")
        assert tick.close == Decimal("0.10")
        assert tick.change == Decimal("-0.05")


# ═══════════════════════════════════════════════════════════════════════
# DISPATCH BRIDGING
# ═══════════════════════════════════════════════════════════════════════

class TestDispatchBridging:
    def test_on_data_calls_dispatch(self, adapter, sample_tick_nifty):
        """_on_data should parse tick and call _dispatch_from_thread."""
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_data(ws=None, message=sample_tick_nifty)

        adapter._dispatch_from_thread.assert_called_once()
        ticks = adapter._dispatch_from_thread.call_args[0][0]
        assert len(ticks) == 1
        assert isinstance(ticks[0], NormalizedTick)
        assert ticks[0].token == 256265

    def test_on_data_skips_empty_parse(self, adapter):
        """_on_data should not dispatch when parsing returns empty list."""
        adapter._dispatch_from_thread = MagicMock()

        adapter._on_data(ws=None, message={"token": "unknown"})

        adapter._dispatch_from_thread.assert_not_called()

    def test_on_data_handles_exception(self, adapter):
        """_on_data should not raise even on parse errors."""
        adapter._parse_tick = MagicMock(side_effect=RuntimeError("boom"))

        # Should not raise
        adapter._on_data(ws=None, message={"token": "99926000"})


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION CALLBACKS
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionCallbacks:
    def test_on_open_sets_event(self, adapter):
        assert not adapter._ws_connected_event.is_set()
        adapter._on_open(ws=None)
        assert adapter._ws_connected_event.is_set()

    def test_on_close_clears_event_and_connected(self, adapter):
        adapter._ws_connected_event.set()
        adapter._connected = True

        adapter._on_close(ws=None, code=1000, reason="normal")

        assert not adapter._ws_connected_event.is_set()
        assert not adapter._connected

    def test_on_error_does_not_raise(self, adapter):
        """_on_error should log but not raise."""
        adapter._on_error(ws=None, error="test error")


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE (with mocked SmartWebSocketV2)
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionLifecycle:
    @pytest.mark.asyncio
    async def test_connect_creates_sws_and_starts_thread(self):
        """connect should create SmartWebSocketV2 and start daemon thread."""
        mock_sws_class = MagicMock()
        mock_sws = MagicMock()
        mock_sws_class.return_value = mock_sws

        adapter = SmartAPITickerAdapter()

        # Simulate _on_open firing when sws.connect() is called
        def fake_connect():
            adapter._on_open(ws=None)

        mock_sws.connect = fake_connect

        creds = {
            "jwt_token": "test_jwt",
            "api_key": "test_key",
            "client_id": "TEST123",
            "feed_token": "test_feed",
        }

        with patch("SmartApi.smartWebSocketV2.SmartWebSocketV2", mock_sws_class):
            await adapter._connect_ws(creds)

        # Verify SmartWebSocketV2 was constructed with correct args
        mock_sws_class.assert_called_once_with(
            auth_token="test_jwt",
            api_key="test_key",
            client_code="TEST123",
            feed_token="test_feed",
        )

        # Verify callbacks were set
        assert mock_sws.on_open == adapter._on_open
        assert mock_sws.on_data == adapter._on_data
        assert mock_sws.on_error == adapter._on_error
        assert mock_sws.on_close == adapter._on_close

        # Verify connection event was set (by fake_connect → _on_open)
        assert adapter._ws_connected_event.is_set()

    @pytest.mark.asyncio
    async def test_disconnect_clears_sws(self):
        adapter = SmartAPITickerAdapter()
        mock_sws = MagicMock()
        adapter.sws = mock_sws

        await adapter._disconnect_ws()

        mock_sws.close_connection.assert_called_once()
        assert adapter.sws is None

    @pytest.mark.asyncio
    async def test_disconnect_handles_error(self):
        adapter = SmartAPITickerAdapter()
        mock_sws = MagicMock()
        mock_sws.close_connection.side_effect = RuntimeError("fail")
        adapter.sws = mock_sws

        # Should not raise
        await adapter._disconnect_ws()
        assert adapter.sws is None

    @pytest.mark.asyncio
    async def test_subscribe_calls_sws(self):
        adapter = SmartAPITickerAdapter()
        mock_sws = MagicMock()
        adapter.sws = mock_sws

        broker_tokens = [{"exchangeType": 2, "tokens": ["12345"]}]
        await adapter._subscribe_ws(broker_tokens, "quote")

        mock_sws.subscribe.assert_called_once_with("ticker_pool", 2, broker_tokens)

    @pytest.mark.asyncio
    async def test_subscribe_raises_when_not_connected(self):
        adapter = SmartAPITickerAdapter()
        adapter.sws = None

        with pytest.raises(ConnectionError):
            await adapter._subscribe_ws([{"exchangeType": 2, "tokens": ["1"]}], "quote")

    @pytest.mark.asyncio
    async def test_unsubscribe_calls_sws(self):
        adapter = SmartAPITickerAdapter()
        mock_sws = MagicMock()
        adapter.sws = mock_sws

        broker_tokens = [{"exchangeType": 2, "tokens": ["12345"]}]
        await adapter._unsubscribe_ws(broker_tokens)

        mock_sws.unsubscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe_noop_when_not_connected(self):
        adapter = SmartAPITickerAdapter()
        adapter.sws = None

        # Should not raise
        await adapter._unsubscribe_ws([{"exchangeType": 2, "tokens": ["1"]}])


# ═══════════════════════════════════════════════════════════════════════
# INTEGRATION: FULL TICK FLOW (adapter → parse → dispatch)
# ═══════════════════════════════════════════════════════════════════════

class TestFullTickFlow:
    def test_end_to_end_tick_dispatch(self, adapter, sample_tick_nifty):
        """Simulate full flow: raw SmartAPI tick → NormalizedTick → callback."""
        received_ticks = []

        def mock_callback(ticks):
            received_ticks.extend(ticks)

        adapter.set_on_tick_callback(mock_callback)
        # Simulate having an event loop (in real code, set by TickerPool)
        loop = asyncio.new_event_loop()
        adapter.set_event_loop(loop)

        # Bypass thread dispatch — call _dispatch_async directly
        ticks = adapter._parse_tick(sample_tick_nifty)
        assert len(ticks) == 1

        # Verify tick properties
        tick = ticks[0]
        assert tick.token == 256265
        assert tick.ltp == Decimal("24500.50")
        assert tick.broker_type == "smartapi"
        assert tick.volume == 1234567
        assert tick.oi == 5678900

        loop.close()

    def test_multiple_ticks_different_tokens(self, adapter):
        """Parse ticks for multiple instruments."""
        tick1 = {
            "token": "99926000",
            "last_traded_price": 2450050,
            "closed_price": 2445075,
            "volume_trade_for_the_day": 100,
            "open_interest": 200,
        }
        tick2 = {
            "token": "99926009",
            "last_traded_price": 5200025,
            "closed_price": 5190000,
            "volume_trade_for_the_day": 300,
            "open_interest": 400,
        }

        ticks1 = adapter._parse_tick(tick1)
        ticks2 = adapter._parse_tick(tick2)

        assert ticks1[0].token == 256265  # NIFTY
        assert ticks1[0].ltp == Decimal("24500.50")

        assert ticks2[0].token == 260105  # BANKNIFTY
        assert ticks2[0].ltp == Decimal("52000.25")
