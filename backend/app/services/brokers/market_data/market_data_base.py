"""
Market Data Broker Adapter Base Interface

Defines the abstract interface for market data broker adapters.
Separate from order execution (BrokerAdapter) to allow independent broker selection:
- Market Data Broker: For live prices, historical OHLCV, WebSocket ticks
- Order Execution Broker: For placing orders, managing positions

All adapters must:
1. Normalize all prices to RUPEES (Decimal)
2. Normalize all symbols to CANONICAL format (Kite format)
3. Normalize all tokens to int
4. Normalize all timestamps to datetime (IST)
5. Return UnifiedQuote for all quote methods
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Optional, Any, Callable
from uuid import UUID

# Import UnifiedQuote from the order execution broker base
from app.services.brokers.base import UnifiedQuote


class MarketDataBrokerType(str, Enum):
    """Supported market data broker types."""
    SMARTAPI = "smartapi"  # Angel One SmartAPI - FREE
    KITE = "kite"          # Zerodha Kite Connect - ₹500/mo
    UPSTOX = "upstox"      # Upstox - FREE
    DHAN = "dhan"          # Dhan - FREE (25 F&O trades/mo) or ₹499/mo
    FYERS = "fyers"        # Fyers - FREE
    PAYTM = "paytm"        # Paytm Money - FREE


@dataclass
class BrokerCredentials:
    """Base class for broker credentials."""
    broker_type: str
    user_id: UUID


@dataclass
class SmartAPIMarketDataCredentials(BrokerCredentials):
    """SmartAPI-specific credentials for market data."""
    client_id: str
    jwt_token: str
    feed_token: str
    broker_type: str = "smartapi"


@dataclass
class KiteMarketDataCredentials(BrokerCredentials):
    """Kite-specific credentials for market data."""
    api_key: str
    access_token: str
    broker_type: str = "kite"


@dataclass
class UpstoxMarketDataCredentials(BrokerCredentials):
    """Upstox-specific credentials for market data."""
    api_key: str
    access_token: str
    broker_type: str = "upstox"


@dataclass
class DhanMarketDataCredentials(BrokerCredentials):
    """Dhan-specific credentials for market data."""
    client_id: str
    access_token: str
    broker_type: str = "dhan"


@dataclass
class FyersMarketDataCredentials(BrokerCredentials):
    """Fyers-specific credentials for market data."""
    app_id: str
    access_token: str
    broker_type: str = "fyers"


@dataclass
class PaytmMarketDataCredentials(BrokerCredentials):
    """Paytm-specific credentials for market data."""
    api_key: str
    access_token: str
    broker_type: str = "paytm"


@dataclass
class OHLCVCandle:
    """Historical OHLC+Volume candle."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    oi: Optional[int] = None  # For F&O instruments

    # Raw response for debugging
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class Instrument:
    """Instrument definition (broker-agnostic)."""
    # Canonical identification
    canonical_symbol: str           # NIFTY25APR25000CE (Kite format)
    exchange: str                   # NSE, NFO, BSE, MCX

    # Broker-specific
    broker_symbol: str              # Broker-specific format
    instrument_token: int           # Broker token

    # Display
    tradingsymbol: str             # Human-readable name
    name: str                      # Full name (e.g., "NIFTY 24 APR 25000 CE")

    # For options
    underlying: Optional[str] = None        # NIFTY, BANKNIFTY
    expiry: Optional[date] = None          # 2025-04-24
    strike: Optional[Decimal] = None        # 25000
    option_type: Optional[str] = None       # CE, PE

    # For futures
    instrument_type: str = "EQ"    # EQ, FUT, CE, PE

    # Trading details
    lot_size: int = 1
    tick_size: Decimal = Decimal("0.05")
    is_tradable: bool = True

    # Metadata
    segment: str = "NFO"           # CASH, NFO, BFO, MCX
    last_price: Optional[Decimal] = None


