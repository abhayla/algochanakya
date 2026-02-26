"""
Factory functions for broker tick data used in unit tests.

Each factory creates the raw broker-format tick dict that the adapter
would receive from the broker's WebSocket. Tests that need multiple
variations just pass keyword overrides.

Usage:
    from tests.factories.ticks import make_kite_tick, make_smartapi_tick

    tick = make_kite_tick(token=256265, ltp=24500.0)
    batch = [make_kite_tick(token=256265), make_kite_tick(token=260105, ltp=52000.0)]
"""

from decimal import Decimal
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# Kite / Zerodha — prices already in rupees, token is canonical int
# ─────────────────────────────────────────────────────────────────────────────

def make_kite_tick(
    token: int = 256265,
    ltp: float = 24500.50,
    open_: float = 24400.0,
    high: float = 24600.0,
    low: float = 24300.0,
    close: float = 24450.0,
    volume: int = 1_000_000,
    oi: int = 5_000_000,
    **overrides,
) -> dict:
    """Raw Kite tick dict (prices in rupees, token is canonical)."""
    tick = {
        "instrument_token": token,
        "tradable": True,
        "mode": "quote",
        "last_price": ltp,
        "last_quantity": 75,
        "average_price": ltp,
        "volume": volume,
        "buy_quantity": 500,
        "sell_quantity": 500,
        "ohlc": {"open": open_, "high": high, "low": low, "close": close},
        "change": round(ltp - close, 2),
        "last_trade_time": datetime.now(),
        "exchange_timestamp": datetime.now(),
        "oi": oi,
        "oi_day_high": oi + 100_000,
        "oi_day_low": oi - 100_000,
    }
    tick.update(overrides)
    return tick


# ─────────────────────────────────────────────────────────────────────────────
# SmartAPI / AngelOne — prices in PAISE (adapter divides by 100)
# Token is SmartAPI string like "99926000", not canonical int
# ─────────────────────────────────────────────────────────────────────────────

def make_smartapi_tick(
    token: str = "99926000",     # SmartAPI NIFTY token
    ltp_paise: int = 2_450_050,  # ₹24,500.50 in paise
    open_paise: int = 2_440_000,
    high_paise: int = 2_460_000,
    low_paise: int = 2_430_000,
    close_paise: int = 2_445_000,
    volume: int = 1_000_000,
    exchange_type: int = 1,  # 1 = NSE
    **overrides,
) -> dict:
    """Raw SmartAPI tick dict (prices in PAISE — adapter must divide by 100)."""
    tick = {
        "token": token,
        "exchange_type": exchange_type,
        "last_traded_price": ltp_paise,
        "last_traded_quantity": 75,
        "average_traded_price": ltp_paise,
        "volume_trade_for_the_day": volume,
        "total_buy_quantity": 500.0,
        "total_sell_quantity": 500.0,
        "open_price_of_the_day": open_paise,
        "high_price_of_the_day": high_paise,
        "low_price_of_the_day": low_paise,
        "closed_price": close_paise,
        "last_traded_timestamp": "1703001600",
        "open_interest": 5_000_000,
        "open_interest_change_percentage": 0.5,
    }
    tick.update(overrides)
    return tick


# ─────────────────────────────────────────────────────────────────────────────
# Dhan — binary packet (use build helpers in test_dhan_ticker_adapter.py)
# This factory produces the PARSED dict that DhanTickerAdapter emits internally
# ─────────────────────────────────────────────────────────────────────────────

def make_dhan_parsed_tick(
    security_id: int = 13,       # Dhan NIFTY security_id
    exchange_segment: int = 0,   # NSE
    ltp: float = 24500.50,
    open_: float = 24400.0,
    high: float = 24600.0,
    low: float = 24300.0,
    close: float = 24450.0,
    volume: int = 1_000_000,
    **overrides,
) -> dict:
    """Parsed Dhan Quote-mode tick (after binary parsing)."""
    tick = {
        "security_id": security_id,
        "exchange_segment": exchange_segment,
        "ltp": ltp,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "oi": 5_000_000,
    }
    tick.update(overrides)
    return tick


# ─────────────────────────────────────────────────────────────────────────────
# Fyers — JSON dict (prices already in rupees, symbol is NSE: prefixed)
# ─────────────────────────────────────────────────────────────────────────────

def make_fyers_tick(
    symbol: str = "NSE:NIFTY50-INDEX",
    ltp: float = 24500.50,
    open_: float = 24400.0,
    high: float = 24600.0,
    low: float = 24300.0,
    close: float = 24450.0,
    volume: int = 1_000_000,
    **overrides,
) -> dict:
    """Raw Fyers tick dict (prices in rupees, NSE: symbol prefix)."""
    tick = {
        "symbol": symbol,
        "ltp": ltp,
        "open_price": open_,
        "high_price": high,
        "low_price": low,
        "prev_close_price": close,
        "vol_traded_today": volume,
        "oi": 5_000_000,
        "tt": int(datetime.now().timestamp()),
    }
    tick.update(overrides)
    return tick


# ─────────────────────────────────────────────────────────────────────────────
# Paytm Money — JSON message body (prices in rupees, ISO timestamps)
# ─────────────────────────────────────────────────────────────────────────────

def make_paytm_tick(
    scrip_id: str = "NIFTY50",
    ltp: float = 24500.50,
    open_: float = 24400.0,
    high: float = 24600.0,
    low: float = 24300.0,
    close: float = 24450.0,
    volume: int = 1_000_000,
    **overrides,
) -> dict:
    """Raw Paytm Money tick dict (prices in rupees, ISO timestamp)."""
    tick = {
        "scrip_id": scrip_id,
        "data": {
            "ltp": ltp,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "oi": 5_000_000,
            "timestamp": datetime.now().isoformat(),
        }
    }
    tick.update(overrides)
    return tick


# ─────────────────────────────────────────────────────────────────────────────
# Upstox — uses protobuf; provide the decoded dict that the adapter normalizes
# ─────────────────────────────────────────────────────────────────────────────

def make_upstox_tick(
    instrument_key: str = "NSE_INDEX|Nifty 50",
    ltp: float = 24500.50,
    open_: float = 24400.0,
    high: float = 24600.0,
    low: float = 24300.0,
    close: float = 24450.0,
    volume: int = 1_000_000,
    **overrides,
) -> dict:
    """Decoded Upstox LTPC/Full-mode tick dict."""
    tick = {
        "instrument_key": instrument_key,
        "ltpc": {
            "ltp": ltp,
            "ltt": datetime.now().isoformat(),
            "cp": close,
        },
        "market_ohlc": {
            "ohlc": [
                {"interval": "I1D", "open": open_, "high": high, "low": low, "close": close, "volume": volume}
            ]
        },
        "total_sell_quantity": 500,
        "total_buy_quantity": 500,
    }
    tick.update(overrides)
    return tick
