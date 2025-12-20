"""
Centralized Trading Constants

This is the SINGLE SOURCE OF TRUTH for trading parameters.
Do NOT hardcode these values elsewhere - import from this module.

Updated: 2025-12-20
User requirement: All strike steps should be 100 (round to nearest 100)
"""

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
}


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
