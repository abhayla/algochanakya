"""Market Data Broker Abstraction Package"""
from .market_data_base import (
    MarketDataBrokerAdapter,
    MarketDataBrokerType,
    BrokerCredentials,
    SmartAPIMarketDataCredentials,
    KiteMarketDataCredentials,
    UpstoxMarketDataCredentials,
    DhanMarketDataCredentials,
    FyersMarketDataCredentials,
    PaytmMarketDataCredentials,
    OHLCVCandle,
    Instrument,
)
from .ticker_base import TickerService, get_ticker_service
from .symbol_converter import CanonicalSymbol, SymbolConverter
from .exceptions import (
    MarketDataError,
    BrokerAPIError,
    RateLimitError,
    AuthenticationError,
    InvalidSymbolError,
    ConnectionError,
    SubscriptionError,
    DataNotAvailableError,
)
from .rate_limiter import RateLimiter, broker_rate_limiters, rate_limited
from .token_manager import TokenManager, TokenManagerFactory
# Note: Adapters are imported lazily in factory to avoid circular imports
# with smartapi_market_data.py and smartapi_historical.py which import rate_limiter
from .factory import (
    get_market_data_adapter,
    get_user_market_data_adapter,
)

# Lazy imports for adapters - use these functions to get adapter classes
def get_smartapi_adapter_class():
    """Lazy import to avoid circular dependencies."""
    from .smartapi_adapter import SmartAPIMarketDataAdapter
    return SmartAPIMarketDataAdapter

def get_kite_adapter_class():
    """Lazy import to avoid circular dependencies."""
    from .kite_adapter import KiteMarketDataAdapter
    return KiteMarketDataAdapter

__all__ = [
    # Adapters and types
    "MarketDataBrokerAdapter",
    "MarketDataBrokerType",
    "BrokerCredentials",
    "SmartAPIMarketDataCredentials",
    "KiteMarketDataCredentials",
    "UpstoxMarketDataCredentials",
    "DhanMarketDataCredentials",
    "FyersMarketDataCredentials",
    "PaytmMarketDataCredentials",
    "OHLCVCandle",
    "Instrument",
    # Broker adapter factories (lazy import to avoid circular deps)
    "get_smartapi_adapter_class",
    "get_kite_adapter_class",
    # Factory
    "get_market_data_adapter",
    "get_user_market_data_adapter",
    # Ticker service
    "TickerService",
    "get_ticker_service",
    # Symbol conversion
    "CanonicalSymbol",
    "SymbolConverter",
    # Exceptions
    "MarketDataError",
    "BrokerAPIError",
    "RateLimitError",
    "AuthenticationError",
    "InvalidSymbolError",
    "ConnectionError",
    "SubscriptionError",
    "DataNotAvailableError",
    # Rate limiting
    "RateLimiter",
    "broker_rate_limiters",
    "rate_limited",
    # Token management
    "TokenManager",
    "TokenManagerFactory",
]
