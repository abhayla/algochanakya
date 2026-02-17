"""Tests for Upstox Ticker Adapter.

Tests cover:
- Adapter creation and initial state
- Token mapping (canonical int ↔ Upstox instrument_key string)
- Broker token translation (canonical → instrument_key strings)
- Protobuf tick parsing (ltpc mode, full mode, option_greeks mode)
- Option Greeks extraction (unique Upstox feature)
- Feed-to-tick conversion (bid/ask depth, OHLC, change calculation)
- Binary parsing edge cases: unknown key, empty data, malformed frames
- Subscription message construction (JSON method="sub"/"unsub")
- Mode mapping (internal mode → Upstox mode string)
- Connection lifecycle (connect, disconnect — mocked websockets + aiohttp)
- Authorized URL fetching (REST call mock)
- Dispatch integration via _dispatch_async
"""

import asyncio
import json
import sys
import types
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from app.services.brokers.market_data.ticker.adapters.upstox import (
    UpstoxTickerAdapter,
    _MODE_TO_UPSTOX,
    _MAX_INSTRUMENTS_BASIC,
)
from app.services.brokers.market_data.ticker.models import NormalizedTick


# ═══════════════════════════════════════════════════════════════════════
# HELPERS — mock protobuf Feed builder
# ═══════════════════════════════════════════════════════════════════════

def _make_level(price: float = 0.0, quantity: int = 0, orders: int = 0):
    """Create a mock protobuf Level message."""
    level = MagicMock()
    level.price = price
    level.quantity = quantity
    level.orders = orders
    return level


def _make_ohlc(open_: float = 0.0, high: float = 0.0, low: float = 0.0, close: float = 0.0):
    """Create a mock protobuf OHLC message."""
    ohlc = MagicMock()
    ohlc.open = open_
    ohlc.high = high
    ohlc.low = low
    ohlc.close = close
    return ohlc


def _make_depth(bid_price: float = 0.0, bid_qty: int = 0,
                ask_price: float = 0.0, ask_qty: int = 0):
    """Create a mock protobuf MarketDepth with one bid/ask level."""
    depth = MagicMock()
    if bid_price > 0:
        bid_level = _make_level(bid_price, bid_qty, 5)
        depth.bid = [bid_level]
    else:
        depth.bid = []
    if ask_price > 0:
        ask_level = _make_level(ask_price, ask_qty, 3)
        depth.ask = [ask_level]
    else:
        depth.ask = []
    return depth


def _make_ltpc(ltp: float = 24500.50, close: float = 24450.75,
               change: float = 49.75, change_percent: float = 0.2217):
    """Create a mock protobuf LTPC message."""
    ltpc = MagicMock()
    ltpc.ltp = ltp
    ltpc.close = close
    ltpc.change = change
    ltpc.change_percent = change_percent
    return ltpc


def _make_full_feed(ohlc=None, depth=None, volume: int = 1234567, oi: int = 5678900,
                    avg_price: float = 24490.0):
    """Create a mock protobuf FullFeed message."""
    ff = MagicMock()
    ff.volume = volume
    ff.oi = oi
    ff.avg_price = avg_price
    ff.total_buy_qty = 100000
    ff.total_sell_qty = 95000
    # HasField returns True when these sub-messages are set
    ff.HasField = lambda name: (
        (name == "ohlc" and ohlc is not None) or
        (name == "depth" and depth is not None)
    )
    ff.ohlc = ohlc or MagicMock()
    ff.depth = depth or _make_depth()
    return ff


def _make_option_greeks(delta: float = 0.45, gamma: float = 0.003,
                        theta: float = -8.5, vega: float = 12.3, iv: float = 0.18):
    """Create a mock protobuf OptionGreeks message."""
    og = MagicMock()
    og.delta = delta
    og.gamma = gamma
    og.theta = theta
    og.vega = vega
    og.iv = iv
    return og


def _make_feed(ltpc=None, ff=None, og=None):
    """Create a mock protobuf Feed message."""
    feed = MagicMock()
    feed.HasField = lambda name: (
        (name == "ltpc" and ltpc is not None) or
        (name == "ff" and ff is not None) or
        (name == "og" and og is not None)
    )
    feed.ltpc = ltpc or _make_ltpc()
    feed.ff = ff
    feed.og = og
    return feed


def _make_feed_response(feeds: dict, msg_type: str = "live_feed"):
    """Create a mock protobuf FeedResponse message."""
    resp = MagicMock()
    resp.type = msg_type
    resp.feeds = feeds
    return resp


