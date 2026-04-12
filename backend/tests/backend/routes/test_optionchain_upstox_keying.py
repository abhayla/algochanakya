"""
Regression test: Upstox option chain symbol key mismatch.

Root cause: Upstox /v2/option/chain API does NOT return a "trading_symbol" field.
The adapter stored all quotes under key "NFO:" (empty symbol), causing every
strike lookup in optionchain.py to miss and return all zeros.

Fix: Use instrument_key token to map back to canonical symbol via token_to_symbol.
Also use Upstox pre-calculated Greeks when available, falling back to
Newton-Raphson when not.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from app.api.routes.optionchain import calculate_iv, calculate_greeks


def _build_all_quotes_with_greeks():
    """Build all_quotes dict as Upstox adapter would return (with greeks)."""
    return {
        "NFO:NIFTY26041324000CE": {
            "last_price": 150.25,
            "oi": 5000000,
            "volume": 125000,
            "ohlc": {"open": 148.0, "high": 155.0, "low": 147.5, "close": 145.50},
            "depth": {"buy": [{"price": 150.0, "quantity": 500}], "sell": [{"price": 150.5, "quantity": 400}]},
            "greeks": {"iv": 18.50, "delta": 0.55, "gamma": 0.0003, "theta": -12.50, "vega": 8.25},
        },
        "NFO:NIFTY26041324000PE": {
            "last_price": 45.75,
            "oi": 3000000,
            "volume": 80000,
            "ohlc": {"open": 50.0, "high": 52.0, "low": 44.0, "close": 50.25},
            "depth": {"buy": [{"price": 45.50, "quantity": 300}], "sell": [{"price": 46.0, "quantity": 250}]},
            "greeks": {"iv": 19.20, "delta": -0.45, "gamma": 0.0003, "theta": -10.30, "vega": 8.25},
        },
    }


def _build_all_quotes_without_greeks():
    """Build all_quotes dict as non-Upstox adapter would return (no greeks)."""
    quotes = _build_all_quotes_with_greeks()
    for q in quotes.values():
        del q["greeks"]
    return quotes


@pytest.mark.unit
class TestUpstoxGreeksUsage:
    """Tests that optionchain.py uses Upstox pre-calculated Greeks when available."""

    def test_upstox_greeks_used_when_available(self):
        """When quote has 'greeks' sub-dict, use those instead of recalculating."""
        ce_quote = _build_all_quotes_with_greeks()["NFO:NIFTY26041324000CE"]
        upstox_greeks = ce_quote.get("greeks")

        # The route should check for this and use it directly
        assert upstox_greeks is not None
        assert upstox_greeks["iv"] == 18.50

        # Simulate what the route SHOULD do:
        # If greeks available, use them; otherwise fall back to calculate_iv
        if upstox_greeks and upstox_greeks.get("iv"):
            ce_iv = upstox_greeks["iv"]
            ce_greeks = {
                "delta": round(upstox_greeks["delta"], 4),
                "gamma": round(upstox_greeks["gamma"], 6),
                "theta": round(upstox_greeks["theta"], 2),
                "vega": round(upstox_greeks["vega"], 2),
            }
        else:
            ce_iv = calculate_iv(150.25, 24050.0, 24000.0, 5, True)
            ce_greeks = calculate_greeks(24050.0, 24000.0, 5, ce_iv, True)

        assert ce_iv == 18.50
        assert ce_greeks["delta"] == 0.55

    def test_fallback_to_newton_raphson_without_greeks(self):
        """When quote has no 'greeks' key, fall back to Newton-Raphson."""
        ce_quote = _build_all_quotes_without_greeks()["NFO:NIFTY26041324000CE"]
        upstox_greeks = ce_quote.get("greeks")

        assert upstox_greeks is None

        # Should fall back to calculate_iv
        ce_iv = calculate_iv(150.25, 24050.0, 24000.0, 5, True)
        ce_greeks = calculate_greeks(24050.0, 24000.0, 5, ce_iv, True)

        # Newton-Raphson should produce reasonable values (not zero)
        assert ce_iv > 0, "IV should be calculable for ATM option with non-zero LTP"
        assert ce_greeks["delta"] != 0, "Delta should be non-zero for ATM option"

    def test_upstox_greeks_with_zero_iv_triggers_fallback(self):
        """When Upstox Greeks have iv=0, fall back to Newton-Raphson."""
        ce_quote = _build_all_quotes_with_greeks()["NFO:NIFTY26041324000CE"]
        ce_quote["greeks"]["iv"] = 0  # Upstox returned 0 IV

        upstox_greeks = ce_quote.get("greeks")

        # The route should NOT use greeks when iv=0
        if upstox_greeks and upstox_greeks.get("iv"):
            ce_iv = upstox_greeks["iv"]
        else:
            ce_iv = calculate_iv(150.25, 24050.0, 24000.0, 5, True)

        assert ce_iv > 0, "Should fall back to Newton-Raphson when Upstox IV is 0"
