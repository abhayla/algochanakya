"""
Centralized Trading Constants

This is the SINGLE SOURCE OF TRUTH for trading parameters.
Do NOT hardcode these values elsewhere - import from this module.

Updated: 2025-12-21
User requirement: All strike steps should be 100 (round to nearest 100)
"""

# =============================================================================
# UNDERLYING INSTRUMENTS
# =============================================================================

UNDERLYINGS = ["NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY"]

# Strike step intervals for each underlying (points between strikes)
# All set to 100 per user requirement for consistent rounding
STRIKE_STEPS = {
    "NIFTY": 100,
    "BANKNIFTY": 100,
    "FINNIFTY": 100,
    "SENSEX": 100,
}

# Lot sizes for each underlying
LOT_SIZES = {
    "NIFTY": 25,
    "BANKNIFTY": 15,
    "FINNIFTY": 25,
    "SENSEX": 10,
    "MIDCPNIFTY": 75,
}

# =============================================================================
# INDEX TOKENS (NSE instrument tokens for WebSocket subscriptions)
# =============================================================================

INDEX_TOKENS = {
    "NIFTY": 256265,      # NSE:NIFTY 50
    "BANKNIFTY": 260105,  # NSE:NIFTY BANK
    "FINNIFTY": 257801,   # NSE:NIFTY FIN SERVICE
    "SENSEX": 265,        # BSE:SENSEX
    "INDIAVIX": 264969,   # NSE:INDIA VIX
}

# Exchange mappings for indices
INDEX_EXCHANGES = {
    "NIFTY": "NSE",
    "BANKNIFTY": "NSE",
    "FINNIFTY": "NSE",
    "SENSEX": "BSE",
    "INDIAVIX": "NSE",
}

# Kite Connect trading symbols for LTP API
INDEX_SYMBOLS = {
    "NIFTY": "NSE:NIFTY 50",
    "BANKNIFTY": "NSE:NIFTY BANK",
    "FINNIFTY": "NSE:NIFTY FIN SERVICE",
    "SENSEX": "BSE:SENSEX",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_strike_step(underlying: str) -> int:
    """
    Get strike step interval for an underlying.

    Args:
        underlying: Underlying symbol (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)

    Returns:
        Strike step in points (defaults to 100 if underlying not found)

    Example:
        >>> get_strike_step("NIFTY")
        100
        >>> get_strike_step("UNKNOWN")
        100
    """
    return STRIKE_STEPS.get(underlying.upper(), 100)


def get_lot_size(underlying: str) -> int:
    """
    Get lot size for an underlying.

    Args:
        underlying: Underlying symbol (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)

    Returns:
        Lot size (defaults to 25 if underlying not found)

    Example:
        >>> get_lot_size("NIFTY")
        25
        >>> get_lot_size("BANKNIFTY")
        15
    """
    return LOT_SIZES.get(underlying.upper(), 25)


def get_index_token(underlying: str) -> int:
    """
    Get NSE instrument token for an underlying.

    Args:
        underlying: Underlying symbol (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)

    Returns:
        Index token or None if underlying not found

    Example:
        >>> get_index_token("NIFTY")
        256265
    """
    return INDEX_TOKENS.get(underlying.upper())


def get_index_symbol(underlying: str) -> str:
    """
    Get Kite trading symbol for an underlying.

    Args:
        underlying: Underlying symbol (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)

    Returns:
        Trading symbol or None if underlying not found

    Example:
        >>> get_index_symbol("NIFTY")
        'NSE:NIFTY 50'
    """
    return INDEX_SYMBOLS.get(underlying.upper())


def is_valid_underlying(underlying: str) -> bool:
    """
    Check if underlying is supported.

    Args:
        underlying: Underlying symbol to validate

    Returns:
        True if underlying is supported, False otherwise

    Example:
        >>> is_valid_underlying("NIFTY")
        True
        >>> is_valid_underlying("UNKNOWN")
        False
    """
    return underlying.upper() in UNDERLYINGS
