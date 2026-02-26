"""
Shared constants for live integration tests.

All instrument tokens, symbols, and test parameters are centralized here.
Never hardcode tokens or symbols directly in test files — import from here.
"""

from datetime import date, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Canonical instrument tokens (Kite/NSE standard)
# ─────────────────────────────────────────────────────────────────────────────
NIFTY_TOKEN = 256265
BANKNIFTY_TOKEN = 260105
FINNIFTY_TOKEN = 257801
SENSEX_TOKEN = 265

# ─────────────────────────────────────────────────────────────────────────────
# Index symbols for SmartAPI — must match SmartAPIMarketDataAdapter.INDEX_SYMBOLS
# (no "NSE:" prefix — SmartAPI uses bare index names for get_index_quote)
# ─────────────────────────────────────────────────────────────────────────────
NIFTY_SYMBOL = "NIFTY 50"
BANKNIFTY_SYMBOL = "NIFTY BANK"
FINNIFTY_SYMBOL = "NIFTY FIN SERVICE"

# ─────────────────────────────────────────────────────────────────────────────
# Tokens to subscribe for WebSocket tick tests
# ─────────────────────────────────────────────────────────────────────────────
LIVE_TICK_TOKENS = [NIFTY_TOKEN, BANKNIFTY_TOKEN]

# ─────────────────────────────────────────────────────────────────────────────
# Historical data parameters
# ─────────────────────────────────────────────────────────────────────────────
HIST_TO_DATE = date.today()
HIST_FROM_DATE = date.today() - timedelta(days=5)  # 5 trading days back
HIST_INTERVAL = "day"

# ─────────────────────────────────────────────────────────────────────────────
# All supported broker identifiers (used for parametrize IDs)
# ─────────────────────────────────────────────────────────────────────────────
ALL_BROKERS = ["angelone", "kite", "upstox", "dhan", "fyers", "paytm"]

# ─────────────────────────────────────────────────────────────────────────────
# Timeouts
# ─────────────────────────────────────────────────────────────────────────────
TICK_WAIT_SECONDS = 10      # seconds to wait for live ticks to arrive
API_TIMEOUT_SECONDS = 30    # max time for a REST API call

# ─────────────────────────────────────────────────────────────────────────────
# Price sanity bounds (NIFTY/BANKNIFTY realistic range)
# ─────────────────────────────────────────────────────────────────────────────
NIFTY_MIN_PRICE = 10_000
NIFTY_MAX_PRICE = 100_000
BANKNIFTY_MIN_PRICE = 20_000
BANKNIFTY_MAX_PRICE = 200_000

# ─────────────────────────────────────────────────────────────────────────────
# Required .env keys per broker
# ─────────────────────────────────────────────────────────────────────────────
BROKER_REQUIRED_ENV_KEYS = {
    "angelone": ["ANGEL_CLIENT_ID", "ANGEL_PIN", "ANGEL_TOTP_SECRET", "ANGEL_API_KEY"],
    "kite":     ["KITE_API_KEY", "KITE_API_SECRET"],
    "upstox":   ["UPSTOX_API_KEY", "UPSTOX_API_SECRET"],
    "dhan":     ["DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN"],
    "fyers":    ["FYERS_APP_ID", "FYERS_SECRET_KEY"],
    "paytm":    ["PAYTM_API_KEY", "PAYTM_API_SECRET"],
}
