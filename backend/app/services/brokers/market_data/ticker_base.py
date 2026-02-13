"""
Base Ticker Service Interface

Defines the abstract interface for WebSocket ticker services.
Separate from MarketDataBrokerAdapter because WebSocket management
is a separate concern from REST API operations.

All ticker services must:
1. Normalize prices to RUPEES (Decimal)
2. Convert broker tokens to CANONICAL symbols
3. Return UnifiedQuote objects
4. Handle reconnection with exponential backoff
5. Manage subscription state
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Set, Optional
from app.services.brokers.base import UnifiedQuote


class TickerService(ABC):
    """
    Abstract interface for broker WebSocket ticker services.

    All broker ticker services (SmartAPI, Kite, Upstox, Dhan, Fyers, Paytm)
    must implement this interface.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Establish WebSocket connection to broker.

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close WebSocket connection gracefully.

        Should unsubscribe from all tokens before closing.
        """
        pass

    @abstractmethod
    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to instrument tokens for live ticks.

        Args:
            tokens: List of instrument tokens (broker-specific tokens)
            mode: "ltp" (price only) or "quote" (full quote with depth)

        Raises:
            ConnectionError: If WebSocket not connected
            ValueError: If mode invalid
        """
        pass

    @abstractmethod
    async def unsubscribe(self, tokens: List[int]) -> None:
        """
        Unsubscribe from instrument tokens.

        Args:
            tokens: List of instrument tokens to unsubscribe

        Raises:
            ConnectionError: If WebSocket not connected
        """
        pass

    @abstractmethod
    def on_tick(self, callback: Callable[[List[UnifiedQuote]], None]) -> None:
        """
        Register callback for incoming tick data.

        Callback will be invoked with list of UnifiedQuote objects.
        All prices normalized to RUPEES, all symbols in CANONICAL format.

        Args:
            callback: Function to call with tick data
        """
        pass

    @abstractmethod
    def on_error(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for WebSocket errors.

        Args:
            callback: Function to call with error message
        """
        pass

    @abstractmethod
    def on_close(self, callback: Callable[[str], None]) -> None:
        """
        Register callback for connection close.

        Args:
            callback: Function to call with close reason
        """
        pass

    @abstractmethod
    async def reconnect(self, max_retries: int = 5) -> bool:
        """
        Reconnect WebSocket with exponential backoff.

        Args:
            max_retries: Maximum number of reconnection attempts

        Returns:
            True if reconnection successful, False otherwise
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if WebSocket is currently connected."""
        pass

    @property
    @abstractmethod
    def subscribed_tokens(self) -> Set[int]:
        """Get set of currently subscribed tokens."""
        pass

    @property
    @abstractmethod
    def reconnection_attempts(self) -> int:
        """Get number of reconnection attempts made."""
        pass


def get_ticker_service(broker_type: str, credentials) -> TickerService:
    """
    Factory to get ticker service based on broker type.

    Args:
        broker_type: Broker identifier (smartapi, kite, upstox, dhan, fyers, paytm)
        credentials: Broker-specific credentials object

    Returns:
        TickerService implementation for the broker

    Raises:
        ValueError: If broker type not supported

    Example:
        >>> from app.services.brokers.market_data.ticker_base import get_ticker_service
        >>> ticker = get_ticker_service("smartapi", smartapi_creds)
        >>> await ticker.connect()
        >>> await ticker.subscribe([256265], mode="quote")
    """
    if broker_type == "smartapi":
        from app.services.legacy.smartapi_ticker import SmartAPITickerService
        return SmartAPITickerService(credentials)
    elif broker_type == "kite":
        from app.services.legacy.kite_ticker import KiteTickerService
        return KiteTickerService(credentials)
    elif broker_type == "upstox":
        # Future implementation
        raise NotImplementedError("Upstox ticker service not yet implemented")
    elif broker_type == "dhan":
        # Future implementation
        raise NotImplementedError("Dhan ticker service not yet implemented")
    elif broker_type == "fyers":
        # Future implementation
        raise NotImplementedError("Fyers ticker service not yet implemented")
    elif broker_type == "paytm":
        # Future implementation
        raise NotImplementedError("Paytm ticker service not yet implemented")
    else:
        raise ValueError(f"Unsupported broker type: {broker_type}")
