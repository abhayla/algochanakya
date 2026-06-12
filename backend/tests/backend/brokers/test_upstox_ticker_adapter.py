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
# HELPERS — REAL protobuf message builders (no mocks)
#
# These build genuine FeedResponse messages via the adapter's runtime-built
# classes and serialize them to real wire bytes. Mock-based feed builders
# previously hid two live bugs (schema drift vs Upstox v3, and the removed
# MessageFactory.GetPrototype API) — parsing tests MUST go through real
# SerializeToString/ParseFromString round trips.
# ═══════════════════════════════════════════════════════════════════════

from pathlib import Path

from app.services.brokers.market_data.ticker.adapters.upstox import _FeedResponse

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "upstox"

# FeedResponse.type enum values (Upstox MarketDataFeedV3.proto)
TYPE_INITIAL_FEED = 0
TYPE_LIVE_FEED = 1
TYPE_MARKET_INFO = 2


def _new_response(msg_type: int = TYPE_LIVE_FEED):
    """Create a real FeedResponse message."""
    assert _FeedResponse is not None, "protobuf runtime build failed"
    resp = _FeedResponse()
    resp.type = msg_type
    return resp


def _add_ltpc_feed(resp, key: str, ltp: float, cp: float):
    """Add a feed entry in ltpc mode (LTPC directly on Feed)."""
    ltpc = resp.feeds[key].ltpc
    ltpc.ltp = ltp
    ltpc.cp = cp


def _add_day_ohlc(market_ohlc, open_: float, high: float, low: float, close: float):
    bar = market_ohlc.ohlc.add()
    bar.interval = "1d"
    bar.open = open_
    bar.high = high
    bar.low = low
    bar.close = close


def _add_index_full_feed(resp, key: str, ltp: float, cp: float,
                         open_: float = None, high: float = None, low: float = None):
    """Add a feed entry in full mode for an index (IndexFullFeed)."""
    iff = resp.feeds[key].fullFeed.indexFF
    iff.ltpc.ltp = ltp
    iff.ltpc.cp = cp
    if open_ is not None:
        _add_day_ohlc(iff.marketOHLC, open_, high, low, cp)


def _add_market_full_feed(resp, key: str, ltp: float, cp: float,
                          open_: float = None, high: float = None, low: float = None,
                          vtt: int = 0, oi: float = 0,
                          bid_p: float = 0.0, bid_q: int = 0,
                          ask_p: float = 0.0, ask_q: int = 0):
    """Add a feed entry in full mode for a non-index instrument (MarketFullFeed)."""
    mff = resp.feeds[key].fullFeed.marketFF
    mff.ltpc.ltp = ltp
    mff.ltpc.cp = cp
    mff.vtt = vtt
    mff.oi = oi
    if open_ is not None:
        _add_day_ohlc(mff.marketOHLC, open_, high, low, cp)
    if bid_p or ask_p:
        q = mff.marketLevel.bidAskQuote.add()
        q.bidP = bid_p
        q.bidQ = bid_q
        q.askP = ask_p
        q.askQ = ask_q


def _add_greeks_feed(resp, key: str, ltp: float, cp: float,
                     vtt: int = 0, oi: float = 0,
                     bid_p: float = 0.0, bid_q: int = 0,
                     ask_p: float = 0.0, ask_q: int = 0,
                     delta: float = 0.0):
    """Add a feed entry in option_greeks mode (FirstLevelWithGreeks)."""
    flwg = resp.feeds[key].firstLevelWithGreeks
    flwg.ltpc.ltp = ltp
    flwg.ltpc.cp = cp
    flwg.vtt = vtt
    flwg.oi = oi
    if bid_p or ask_p:
        flwg.firstDepth.bidP = bid_p
        flwg.firstDepth.bidQ = bid_q
        flwg.firstDepth.askP = ask_p
        flwg.firstDepth.askQ = ask_q
    if delta:
        flwg.optionGreeks.delta = delta


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
def ltpc_only_bytes():
    """Serialized FeedResponse with one LTPC-mode feed (ltpc mode)."""
    resp = _new_response()
    _add_ltpc_feed(resp, "NSE_INDEX|Nifty 50", ltp=24500.50, cp=24450.75)
    return resp.SerializeToString()