class MarketDataBrokerAdapter(ABC):
    """
    Abstract interface for all market data broker adapters.

    EVERY adapter MUST:
    1. Normalize all prices to RUPEES (Decimal)
    2. Normalize all symbols to CANONICAL format (Kite: NIFTY25APR25000CE)
    3. Normalize all tokens to int
    4. Normalize all timestamps to datetime (IST)
    5. Return UnifiedQuote for all quote methods

    CRITICAL: SmartAPI returns prices in PAISE - adapter must divide by 100!
    """

    def __init__(self, credentials: BrokerCredentials):
        """
        Initialize the market data adapter.

        Args:
            credentials: Broker-specific credentials object
        """
        self.credentials = credentials
        self._initialized = False

    @property
    @abstractmethod
    def broker_type(self) -> MarketDataBrokerType:
        """Return the broker type identifier."""
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE QUOTES (REST API)
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def get_quote(self, symbols: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quotes for symbols.

        Args:
            symbols: List of CANONICAL symbols (Kite format: NIFTY25APR25000CE)

        Returns:
            Dict mapping canonical symbol to UnifiedQuote
            All prices in RUPEES (Decimal), all symbols in CANONICAL format

        Raises:
            RateLimitError: If rate limit exceeded
            BrokerAPIError: If broker API call fails
        """
        pass

    @abstractmethod
    async def get_ltp(self, symbols: List[str]) -> Dict[str, Decimal]:
        """
        Get LTP only (lightweight).

        Args:
            symbols: List of CANONICAL symbols

        Returns:
            Dict mapping canonical symbol to LTP (Decimal, in RUPEES)

        Raises:
            RateLimitError: If rate limit exceeded
            BrokerAPIError: If broker API call fails
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # WEBSOCKET TICKS
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def subscribe(self, tokens: List[int], mode: str = "quote") -> None:
        """
        Subscribe to live ticks via WebSocket.

        Args:
            tokens: List of instrument tokens (broker-specific tokens)
            mode: "ltp" (price only) or "quote" (full quote with depth)

        Raises:
            ConnectionError: If WebSocket not connected
            BrokerAPIError: If subscription fails
        """
        pass

    @abstractmethod
    async def unsubscribe(self, tokens: List[int]) -> None:
        """
        Unsubscribe from live ticks.

        Args:
            tokens: List of instrument tokens to unsubscribe

        Raises:
            ConnectionError: If WebSocket not connected
        """
        pass

    @abstractmethod
    def on_tick(self, callback: Callable[[List[UnifiedQuote]], None]) -> None:
        """
        Register callback for incoming ticks.

        Callback receives list of UnifiedQuote (normalized to RUPEES, canonical symbols).

        Args:
            callback: Function to call with tick data
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # HISTORICAL DATA
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def get_historical(
        self,
        symbol: str,
        from_date: date,
        to_date: date,
        interval: str = "day"  # "1min", "5min", "15min", "hour", "day"
    ) -> List[OHLCVCandle]:
        """
        Get historical OHLCV data.

        Args:
            symbol: CANONICAL symbol (Kite format)
            from_date: Start date
            to_date: End date
            interval: Candle interval

        Returns:
            List of OHLCV candles (prices in RUPEES, Decimal)

        Raises:
            InvalidSymbolError: If symbol not found
            RateLimitError: If rate limit exceeded
            BrokerAPIError: If broker API call fails
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # INSTRUMENTS
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def get_instruments(self, exchange: str = "NFO") -> List[Instrument]:
        """
        Get all instruments for exchange.

        Args:
            exchange: Exchange code (NSE, NFO, BSE, BFO, MCX)

        Returns:
            List of Instrument objects with canonical symbols

        Raises:
            BrokerAPIError: If broker API call fails
        """
        pass

    @abstractmethod
    async def search_instruments(self, query: str) -> List[Instrument]:
        """
        Search instruments by name/symbol.

        Args:
            query: Search query (e.g., "NIFTY", "25000 CE")

        Returns:
            List of matching Instrument objects

        Raises:
            BrokerAPIError: If broker API call fails
        """
        pass

    @abstractmethod
    async def get_token(self, symbol: str) -> int:
        """
        Get broker token for canonical symbol.

        Uses internal mapping table (broker_instrument_tokens).

        Args:
            symbol: CANONICAL symbol (Kite format)

        Returns:
            Broker-specific instrument token

        Raises:
            InvalidSymbolError: If symbol not found in mapping
        """
        pass

    @abstractmethod
    async def get_symbol(self, token: int) -> str:
        """
        Get canonical symbol for broker token.

        Args:
            token: Broker-specific instrument token

        Returns:
            CANONICAL symbol (Kite format)

        Raises:
            InvalidSymbolError: If token not found in mapping
        """
        pass

    # ═══════════════════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to broker (WebSocket if applicable).

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If credentials invalid
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to broker gracefully.

        Should unsubscribe from all tokens before closing WebSocket.
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to broker."""
        pass
