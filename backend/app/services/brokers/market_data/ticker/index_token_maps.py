"""Hardcoded index token maps per broker — canonical Kite token → broker format.

Every broker credential block MUST pass a token_map to pool.set_credentials();
without it the ticker adapter connects, subscribes to nothing, and the user
silently gets zero ticks. Formats differ per adapter — see each adapter's
load_token_map() docstring.

broker_instrument_tokens currently only holds smartapi rows, so these index
maps are the working set for the other brokers until per-broker instrument
population lands (Q2 roadmap). SmartAPI's own fallback map lives in
websocket.py next to its DB loader.

Canonical tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265
(see app.constants.trading.INDEX_TOKENS).
"""

INDEX_TOKEN_MAPS = {
    "upstox": {
        256265: "NSE_INDEX|Nifty 50",
        260105: "NSE_INDEX|Nifty Bank",
        257801: "NSE_INDEX|Nifty Fin Service",
        265: "BSE_INDEX|SENSEX",
    },
    "dhan": {
        256265: ("13", "IDX_I"),
        260105: ("25", "IDX_I"),
        257801: ("27", "IDX_I"),
        265: ("51", "IDX_I"),
    },
    "fyers": {
        256265: "NSE:NIFTY50-INDEX",
        260105: "NSE:NIFTYBANK-INDEX",
        257801: "NSE:NIFTYFINSERVICE-INDEX",
        265: "BSE:SENSEX-INDEX",
    },
    # Paytm: only NIFTY/BANKNIFTY security IDs are verified; FINNIFTY/SENSEX
    # IDs are not confirmed against Paytm's scrip master — add once verified.
    "paytm": {
        256265: ("999920000", "NSE", "INDEX"),
        260105: ("999920005", "NSE", "INDEX"),
    },
}
