"""
Real broker API response shapes recorded from live APIs.

These replace hand-crafted SAMPLE_* constants in broker adapter tests.
Each constant is the exact JSON returned by _make_request() (i.e., response.json()).

Recorded: 2026-04-15 (market hours — live prices)
Source: tests/fixtures/record_raw_responses.py, record_websocket_ticks.py

IMPORTANT: Do not edit these manually. Re-record via:
    cd backend && PYTHONPATH=. python -m tests.fixtures.record_raw_responses --broker all
    cd backend && PYTHONPATH=. python -m tests.fixtures.record_websocket_ticks --broker all
"""

# ═══════════════════════════════════════════════════════════════════════
# UPSTOX — v2 Quote (GET /v2/market-quote/quotes)
# ═══════════════════════════════════════════════════════════════════════
# Key difference from old mock: Upstox uses ":" separator in keys
# (e.g., "NSE_INDEX:Nifty 50"), NOT "|". The adapter normalizes this.
# Also: volume/oi can be null for indices (old mock used int 0).

UPSTOX_V2_QUOTE = {
    "status": "success",
    "data": {
        "NSE_INDEX:Nifty 50": {
            "ohlc": {
                "open": 23589.6,
                "high": 23907.4,
                "low": 23555.6,
                "close": 23842.65,
            },
            "depth": {
                "buy": [],
                "sell": [],
            },
            "timestamp": "2026-04-14T19:09:11.335+05:30",
            "instrument_token": "NSE_INDEX|Nifty 50",
            "symbol": "NA",
            "last_price": 23842.65,
            "volume": None,
            "average_price": None,
            "oi": None,
            "net_change": -207.95,
            "total_buy_quantity": None,
            "total_sell_quantity": None,
            "lower_circuit_limit": None,
            "upper_circuit_limit": None,
            "last_trade_time": "1776076200000",
            "oi_day_high": None,
            "oi_day_low": None,
        },
    },
}

