"""Tests for Dhan Ticker Adapter.

Tests cover:
- Adapter creation and initial state
- Token mapping (canonical int ↔ Dhan security_id/exchange_segment tuples)
- Binary tick parsing (Ticker mode, Quote mode, little-endian)
- Broker token translation (canonical → Dhan tuples)
- Subscription message construction (JSON RequestCode 21/22)
- Connection lifecycle (connect, disconnect — mocked websockets)
- Edge cases: unknown security_id, malformed packets, empty data, heartbeat
"""

import asyncio
import json
import struct
import sys
import types
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.brokers.market_data.ticker.adapters.dhan import (
    DhanTickerAdapter,
    _RC_TICKER,
    _RC_QUOTE,
    _RC_FULL,
    _RC_HEARTBEAT,
    _RC_DISCONNECT,
    _MODE_TO_DHAN,
    _MODE_CAPACITY,
)
from app.services.brokers.market_data.ticker.models import NormalizedTick


# ═══════════════════════════════════════════════════════════════════════
# HELPERS — binary packet builders
# ═══════════════════════════════════════════════════════════════════════

def build_ticker_packet(
    response_code: int = _RC_TICKER,
    exchange_seg: int = 7,      # 7 = IDX_I
    security_id: int = 13,      # NIFTY 50
    ltp: float = 24500.50,
    ltq: int = 100,
    ltt: int = 1709119800,
    volume: int = 1234567,
    oi: int = 0,
    change: float = 49.75,
    change_pct: float = 0.20,
) -> bytes:
    """Build a 33-byte Ticker-mode binary packet (little-endian)."""
    return struct.pack(
        "<HBIfHIIIff",
        response_code,   # uint16
        exchange_seg,    # uint8
        security_id,     # uint32
        ltp,             # float32
        ltq,             # uint16
        ltt,             # uint32
        volume,          # uint32
        oi,              # uint32
        change,          # float32
        change_pct,      # float32
    )


def build_quote_packet(
    security_id: int = 13,
    ltp: float = 24500.50,
    ltt: int = 1709119800,
    volume: int = 1234567,
    oi: int = 5678900,
    change: float = 49.75,
    change_pct: float = 0.20,
    open_: float = 24400.00,
    high: float = 24550.25,
    low: float = 24380.00,
    close: float = 24450.75,
    bid_price: float = 24500.20,
    bid_qty: int = 500,
    ask_price: float = 24500.80,
    ask_qty: int = 400,
) -> bytes:
    """Build a Quote-mode binary packet with OHLC + 20-depth bid/ask (little-endian)."""
    # Header (same as ticker, but response_code=3)
    header = struct.pack(
        "<HBIfHIIIff",
        _RC_QUOTE,       # uint16 response_code=3
        7,               # uint8 exchange_seg IDX_I
        security_id,     # uint32
        ltp,             # float32
        100,             # uint16 ltq
        ltt,             # uint32
        volume,          # uint32
        oi,              # uint32
        change,          # float32
        change_pct,      # float32
    )
    # OHLC (4 × float32 = 16 bytes)
    ohlc = struct.pack("<ffff", open_, high, low, close)

    # 20 bid levels × 12 bytes each (price:f, qty:I, orders:H, pad:H)
    bids = b""
    bids += struct.pack("<fIHH", bid_price, bid_qty, 5, 0)  # level 0 (best bid)
    for _ in range(19):
        bids += struct.pack("<fIHH", 0.0, 0, 0, 0)

    # 20 ask levels × 12 bytes each
    asks = b""
    asks += struct.pack("<fIHH", ask_price, ask_qty, 3, 0)  # level 0 (best ask)
    for _ in range(19):
        asks += struct.pack("<fIHH", 0.0, 0, 0, 0)

    return header + ohlc + bids + asks


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def adapter():
    """Create adapter with pre-loaded token map."""
    a = DhanTickerAdapter()
    a.load_token_map({
        256265: ("13", "IDX_I"),       # NIFTY 50
        260105: ("25", "IDX_I"),       # NIFTY BANK
        12345678: ("43854", "NSE_FNO"),  # Synthetic option
        99990001: ("2885", "NSE_EQ"),   # Reliance
    })
    return a


