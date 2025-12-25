"""
AI Services Module

Autonomous AI trading system services including:
- Historical data fetching with caching
- Technical indicators calculation (RSI, ADX, EMA, ATR, Bollinger Bands)
- Market regime classification
- Strategy recommendation engine
- Position synchronization
"""

from app.services.ai.indicators import TechnicalIndicators
from app.services.ai.historical_data import HistoricalDataService
from app.services.ai.market_regime import MarketRegimeClassifier, RegimeType, RegimeResult

__all__ = [
    "TechnicalIndicators",
    "HistoricalDataService",
    "MarketRegimeClassifier",
    "RegimeType",
    "RegimeResult",
]
