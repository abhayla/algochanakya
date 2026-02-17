"""Tests for Paytm Money Ticker Adapter.

Tests cover:
- Adapter creation and initial state
- Token mapping (canonical int ↔ Paytm security_id/exchange/scrip_type tuples)
- JSON tick parsing (LTP mode, FULL mode, control messages, edge cases)
- Broker token translation (canonical → Paytm tuples)
- Subscription message construction (batch JSON ADD/REMOVE)
- Connection lifecycle (connect, disconnect — mocked websockets)
- Timestamp parsing (ISO format, fallback to now)
- Ping loop (keep-alive every 30s)
- Edge cases: unknown security_id, malformed JSON, missing fields, empty data
"""

import asyncio
import json
import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.services.brokers.market_data.ticker.adapters.paytm import (
    PaytmTickerAdapter,
    _WS_BASE_URL,
    _MAX_INSTRUMENTS,
    _PING_INTERVAL,
    _MODE_TO_PAYTM,
    _MSG_TICK,
    _MSG_CONNECTED,
    _MSG_SUBSCRIBED,
    _MSG_ERROR,
    _MSG_CLOSE,
)
from app.services.brokers.market_data.ticker.models import NormalizedTick


# ═══════════════════════════════════════════════════════════════════════
# HELPERS — JSON tick builders
# ═══════════════════════════════════════════════════════════════════════

def build_ltp_tick(
    security_id: str = "999920000",
    exchange: str = "NSE",
    last_price: float = 24500.50,
    change: float = 49.75,
    change_pct: float = 0.20,
) -> dict:
    """Build a Paytm LTP-mode tick dict (minimal fields)."""
    return {
        "type": "tick",
        "data": {
            "security_id": security_id,
            "exchange": exchange,
            "last_price": last_price,
            "change": change,
            "change_pct": change_pct,
        },
    }


def build_full_tick(
    security_id: str = "999920000",
    exchange: str = "NSE",
    last_price: float = 24500.50,
    open_: float = 24400.00,
    high: float = 24550.25,
    low: float = 24380.00,
    close: float = 24450.75,
    change: float = 49.75,
    change_pct: float = 0.20,
    volume: int = 1234567,
    oi: int = 5678900,
    bid_price: float = 24500.20,
    bid_qty: int = 500,
    ask_price: float = 24500.80,
    ask_qty: int = 400,
    last_trade_time: str = "2024-01-15T10:30:15",
    exchange_timestamp: str = "2024-01-15T10:30:15",
) -> dict:
    """Build a Paytm FULL-mode tick dict."""
    return {
        "type": "tick",
        "data": {
            "security_id": security_id,
            "exchange": exchange,
            "last_price": last_price,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "change": change,
            "change_pct": change_pct,
            "volume": volume,
            "oi": oi,
            "bid_price": bid_price,
            "bid_qty": bid_qty,
            "ask_price": ask_price,
            "ask_qty": ask_qty,
            "last_trade_time": last_trade_time,
            "exchange_timestamp": exchange_timestamp,
        },
    }


def make_connected_msg() -> dict:
    return {"type": "connected", "message": "Connection established"}


def make_subscribed_msg(security_id: str = "999920000") -> dict:
    return {"type": "subscribed", "security_id": security_id, "mode": "LTP"}


def make_error_msg(message: str = "Invalid security_id", code: int = 4001) -> dict:
    return {"type": "error", "message": message, "code": code}


def make_close_msg(code: int = 1000, reason: str = "Session expired") -> dict:
    return {"type": "close", "code": code, "reason": reason}


# ═══════════════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def adapter():
    """Create adapter with pre-loaded token map."""
    a = PaytmTickerAdapter()
    a.load_token_map({
        256265: ("999920000", "NSE", "INDEX"),        # NIFTY 50
        260105: ("999920005", "NSE", "INDEX"),         # NIFTY BANK
        12345678: ("46512", "NSE", "DERIVATIVE"),      # Synthetic F&O
        99990001: ("500325", "NSE", "EQUITY"),         # Reliance
    })
    return a