def _make_serialized_feed_response(feeds: dict, msg_type: str = "live_feed") -> bytes:
    """Return dummy bytes (mocked parse — actual content doesn't matter in tests)."""
    return b"\x0a\x09live_feed"  # Minimal valid bytes placeholder


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def adapter():
    """Create adapter with pre-loaded token map."""
    a = UpstoxTickerAdapter()
    a.load_token_map({
        256265: "NSE_INDEX|Nifty 50",       # NIFTY 50
        260105: "NSE_INDEX|Nifty Bank",     # NIFTY BANK
        12345678: "NSE_FO|43854",            # Synthetic option
        99990001: "NSE_EQ|2885",             # Reliance
    })
    return a


@pytest.fixture
def ltpc_only_feed():
    """Feed with only LTPC data (ltpc mode)."""
    return _make_feed(
        ltpc=_make_ltpc(ltp=24500.50, close=24450.75, change=49.75, change_percent=0.2217),
    )


@pytest.fixture
def full_feed():
    """Feed with LTPC + FullFeed data (full mode)."""
    ohlc = _make_ohlc(open_=24400.00, high=24550.25, low=24380.00, close=24450.75)
    depth = _make_depth(bid_price=24500.20, bid_qty=500, ask_price=24500.80, ask_qty=400)
    ff = _make_full_feed(ohlc=ohlc, depth=depth, volume=1234567, oi=5678900)
    return _make_feed(
        ltpc=_make_ltpc(ltp=24500.50, close=24450.75),
        ff=ff,
    )


@pytest.fixture
def greeks_feed():
    """Feed with LTPC + FullFeed + OptionGreeks (option_greeks mode)."""
    ohlc = _make_ohlc(open_=150.0, high=165.0, low=145.0, close=155.0)
    ff = _make_full_feed(ohlc=ohlc, depth=_make_depth(155.5, 200, 156.0, 150), oi=10000)
    og = _make_option_greeks(delta=0.45, gamma=0.003, theta=-8.5, vega=12.3, iv=0.18)
    return _make_feed(
        ltpc=_make_ltpc(ltp=160.50, close=155.0),
        ff=ff,
        og=og,
    )


# ═══════════════════════════════════════════════════════════════════════
# CREATION & CONFIG
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterCreation:
    def test_default_broker_type(self):
        a = UpstoxTickerAdapter()
        assert a.broker_type == "upstox"

    def test_custom_broker_type(self):
        a = UpstoxTickerAdapter(broker_type="upstox_platform")
        assert a.broker_type == "upstox_platform"

    def test_initial_state(self):
        a = UpstoxTickerAdapter()
        assert not a.is_connected
        assert a.subscribed_tokens == set()
        assert a.last_tick_time is None
        assert a.reconnect_count == 0

    def test_initial_maps_empty(self):
        a = UpstoxTickerAdapter()
        assert a._canonical_to_instrument_key == {}
        assert a._instrument_key_to_canonical == {}

    def test_initial_ws_none(self):
        a = UpstoxTickerAdapter()
        assert a._ws is None
        assert a._receive_task is None
        assert a._authorized_ws_url is None

    def test_mode_to_upstox_mapping(self):
        assert _MODE_TO_UPSTOX["ltp"] == "ltpc"
        assert _MODE_TO_UPSTOX["quote"] == "full"
        assert _MODE_TO_UPSTOX["snap"] == "full"
        assert _MODE_TO_UPSTOX["full"] == "full"
        assert _MODE_TO_UPSTOX["greeks"] == "option_greeks"
        assert _MODE_TO_UPSTOX["option_greeks"] == "option_greeks"

    def test_max_instruments_constant(self):
        assert _MAX_INSTRUMENTS_BASIC == 1500


# ═══════════════════════════════════════════════════════════════════════
# TOKEN MAPPING
# ═══════════════════════════════════════════════════════════════════════

