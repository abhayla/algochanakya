"""
IV Metrics Service

Calculates IV Rank and IV Percentile for monitoring volatility conditions.
Phase 5B Feature #53.

IV Rank = (Current IV - 52w Low) / (52w High - Low) * 100
IV Percentile = % of days in past year where IV was lower than current
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.market_data import MarketDataService

logger = logging.getLogger(__name__)


class IVMetricsService:
    """
    Service for calculating IV Rank and IV Percentile.

    Note: For initial implementation, we'll use VIX as a proxy for IV.
    Future enhancement: Store historical IV per underlying.
    """

    CACHE_TTL = 300  # 5 minutes (IV doesn't change rapidly)

    # VIX historical ranges (approximate - should be calculated from DB)
    VIX_52W_HIGH = 35.0  # Typical high during volatility spike
    VIX_52W_LOW = 10.0   # Typical low during calm markets

    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data
        self._cache: Dict[str, Dict] = {}

    async def get_iv_rank(self, underlying: str = "NIFTY") -> float:
        """
        Calculate IV Rank (0-100).

        IV Rank = (Current IV - 52w Low) / (52w High - Low) * 100

        Higher IV Rank means current volatility is high relative to past year.
        - 0-25: Low volatility
        - 25-50: Medium volatility
        - 50-75: High volatility
        - 75-100: Very high volatility

        Returns:
            IV Rank as percentage (0-100)
        """
        try:
            # Get current VIX (proxy for IV)
            current_vix = await self.market_data.get_vix()

            if current_vix is None:
                logger.warning("VIX data not available, returning default IV Rank")
                return 50.0  # Neutral value

            current_iv = float(current_vix)

            # Calculate IV Rank
            iv_range = self.VIX_52W_HIGH - self.VIX_52W_LOW
            if iv_range == 0:
                return 50.0

            iv_rank = ((current_iv - self.VIX_52W_LOW) / iv_range) * 100

            # Clamp to 0-100 range
            iv_rank = max(0, min(100, iv_rank))

            logger.debug(f"IV Rank for {underlying}: {iv_rank:.2f}% (Current VIX: {current_iv})")
            return round(iv_rank, 2)

        except Exception as e:
            logger.error(f"Error calculating IV Rank: {e}")
            return 50.0  # Return neutral value on error

    async def get_iv_percentile(self, underlying: str = "NIFTY") -> float:
        """
        Calculate IV Percentile (0-100).

        IV Percentile = % of days in past 252 trading days where IV was lower

        Higher percentile means current volatility is high compared to recent history.

        Note: For initial implementation, we approximate using IV Rank.
        Future: Calculate from actual historical IV data in database.

        Returns:
            IV Percentile as percentage (0-100)
        """
        try:
            # For now, use IV Rank as proxy
            # Future: Query historical VIX data from database
            iv_rank = await self.get_iv_rank(underlying)

            # Approximate percentile (would be more accurate with actual historical data)
            iv_percentile = iv_rank

            logger.debug(f"IV Percentile for {underlying}: {iv_percentile:.2f}%")
            return iv_percentile

        except Exception as e:
            logger.error(f"Error calculating IV Percentile: {e}")
            return 50.0

    async def get_iv_metrics(self, underlying: str = "NIFTY") -> Dict[str, any]:
        """
        Get all IV metrics for an underlying.

        Returns:
            Dictionary with iv_rank, iv_percentile, current_iv, interpretation
        """
        try:
            current_vix = await self.market_data.get_vix()
            iv_rank = await self.get_iv_rank(underlying)
            iv_percentile = await self.get_iv_percentile(underlying)

            # Interpretation
            if iv_rank < 25:
                interpretation = "Low volatility - Good for credit strategies"
            elif iv_rank < 50:
                interpretation = "Medium volatility - Neutral conditions"
            elif iv_rank < 75:
                interpretation = "High volatility - Consider debit strategies"
            else:
                interpretation = "Very high volatility - Caution advised"

            return {
                'current_iv': float(current_vix) if current_vix else 0.0,
                'iv_rank': iv_rank,
                'iv_percentile': iv_percentile,
                'interpretation': interpretation,
                '52w_high': self.VIX_52W_HIGH,
                '52w_low': self.VIX_52W_LOW
            }

        except Exception as e:
            logger.error(f"Error getting IV metrics: {e}")
            return {
                'current_iv': 0.0,
                'iv_rank': 50.0,
                'iv_percentile': 50.0,
                'interpretation': 'Error calculating IV metrics'
            }

    def update_historical_range(self, high: float, low: float):
        """
        Update the 52-week high/low range.

        This should be called periodically (daily) to update the historical range.
        Future: Automate this by querying historical data.
        """
        self.VIX_52W_HIGH = high
        self.VIX_52W_LOW = low
        logger.info(f"Updated VIX 52w range: High={high}, Low={low}")


# Service instance cache
_iv_metrics_services: Dict[str, IVMetricsService] = {}


def get_iv_metrics_service(market_data: MarketDataService) -> IVMetricsService:
    """Get or create IVMetricsService instance."""
    token_key = market_data.kite.access_token or "default"

    if token_key not in _iv_metrics_services:
        _iv_metrics_services[token_key] = IVMetricsService(market_data)

    return _iv_metrics_services[token_key]


def clear_iv_metrics_services():
    """Clear all cached service instances."""
    global _iv_metrics_services
    _iv_metrics_services.clear()