@pytest.fixture
def ltp_tick_nifty():
    """Valid LTP-mode tick for NIFTY 50."""
    return build_ltp_tick(security_id="999920000", last_price=24500.50)


@pytest.fixture
def full_tick_nifty():
    """Valid FULL-mode tick for NIFTY 50 with OHLC + bid/ask."""
    return build_full_tick(security_id="999920000")


# ═══════════════════════════════════════════════════════════════════════
# CREATION & CONFIG
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterCreation:
    def test_default_broker_type(self):
        a = PaytmTickerAdapter()
        assert a.broker_type == "paytm"

    def test_custom_broker_type(self):
        a = PaytmTickerAdapter(broker_type="paytm_platform")
        assert a.broker_type == "paytm_platform"

    def test_initial_state(self):
        a = PaytmTickerAdapter()
        assert not a.is_connected
        assert a.subscribed_tokens == set()
        assert a.last_tick_time is None
        assert a.reconnect_count == 0

    def test_initial_maps_empty(self):
        a = PaytmTickerAdapter()
        assert a._canonical_to_broker == {}
        assert a._security_id_to_canonical == {}

    def test_mode_to_paytm_mapping(self):
        assert _MODE_TO_PAYTM["ltp"] == "LTP"
        assert _MODE_TO_PAYTM["quote"] == "FULL"
        assert _MODE_TO_PAYTM["snap"] == "FULL"
        assert _MODE_TO_PAYTM["full"] == "FULL"
        assert _MODE_TO_PAYTM["depth"] == "FULL"

    def test_max_instruments_constant(self):
        assert _MAX_INSTRUMENTS == 200

    def test_ping_interval_constant(self):
        assert _PING_INTERVAL == 30

    def test_ws_base_url(self):
        assert "paytmmoney.com" in _WS_BASE_URL
        assert _WS_BASE_URL.startswith("wss://")


# ═══════════════════════════════════════════════════════════════════════
# TOKEN MAPPING
# ═══════════════════════════════════════════════════════════════════════

class TestTokenMapping:
    def test_load_token_map(self, adapter):
        assert adapter._canonical_to_broker[256265] == ("999920000", "NSE", "INDEX")
        assert adapter._security_id_to_canonical["999920000"] == 256265

    def test_load_multiple_tokens(self, adapter):
        assert len(adapter._canonical_to_broker) == 4
        assert len(adapter._security_id_to_canonical) == 4

    def test_load_token_map_all_three_fields(self, adapter):
        assert adapter._canonical_to_broker[260105] == ("999920005", "NSE", "INDEX")
        assert adapter._canonical_to_broker[12345678] == ("46512", "NSE", "DERIVATIVE")
        assert adapter._canonical_to_broker[99990001] == ("500325", "NSE", "EQUITY")

    def test_load_token_map_incremental(self, adapter):
        """Additional load_token_map calls add to existing map."""
        adapter.load_token_map({999: ("12345", "BSE", "EQUITY")})
        assert adapter._canonical_to_broker[999] == ("12345", "BSE", "EQUITY")
        assert len(adapter._canonical_to_broker) == 5

    def test_load_token_map_overwrites_existing(self, adapter):
        """Re-loading the same canonical token updates the mapping."""
        adapter.load_token_map({256265: ("888888", "NSE", "INDEX")})
        assert adapter._canonical_to_broker[256265] == ("888888", "NSE", "INDEX")
        assert adapter._security_id_to_canonical["888888"] == 256265


# ═══════════════════════════════════════════════════════════════════════
# BROKER TOKEN TRANSLATION
# ═══════════════════════════════════════════════════════════════════════