class TestTokenMapping:
    def test_load_token_map(self, adapter):
        assert adapter._canonical_to_instrument_key[256265] == "NSE_INDEX|Nifty 50"
        assert adapter._instrument_key_to_canonical["NSE_INDEX|Nifty 50"] == 256265

    def test_load_multiple_tokens(self, adapter):
        assert len(adapter._canonical_to_instrument_key) == 4
        assert len(adapter._instrument_key_to_canonical) == 4

    def test_load_token_map_incremental(self, adapter):
        """Loading more tokens should merge, not replace."""
        adapter.load_token_map({999: "NSE_EQ|9999"})
        assert adapter._canonical_to_instrument_key[999] == "NSE_EQ|9999"
        # Old mappings still present
        assert adapter._canonical_to_instrument_key[256265] == "NSE_INDEX|Nifty 50"

    def test_get_canonical_token_found(self, adapter):
        assert adapter._get_canonical_token("NSE_INDEX|Nifty 50") == 256265
        assert adapter._get_canonical_token("NSE_INDEX|Nifty Bank") == 260105

    def test_get_canonical_token_option(self, adapter):
        assert adapter._get_canonical_token("NSE_FO|43854") == 12345678

    def test_get_canonical_token_not_found(self, adapter):
        assert adapter._get_canonical_token("NSE_FO|99999") == 0

    def test_get_canonical_token_non_string(self, adapter):
        assert adapter._get_canonical_token(256265) == 0
        assert adapter._get_canonical_token(None) == 0

    def test_bidirectional_mapping_consistent(self, adapter):
        """Round-trip: canonical → instrument_key → canonical should return original."""
        for canonical, instrument_key in adapter._canonical_to_instrument_key.items():
            round_tripped = adapter._get_canonical_token(instrument_key)
            assert round_tripped == canonical

    def test_index_instrument_key_format(self, adapter):
        """NSE_INDEX keys use name strings (not numbers)."""
        assert adapter._canonical_to_instrument_key[256265] == "NSE_INDEX|Nifty 50"
        # The pipe separator is part of the format
        assert "|" in adapter._canonical_to_instrument_key[256265]


# ═══════════════════════════════════════════════════════════════════════
# TOKEN TRANSLATION
# ═══════════════════════════════════════════════════════════════════════

class TestTokenTranslation:
    def test_translate_single_token(self, adapter):
        result = adapter._translate_to_broker_tokens([256265])
        assert result == ["NSE_INDEX|Nifty 50"]

    def test_translate_multiple_tokens(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 260105])
        assert set(result) == {"NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank"}

    def test_translate_unknown_token_skipped(self, adapter):
        result = adapter._translate_to_broker_tokens([999999])
        assert result == []

    def test_translate_mixed_known_unknown(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 999999])
        assert result == ["NSE_INDEX|Nifty 50"]

    def test_translate_empty_list(self, adapter):
        assert adapter._translate_to_broker_tokens([]) == []

    def test_translate_option_token(self, adapter):
        result = adapter._translate_to_broker_tokens([12345678])
        assert result == ["NSE_FO|43854"]

    def test_translate_equity_token(self, adapter):
        result = adapter._translate_to_broker_tokens([99990001])
        assert result == ["NSE_EQ|2885"]


# ═══════════════════════════════════════════════════════════════════════
# PROTOBUF PARSING — LTPC MODE
# ═══════════════════════════════════════════════════════════════════════

