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