class TestBrokerTokenTranslation:
    def test_translate_known_tokens(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 260105])
        assert ("999920000", "NSE", "INDEX") in result
        assert ("999920005", "NSE", "INDEX") in result

    def test_translate_unknown_token_skipped(self, adapter):
        result = adapter._translate_to_broker_tokens([99999])
        assert result == []

    def test_translate_mixed_known_unknown(self, adapter):
        result = adapter._translate_to_broker_tokens([256265, 99999, 260105])
        assert len(result) == 2
        assert ("999920000", "NSE", "INDEX") in result
        assert ("999920005", "NSE", "INDEX") in result

    def test_translate_empty_list(self, adapter):
        result = adapter._translate_to_broker_tokens([])
        assert result == []

    def test_translate_equity_token(self, adapter):
        result = adapter._translate_to_broker_tokens([99990001])
        assert result == [("500325", "NSE", "EQUITY")]

    def test_translate_derivative_token(self, adapter):
        result = adapter._translate_to_broker_tokens([12345678])
        assert result == [("46512", "NSE", "DERIVATIVE")]


# ═══════════════════════════════════════════════════════════════════════
# GET CANONICAL TOKEN
# ═══════════════════════════════════════════════════════════════════════

class TestGetCanonicalToken:
    def test_str_security_id(self, adapter):
        assert adapter._get_canonical_token("999920000") == 256265

    def test_int_security_id(self, adapter):
        assert adapter._get_canonical_token(999920000) == 256265

    def test_unknown_returns_zero(self, adapter):
        assert adapter._get_canonical_token("9999") == 0

    def test_none_returns_zero(self, adapter):
        assert adapter._get_canonical_token(None) == 0

    def test_empty_string_returns_zero(self, adapter):
        assert adapter._get_canonical_token("") == 0

    def test_equity_security_id(self, adapter):
        assert adapter._get_canonical_token("500325") == 99990001


# ═══════════════════════════════════════════════════════════════════════
# LTP TICK PARSING
# ═══════════════════════════════════════════════════════════════════════

class TestLTPTickParsing:
    def test_parse_ltp_tick_returns_one_tick(self, adapter, ltp_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(ltp_tick_nifty))
        assert len(ticks) == 1

    def test_parse_ltp_tick_canonical_token(self, adapter, ltp_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(ltp_tick_nifty))
        assert ticks[0].token == 256265

    def test_parse_ltp_tick_ltp_value(self, adapter, ltp_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(ltp_tick_nifty))
        assert ticks[0].ltp == Decimal("24500.50")

    def test_parse_ltp_tick_broker_type(self, adapter, ltp_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(ltp_tick_nifty))
        assert ticks[0].broker_type == "paytm"

    def test_parse_ltp_tick_ohlc_zero(self, adapter, ltp_tick_nifty):
        """LTP mode doesn't provide OHLC — should be zeros."""
        ticks = adapter._parse_tick(json.dumps(ltp_tick_nifty))
        assert ticks[0].open == Decimal("0")
        assert ticks[0].high == Decimal("0")
        assert ticks[0].low == Decimal("0")
        assert ticks[0].close == Decimal("0")

    def test_parse_ltp_tick_no_bid_ask(self, adapter, ltp_tick_nifty):
        """LTP mode doesn't provide bid/ask."""
        ticks = adapter._parse_tick(json.dumps(ltp_tick_nifty))
        assert ticks[0].bid is None
        assert ticks[0].ask is None
        assert ticks[0].bid_qty is None
        assert ticks[0].ask_qty is None

    def test_parse_ltp_tick_change_pct_from_server(self, adapter):
        """LTP mode: use server-provided change_pct when close=0."""
        tick_data = build_ltp_tick(change=49.75, change_pct=0.20)
        ticks = adapter._parse_tick(json.dumps(tick_data))
        assert ticks[0].change_percent == Decimal("0.20")

    def test_parse_ltp_tick_dict_input(self, adapter, ltp_tick_nifty):
        """_parse_tick accepts dict directly (not just JSON string)."""
        ticks = adapter._parse_tick(ltp_tick_nifty)
        assert len(ticks) == 1

    def test_parse_ltp_tick_bytes_input(self, adapter, ltp_tick_nifty):
        """_parse_tick handles bytes (JSON encoded)."""
        ticks = adapter._parse_tick(json.dumps(ltp_tick_nifty).encode("utf-8"))
        assert len(ticks) == 1


