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
from .smartapi_adapter import SmartAPIMarketDataAdapter
from .kite_adapter import KiteMarketDataAdapter
from .factory import (
    get_market_data_adapter,
    get_user_market_data_adapter,
)

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
    # Broker adapters
    "SmartAPIMarketDataAdapter",
    "KiteMarketDataAdapter",
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