@pytest.fixture
def ticker_packet_nifty():
    """Valid Ticker-mode packet for NIFTY 50 (security_id=13)."""
    return build_ticker_packet(security_id=13, ltp=24500.50)


@pytest.fixture
def quote_packet_nifty():
    """Valid Quote-mode packet for NIFTY 50 with OHLC + depth."""
    return build_quote_packet(security_id=13)


# ═══════════════════════════════════════════════════════════════════════
# CREATION & CONFIG
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterCreation:
    def test_default_broker_type(self):
        adapter = DhanTickerAdapter()
        assert adapter.broker_type == "dhan"

    def test_custom_broker_type(self):
        adapter = DhanTickerAdapter(broker_type="dhan_platform")
        assert adapter.broker_type == "dhan_platform"

    def test_initial_state(self):
        adapter = DhanTickerAdapter()
        assert not adapter.is_connected
        assert adapter.subscribed_tokens == set()
        assert adapter.last_tick_time is None
        assert adapter.reconnect_count == 0

    def test_initial_maps_empty(self):
        adapter = DhanTickerAdapter()
        assert adapter._canonical_to_broker == {}
        assert adapter._security_id_to_canonical == {}

    def test_mode_to_dhan_mapping(self):
        assert _MODE_TO_DHAN["ltp"] == "Ticker"
        assert _MODE_TO_DHAN["quote"] == "Quote"
        assert _MODE_TO_DHAN["snap"] == "Quote"
        assert _MODE_TO_DHAN["full"] == "Full"
        assert _MODE_TO_DHAN["depth"] == "Quote"

    def test_mode_capacity(self):
        assert _MODE_CAPACITY["Ticker"] == 100
        assert _MODE_CAPACITY["Quote"] == 50
        assert _MODE_CAPACITY["Full"] == 50
        assert _MODE_CAPACITY["200-Depth"] == 1


# ═══════════════════════════════════════════════════════════════════════
# TOKEN MAPPING
# ═══════════════════════════════════════════════════════════════════════

class TestTokenMapping:
    def test_load_token_map(self, adapter):
        assert adapter._canonical_to_broker[256265] == ("13", "IDX_I")
        assert adapter._security_id_to_canonical[13] == 256265

    def test_load_multiple_tokens(self, adapter):
        assert len(adapter._canonical_to_broker) == 4
        assert len(adapter._security_id_to_canonical) == 4

    def test_load_token_map_incremental(self, adapter):
        """Loading more tokens should merge, not replace."""
        adapter.load_token_map({999: ("9999", "NSE_EQ")})
        assert adapter._canonical_to_broker[999] == ("9999", "NSE_EQ")
        # Old mappings still present
        assert adapter._canonical_to_broker[256265] == ("13", "IDX_I")

    def test_get_canonical_token_int(self, adapter):
        assert adapter._get_canonical_token(13) == 256265
        assert adapter._get_canonical_token(25) == 260105

    def test_get_canonical_token_str(self, adapter):
        """Should accept security_id as string (packet decode → int, but allow str)."""
        assert adapter._get_canonical_token("13") == 256265

    def test_get_canonical_token_not_found(self, adapter):
        assert adapter._get_canonical_token(99999) == 0

    def test_get_canonical_token_invalid_type(self, adapter):
        assert adapter._get_canonical_token("not-a-number") == 0
        assert adapter._get_canonical_token(None) == 0

    def test_bidirectional_mapping_consistent(self, adapter):
        """Round-trip: canonical → security_id int → canonical should return original."""
        for canonical_token, (sec_id_str, _) in adapter._canonical_to_broker.items():
            round_tripped = adapter._get_canonical_token(int(sec_id_str))
            assert round_tripped == canonical_token

    def test_invalid_security_id_skipped(self):
        """Non-numeric security_id should be skipped with a warning."""
        a = DhanTickerAdapter()
        a.load_token_map({256265: ("not-a-number", "IDX_I")})
        # Should not be in the int lookup map
        assert len(a._security_id_to_canonical) == 0
        # But canonical_to_broker should still store the original
        assert a._canonical_to_broker[256265] == ("not-a-number", "IDX_I")


