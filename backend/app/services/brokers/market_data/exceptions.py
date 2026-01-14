"""
Market Data Broker Exceptions

Defines broker-specific exceptions for market data operations.
"""


class MarketDataError(Exception):
    """Base exception for all market data errors."""
    pass


class BrokerAPIError(MarketDataError):
    """Broker API returned an error."""

    def __init__(self, broker: str, message: str, status_code: int = None, raw_response: dict = None):
        self.broker = broker
        self.status_code = status_code
        self.raw_response = raw_response
        super().__init__(f"[{broker}] {message}")


class RateLimitError(MarketDataError):
    """Rate limit exceeded for broker API."""

    def __init__(self, broker: str, retry_after: int = None):
        self.broker = broker
        self.retry_after = retry_after
        message = f"[{broker}] Rate limit exceeded"
        if retry_after:
            message += f" - retry after {retry_after} seconds"
        super().__init__(message)


class AuthenticationError(MarketDataError):
    """Broker authentication failed."""

    def __init__(self, broker: str, message: str = "Authentication failed"):
        self.broker = broker
        super().__init__(f"[{broker}] {message}")


class InvalidSymbolError(MarketDataError):
    """Symbol not found or invalid."""

    def __init__(self, symbol: str, broker: str = None):
        self.symbol = symbol
        self.broker = broker
        message = f"Invalid or unknown symbol: {symbol}"
        if broker:
            message = f"[{broker}] {message}"
        super().__init__(message)


class ConnectionError(MarketDataError):
    """WebSocket or HTTP connection error."""

    def __init__(self, broker: str, message: str = "Connection failed"):
        self.broker = broker
        super().__init__(f"[{broker}] {message}")


class SubscriptionError(MarketDataError):
    """Failed to subscribe to instrument."""

    def __init__(self, broker: str, tokens: list, message: str = None):
        self.broker = broker
        self.tokens = tokens
        msg = f"[{broker}] Failed to subscribe to tokens: {tokens}"
        if message:
            msg += f" - {message}"
        super().__init__(msg)


class DataNotAvailableError(MarketDataError):
    """Requested data not available (e.g., no historical data for date range)."""

    def __init__(self, broker: str, message: str):
        self.broker = broker
        super().__init__(f"[{broker}] {message}")