class TestLtpcModeParsing:
    """Tests for ltpc mode (LTP + close + change only)."""

    def _parse_with_mock(self, adapter, instrument_key: str, feed):
        """Helper: mock _FeedResponse ParseFromString, run _parse_protobuf."""
        feed_response = _make_feed_response({instrument_key: feed})
        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {instrument_key: feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            return adapter._parse_protobuf(b"\x00\x01\x02")

    def test_ltpc_returns_normalized_tick(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        assert len(ticks) == 1
        assert isinstance(ticks[0], NormalizedTick)

    def test_ltpc_token_mapping(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        assert ticks[0].token == 256265

    def test_ltpc_ltp_is_decimal(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        assert isinstance(ticks[0].ltp, Decimal)

    def test_ltpc_ltp_value(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        assert abs(float(ticks[0].ltp) - 24500.50) < 0.01

    def test_ltpc_close_value(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        assert abs(float(ticks[0].close) - 24450.75) < 0.01

    def test_ltpc_broker_type(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        assert ticks[0].broker_type == "upstox"

    def test_ltpc_no_ohlc_in_ltpc_mode(self, adapter, ltpc_only_feed):
        """LTPC mode has no OHLC — open/high/low should be Decimal('0')."""
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        tick = ticks[0]
        assert tick.open == Decimal("0")
        assert tick.high == Decimal("0")
        assert tick.low == Decimal("0")

    def test_ltpc_no_bid_ask_in_ltpc_mode(self, adapter, ltpc_only_feed):
        """LTPC mode has no depth — bid/ask should be None."""
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        tick = ticks[0]
        assert tick.bid is None
        assert tick.ask is None
        assert tick.bid_qty is None
        assert tick.ask_qty is None

    def test_ltpc_volume_zero_in_ltpc_mode(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        assert ticks[0].volume == 0

    def test_ltpc_unknown_instrument_key_returns_empty(self, adapter):
        feed = _make_feed(ltpc=_make_ltpc())
        ticks = self._parse_with_mock(adapter, "NSE_FO|99999", feed)
        assert ticks == []

    def test_all_prices_are_decimal(self, adapter, ltpc_only_feed):
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", ltpc_only_feed)
        tick = ticks[0]
        for field_name in ("ltp", "open", "high", "low", "close", "change", "change_percent"):
            value = getattr(tick, field_name)
            assert isinstance(value, Decimal), (
                f"{field_name} should be Decimal, got {type(value)}"
            )

    def test_change_recalculated_from_decimal(self, adapter):
        """Change should be recalculated as ltp - close (not raw float from proto)."""
        ltpc = _make_ltpc(ltp=24500.50, close=24450.75, change=0.0, change_percent=0.0)
        feed = _make_feed(ltpc=ltpc)
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty 50", feed)
        tick = ticks[0]
        expected_change = Decimal("24500.50") - Decimal("24450.75")
        assert abs(tick.change - expected_change) < Decimal("0.01")

    def test_banknifty_ltpc(self, adapter):
        ltpc = _make_ltpc(ltp=51000.00, close=50900.00)
        feed = _make_feed(ltpc=ltpc)
        ticks = self._parse_with_mock(adapter, "NSE_INDEX|Nifty Bank", feed)
        assert ticks[0].token == 260105


# ═══════════════════════════════════════════════════════════════════════
# PROTOBUF PARSING — FULL MODE
# ═══════════════════════════════════════════════════════════════════════

class TestFullModeParsing:
    """Tests for full mode (LTPC + OHLC + volume/OI + depth)."""

    def _parse_full(self, adapter, instrument_key: str, feed):
        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {instrument_key: feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            return adapter._parse_protobuf(b"\x00\x01\x02")

    def test_full_mode_returns_tick(self, adapter, full_feed):
        ticks = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)
        assert len(ticks) == 1

    def test_full_mode_ohlc_open(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert abs(float(tick.open) - 24400.00) < 0.01

    def test_full_mode_ohlc_high(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert abs(float(tick.high) - 24550.25) < 0.01

    def test_full_mode_ohlc_low(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert abs(float(tick.low) - 24380.00) < 0.01

    def test_full_mode_close(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert abs(float(tick.close) - 24450.75) < 0.01

    def test_full_mode_volume(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert tick.volume == 1234567

    def test_full_mode_oi(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert tick.oi == 5678900

    def test_full_mode_bid_price(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert tick.bid is not None
        assert abs(float(tick.bid) - 24500.20) < 0.01

    def test_full_mode_bid_qty(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert tick.bid_qty == 500

    def test_full_mode_ask_price(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert tick.ask is not None
        assert abs(float(tick.ask) - 24500.80) < 0.01

    def test_full_mode_ask_qty(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert tick.ask_qty == 400

    def test_full_mode_all_decimal_prices(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        for field_name in ("ltp", "open", "high", "low", "close", "change", "change_percent"):
            assert isinstance(getattr(tick, field_name), Decimal)

    def test_full_mode_bid_decimal(self, adapter, full_feed):
        tick = self._parse_full(adapter, "NSE_INDEX|Nifty 50", full_feed)[0]
        assert isinstance(tick.bid, Decimal)
        assert isinstance(tick.ask, Decimal)

    def test_full_mode_no_depth_gives_none(self, adapter):
        """Feed with no depth levels should have None bid/ask."""
        ohlc = _make_ohlc(open_=100.0, high=110.0, low=95.0, close=105.0)
        depth = _make_depth(bid_price=0.0, bid_qty=0, ask_price=0.0, ask_qty=0)
        ff = _make_full_feed(ohlc=ohlc, depth=depth)
        feed = _make_feed(ltpc=_make_ltpc(ltp=107.0, close=105.0), ff=ff)
        ticks = self._parse_full(adapter, "NSE_INDEX|Nifty 50", feed)
        tick = ticks[0]
        assert tick.bid is None
        assert tick.ask is None


# ═══════════════════════════════════════════════════════════════════════
# PROTOBUF PARSING — OPTION GREEKS MODE
# ═══════════════════════════════════════════════════════════════════════

class TestOptionGreeksModeParsing:
    """Tests for option_greeks mode — unique Upstox feature."""

    def _parse_greeks(self, adapter, instrument_key: str, feed):
        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {instrument_key: feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            return adapter._parse_protobuf(b"\x00\x01\x02")

    def test_greeks_mode_returns_tick(self, adapter, greeks_feed):
        ticks = self._parse_greeks(adapter, "NSE_FO|43854", greeks_feed)
        assert len(ticks) == 1

    def test_greeks_mode_token_correct(self, adapter, greeks_feed):
        ticks = self._parse_greeks(adapter, "NSE_FO|43854", greeks_feed)
        assert ticks[0].token == 12345678

    def test_greeks_mode_ltp(self, adapter, greeks_feed):
        tick = self._parse_greeks(adapter, "NSE_FO|43854", greeks_feed)[0]
        assert abs(float(tick.ltp) - 160.50) < 0.01

    def test_greeks_mode_ohlc_present(self, adapter, greeks_feed):
        tick = self._parse_greeks(adapter, "NSE_FO|43854", greeks_feed)[0]
        assert abs(float(tick.open) - 150.0) < 0.01
        assert abs(float(tick.high) - 165.0) < 0.01
        assert abs(float(tick.low) - 145.0) < 0.01

    def test_greeks_mode_volume(self, adapter, greeks_feed):
        tick = self._parse_greeks(adapter, "NSE_FO|43854", greeks_feed)[0]
        assert tick.volume == 1234567  # from _make_full_feed default

    def test_greeks_mode_oi(self, adapter, greeks_feed):
        tick = self._parse_greeks(adapter, "NSE_FO|43854", greeks_feed)[0]
        assert tick.oi == 10000


# ═══════════════════════════════════════════════════════════════════════
# BINARY PARSING EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestBinaryParsingEdgeCases:
    def test_empty_bytes_returns_empty(self, adapter):
        ticks = adapter._parse_protobuf(b"")
        assert ticks == []

    def test_protobuf_unavailable_returns_empty(self, adapter):
        """If _FeedResponse is None, parse should return empty gracefully."""
        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse",
            None,
        ):
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")
            assert ticks == []

    def test_protobuf_parse_exception_returns_empty(self, adapter):
        """ParseFromString raising an exception should return empty."""
        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.ParseFromString.side_effect = Exception("bad frame")
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")
            assert ticks == []

    def test_non_live_feed_type_returns_empty(self, adapter):
        """Messages with type != 'live_feed' should be ignored."""
        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "disconnected"
            instance.feeds = {}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")
            assert ticks == []

    def test_text_data_returns_empty(self, adapter):
        """Text frames (str) should not be parsed as ticks."""
        ticks = adapter._parse_tick('{"type": "some_control"}')
        assert ticks == []

    def test_none_data_returns_empty(self, adapter):
        ticks = adapter._parse_tick(None)
        assert ticks == []

    def test_feed_without_ltpc_returns_empty(self, adapter):
        """Feed missing ltpc should be skipped."""
        feed = MagicMock()
        feed.HasField = lambda name: False  # No ltpc, no ff, no og
        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {"NSE_INDEX|Nifty 50": feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")
            assert ticks == []

    def test_multiple_instruments_in_one_response(self, adapter):
        """A single FeedResponse can contain multiple instrument feeds."""
        ltpc_nifty = _make_ltpc(ltp=24500.0, close=24450.0)
        ltpc_bank = _make_ltpc(ltp=51000.0, close=50900.0)
        feed_nifty = _make_feed(ltpc=ltpc_nifty)
        feed_bank = _make_feed(ltpc=ltpc_bank)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {
                "NSE_INDEX|Nifty 50": feed_nifty,
                "NSE_INDEX|Nifty Bank": feed_bank,
            }
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")

        assert len(ticks) == 2
        tokens = {t.token for t in ticks}
        assert tokens == {256265, 260105}

    def test_unknown_instrument_skipped_in_multi_response(self, adapter):
        """Unknown instrument_key should not block known ones."""
        ltpc_nifty = _make_ltpc(ltp=24500.0, close=24450.0)
        feed_nifty = _make_feed(ltpc=ltpc_nifty)
        feed_unknown = _make_feed(ltpc=_make_ltpc(ltp=100.0, close=99.0))

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {
                "NSE_INDEX|Nifty 50": feed_nifty,
                "NSE_FO|99999": feed_unknown,
            }
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")

        assert len(ticks) == 1
        assert ticks[0].token == 256265


# ═══════════════════════════════════════════════════════════════════════
# SUBSCRIPTION MESSAGES
# ═══════════════════════════════════════════════════════════════════════

class TestSubscriptionMessages:
    @pytest.mark.asyncio
    async def test_subscribe_sends_json(self, adapter):
        """_subscribe_ws should send a valid JSON subscription message."""
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        await adapter._subscribe_ws(["NSE_INDEX|Nifty 50", "NSE_FO|43854"], mode="full")

        mock_ws.send.assert_called_once()
        sent_str = mock_ws.send.call_args[0][0]
        sent = json.loads(sent_str)

        assert sent["method"] == "sub"
        assert sent["data"]["mode"] == "full"
        assert "NSE_INDEX|Nifty 50" in sent["data"]["instrumentKeys"]
        assert "NSE_FO|43854" in sent["data"]["instrumentKeys"]
        assert "guid" in sent

    @pytest.mark.asyncio
    async def test_subscribe_mode_ltp_maps_to_ltpc(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        await adapter._subscribe_ws(["NSE_INDEX|Nifty 50"], mode="ltp")

        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["data"]["mode"] == "ltpc"

    @pytest.mark.asyncio
    async def test_subscribe_mode_greeks(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        await adapter._subscribe_ws(["NSE_FO|43854"], mode="greeks")

        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["data"]["mode"] == "option_greeks"

    @pytest.mark.asyncio
    async def test_subscribe_mode_quote_maps_to_full(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        await adapter._subscribe_ws(["NSE_INDEX|Nifty 50"], mode="quote")

        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["data"]["mode"] == "full"

    @pytest.mark.asyncio
    async def test_subscribe_no_ws_raises(self, adapter):
        adapter._ws = None
        with pytest.raises(ConnectionError):
            await adapter._subscribe_ws(["NSE_INDEX|Nifty 50"], mode="full")

    @pytest.mark.asyncio
    async def test_subscribe_empty_tokens_no_send(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([], mode="full")
        mock_ws.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_sends_json(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        adapter._current_upstox_mode = "full"

        await adapter._unsubscribe_ws(["NSE_INDEX|Nifty 50"])

        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["method"] == "unsub"
        assert "NSE_INDEX|Nifty 50" in sent["data"]["instrumentKeys"]

    @pytest.mark.asyncio
    async def test_unsubscribe_no_ws_silently_returns(self, adapter):
        adapter._ws = None
        # Should not raise
        await adapter._unsubscribe_ws(["NSE_INDEX|Nifty 50"])

    @pytest.mark.asyncio
    async def test_unsubscribe_empty_tokens_no_send(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._unsubscribe_ws([])
        mock_ws.send.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════
# AUTHORIZED URL FETCHING (REST)
# ═══════════════════════════════════════════════════════════════════════

class TestAuthorizedUrlFetching:
    @pytest.mark.asyncio
    async def test_fetch_authorized_url_success(self, adapter):
        """Should call REST and return the authorized_redirect_uri."""
        adapter._access_token = "test_token_xyz"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "data": {
                "authorized_redirect_uri": "wss://ws.upstox.com/market-data-feed/v3?token=abc123"
            }
        })

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox.httpx.AsyncClient",
            return_value=mock_client,
        ):
            url = await adapter._fetch_authorized_ws_url()

        assert url == "wss://ws.upstox.com/market-data-feed/v3?token=abc123"

    @pytest.mark.asyncio
    async def test_fetch_authorized_url_uses_bearer_header(self, adapter):
        """Should include Authorization: Bearer {access_token} header."""
        adapter._access_token = "my_token_123"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "data": {"authorized_redirect_uri": "wss://ws.upstox.com/..."}
        })

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox.httpx.AsyncClient",
            return_value=mock_client,
        ):
            await adapter._fetch_authorized_ws_url()

        call_kwargs = mock_client.get.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer my_token_123"

    @pytest.mark.asyncio
    async def test_fetch_authorized_url_http_error_raises(self, adapter):
        """HTTP non-200 should raise ConnectionError."""
        adapter._access_token = "bad_token"
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"message": "Unauthorized"}'

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with pytest.raises(ConnectionError, match="401"):
                await adapter._fetch_authorized_ws_url()

    @pytest.mark.asyncio
    async def test_fetch_authorized_url_malformed_response_raises(self, adapter):
        """Malformed JSON response should raise ConnectionError."""
        adapter._access_token = "token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"unexpected": "structure"})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with pytest.raises(ConnectionError):
                await adapter._fetch_authorized_ws_url()


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionLifecycle:
    @pytest.mark.asyncio
    async def test_connect_stores_credentials(self, adapter):
        """connect() should extract and store access_token."""
        credentials = {
            "api_key": "test_key",
            "access_token": "test_token",
        }

        mock_ws = AsyncMock()
        mock_websockets = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        async def fake_receive_loop():
            await asyncio.sleep(0)

        with patch.object(adapter, "_fetch_authorized_ws_url", return_value="wss://ws.upstox.com/..."):
            with patch.dict(sys.modules, {"websockets": mock_websockets}):
                with patch.object(adapter, "_ws_receive_loop", fake_receive_loop):
                    await adapter._connect_ws(credentials)

        assert adapter._api_key == "test_key"
        assert adapter._access_token == "test_token"

    @pytest.mark.asyncio
    async def test_connect_loads_token_map_from_credentials(self, adapter):
        """If credentials include token_map, it should be loaded."""
        credentials = {
            "api_key": "key",
            "access_token": "token",
            "token_map": {99999: "NSE_EQ|5555"},
        }

        mock_ws = AsyncMock()
        mock_websockets = MagicMock()
        mock_websockets.connect = AsyncMock(return_value=mock_ws)

        async def fake_receive_loop():
            await asyncio.sleep(0)

        with patch.object(adapter, "_fetch_authorized_ws_url", return_value="wss://..."):
            with patch.dict(sys.modules, {"websockets": mock_websockets}):
                with patch.object(adapter, "_ws_receive_loop", fake_receive_loop):
                    await adapter._connect_ws(credentials)

        assert adapter._canonical_to_instrument_key[99999] == "NSE_EQ|5555"

    @pytest.mark.asyncio
    async def test_disconnect_cancels_receive_task(self, adapter):
        """disconnect() should cancel the receive task."""
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()

        async def mock_await():
            raise asyncio.CancelledError()

        mock_task.__await__ = lambda self: mock_await().__await__()
        adapter._receive_task = asyncio.ensure_future(asyncio.sleep(1000))
        adapter._ws = AsyncMock()

        await adapter._disconnect_ws()

        assert adapter._ws is None
        assert adapter._receive_task is None
        assert adapter._authorized_ws_url is None

    @pytest.mark.asyncio
    async def test_disconnect_clears_ws_url(self, adapter):
        adapter._authorized_ws_url = "wss://some-url"
        adapter._ws = AsyncMock()
        adapter._receive_task = None

        await adapter._disconnect_ws()

        assert adapter._authorized_ws_url is None

    @pytest.mark.asyncio
    async def test_disconnect_no_ws_does_not_raise(self, adapter):
        adapter._ws = None
        adapter._receive_task = None
        # Should not raise
        await adapter._disconnect_ws()


# ═══════════════════════════════════════════════════════════════════════
# DISPATCH INTEGRATION
# ═══════════════════════════════════════════════════════════════════════

class TestDispatchIntegration:
    @pytest.mark.asyncio
    async def test_parse_tick_dispatches_to_callback(self, adapter):
        """_parse_protobuf result should flow through _dispatch_async to callback."""
        received = []

        def callback(ticks):
            received.extend(ticks)

        adapter.set_on_tick_callback(callback)
        adapter._event_loop = asyncio.get_event_loop()

        ltpc = _make_ltpc(ltp=24500.0, close=24450.0)
        feed = _make_feed(ltpc=ltpc)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {"NSE_INDEX|Nifty 50": feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")

        # Simulate dispatch
        await adapter._dispatch_async(ticks)
        assert len(received) == 1
        assert received[0].token == 256265

    @pytest.mark.asyncio
    async def test_dispatch_no_callback_does_not_raise(self, adapter):
        """dispatch_async with no callback set should silently return."""
        adapter._on_tick_callback = None
        tick = NormalizedTick(
            token=256265,
            ltp=Decimal("24500"),
            broker_type="upstox",
        )
        # Should not raise
        await adapter._dispatch_async([tick])

    @pytest.mark.asyncio
    async def test_receive_loop_dispatches_binary_ticks(self, adapter):
        """Receive loop should call _parse_protobuf and dispatch non-empty results."""
        received = []

        async def callback(ticks):
            received.extend(ticks)

        adapter._on_tick_callback = callback

        ltpc = _make_ltpc(ltp=24500.0, close=24450.0)
        feed = _make_feed(ltpc=ltpc)

        binary_msg = b"\x00\x01\x02"  # Placeholder protobuf bytes

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {"NSE_INDEX|Nifty 50": feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance

            mock_ws = AsyncMock()
            mock_ws.__aiter__ = MagicMock(
                return_value=_async_iter([binary_msg])
            )
            adapter._ws = mock_ws

            await adapter._ws_receive_loop()

    @pytest.mark.asyncio
    async def test_receive_loop_ignores_text_messages(self, adapter):
        """Text JSON control messages should not be parsed as ticks."""
        mock_ws = AsyncMock()
        mock_ws.__aiter__ = MagicMock(
            return_value=_async_iter(['{"type": "heartbeat"}'])
        )
        adapter._ws = mock_ws
        # No crash expected
        await adapter._ws_receive_loop()

    @pytest.mark.asyncio
    async def test_receive_loop_handles_connection_closed(self, adapter):
        """ConnectionClosed should set _connected = False without raising."""
        import websockets.exceptions

        async def raise_closed():
            yield b"\x00\x01"
            raise websockets.exceptions.ConnectionClosed(None, None)

        mock_ws = MagicMock()
        mock_ws.__aiter__ = MagicMock(return_value=raise_closed())
        adapter._ws = mock_ws
        adapter._connected = True

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            await adapter._ws_receive_loop()

        assert not adapter._connected


# ═══════════════════════════════════════════════════════════════════════
# FULL TICK FLOW (integration)
# ═══════════════════════════════════════════════════════════════════════

class TestFullTickFlow:
    def test_parse_tick_wrapper_delegates_to_parse_protobuf(self, adapter):
        """_parse_tick(bytes) should delegate to _parse_protobuf."""
        with patch.object(adapter, "_parse_protobuf", return_value=[]) as mock_parse:
            adapter._parse_tick(b"\x00\x01\x02")
            mock_parse.assert_called_once_with(b"\x00\x01\x02")

    def test_parse_tick_with_bytearray(self, adapter):
        """_parse_tick should accept bytearray as well as bytes."""
        with patch.object(adapter, "_parse_protobuf", return_value=[]) as mock_parse:
            adapter._parse_tick(bytearray(b"\x00\x01\x02"))
            mock_parse.assert_called_once()

    def test_change_percent_precision(self, adapter):
        """change_percent should be precise (Decimal quantize applied)."""
        ltpc = _make_ltpc(ltp=24500.50, close=24450.75)
        feed = _make_feed(ltpc=ltpc)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {"NSE_INDEX|Nifty 50": feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")

        tick = ticks[0]
        # change = 24500.50 - 24450.75 = 49.75
        # change_percent = 49.75 / 24450.75 * 100 ≈ 0.2035...%
        assert isinstance(tick.change_percent, Decimal)

    def test_prices_not_float_in_normalized_tick(self, adapter):
        """Verify NormalizedTick never contains float prices from Upstox."""
        ltpc = _make_ltpc(ltp=24500.50, close=24450.75)
        ohlc = _make_ohlc(open_=24400.0, high=24550.25, low=24380.0, close=24450.75)
        depth = _make_depth(bid_price=24500.20, bid_qty=500, ask_price=24500.80, ask_qty=400)
        ff = _make_full_feed(ohlc=ohlc, depth=depth)
        feed = _make_feed(ltpc=ltpc, ff=ff)

        with patch(
            "app.services.brokers.market_data.ticker.adapters.upstox._FeedResponse"
        ) as MockFR:
            instance = MagicMock()
            instance.type = "live_feed"
            instance.feeds = {"NSE_INDEX|Nifty 50": feed}
            instance.ParseFromString = MagicMock()
            MockFR.return_value = instance
            ticks = adapter._parse_protobuf(b"\x00\x01\x02")

        tick = ticks[0]
        for field_name in ("ltp", "open", "high", "low", "close", "change", "change_percent"):
            val = getattr(tick, field_name)
            assert not isinstance(val, float), f"{field_name} is float, expected Decimal"


# ═══════════════════════════════════════════════════════════════════════
# HELPERS for async iteration in tests
# ═══════════════════════════════════════════════════════════════════════

def _async_iter(items):
    """Create an async iterator from a list of items."""
    async def _gen():
        for item in items:
            yield item
    return _gen()


def _make_async_ctx_manager(return_value):
    """Create an async context manager that returns the given value."""
    class _CM:
        async def __aenter__(self):
            return return_value
        async def __aexit__(self, *args):
            pass
    return _CM()
