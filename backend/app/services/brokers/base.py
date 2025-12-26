"""
Base Broker Adapter - Priority 4.2

Defines the abstract interface that all broker adapters must implement.
Provides unified data models for orders, positions, and quotes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BrokerType(str, Enum):
    """Supported broker types."""
    KITE = "kite"           # Zerodha Kite Connect
    UPSTOX = "upstox"       # Upstox (future)
    ANGEL = "angel"         # Angel One (future)
    FYERS = "fyers"         # Fyers (future)


class OrderSide(str, Enum):
    """Order side - buy or sell."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"


class ProductType(str, Enum):
    """Product type for F&O."""
    NRML = "NRML"   # Normal (carry forward)
    MIS = "MIS"     # Margin Intraday Square-off


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    TRIGGER_PENDING = "TRIGGER_PENDING"


class ExchangeType(str, Enum):
    """Exchange types."""
    NSE = "NSE"
    NFO = "NFO"
    BSE = "BSE"
    BFO = "BFO"
    MCX = "MCX"


@dataclass
class UnifiedOrder:
    """
    Unified order representation across all brokers.

    This is the broker-agnostic order format. Each broker adapter
    is responsible for converting to/from this format.
    """
    # Order identification
    order_id: Optional[str] = None  # Broker's order ID
    internal_id: Optional[str] = None  # Our internal tracking ID

    # Instrument details
    exchange: str = "NFO"
    tradingsymbol: str = ""
    instrument_token: Optional[int] = None

    # Order details
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    product: ProductType = ProductType.NRML
    quantity: int = 0
    price: Optional[Decimal] = None  # For LIMIT orders
    trigger_price: Optional[Decimal] = None  # For SL orders

    # Status
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: Optional[Decimal] = None
    pending_quantity: int = 0

    # Metadata
    tag: str = ""  # User tag for the order
    disclosed_quantity: int = 0
    validity: str = "DAY"

    # Timestamps
    placed_at: Optional[datetime] = None
    exchange_timestamp: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Error handling
    status_message: str = ""
    rejection_reason: str = ""

    # Original broker response (for debugging)
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class UnifiedPosition:
    """
    Unified position representation across all brokers.
    """
    # Instrument details
    exchange: str = "NFO"
    tradingsymbol: str = ""
    instrument_token: Optional[int] = None

    # Underlying details (for F&O)
    underlying: str = ""
    expiry: Optional[date] = None
    strike: Optional[Decimal] = None
    option_type: str = ""  # CE, PE, or empty for futures

    # Position details
    quantity: int = 0  # Net quantity (+ve for long, -ve for short)
    buy_quantity: int = 0
    sell_quantity: int = 0

    # Average prices
    average_price: Decimal = Decimal("0")
    buy_average: Decimal = Decimal("0")
    sell_average: Decimal = Decimal("0")

    # P&L
    last_price: Decimal = Decimal("0")
    pnl: Decimal = Decimal("0")
    realised_pnl: Decimal = Decimal("0")
    unrealised_pnl: Decimal = Decimal("0")
    day_pnl: Decimal = Decimal("0")

    # Value
    value: Decimal = Decimal("0")
    buy_value: Decimal = Decimal("0")
    sell_value: Decimal = Decimal("0")

    # Margin
    margin_used: Decimal = Decimal("0")

    # Product type
    product: ProductType = ProductType.NRML

    # Day vs overnight position
    overnight_quantity: int = 0
    day_buy_quantity: int = 0
    day_sell_quantity: int = 0

    # Metadata
    multiplier: int = 1  # Lot size multiplier

    # Original broker response
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class UnifiedQuote:
    """
    Unified quote/LTP representation across all brokers.
    """
    tradingsymbol: str = ""
    exchange: str = ""
    instrument_token: Optional[int] = None

    # Prices
    last_price: Decimal = Decimal("0")
    open: Decimal = Decimal("0")
    high: Decimal = Decimal("0")
    low: Decimal = Decimal("0")
    close: Decimal = Decimal("0")  # Previous close

    # Change
    change: Decimal = Decimal("0")
    change_percent: Decimal = Decimal("0")

    # Volume & OI
    volume: int = 0
    oi: int = 0
    oi_change: int = 0

    # Bid/Ask
    bid_price: Decimal = Decimal("0")
    bid_quantity: int = 0
    ask_price: Decimal = Decimal("0")
    ask_quantity: int = 0

    # Timestamps
    last_trade_time: Optional[datetime] = None
    exchange_timestamp: Optional[datetime] = None

    # Original response
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class BrokerCapabilities:
    """Describes what a broker supports."""
    supports_basket_orders: bool = True
    supports_amo: bool = True  # After Market Orders
    supports_gtt: bool = True  # Good Till Triggered
    supports_trailing_sl: bool = False
    max_orders_per_second: int = 10
    max_instruments_per_quote: int = 500
    supports_websocket: bool = True
    supports_historical_data: bool = True