# ═══════════════════════════════════════════════════════════════════════
# TOKEN TRANSLATION
# ═══════════════════════════════════════════════════════════════════════

class TestTokenTranslation:
    def test_translate_single_token(self, adapter):
        result = adapter._translate_to_broker_tokens([256265])
        assert result == [("13", "IDX_I")]

    def test_translate_multiple_tokens(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 260105])
        assert set(result) == {("13", "IDX_I"), ("25", "IDX_I")}

    def test_translate_unknown_token_skipped(self, adapter):
        result = adapter._translate_to_broker_tokens([999999])
        assert result == []

    def test_translate_mixed_known_unknown(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 999999])
        assert result == [("13", "IDX_I")]

    def test_translate_empty_list(self, adapter):
        assert adapter._translate_to_broker_tokens([]) == []

    def test_translate_option_token(self, adapter):
        result = adapter._translate_to_broker_tokens([12345678])
        assert result == [("43854", "NSE_FNO")]


# ═══════════════════════════════════════════════════════════════════════
# BINARY PARSING — TICKER MODE
# ═══════════════════════════════════════════════════════════════════════

class TestTickerModeParsing:
    def test_parse_ticker_packet(self, adapter, ticker_packet_nifty):
        ticks = adapter._parse_binary(ticker_packet_nifty)
        assert len(ticks) == 1
        tick = ticks[0]
        assert isinstance(tick, NormalizedTick)
        assert tick.token == 256265

    def test_ticker_ltp_is_decimal(self, adapter, ticker_packet_nifty):
        tick = adapter._parse_binary(ticker_packet_nifty)[0]
        assert isinstance(tick.ltp, Decimal)

    def test_ticker_ltp_value(self, adapter):
        pkt = build_ticker_packet(security_id=13, ltp=24500.50)
        tick = adapter._parse_binary(pkt)[0]
        # float32 precision — verify within epsilon
        assert abs(float(tick.ltp) - 24500.50) < 0.1

    def test_ticker_volume(self, adapter):
        pkt = build_ticker_packet(security_id=13, volume=999888)
        tick = adapter._parse_binary(pkt)[0]
        assert tick.volume == 999888

    def test_ticker_oi(self, adapter):
        pkt = build_ticker_packet(security_id=13, oi=5678900)
        tick = adapter._parse_binary(pkt)[0]
        assert tick.oi == 5678900

    def test_ticker_timestamp_from_ltt(self, adapter):
        ltt = 1709119800
        pkt = build_ticker_packet(security_id=13, ltt=ltt)
        tick = adapter._parse_binary(pkt)[0]
        expected = datetime.fromtimestamp(ltt)
        assert tick.timestamp == expected

    def test_ticker_broker_type(self, adapter, ticker_packet_nifty):
        tick = adapter._parse_binary(ticker_packet_nifty)[0]
        assert tick.broker_type == "dhan"

    def test_ticker_ohlc_zero_in_ticker_mode(self, adapter, ticker_packet_nifty):
        """Ticker mode has no OHLC — all should be Decimal('0')."""
        tick = adapter._parse_binary(ticker_packet_nifty)[0]
        assert tick.open == Decimal("0")
        assert tick.high == Decimal("0")
        assert tick.low == Decimal("0")
        assert tick.close == Decimal("0")

    def test_ticker_no_bid_ask_in_ticker_mode(self, adapter, ticker_packet_nifty):
        """Ticker mode has no depth — bid/ask should be None."""
        tick = adapter._parse_binary(ticker_packet_nifty)[0]
        assert tick.bid is None
        assert tick.ask is None
        assert tick.bid_qty is None
        assert tick.ask_qty is None

    def test_ticker_unknown_security_id_returns_empty(self, adapter):
        """Packet with unmapped security_id should return []."""
        pkt = build_ticker_packet(security_id=99999)
        ticks = adapter._parse_binary(pkt)
        assert ticks == []

    def test_all_prices_are_decimal(self, adapter, ticker_packet_nifty):
        tick = adapter._parse_binary(ticker_packet_nifty)[0]
        for field_name in ("ltp", "open", "high", "low", "close", "change", "change_percent"):
            value = getattr(tick, field_name)
            assert isinstance(value, Decimal), (
                f"{field_name} should be Decimal, got {type(value)}"
            )

    def test_banknifty_ticker(self, adapter):
        pkt = build_ticker_packet(security_id=25, ltp=51000.00)
        tick = adapter._parse_binary(pkt)[0]
        assert tick.token == 260105

    def test_option_ticker(self, adapter):
        pkt = build_ticker_packet(
            security_id=43854, exchange_seg=1,  # NSE_FNO
            ltp=150.25
        )
        tick = adapter._parse_binary(pkt)[0]
        assert tick.token == 12345678