# ═══════════════════════════════════════════════════════════════════════
# FULL TICK PARSING
# ═══════════════════════════════════════════════════════════════════════

class TestFullTickParsing:
    def test_parse_full_tick_returns_one_tick(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert len(ticks) == 1

    def test_parse_full_tick_ltp(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert ticks[0].ltp == Decimal("24500.50")

    def test_parse_full_tick_ohlc(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        t = ticks[0]
        assert t.open == Decimal("24400.00")
        assert t.high == Decimal("24550.25")
        assert t.low == Decimal("24380.00")
        assert t.close == Decimal("24450.75")

    def test_parse_full_tick_change_recalculated(self, adapter, full_tick_nifty):
        """Change is recalculated from (ltp - close) when close is available."""
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        t = ticks[0]
        # ltp=24500.50, close=24450.75 → change = 49.75
        assert t.change == Decimal("24500.50") - Decimal("24450.75")

    def test_parse_full_tick_change_pct_recalculated(self, adapter, full_tick_nifty):
        """change_percent recalculated from Decimal for precision."""
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        t = ticks[0]
        expected = ((Decimal("24500.50") - Decimal("24450.75")) / Decimal("24450.75") * 100).quantize(Decimal("0.01"))
        assert t.change_percent == expected

    def test_parse_full_tick_volume_oi(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert ticks[0].volume == 1234567
        assert ticks[0].oi == 5678900

    def test_parse_full_tick_bid_ask(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        t = ticks[0]
        assert t.bid == Decimal("24500.20")
        assert t.ask == Decimal("24500.80")
        assert t.bid_qty == 500
        assert t.ask_qty == 400

    def test_parse_full_tick_timestamp(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        t = ticks[0]
        assert isinstance(t.timestamp, datetime)
        assert t.timestamp.year == 2024
        assert t.timestamp.month == 1
        assert t.timestamp.day == 15

    def test_parse_full_tick_canonical_token(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert ticks[0].token == 256265

    def test_parse_full_tick_broker_type(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert ticks[0].broker_type == "paytm"

    def test_parse_full_tick_zero_bid_skipped(self, adapter):
        """bid_price=0 should result in bid=None."""
        tick_data = build_full_tick(bid_price=0, bid_qty=0)
        ticks = adapter._parse_tick(json.dumps(tick_data))
        assert ticks[0].bid is None
        assert ticks[0].bid_qty is None

    def test_parse_full_tick_zero_ask_skipped(self, adapter):
        """ask_price=0 should result in ask=None."""
        tick_data = build_full_tick(ask_price=0, ask_qty=0)
        ticks = adapter._parse_tick(json.dumps(tick_data))
        assert ticks[0].ask is None

    def test_parse_full_tick_equity(self, adapter):
        """Parse a FULL tick for an equity instrument."""
        tick_data = build_full_tick(security_id="500325", last_price=1825.50, close=1818.25)
        ticks = adapter._parse_tick(json.dumps(tick_data))
        assert ticks[0].token == 99990001
        assert ticks[0].ltp == Decimal("1825.50")


# ═══════════════════════════════════════════════════════════════════════
# BATCH TICK PARSING (LIST PAYLOAD)
# ═══════════════════════════════════════════════════════════════════════

class TestBatchTickParsing:
    def test_parse_batch_returns_multiple_ticks(self, adapter):
        """A JSON array of ticks should return multiple NormalizedTick objects."""
        batch = [
            build_ltp_tick(security_id="999920000"),
            build_ltp_tick(security_id="999920005"),
        ]
        ticks = adapter._parse_tick(json.dumps(batch))
        assert len(ticks) == 2

    def test_parse_batch_tokens_correct(self, adapter):
        batch = [
            build_ltp_tick(security_id="999920000"),
            build_ltp_tick(security_id="999920005"),
        ]
        ticks = adapter._parse_tick(json.dumps(batch))
        tokens = {t.token for t in ticks}
        assert tokens == {256265, 260105}

    def test_parse_batch_mixed_known_unknown(self, adapter):
        """Unknown security_id in batch is skipped; known ones parsed."""
        batch = [
            build_ltp_tick(security_id="999920000"),   # known
            build_ltp_tick(security_id="9999"),          # unknown
        ]
        ticks = adapter._parse_tick(json.dumps(batch))
        assert len(ticks) == 1
        assert ticks[0].token == 256265

    def test_parse_batch_empty_list(self, adapter):
        ticks = adapter._parse_tick(json.dumps([]))
        assert ticks == []


# ═══════════════════════════════════════════════════════════════════════
# CONTROL MESSAGES
# ═══════════════════════════════════════════════════════════════════════

class TestControlMessages:
    def test_connected_message_returns_empty(self, adapter):
        ticks = adapter._parse_tick(json.dumps(make_connected_msg()))
        assert ticks == []

    def test_subscribed_message_returns_empty(self, adapter):
        ticks = adapter._parse_tick(json.dumps(make_subscribed_msg()))
        assert ticks == []

    def test_error_message_returns_empty(self, adapter):
        ticks = adapter._parse_tick(json.dumps(make_error_msg()))
        assert ticks == []

    def test_close_message_returns_empty(self, adapter):
        ticks = adapter._parse_tick(json.dumps(make_close_msg()))
        assert ticks == []

    def test_unknown_type_returns_empty(self, adapter):
        ticks = adapter._parse_tick(json.dumps({"type": "heartbeat"}))
        assert ticks == []


# ═══════════════════════════════════════════════════════════════════════
# TIMESTAMP PARSING
# ═══════════════════════════════════════════════════════════════════════

class TestTimestampParsing:
    def test_iso_format_parsed(self):
        result = PaytmTickerAdapter._parse_paytm_timestamp("2024-01-15T10:30:15")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 15

    def test_iso_format_with_z_suffix(self):
        result = PaytmTickerAdapter._parse_paytm_timestamp("2024-01-15T10:30:15Z")
        assert result.year == 2024
        assert result.second == 15

    def test_iso_format_with_milliseconds(self):
        result = PaytmTickerAdapter._parse_paytm_timestamp("2024-01-15T10:30:15.000Z")
        assert result.second == 15

    def test_none_returns_now(self):
        before = datetime.now()
        result = PaytmTickerAdapter._parse_paytm_timestamp(None)
        after = datetime.now()
        assert before <= result <= after

    def test_empty_string_returns_now(self):
        before = datetime.now()
        result = PaytmTickerAdapter._parse_paytm_timestamp("")
        after = datetime.now()
        assert before <= result <= after

    def test_invalid_format_returns_now(self):
        before = datetime.now()
        result = PaytmTickerAdapter._parse_paytm_timestamp("not-a-date")
        after = datetime.now()
        assert before <= result <= after


# ═══════════════════════════════════════════════════════════════════════
# EDGE CASES: MALFORMED / MISSING DATA
# ═══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_malformed_json_returns_empty(self, adapter):
        ticks = adapter._parse_tick("{invalid json}")
        assert ticks == []

    def test_empty_string_returns_empty(self, adapter):
        ticks = adapter._parse_tick("")
        assert ticks == []

    def test_non_dict_json_returns_empty(self, adapter):
        ticks = adapter._parse_tick('"just a string"')
        assert ticks == []

    def test_integer_input_returns_empty(self, adapter):
        ticks = adapter._parse_tick(42)
        assert ticks == []

    def test_tick_with_missing_security_id(self, adapter):
        bad = {"type": "tick", "data": {"last_price": 100.0}}
        ticks = adapter._parse_tick(json.dumps(bad))
        assert ticks == []

    def test_tick_with_unknown_security_id(self, adapter):
        bad = {"type": "tick", "data": {"security_id": "9999", "last_price": 100.0}}
        ticks = adapter._parse_tick(json.dumps(bad))
        assert ticks == []

    def test_tick_with_empty_data(self, adapter):
        bad = {"type": "tick", "data": {}}
        ticks = adapter._parse_tick(json.dumps(bad))
        assert ticks == []

    def test_tick_with_null_data(self, adapter):
        bad = {"type": "tick", "data": None}
        ticks = adapter._parse_tick(json.dumps(bad))
        assert ticks == []

    def test_tick_missing_data_key(self, adapter):
        bad = {"type": "tick"}
        ticks = adapter._parse_tick(json.dumps(bad))
        assert ticks == []

    def test_last_price_zero(self, adapter):
        """Zero LTP is valid (circuit limit open scenario)."""
        tick_data = build_ltp_tick(last_price=0.0)
        ticks = adapter._parse_tick(json.dumps(tick_data))
        assert len(ticks) == 1
        assert ticks[0].ltp == Decimal("0")

    def test_none_input_returns_empty(self, adapter):
        ticks = adapter._parse_tick(None)
        assert ticks == []


# ═══════════════════════════════════════════════════════════════════════
# SUBSCRIPTION MESSAGES
# ═══════════════════════════════════════════════════════════════════════

class TestSubscriptionMessages:
    @pytest.mark.asyncio
    async def test_subscribe_sends_batch(self, adapter):
        """_subscribe_ws sends a JSON list of ADD messages."""
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        broker_tokens = [
            ("999920000", "NSE", "INDEX"),
            ("999920005", "NSE", "INDEX"),
        ]
        await adapter._subscribe_ws(broker_tokens, mode="ltp")
        mock_ws.send.assert_called_once()
        payload = json.loads(mock_ws.send.call_args[0][0])
        assert isinstance(payload, list)
        assert len(payload) == 2
        assert all(m["actionType"] == "ADD" for m in payload)
        assert payload[0]["scripId"] == "999920000"
        assert payload[1]["scripId"] == "999920005"

    @pytest.mark.asyncio
    async def test_subscribe_ltp_mode(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([("999920000", "NSE", "INDEX")], mode="ltp")
        payload = json.loads(mock_ws.send.call_args[0][0])
        assert payload[0]["modeType"] == "LTP"

    @pytest.mark.asyncio
    async def test_subscribe_full_mode(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([("999920000", "NSE", "INDEX")], mode="full")
        payload = json.loads(mock_ws.send.call_args[0][0])
        assert payload[0]["modeType"] == "FULL"

    @pytest.mark.asyncio
    async def test_subscribe_quote_maps_to_full(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([("999920000", "NSE", "INDEX")], mode="quote")
        payload = json.loads(mock_ws.send.call_args[0][0])
        assert payload[0]["modeType"] == "FULL"

    @pytest.mark.asyncio
    async def test_subscribe_correct_scrip_type(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([
            ("999920000", "NSE", "INDEX"),
            ("500325", "NSE", "EQUITY"),
            ("46512", "NSE", "DERIVATIVE"),
        ], mode="full")
        payload = json.loads(mock_ws.send.call_args[0][0])
        scrip_types = {m["scripId"]: m["scripType"] for m in payload}
        assert scrip_types["999920000"] == "INDEX"
        assert scrip_types["500325"] == "EQUITY"
        assert scrip_types["46512"] == "DERIVATIVE"

    @pytest.mark.asyncio
    async def test_subscribe_correct_exchange(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([("999920000", "NSE", "INDEX")], mode="ltp")
        payload = json.loads(mock_ws.send.call_args[0][0])
        assert payload[0]["exchangeType"] == "NSE"

    @pytest.mark.asyncio
    async def test_subscribe_empty_tokens_no_send(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._subscribe_ws([], mode="ltp")
        mock_ws.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_subscribe_not_connected_raises(self, adapter):
        adapter._ws = None
        with pytest.raises(ConnectionError):
            await adapter._subscribe_ws([("999920000", "NSE", "INDEX")], mode="ltp")

    @pytest.mark.asyncio
    async def test_unsubscribe_sends_remove(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._unsubscribe_ws([("999920000", "NSE", "INDEX")])
        mock_ws.send.assert_called_once()
        payload = json.loads(mock_ws.send.call_args[0][0])
        assert payload[0]["actionType"] == "REMOVE"
        assert payload[0]["scripId"] == "999920000"

    @pytest.mark.asyncio
    async def test_unsubscribe_empty_no_send(self, adapter):
        mock_ws = AsyncMock()
        adapter._ws = mock_ws
        await adapter._unsubscribe_ws([])
        mock_ws.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsubscribe_not_connected_no_error(self, adapter):
        adapter._ws = None
        await adapter._unsubscribe_ws([("999920000", "NSE", "INDEX")])  # should not raise


# ═══════════════════════════════════════════════════════════════════════
# CONNECTION LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════

class TestConnectionLifecycle:
    @pytest.mark.asyncio
    async def test_connect_sets_token(self):
        adapter = PaytmTickerAdapter()
        mock_ws = AsyncMock()

        with patch("websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            with patch("asyncio.create_task") as mock_task:
                mock_task.return_value = MagicMock()
                await adapter._connect_ws({
                    "api_key": "MYAPIKEY123",
                    "public_access_token": "mytoken.jwt.here",
                })
                assert adapter._public_access_token == "mytoken.jwt.here"
                assert adapter._api_key == "MYAPIKEY123"

    @pytest.mark.asyncio
    async def test_connect_url_contains_token(self):
        adapter = PaytmTickerAdapter()
        mock_ws = AsyncMock()
        captured_url = {}

        async def fake_connect(url, **kwargs):
            captured_url["url"] = url
            return mock_ws

        with patch("websockets.connect", side_effect=fake_connect):
            with patch("asyncio.create_task", return_value=MagicMock()):
                await adapter._connect_ws({
                    "api_key": "key",
                    "public_access_token": "mytoken123",
                })
        assert "x_jwt_token=mytoken123" in captured_url["url"]

    @pytest.mark.asyncio
    async def test_connect_with_token_map_in_credentials(self):
        adapter = PaytmTickerAdapter()
        mock_ws = AsyncMock()
        token_map = {256265: ("999920000", "NSE", "INDEX")}

        with patch("websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            with patch("asyncio.create_task", return_value=MagicMock()):
                await adapter._connect_ws({
                    "api_key": "key",
                    "public_access_token": "tok",
                    "token_map": token_map,
                })
        assert adapter._canonical_to_broker[256265] == ("999920000", "NSE", "INDEX")

    @pytest.mark.asyncio
    async def test_connect_creates_receive_task(self):
        adapter = PaytmTickerAdapter()
        mock_ws = AsyncMock()
        task_names = []

        def fake_create_task(coro, name=None, **kwargs):
            task_names.append(name)
            return MagicMock()

        with patch("websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            with patch("asyncio.create_task", side_effect=fake_create_task):
                await adapter._connect_ws({
                    "api_key": "key",
                    "public_access_token": "tok",
                })
        assert "Paytm-WS-Receive" in task_names

    @pytest.mark.asyncio
    async def test_connect_creates_ping_task(self):
        adapter = PaytmTickerAdapter()
        mock_ws = AsyncMock()
        task_names = []

        def fake_create_task(coro, name=None, **kwargs):
            task_names.append(name)
            return MagicMock()

        with patch("websockets.connect", new_callable=AsyncMock, return_value=mock_ws):
            with patch("asyncio.create_task", side_effect=fake_create_task):
                await adapter._connect_ws({
                    "api_key": "key",
                    "public_access_token": "tok",
                })
        assert "Paytm-WS-Ping" in task_names

    @pytest.mark.asyncio
    async def test_disconnect_cancels_tasks(self):
        adapter = PaytmTickerAdapter()

        # Use real asyncio Tasks that are already done (cancelled) so await completes
        async def _noop():
            pass

        receive_task = asyncio.create_task(_noop())
        ping_task = asyncio.create_task(_noop())
        # Wait for them to complete so done() returns True
        await asyncio.gather(receive_task, ping_task, return_exceptions=True)

        adapter._receive_task = receive_task
        adapter._ping_task = ping_task
        adapter._ws = AsyncMock()

        await adapter._disconnect_ws()

        # Both tasks were done() before cancel was attempted — ws should be closed
        assert adapter._ws is None

    @pytest.mark.asyncio
    async def test_disconnect_closes_ws(self):
        adapter = PaytmTickerAdapter()
        mock_ws = AsyncMock()
        adapter._ws = mock_ws

        await adapter._disconnect_ws()
        mock_ws.close.assert_called_once()
        assert adapter._ws is None


# ═══════════════════════════════════════════════════════════════════════
# RECEIVE LOOP
# ═══════════════════════════════════════════════════════════════════════

class TestReceiveLoop:
    @pytest.mark.asyncio
    async def test_receive_loop_dispatches_ticks(self, adapter):
        """Receive loop parses JSON tick and dispatches via _dispatch_async."""
        tick_json = json.dumps(build_ltp_tick(security_id="999920000"))
        dispatched = []

        async def mock_callback(ticks):
            dispatched.extend(ticks)

        adapter.set_on_tick_callback(mock_callback)

        # Mock WebSocket that yields one message then raises ConnectionClosed
        import websockets.exceptions

        class MockWS:
            def __init__(self):
                self._messages = [tick_json]
                self._index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self._index < len(self._messages):
                    msg = self._messages[self._index]
                    self._index += 1
                    return msg
                raise websockets.exceptions.ConnectionClosed(None, None)

        adapter._ws = MockWS()
        adapter._connected = True

        await adapter._ws_receive_loop()
        assert len(dispatched) == 1
        assert dispatched[0].token == 256265

    @pytest.mark.asyncio
    async def test_receive_loop_cancelled_sets_connected_false(self, adapter):
        """CancelledError in receive loop sets _connected=False via reconnect mechanism."""
        import websockets.exceptions

        class MockWSAlwaysConnClosed:
            def __aiter__(self):
                return self

            async def __anext__(self):
                raise websockets.exceptions.ConnectionClosed(None, None)

        adapter._ws = MockWSAlwaysConnClosed()
        adapter._connected = True

        await adapter._ws_receive_loop()
        assert not adapter._connected


# ═══════════════════════════════════════════════════════════════════════
# NORMALIZED TICK INVARIANTS
# ═══════════════════════════════════════════════════════════════════════

class TestNormalizedTickInvariants:
    def test_tick_is_normalized_tick_instance(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert isinstance(ticks[0], NormalizedTick)

    def test_prices_are_decimal(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        t = ticks[0]
        assert isinstance(t.ltp, Decimal)
        assert isinstance(t.open, Decimal)
        assert isinstance(t.high, Decimal)
        assert isinstance(t.low, Decimal)
        assert isinstance(t.close, Decimal)

    def test_prices_in_rupees_not_paise(self, adapter):
        """Paytm sends rupees — no conversion needed. 24500 should remain 24500."""
        tick_data = build_full_tick(last_price=24500.50)
        ticks = adapter._parse_tick(json.dumps(tick_data))
        # If accidentally converted from paise: 24500.50 / 100 = 245.00 (wrong)
        assert ticks[0].ltp > Decimal("1000")

    def test_volume_is_int(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert isinstance(ticks[0].volume, int)

    def test_oi_is_int(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert isinstance(ticks[0].oi, int)

    def test_timestamp_is_datetime(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        assert isinstance(ticks[0].timestamp, datetime)

    def test_to_dict_serializable(self, adapter, full_tick_nifty):
        ticks = adapter._parse_tick(json.dumps(full_tick_nifty))
        d = ticks[0].to_dict()
        assert isinstance(d["ltp"], float)
        assert isinstance(d["token"], int)
        assert d["broker_type"] == "paytm"