class BrokerAdapter(ABC):
    """
    Abstract base class for all broker adapters.

    Each broker (Kite, Upstox, Angel, Fyers) must implement this interface
    to be compatible with AlgoChanakya.
    """

    def __init__(self, access_token: str):
        """
        Initialize the broker adapter.

        Args:
            access_token: OAuth access token from broker
        """
        self.access_token = access_token
        self._initialized = False

    @property
    @abstractmethod
    def broker_type(self) -> BrokerType:
        """Return the broker type."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> BrokerCapabilities:
        """Return broker capabilities."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the connection to the broker.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def validate_session(self) -> bool:
        """
        Validate the current session/token is still valid.

        Returns:
            True if session is valid
        """
        pass

    # =========================================================================
    # Order Management
    # =========================================================================

    @abstractmethod
    async def place_order(self, order: UnifiedOrder) -> UnifiedOrder:
        """
        Place a new order.

        Args:
            order: Order to place

        Returns:
            Updated order with order_id and status
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[Decimal] = None,
        trigger_price: Optional[Decimal] = None,
        order_type: Optional[OrderType] = None
    ) -> UnifiedOrder:
        """
        Modify an existing order.

        Args:
            order_id: Order ID to modify
            quantity: New quantity (optional)
            price: New price (optional)
            trigger_price: New trigger price (optional)
            order_type: New order type (optional)

        Returns:
            Updated order
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful
        """
        pass

    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[UnifiedOrder]:
        """
        Get order details.

        Args:
            order_id: Order ID

        Returns:
            Order details or None if not found
        """
        pass

    @abstractmethod
    async def get_orders(self) -> List[UnifiedOrder]:
        """
        Get all orders for the day.

        Returns:
            List of orders
        """
        pass

    async def place_basket_order(self, orders: List[UnifiedOrder]) -> List[UnifiedOrder]:
        """
        Place multiple orders as a basket.

        Default implementation places orders sequentially.
        Brokers with native basket support can override.

        Args:
            orders: List of orders to place

        Returns:
            List of placed orders with status
        """
        results = []
        for order in orders:
            try:
                result = await self.place_order(order)
                results.append(result)
            except Exception as e:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = str(e)
                results.append(order)
        return results

    # =========================================================================
    # Position Management
    # =========================================================================

    @abstractmethod
    async def get_positions(self) -> List[UnifiedPosition]:
        """
        Get all current positions.

        Returns:
            List of positions
        """
        pass

    async def get_net_positions(self) -> List[UnifiedPosition]:
        """
        Get net positions (day + carry forward).

        Default filters positions with quantity != 0.
        """
        positions = await self.get_positions()
        return [p for p in positions if p.quantity != 0]

    # =========================================================================
    # Market Data
    # =========================================================================

    @abstractmethod
    async def get_ltp(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get last traded price for instruments.

        Args:
            instruments: List of "EXCHANGE:SYMBOL" strings

        Returns:
            Dict mapping instrument to quote
        """
        pass

    @abstractmethod
    async def get_quote(self, instruments: List[str]) -> Dict[str, UnifiedQuote]:
        """
        Get full quote for instruments.

        Args:
            instruments: List of "EXCHANGE:SYMBOL" strings

        Returns:
            Dict mapping instrument to quote
        """
        pass

    # =========================================================================
    # Account Information
    # =========================================================================

    @abstractmethod
    async def get_margins(self) -> Dict[str, Any]:
        """
        Get account margins.

        Returns:
            Dict with margin details
        """
        pass

    @abstractmethod
    async def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile.

        Returns:
            Dict with user details
        """
        pass

    # =========================================================================
    # Instruments
    # =========================================================================

    @abstractmethod
    async def get_instruments(self, exchange: str = "NFO") -> List[Dict[str, Any]]:
        """
        Get available instruments.

        Args:
            exchange: Exchange to fetch instruments for

        Returns:
            List of instrument dictionaries
        """
        pass

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _log_error(self, method: str, error: Exception):
        """Log an error with context."""
        logger.error(f"[{self.broker_type.value}] {method} failed: {error}")

    def _log_info(self, method: str, message: str):
        """Log info with context."""
        logger.info(f"[{self.broker_type.value}] {method}: {message}")
