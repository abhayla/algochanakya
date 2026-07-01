"""
Isolated unit test for SmartAPIMarketDataAdapter._convert_to_unified_quote.

Purpose — the live /api/orders/quote endpoint has been returning option LTP
values 100x too small (NIFTY 24000 CE showing 1.7 instead of ~170). Multiple
code fixes were attempted but the observed value didn't change after backend
restart, suggesting either the code path isn't being hit OR some caching/
wrapping layer is intercepting. This test exercises the function directly
with a captured SmartAPI FULL-mode payload so the fix's correctness at the
code layer can be verified independently of runtime path uncertainty.
"""

from decimal import Decimal

import pytest

from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter


# Payload shape matches SmartAPIMarketData._normalize_quotes output (which the
# code comment at that method insists returns values "already in rupees from
# REST API"). If that comment is truthful, _convert_to_unified_quote MUST NOT
# divide these by 100.
_RUPEES_PAYLOAD = {
    "token": "44620",
    "tradingsymbol": "NIFTY07JUL2624000CE",
    "exchange": "NFO",
    "ltp": Decimal("166.5"),
    "open": Decimal("140.0"),
    "high": Decimal("199.8"),
    "low": Decimal("123.2"),
    "close": Decimal("139.85"),
    "volume": 106000000,
    "oi": 10500000,
    "bid_price": Decimal("166.4"),
    "bid_qty": 750,
    "ask_price": Decimal("166.6"),
    "ask_qty": 750,
}


class _FakeAdapter:
    """Minimal stand-in — _convert_to_unified_quote is instance-method but only
    reads raw_data + canonical_symbol; it doesn't touch self state."""

    _convert_to_unified_quote = SmartAPIMarketDataAdapter._convert_to_unified_quote


def test_convert_to_unified_quote_preserves_rupees_scale():
    """LTP/OHLC must be returned as-passed (rupees), NOT divided by 100."""
    adapter = _FakeAdapter()
    uq = adapter._convert_to_unified_quote(_RUPEES_PAYLOAD, "NIFTY07JUL2624000CE")

    # If the double-divide bug returns: last_price would be Decimal("1.665")
    assert uq.last_price == Decimal("166.5"), (
        f"Expected 166.5 rupees, got {uq.last_price} — /100 bug still present"
    )
    assert uq.open == Decimal("140.0")
    assert uq.high == Decimal("199.8")
    assert uq.low == Decimal("123.2")
    assert uq.close == Decimal("139.85")
    assert uq.bid_price == Decimal("166.4")
    assert uq.ask_price == Decimal("166.6")

    # Change should be ltp - close = 26.65 (not 0.2665)
    assert uq.change == Decimal("26.65")
    # Change percent should be ~19% (26.65/139.85 * 100), not 0.19%
    assert uq.change_percent > Decimal("15") and uq.change_percent < Decimal("25")


def test_convert_to_unified_quote_volume_and_oi_pass_through():
    """volume and oi are pass-through integers, not scaled prices."""
    adapter = _FakeAdapter()
    uq = adapter._convert_to_unified_quote(_RUPEES_PAYLOAD, "NIFTY07JUL2624000CE")
    assert uq.volume == 106000000
    assert uq.oi == 10500000