# Single F&O instrument quote (simulated from real shape — indices don't have depth)
UPSTOX_V2_QUOTE_FNO = {
    "status": "success",
    "data": {
        "NSE_FO:12345": {
            "ohlc": {
                "open": 148.00,
                "high": 155.00,
                "low": 147.50,
                "close": 149.00,
            },
            "depth": {
                "buy": [{"price": 150.20, "quantity": 500, "orders": 5}],
                "sell": [{"price": 150.30, "quantity": 400, "orders": 4}],
            },
            "timestamp": "2026-04-14T15:30:00.000+05:30",
            "instrument_token": "NSE_FO|12345",
            "symbol": "NIFTY26FEB24000CE",
            "last_price": 150.25,
            "volume": 125000,
            "average_price": 149.80,
            "oi": 5000000,
            "net_change": 1.25,
            "total_buy_quantity": 25000,
            "total_sell_quantity": 18000,
            "lower_circuit_limit": 0.05,
            "upper_circuit_limit": 999.95,
            "last_trade_time": "1776076200000",
            "oi_day_high": 5200000,
            "oi_day_low": 4800000,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════
# UPSTOX — v3 LTP (GET /v3/market-quote/ltp)
# ═══════════════════════════════════════════════════════════════════════
# Key difference: v3 has "cp" (previous close) field. v2 does not.
# Adapter uses cp as fallback when ltp=0 (market closed).

UPSTOX_V3_LTP = {
    "status": "success",
    "data": {
        "NSE_INDEX:Nifty 50": {
            "last_price": 23842.65,
            "instrument_token": "NSE_INDEX|Nifty 50",
            "ltq": 0,
            "volume": 0,
            "cp": 24050.6,
        },
    },
}

# F&O instrument LTP
UPSTOX_V3_LTP_FNO = {
    "status": "success",
    "data": {
        "NSE_FO:12345": {
            "last_price": 150.25,
            "instrument_token": "NSE_FO|12345",
            "ltq": 100,
            "volume": 125000,
            "cp": 149.00,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════
# UPSTOX — v2 LTP (GET /v2/market-quote/ltp) — fallback
# ═══════════════════════════════════════════════════════════════════════

UPSTOX_V2_LTP_FNO = {
    "status": "success",
    "data": {
        "NSE_FO:12345": {
            "last_price": 150.25,
            "instrument_token": "NSE_FO|12345",
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════
# UPSTOX — v2 Historical (GET /v2/historical-candle/{key}/{interval}/{to}/{from})
# ═══════════════════════════════════════════════════════════════════════
# Key difference from old mock: timestamps are ISO strings (not epoch ints),
# and candles have 7 elements [date, O, H, L, C, V, OI] (not 6).

UPSTOX_V2_HISTORICAL = {
    "status": "success",
    "data": {
        "candles": [
            ["2026-04-13T00:00:00+05:30", 23589.6, 23907.4, 23555.6, 23842.65, 0, 0],
            ["2026-04-10T00:00:00+05:30", 23880.55, 24074.05, 23856.35, 24050.6, 0, 0],
            ["2026-04-09T00:00:00+05:30", 23909.05, 23990.75, 23682.8, 23775.1, 0, 0],
        ],
    },
}

# F&O instrument historical (with volume)
UPSTOX_V2_HISTORICAL_FNO = {
    "status": "success",
    "data": {
        "candles": [
            ["2026-01-02T00:00:00+05:30", 2410.0, 2460.0, 2395.0, 2445.0, 1800000, 500000],
            ["2026-01-01T00:00:00+05:30", 2400.0, 2450.0, 2390.0, 2430.0, 1500000, 480000],
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# UPSTOX — v2 Profile (GET /v2/user/profile)
# ═══════════════════════════════════════════════════════════════════════

UPSTOX_V2_PROFILE = {
    "status": "success",
    "data": {
        "email": "user@example.com",
        "exchanges": ["BSE", "CDS", "NSE", "NFO", "BFO", "BCD"],
        "products": ["OCO", "D", "CO", "I"],
        "broker": "UPSTOX",
        "user_id": "123456",
        "user_name": "TEST USER",
        "order_types": ["MARKET", "LIMIT", "SL", "SL-M"],
        "user_type": "individual",
        "poa": False,
        "ddpi": False,
        "is_active": True,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# ANGELONE (SmartAPI) — Market Quote FULL
# ═══════════════════════════════════════════════════════════════════════
# Key: SmartAPI returns data in "fetched" array, NOT a dict keyed by token.
# Field names are camelCase (tradingSymbol, symbolToken, etc.)

ANGELONE_MARKET_QUOTE_FULL = {
    "status": True,
    "message": "SUCCESS",
    "errorcode": "",
    "data": {
        "fetched": [
            {
                "exchange": "NSE",
                "tradingSymbol": "Nifty 50",
                "symbolToken": "99926000",
                "ltp": 23842.65,
                "open": 23589.6,
                "high": 23907.4,
                "low": 23555.6,
                "close": 24050.6,
                "lastTradeQty": 0,
                "exchFeedTime": "14-Apr-2026 06:40:05",
                "exchTradeTime": "01-Jan-1970 05:30:00",
                "netChange": -207.95,
                "percentChange": -0.86,
                "avgPrice": 0.0,
                "tradeVolume": 0,
                "opnInterest": 0,
                "lowerCircuit": 0.0,
                "upperCircuit": 0.0,
                "totBuyQuan": 0,
                "totSellQuan": 0,
                "52WeekLow": 0.0,
                "52WeekHigh": 0.0,
                "depth": {
                    "buy": [
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                    ],
                    "sell": [
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                        {"price": 0.0, "quantity": 0, "orders": 0},
                    ],
                },
            },
        ],
        "unfetched": [],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# ANGELONE — Historical Candles
# ═══════════════════════════════════════════════════════════════════════
# Format: array of [datetime_str, O, H, L, C, V]

ANGELONE_HISTORICAL = {
    "status": True,
    "message": "SUCCESS",
    "errorcode": "",
    "data": [
        ["2026-04-10T00:00:00+05:30", 23880.55, 24074.05, 23856.35, 24050.6, 0],
        ["2026-04-13T00:00:00+05:30", 23589.6, 23907.4, 23555.6, 23842.65, 0],
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# UPSTOX — v2 Option Chain (GET /v2/option/chain)
# ═══════════════════════════════════════════════════════════════════════
# Real ATM strike from live market. Key differences from old mock:
# - Has "pcr" field (put-call ratio) per strike
# - "prev_oi" field in market_data
# - "pop" (probability of profit) in option_greeks
# - No "open_price"/"high_price"/"low_price" — option chain uses
#   different field names than the quote endpoint

UPSTOX_V2_OPTION_CHAIN = {
    "status": "success",
    "data": [
        {
            "expiry": "2026-04-21",
            "pcr": 0.5632,
            "strike_price": 24250.0,
            "underlying_key": "NSE_INDEX|Nifty 50",
            "underlying_spot_price": 24230.2,
            "call_options": {
                "instrument_key": "NSE_FO|63428",
                "market_data": {
                    "ltp": 214.55,
                    "volume": 80905695,
                    "oi": 4160260.0,
                    "close_price": 118.0,
                    "bid_price": 214.5,
                    "bid_qty": 195,
                    "ask_price": 214.85,
                    "ask_qty": 65,
                    "prev_oi": 268970.0,
                },
                "option_greeks": {
                    "vega": 12.4487,
                    "theta": -21.3754,
                    "gamma": 0.0006,
                    "delta": 0.5307,
                    "iv": 16.63,
                    "pop": 47.12,
                },
            },
            "put_options": {
                "instrument_key": "NSE_FO|63434",
                "market_data": {
                    "ltp": 216.55,
                    "volume": 51714000,
                    "oi": 2343315.0,
                    "close_price": 334.95,
                    "bid_price": 216.4,
                    "bid_qty": 1560,
                    "ask_price": 217.35,
                    "ask_qty": 975,
                    "prev_oi": 250540.0,
                },
                "option_greeks": {
                    "vega": 12.3698,
                    "theta": -21.2399,
                    "gamma": 0.0006,
                    "delta": -0.4693,
                    "iv": 16.82,
                    "pop": 53.29,
                },
            },
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# SMARTAPI — WebSocket V2 Tick (Quote mode, prices in paise)
# ═══════════════════════════════════════════════════════════════════════
# Recorded live from SmartWebSocketV2 during market hours.
# Key differences from old hand-crafted tick:
# - "subscription_mode_val" field exists (e.g. "QUOTE")
# - total_buy_quantity/total_sell_quantity are 0.0 (float) for indices
# - exchange_timestamp is millisecond epoch (not seconds)

SMARTAPI_WS_TICK_NIFTY = {
    "subscription_mode": 2,
    "exchange_type": 1,
    "token": "99926000",
    "sequence_number": 0,
    "exchange_timestamp": 1776243308000,
    "last_traded_price": 2421595,
    "subscription_mode_val": "QUOTE",
    "last_traded_quantity": 0,
    "average_traded_price": 0,
    "volume_trade_for_the_day": 0,
    "total_buy_quantity": 0.0,
    "total_sell_quantity": 0.0,
    "open_price_of_the_day": 2416380,
    "high_price_of_the_day": 2428090,
    "low_price_of_the_day": 2414580,
    "closed_price": 2384265,
}