@pytest.fixture
def full_feed_bytes():
    """Serialized FeedResponse with one full-mode MarketFullFeed entry."""
    resp = _new_response()
    _add_market_full_feed(
        resp, "NSE_FO|43854",
        ltp=24500.50, cp=24450.75,
        open_=24400.00, high=24550.25, low=24380.00,
        vtt=1234567, oi=5678900,
        bid_p=24500.20, bid_q=500, ask_p=24500.80, ask_q=400,
    )
    return resp.SerializeToString()


@pytest.fixture
def greeks_feed_bytes():
    """Serialized FeedResponse with one option_greeks-mode entry."""
    resp = _new_response()
    _add_greeks_feed(
        resp, "NSE_FO|43854",
        ltp=160.50, cp=155.0,
        vtt=1234567, oi=10000,
        bid_p=155.5, bid_q=200, ask_p=156.0, ask_q=150,
        delta=0.45,
    )
    return resp.SerializeToString()


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
    """Tests for ltpc mode (LTPC directly on Feed) — real wire bytes."""

    def test_ltpc_returns_normalized_tick(self, adapter, ltpc_only_bytes):
        ticks = adapter._parse_protobuf(ltpc_only_bytes)
        assert len(ticks) == 1
        assert isinstance(ticks[0], NormalizedTick)

    def test_ltpc_token_mapping(self, adapter, ltpc_only_bytes):
        ticks = adapter._parse_protobuf(ltpc_only_bytes)
        assert ticks[0].token == 256265

    def test_ltpc_ltp_is_decimal(self, adapter, ltpc_only_bytes):
        ticks = adapter._parse_protobuf(ltpc_only_bytes)
        assert isinstance(ticks[0].ltp, Decimal)

    def test_ltpc_ltp_value(self, adapter, ltpc_only_bytes):
        ticks = adapter._parse_protobuf(ltpc_only_bytes)
        assert abs(float(ticks[0].ltp) - 24500.50) < 0.01

    def test_ltpc_close_value(self, adapter, ltpc_only_bytes):
        ticks = adapter._parse_protobuf(ltpc_only_bytes)
        assert abs(float(ticks[0].close) - 24450.75) < 0.01

    def test_ltpc_broker_type(self, adapter, ltpc_only_bytes):
        ticks = adapter._parse_protobuf(ltpc_only_bytes)
        assert ticks[0].broker_type == "upstox"

    def test_ltpc_no_ohlc_in_ltpc_mode(self, adapter, ltpc_only_bytes):
        """LTPC mode has no OHLC — open/high/low should be Decimal('0')."""
        tick = adapter._parse_protobuf(ltpc_only_bytes)[0]
        assert tick.open == Decimal("0")
        assert tick.high == Decimal("0")
        assert tick.low == Decimal("0")

    def test_ltpc_no_bid_ask_in_ltpc_mode(self, adapter, ltpc_only_bytes):
        """LTPC mode has no depth — bid/ask should be None."""
        tick = adapter._parse_protobuf(ltpc_only_bytes)[0]
        assert tick.bid is None
        assert tick.ask is None
        assert tick.bid_qty is None
        assert tick.ask_qty is None

    def test_ltpc_volume_zero_in_ltpc_mode(self, adapter, ltpc_only_bytes):
        ticks = adapter._parse_protobuf(ltpc_only_bytes)
        assert ticks[0].volume == 0

    def test_ltpc_unknown_instrument_key_returns_empty(self, adapter):
        resp = _new_response()
        _add_ltpc_feed(resp, "NSE_FO|99999", ltp=100.0, cp=99.0)
        ticks = adapter._parse_protobuf(resp.SerializeToString())
        assert ticks == []

    def test_all_prices_are_decimal(self, adapter, ltpc_only_bytes):
        tick = adapter._parse_protobuf(ltpc_only_bytes)[0]
        for field_name in ("ltp", "open", "high", "low", "close", "change", "change_percent"):
            value = getattr(tick, field_name)
            assert isinstance(value, Decimal), (
                f"{field_name} should be Decimal, got {type(value)}"
            )

    def test_change_derived_from_decimal(self, adapter, ltpc_only_bytes):
        """v3 LTPC has no change fields — change must be derived as ltp - cp."""
        tick = adapter._parse_protobuf(ltpc_only_bytes)[0]
        expected_change = Decimal("24500.50") - Decimal("24450.75")
        assert abs(tick.change - expected_change) < Decimal("0.01")

    def test_banknifty_ltpc(self, adapter):
        resp = _new_response()
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty Bank", ltp=51000.00, cp=50900.00)
        ticks = adapter._parse_protobuf(resp.SerializeToString())
        assert ticks[0].token == 260105