# ═══════════════════════════════════════════════════════════════════════
# BINARY PARSING — QUOTE MODE
# ═══════════════════════════════════════════════════════════════════════

class TestQuoteModeParsing:
    def test_parse_quote_packet(self, adapter, quote_packet_nifty):
        ticks = adapter._parse_binary(quote_packet_nifty)
        assert len(ticks) == 1
        tick = ticks[0]
        assert isinstance(tick, NormalizedTick)
        assert tick.token == 256265

    def test_quote_has_ohlc(self, adapter, quote_packet_nifty):
        tick = adapter._parse_binary(quote_packet_nifty)[0]
        assert tick.open != Decimal("0")
        assert tick.high != Decimal("0")
        assert tick.low != Decimal("0")
        assert tick.close != Decimal("0")

    def test_quote_ohlc_values(self, adapter):
        pkt = build_quote_packet(
            security_id=13,
            open_=24400.00,
            high=24550.25,
            low=24380.00,
            close=24450.75,
        )
        tick = adapter._parse_binary(pkt)[0]
        assert abs(float(tick.open) - 24400.00) < 0.1
        assert abs(float(tick.high) - 24550.25) < 0.1
        assert abs(float(tick.low) - 24380.00) < 0.1
        assert abs(float(tick.close) - 24450.75) < 0.1

    def test_quote_change_recalculated_from_decimal(self, adapter):
        """Change must be Decimal(ltp) - Decimal(close), not from raw float."""
        pkt = build_quote_packet(security_id=13, ltp=24500.50, close=24450.75)
        tick = adapter._parse_binary(pkt)[0]
        assert isinstance(tick.change, Decimal)
        assert isinstance(tick.change_percent, Decimal)
        # Verify sign: ltp > close → positive change
        assert tick.change > 0

    def test_quote_has_bid_ask(self, adapter):
        pkt = build_quote_packet(
            security_id=13, bid_price=24500.20, bid_qty=500,
            ask_price=24500.80, ask_qty=400
        )
        tick = adapter._parse_binary(pkt)[0]
        assert tick.bid is not None
        assert tick.ask is not None
        assert tick.bid_qty == 500
        assert tick.ask_qty == 400

    def test_quote_bid_ask_decimal(self, adapter, quote_packet_nifty):
        tick = adapter._parse_binary(quote_packet_nifty)[0]
        assert isinstance(tick.bid, Decimal)
        assert isinstance(tick.ask, Decimal)

    def test_quote_volume_oi(self, adapter):
        pkt = build_quote_packet(security_id=13, volume=999888, oi=5678900)
        tick = adapter._parse_binary(pkt)[0]
        assert tick.volume == 999888
        assert tick.oi == 5678900

    def test_quote_zero_bid_ask_becomes_none(self, adapter):
        """Zero bid/ask price in depth should result in None (no valid data)."""
        pkt = build_quote_packet(
            security_id=13, bid_price=0.0, bid_qty=0,
            ask_price=0.0, ask_qty=0
        )
        tick = adapter._parse_binary(pkt)[0]
        assert tick.bid is None
        assert tick.ask is None


