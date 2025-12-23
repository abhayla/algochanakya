"""Utility functions for constructing Kite tradingsymbols."""
from datetime import date, timedelta


def build_tradingsymbol(
    underlying: str,
    expiry: date,
    strike: float,
    contract_type: str
) -> str:
    """
    Build Kite tradingsymbol for options.

    Format examples:
    - Weekly: NIFTY25D3026000CE (YY + single char month + DD + strike + type)
    - Monthly: NIFTY25DEC26000CE (YY + MMM + strike + type)

    Args:
        underlying: Underlying symbol (e.g., "NIFTY", "BANKNIFTY")
        expiry: Expiry date
        strike: Strike price
        contract_type: Option type ("CE" or "PE")

    Returns:
        Tradingsymbol string (e.g., "NIFTY25D3026000CE")
    """
    year = expiry.strftime("%y")  # e.g., "25"
    day = expiry.day

    # Determine if weekly or monthly expiry
    is_monthly = _is_monthly_expiry(expiry)

    if is_monthly:
        month_str = expiry.strftime("%b").upper()  # e.g., "DEC"
        expiry_str = f"{year}{month_str}"
    else:
        # Weekly format: YY + single char month + DD
        # Special handling for Oct(O), Nov(N), Dec(D)
        month_char = "O" if expiry.month == 10 else (
            "N" if expiry.month == 11 else (
                "D" if expiry.month == 12 else expiry.strftime("%b")[0]
            )
        )
        expiry_str = f"{year}{month_char}{day:02d}"

    return f"{underlying}{expiry_str}{int(strike)}{contract_type}"


def _is_monthly_expiry(expiry: date) -> bool:
    """Check if expiry is a monthly expiry (last Thursday of month)."""
    # Get last day of month
    if expiry.month == 12:
        next_month = date(expiry.year + 1, 1, 1)
    else:
        next_month = date(expiry.year, expiry.month + 1, 1)

    last_day = next_month - timedelta(days=1)

    # Find last Thursday (weekday 3 = Thursday)
    days_since_thursday = (last_day.weekday() - 3) % 7
    last_thursday = last_day - timedelta(days=days_since_thursday)

    return expiry == last_thursday
