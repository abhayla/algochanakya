"""
Symbol Converter

Converts symbols between broker-specific formats and canonical format (Kite).

Canonical Format: NIFTY25APR25000CE (Kite format)
- Monthly expiry: NIFTY25APR25000CE (expiry month in format: YYMMMDD)
- Weekly expiry: NIFTY25424CE (YYMD where D is week number)

This is Phase 1 implementation with basic structure.
Full conversion logic for all 6 brokers will be added in Phase 2-6.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import re
import calendar


@dataclass
class CanonicalSymbol:
    """
    Canonical symbol representation (broker-agnostic).

    Uses Kite format internally for consistency with order execution.
    """
    underlying: str          # "NIFTY", "BANKNIFTY", "FINNIFTY"
    expiry: date            # 2025-04-24
    strike: Decimal         # 25000
    option_type: str        # "CE" or "PE"

    def to_kite_symbol(self) -> str:
        """Convert to Kite format (our canonical string format)."""
        if self.is_monthly_expiry():
            # Monthly: NIFTY25APR25000CE
            return f"{self.underlying}{self.expiry.strftime('%y%b').upper()}{int(self.strike)}{self.option_type}"
        else:
            # Weekly: NIFTY25424CE (YYMD where D is day of month)
            return f"{self.underlying}{self.expiry.strftime('%y%m%d')}{int(self.strike)}{self.option_type}"

    def is_monthly_expiry(self) -> bool:
        """Check if this is a monthly expiry (last Thursday of month)."""
        # Get last Thursday of the month
        last_day = calendar.monthrange(self.expiry.year, self.expiry.month)[1]
        last_date = date(self.expiry.year, self.expiry.month, last_day)

        # Find last Thursday
        while last_date.weekday() != 3:  # 3 = Thursday
            last_date = date(self.expiry.year, self.expiry.month, last_date.day - 1)

        return self.expiry == last_date

    @staticmethod
    def from_kite_symbol(symbol: str) -> "CanonicalSymbol":
        """
        Parse Kite format symbol to CanonicalSymbol.

        Examples:
            NIFTY25APR25000CE -> monthly expiry
            NIFTY25424CE -> weekly expiry (April 24, 2025)
        """
        # Try monthly format first: NIFTY25APR25000CE
        match = re.match(r"^([A-Z]+)(\d{2})([A-Z]{3})(\d+)(CE|PE)$", symbol)
        if match:
            underlying = match.group(1)
            year = int("20" + match.group(2))
            month_str = match.group(3)
            strike = Decimal(match.group(4))
            option_type = match.group(5)

            # Convert month string to number
            month = datetime.strptime(month_str, "%b").month

            # Get last Thursday of month
            last_day = calendar.monthrange(year, month)[1]
            expiry = date(year, month, last_day)
            while expiry.weekday() != 3:  # Thursday
                expiry = date(year, month, expiry.day - 1)

            return CanonicalSymbol(underlying, expiry, strike, option_type)

        # Try weekly format: NIFTY25424CE (YYMMDD)
        match = re.match(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})(\d+)(CE|PE)$", symbol)
        if match:
            underlying = match.group(1)
            year = int("20" + match.group(2))
            month = int(match.group(3))
            day = int(match.group(4))
            strike = Decimal(match.group(5))
            option_type = match.group(6)

            expiry = date(year, month, day)
            return CanonicalSymbol(underlying, expiry, strike, option_type)

        raise ValueError(f"Invalid Kite symbol format: {symbol}")


class SymbolConverter:
    """
    Converts symbols between broker formats and canonical format.

    Phase 1: Basic structure with Kite and SmartAPI support
    Phase 2-6: Add full support for remaining brokers
    """

    def parse_smartapi(self, symbol: str) -> CanonicalSymbol:
        """
        Parse SmartAPI format to canonical.

        SmartAPI format: NIFTY24APR2525000CE
        - Note: Year is FULL (24), not YY (25)
        - Day is included: 25 (April 25, 2025)
        """
        # SmartAPI monthly: NIFTY24APR2525000CE
        match = re.match(r"^([A-Z]+)(\d{2})([A-Z]{3})(\d{2})(\d+)(CE|PE)$", symbol)
        if match:
            underlying = match.group(1)
            day = int(match.group(2))  # Day of month
            month_str = match.group(3)
            year = int("20" + match.group(4))  # Year
            strike = Decimal(match.group(5))
            option_type = match.group(6)

            month = datetime.strptime(month_str, "%b").month
            expiry = date(year, month, day)

            return CanonicalSymbol(underlying, expiry, strike, option_type)

        raise ValueError(f"Invalid SmartAPI symbol format: {symbol}")

    def format_smartapi(self, canonical: CanonicalSymbol) -> str:
        """
        Format canonical to SmartAPI format.

        Returns: NIFTY24APR2525000CE (with day included)
        """
        return f"{canonical.underlying}{canonical.expiry.strftime('%d%b%y').upper()}{int(canonical.strike)}{canonical.option_type}"

    def parse_kite(self, symbol: str) -> CanonicalSymbol:
        """Parse Kite format (already canonical)."""
        return CanonicalSymbol.from_kite_symbol(symbol)

    def format_kite(self, canonical: CanonicalSymbol) -> str:
        """Format canonical to Kite format (identity function)."""
        return canonical.to_kite_symbol()

    def convert(self, symbol: str, from_broker: str, to_broker: str) -> str:
        """
        Convert symbol from one broker format to another.

        Args:
            symbol: Source broker symbol
            from_broker: Source broker type ("smartapi", "kite", etc.)
            to_broker: Target broker type

        Returns:
            Symbol in target broker format

        Example:
            >>> converter = SymbolConverter()
            >>> converter.convert("NIFTY24APR2525000CE", "smartapi", "kite")
            "NIFTY25APR25000CE"
        """
        # Parse from source broker to canonical
        if from_broker == "smartapi":
            canonical = self.parse_smartapi(symbol)
        elif from_broker == "kite":
            canonical = self.parse_kite(symbol)
        elif from_broker == "upstox":
            raise NotImplementedError("Upstox symbol conversion not yet implemented (Phase 3)")
        elif from_broker == "dhan":
            raise NotImplementedError("Dhan symbol conversion not yet implemented (Phase 4)")
        elif from_broker == "fyers":
            raise NotImplementedError("Fyers symbol conversion not yet implemented (Phase 5)")
        elif from_broker == "paytm":
            raise NotImplementedError("Paytm symbol conversion not yet implemented (Phase 6)")
        else:
            raise ValueError(f"Unsupported source broker: {from_broker}")

        # Format from canonical to target broker
        if to_broker == "smartapi":
            return self.format_smartapi(canonical)
        elif to_broker == "kite":
            return self.format_kite(canonical)
        elif to_broker == "upstox":
            raise NotImplementedError("Upstox symbol conversion not yet implemented (Phase 3)")
        elif to_broker == "dhan":
            raise NotImplementedError("Dhan symbol conversion not yet implemented (Phase 4)")
        elif to_broker == "fyers":
            raise NotImplementedError("Fyers symbol conversion not yet implemented (Phase 5)")
        elif to_broker == "paytm":
            raise NotImplementedError("Paytm symbol conversion not yet implemented (Phase 6)")
        else:
            raise ValueError(f"Unsupported target broker: {to_broker}")

    def to_canonical(self, symbol: str, broker: str) -> str:
        """
        Convert broker symbol to canonical (Kite) format.

        Args:
            symbol: Broker-specific symbol
            broker: Broker type

        Returns:
            Canonical symbol (Kite format)
        """
        return self.convert(symbol, broker, "kite")

    def from_canonical(self, canonical_symbol: str, broker: str) -> str:
        """
        Convert canonical (Kite) symbol to broker format.

        Args:
            canonical_symbol: Canonical symbol (Kite format)
            broker: Target broker type

        Returns:
            Broker-specific symbol
        """
        return self.convert(canonical_symbol, "kite", broker)