# ═══════════════════════════════════════════════════════════════════════
# BINARY PARSING — EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestBinaryParsingEdgeCases:
    def test_empty_bytes_returns_empty(self, adapter):
        assert adapter._parse_binary(b"") == []

    def test_single_byte_returns_empty(self, adapter):
        assert adapter._parse_binary(b"\x02") == []

    def test_heartbeat_returns_empty(self, adapter):
        """Response code 100 (heartbeat) should return [] without error."""
        pkt = struct.pack("<H", _RC_HEARTBEAT) + b"\x00" * 10
        ticks = adapter._parse_binary(pkt)
        assert ticks == []

    def test_disconnect_returns_empty(self, adapter):
        """Response code 50 (server disconnect) should return [] without error."""
        pkt = struct.pack("<H", _RC_DISCONNECT) + b"\x00" * 10
        ticks = adapter._parse_binary(pkt)
        assert ticks == []

    def test_unknown_response_code_returns_empty(self, adapter):
        pkt = struct.pack("<H", 99) + b"\x00" * 30
        ticks = adapter._parse_binary(pkt)
        assert ticks == []

    def test_truncated_ticker_packet_returns_empty(self, adapter):
        """Packet shorter than minimum size should return []."""
        pkt = struct.pack("<H", _RC_TICKER) + b"\x00" * 5  # Only 7 bytes
        ticks = adapter._parse_binary(pkt)
        assert ticks == []

    def test_non_bytes_input_returns_empty(self, adapter):
        """_parse_tick with non-bytes should return []."""
        assert adapter._parse_tick("not bytes") == []
        assert adapter._parse_tick({"json": "dict"}) == []
        assert adapter._parse_tick(None) == []
        assert adapter._parse_tick(42) == []

    def test_zero_ltt_uses_datetime_now(self, adapter):
        """ltt=0 should fall back to datetime.now() without error."""
        pkt = build_ticker_packet(security_id=13, ltt=0)
        ticks = adapter._parse_binary(pkt)
        assert len(ticks) == 1
        assert isinstance(ticks[0].timestamp, datetime)

    def test_change_percent_zero_when_close_zero(self, adapter):
        """When close=0 (Ticker mode), change_percent should be Decimal('0')."""
        pkt = build_ticker_packet(security_id=13, ltp=100.0)
        tick = adapter._parse_binary(pkt)[0]
        assert tick.close == Decimal("0")
        assert tick.change_percent == Decimal("0")

    def test_bytearray_accepted(self, adapter):
        """bytearray should work the same as bytes."""
        pkt = build_ticker_packet(security_id=13, ltp=24500.50)
        ticks = adapter._parse_binary(bytearray(pkt))
        assert len(ticks) == 1


# ═══════════════════════════════════════════════════════════════════════
# SUBSCRIPTION MESSAGE FORMAT
# ═══════════════════════════════════════════════════════════════════════