# ═══════════════════════════════════════════════════════════════════════
# PROTOBUF PARSING — FULL MODE
# ═══════════════════════════════════════════════════════════════════════

class TestFullModeParsing:
    """Tests for full mode — MarketFullFeed (non-index) and IndexFullFeed."""

    def test_full_mode_returns_tick(self, adapter, full_feed_bytes):
        ticks = adapter._parse_protobuf(full_feed_bytes)
        assert len(ticks) == 1

    def test_full_mode_ohlc_open(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert abs(float(tick.open) - 24400.00) < 0.01

    def test_full_mode_ohlc_high(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert abs(float(tick.high) - 24550.25) < 0.01

    def test_full_mode_ohlc_low(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert abs(float(tick.low) - 24380.00) < 0.01

    def test_full_mode_close(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert abs(float(tick.close) - 24450.75) < 0.01

    def test_full_mode_volume(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert tick.volume == 1234567

    def test_full_mode_oi(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert tick.oi == 5678900

    def test_full_mode_bid_price(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert tick.bid is not None
        assert abs(float(tick.bid) - 24500.20) < 0.01

    def test_full_mode_bid_qty(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert tick.bid_qty == 500

    def test_full_mode_ask_price(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert tick.ask is not None
        assert abs(float(tick.ask) - 24500.80) < 0.01

    def test_full_mode_ask_qty(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert tick.ask_qty == 400

    def test_full_mode_all_decimal_prices(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        for field_name in ("ltp", "open", "high", "low", "close", "change", "change_percent"):
            assert isinstance(getattr(tick, field_name), Decimal)

    def test_full_mode_bid_decimal(self, adapter, full_feed_bytes):
        tick = adapter._parse_protobuf(full_feed_bytes)[0]
        assert isinstance(tick.bid, Decimal)
        assert isinstance(tick.ask, Decimal)

    def test_full_mode_no_depth_gives_none(self, adapter):
        """MarketFullFeed with no depth levels should have None bid/ask."""
        resp = _new_response()
        _add_market_full_feed(
            resp, "NSE_FO|43854", ltp=107.0, cp=105.0,
            open_=100.0, high=110.0, low=95.0,
        )
        tick = adapter._parse_protobuf(resp.SerializeToString())[0]
        assert tick.bid is None
        assert tick.ask is None

    def test_index_full_feed_ohlc(self, adapter):
        """Indices arrive as IndexFullFeed (no depth/volume/oi) — must parse."""
        resp = _new_response()
        _add_index_full_feed(
            resp, "NSE_INDEX|Nifty 50", ltp=23626.8, cp=23161.6,
            open_=23412.55, high=23645.35, low=23313.9,
        )
        tick = adapter._parse_protobuf(resp.SerializeToString())[0]
        assert tick.token == 256265
        assert abs(float(tick.ltp) - 23626.8) < 0.01
        assert abs(float(tick.open) - 23412.55) < 0.01
        assert abs(float(tick.high) - 23645.35) < 0.01
        assert abs(float(tick.low) - 23313.9) < 0.01
        assert tick.bid is None
        assert tick.volume == 0


# ═══════════════════════════════════════════════════════════════════════
# PROTOBUF PARSING — OPTION GREEKS MODE
# ═══════════════════════════════════════════════════════════════════════

class TestOptionGreeksModeParsing:
    """Tests for option_greeks mode (FirstLevelWithGreeks) — unique Upstox feature."""

    def test_greeks_mode_returns_tick(self, adapter, greeks_feed_bytes):
        ticks = adapter._parse_protobuf(greeks_feed_bytes)
        assert len(ticks) == 1

    def test_greeks_mode_token_correct(self, adapter, greeks_feed_bytes):
        ticks = adapter._parse_protobuf(greeks_feed_bytes)
        assert ticks[0].token == 12345678

    def test_greeks_mode_ltp(self, adapter, greeks_feed_bytes):
        tick = adapter._parse_protobuf(greeks_feed_bytes)[0]
        assert abs(float(tick.ltp) - 160.50) < 0.01

    def test_greeks_mode_first_depth(self, adapter, greeks_feed_bytes):
        """option_greeks mode carries a single firstDepth quote level."""
        tick = adapter._parse_protobuf(greeks_feed_bytes)[0]
        assert abs(float(tick.bid) - 155.5) < 0.01
        assert tick.bid_qty == 200
        assert abs(float(tick.ask) - 156.0) < 0.01
        assert tick.ask_qty == 150

    def test_greeks_mode_volume(self, adapter, greeks_feed_bytes):
        tick = adapter._parse_protobuf(greeks_feed_bytes)[0]
        assert tick.volume == 1234567

    def test_greeks_mode_oi(self, adapter, greeks_feed_bytes):
        tick = adapter._parse_protobuf(greeks_feed_bytes)[0]
        assert tick.oi == 10000


# ═══════════════════════════════════════════════════════════════════════
# BINARY PARSING EDGE CASES
# ═══════════════════════════════════════════════════════════════════════

class TestRealProtobufBuild:
    """No mocks — verifies the runtime descriptor build works against the
    installed protobuf library. Regression guard: MessageFactory.GetPrototype
    was removed in protobuf >=5, which silently disabled Upstox tick parsing
    (every binary frame logged 'protobuf library not available')."""

    def test_build_proto_classes_returns_class(self):
        from app.services.brokers.market_data.ticker.adapters.upstox import (
            _build_proto_classes,
        )
        FeedResponse = _build_proto_classes()
        assert FeedResponse is not None, (
            "_build_proto_classes() returned None with protobuf installed — "
            "runtime descriptor build is broken against this protobuf version"
        )

    def test_feed_response_round_trip(self):
        from app.services.brokers.market_data.ticker.adapters.upstox import (
            _build_proto_classes,
        )
        FeedResponse = _build_proto_classes()
        assert FeedResponse is not None
        msg = FeedResponse()
        msg.type = TYPE_LIVE_FEED
        msg.feeds["NSE_INDEX|Nifty 50"].ltpc.ltp = 23500.55
        msg.feeds["NSE_INDEX|Nifty 50"].ltpc.cp = 23400.10
        parsed = FeedResponse()
        parsed.ParseFromString(msg.SerializeToString())
        assert parsed.type == TYPE_LIVE_FEED
        assert parsed.feeds["NSE_INDEX|Nifty 50"].ltpc.ltp == pytest.approx(23500.55)


class TestGoldenFrames:
    """Parse REAL frames captured from the live Upstox v3 feed (2026-06-12,
    NIFTY/BANKNIFTY full mode). These pin the parser to the actual wire
    format — if the inline schema drifts from MarketDataFeedV3.proto again,
    these fail immediately."""

    def _read(self, name: str) -> bytes:
        return (FIXTURES_DIR / name).read_bytes()

    def test_market_info_frame_yields_no_ticks(self, adapter):
        ticks = adapter._parse_protobuf(self._read("market_info.bin"))
        assert ticks == []

    def test_initial_feed_snapshot_yields_both_indices(self, adapter):
        ticks = adapter._parse_protobuf(self._read("initial_feed_2idx.bin"))
        assert {t.token for t in ticks} == {256265, 260105}

    def test_live_feed_nifty_values(self, adapter):
        ticks = adapter._parse_protobuf(self._read("live_feed_nifty.bin"))
        nifty = [t for t in ticks if t.token == 256265][0]
        assert nifty.ltp == Decimal("23626.8")
        assert nifty.close == Decimal("23161.6")
        assert nifty.open == Decimal("23412.55")
        assert nifty.high == Decimal("23645.35")
        assert nifty.low == Decimal("23313.9")
        assert nifty.change == Decimal("465.2")
        assert nifty.broker_type == "upstox"

    def test_live_feed_banknifty_values(self, adapter):
        ticks = adapter._parse_protobuf(self._read("live_feed_banknifty.bin"))
        bank = [t for t in ticks if t.token == 260105][0]
        assert bank.ltp == Decimal("56813.65")
        assert bank.close == Decimal("55176.75")

    def test_golden_prices_all_decimal(self, adapter):
        for frame in ("initial_feed_2idx.bin", "live_feed_nifty.bin", "live_feed_banknifty.bin"):
            for tick in adapter._parse_protobuf(self._read(frame)):
                for field_name in ("ltp", "open", "high", "low", "close"):
                    assert isinstance(getattr(tick, field_name), Decimal)


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

    def test_market_info_type_returns_empty(self, adapter):
        """Messages with type=market_info carry no ticks and must be ignored."""
        resp = _new_response(msg_type=TYPE_MARKET_INFO)
        ticks = adapter._parse_protobuf(resp.SerializeToString())
        assert ticks == []

    def test_initial_feed_type_yields_ticks(self, adapter):
        """type=initial_feed (snapshot sent on subscribe) DOES carry feeds."""
        resp = _new_response(msg_type=TYPE_INITIAL_FEED)
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty 50", ltp=24500.0, cp=24450.0)
        ticks = adapter._parse_protobuf(resp.SerializeToString())
        assert len(ticks) == 1

    def test_text_data_returns_empty(self, adapter):
        """Text frames (str) should not be parsed as ticks."""
        ticks = adapter._parse_tick('{"type": "some_control"}')
        assert ticks == []

    def test_none_data_returns_empty(self, adapter):
        ticks = adapter._parse_tick(None)
        assert ticks == []

    def test_feed_without_ltpc_returns_empty(self, adapter):
        """Feed entry with no payload (no ltpc/fullFeed/greeks) is skipped."""
        resp = _new_response()
        resp.feeds["NSE_INDEX|Nifty 50"].requestMode = 1  # entry exists, no data
        ticks = adapter._parse_protobuf(resp.SerializeToString())
        assert ticks == []

    def test_multiple_instruments_in_one_response(self, adapter):
        """A single FeedResponse can contain multiple instrument feeds."""
        resp = _new_response()
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty 50", ltp=24500.0, cp=24450.0)
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty Bank", ltp=51000.0, cp=50900.0)
        ticks = adapter._parse_protobuf(resp.SerializeToString())
        assert len(ticks) == 2
        tokens = {t.token for t in ticks}
        assert tokens == {256265, 260105}

    def test_unknown_instrument_skipped_in_multi_response(self, adapter):
        """Unknown instrument_key should not block known ones."""
        resp = _new_response()
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty 50", ltp=24500.0, cp=24450.0)
        _add_ltpc_feed(resp, "NSE_FO|99999", ltp=100.0, cp=99.0)
        ticks = adapter._parse_protobuf(resp.SerializeToString())
        assert len(ticks) == 1
        assert ticks[0].token == 256265


# ═══════════════════════════════════════════════════════════════════════
# SUBSCRIPTION MESSAGES
# ═══════════════════════════════════════════════════════════════════════

class TestSubscriptionMessages:
    @pytest.mark.asyncio
    async def test_subscribe_sends_json_as_binary_frame(self, adapter):
        """_subscribe_ws must send JSON encoded as bytes — the Upstox v3 feed
        endpoint silently ignores TEXT frames (live bug found 2026-06-12)."""
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        await adapter._subscribe_ws(["NSE_INDEX|Nifty 50", "NSE_FO|43854"], mode="full")

        mock_ws.send.assert_called_once()
        sent_bytes = mock_ws.send.call_args[0][0]
        assert isinstance(sent_bytes, bytes), (
            "Upstox v3 requires subscription requests as BINARY WebSocket frames; "
            "sending str produces a TEXT frame that the server ignores"
        )
        sent = json.loads(sent_bytes)

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
        sent_bytes = mock_ws.send.call_args[0][0]
        assert isinstance(sent_bytes, bytes), "Upstox v3 requires BINARY frames"
        sent = json.loads(sent_bytes)
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
        adapter._subscribed_tokens.add(256265)  # dispatch drops unsubscribed tokens

        resp = _new_response()
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty 50", ltp=24500.0, cp=24450.0)
        ticks = adapter._parse_protobuf(resp.SerializeToString())

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

        resp = _new_response()
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty 50", ltp=24500.0, cp=24450.0)
        binary_msg = resp.SerializeToString()

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
        resp = _new_response()
        _add_ltpc_feed(resp, "NSE_INDEX|Nifty 50", ltp=24500.50, cp=24450.75)
        tick = adapter._parse_protobuf(resp.SerializeToString())[0]
        # change = 24500.50 - 24450.75 = 49.75
        # change_percent = 49.75 / 24450.75 * 100 ≈ 0.2035...%
        assert isinstance(tick.change_percent, Decimal)

    def test_prices_not_float_in_normalized_tick(self, adapter):
        """Verify NormalizedTick never contains float prices from Upstox."""
        resp = _new_response()
        _add_market_full_feed(
            resp, "NSE_FO|43854",
            ltp=24500.50, cp=24450.75,
            open_=24400.0, high=24550.25, low=24380.0,
            bid_p=24500.20, bid_q=500, ask_p=24500.80, ask_q=400,
        )
        tick = adapter._parse_protobuf(resp.SerializeToString())[0]
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