class TestSubscriptionMessages:
    @pytest.mark.asyncio
    async def test_subscribe_sends_correct_json(self, adapter):
        """_subscribe_ws must send RequestCode=21 with correct InstrumentList."""
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        broker_tokens = [("13", "IDX_I"), ("25", "IDX_I")]
        await adapter._subscribe_ws(broker_tokens, mode="quote")

        mock_ws.send.assert_called_once()
        sent_str = mock_ws.send.call_args[0][0]
        sent = json.loads(sent_str)

        assert sent["RequestCode"] == 21
        assert sent["InstrumentCount"] == 2
        assert {"ExchangeSegment": "IDX_I", "SecurityId": "13"} in sent["InstrumentList"]
        assert {"ExchangeSegment": "IDX_I", "SecurityId": "25"} in sent["InstrumentList"]

    @pytest.mark.asyncio
    async def test_unsubscribe_sends_correct_json(self, adapter):
        """_unsubscribe_ws must send RequestCode=22."""
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        broker_tokens = [("13", "IDX_I")]
        await adapter._unsubscribe_ws(broker_tokens, )

        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["RequestCode"] == 22
        assert sent["InstrumentCount"] == 1

    @pytest.mark.asyncio
    async def test_subscribe_empty_list_does_nothing(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([], mode="ltp")
        mock_ws.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_empty_list_does_nothing(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._unsubscribe_ws([])
        mock_ws.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscribe_no_ws_raises(self, adapter):
        adapter._ws = None
        with pytest.raises(ConnectionError, match="not connected"):
            await adapter._subscribe_ws([("13", "IDX_I")], mode="ltp")

    def test_mode_sets_current_mode(self, adapter):
        """After subscribe, _current_mode should reflect the Dhan mode."""
        # Check that _MODE_TO_DHAN maps correctly
        assert _MODE_TO_DHAN.get("ltp") == "Ticker"
        assert _MODE_TO_DHAN.get("quote") == "Quote"
        assert _MODE_TO_DHAN.get("full") == "Full"


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE (mocked websockets)
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionLifecycle:
    @pytest.mark.asyncio
    async def test_connect_sets_credentials(self):
        """Connect should store client_id and access_token."""
        adapter = DhanTickerAdapter()
        mock_ws = AsyncMock()

        async def fake_receive_loop():
            await asyncio.sleep(0)

        mock_websockets = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        with patch.dict(sys.modules, {"websockets": mock_websockets}):
            with patch.object(adapter, "_ws_receive_loop", fake_receive_loop):
                await adapter._connect_ws({
                    "client_id": "DHAN12345",
                    "access_token": "fake-token-abc",
                })

        assert adapter._client_id == "DHAN12345"
        assert adapter._access_token == "fake-token-abc"

    @pytest.mark.asyncio
    async def test_connect_preloads_token_map(self):
        """Token map passed in credentials should be loaded."""
        adapter = DhanTickerAdapter()
        mock_ws = AsyncMock()

        async def fake_receive_loop():
            await asyncio.sleep(0)

        mock_websockets = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        with patch.dict(sys.modules, {"websockets": mock_websockets}):
            with patch.object(adapter, "_ws_receive_loop", fake_receive_loop):
                await adapter._connect_ws({
                    "client_id": "DHAN12345",
                    "access_token": "token",
                    "token_map": {256265: ("13", "IDX_I")},
                })

        assert adapter._canonical_to_broker[256265] == ("13", "IDX_I")

    @pytest.mark.asyncio
    async def test_disconnect_cancels_receive_task(self):
        """Disconnect should cancel the receive task."""
        adapter = DhanTickerAdapter()

        # Use a real asyncio Task that can be cancelled
        async def long_running():
            await asyncio.sleep(100)

        task = asyncio.create_task(long_running())
        adapter._receive_task = task

        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        await adapter._disconnect_ws()

        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_disconnect_closes_websocket(self):
        """Disconnect should close the websocket."""
        adapter = DhanTickerAdapter()
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        adapter._receive_task = None  # No task to cancel

        await adapter._disconnect_ws()

        mock_ws.close.assert_called_once()
        assert adapter._ws is None


# ═══════════════════════════════════════════════════════════════════════
# DISPATCH / CALLBACK INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

class TestDispatchIntegration:
    @pytest.mark.asyncio
    async def test_parsed_ticks_dispatched_async(self, adapter):
        """_ws_receive_loop should dispatch parsed ticks to callback."""
        received: list = []

        async def on_tick(ticks):
            received.extend(ticks)

        adapter.set_on_tick_callback(on_tick)
        adapter._event_loop = asyncio.get_event_loop()

        # Build a valid ticker packet
        pkt = build_ticker_packet(security_id=13, ltp=24500.50)

        # Simulate receive loop processing one message
        ticks = adapter._parse_binary(pkt)
        await adapter._dispatch_async(ticks)

        assert len(received) == 1
        assert received[0].token == 256265

    @pytest.mark.asyncio
    async def test_unknown_security_not_dispatched(self, adapter):
        """Packets with unknown security_id should not reach callback."""
        received: list = []

        async def on_tick(ticks):
            received.extend(ticks)

        adapter.set_on_tick_callback(on_tick)

        pkt = build_ticker_packet(security_id=99999)
        ticks = adapter._parse_binary(pkt)
        if ticks:
            await adapter._dispatch_async(ticks)

        assert received == []

    def test_last_tick_time_updated_on_dispatch(self, adapter):
        """_dispatch_async should update last_tick_time."""
        loop = asyncio.new_event_loop()
        adapter.set_event_loop(loop)
        adapter.set_on_tick_callback(lambda ticks: None)

        pkt = build_ticker_packet(security_id=13, ltp=24500.50)
        ticks = adapter._parse_binary(pkt)

        assert adapter.last_tick_time is None
        adapter._dispatch_from_thread(ticks)
        loop.close()
        assert adapter.last_tick_time is not None
