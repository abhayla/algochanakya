"""
Drawdown Tracker Service

Tracks portfolio drawdown and P&L volatility for drawdown-aware position sizing.
Implements Priority 1.2: Drawdown-Aware Position Sizing.

Features:
- High-water mark tracking
- Current drawdown calculation
- P&L volatility calculation (rolling standard deviation)
- Automatic portfolio value updates
"""

import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
import statistics

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.models.ai import AIUserConfig
from app.models.autopilot import AutoPilotOrder

logger = logging.getLogger(__name__)


class DrawdownLevel:
    """Drawdown severity levels"""
    NORMAL = "NORMAL"           # 0-5% drawdown
    CAUTION = "CAUTION"         # 5-10% drawdown
    WARNING = "WARNING"         # 10-15% drawdown
    CRITICAL = "CRITICAL"       # 15-20% drawdown
    SEVERE = "SEVERE"           # >20% drawdown


class VolatilityLevel:
    """Volatility severity levels"""
    LOW = "LOW"                 # Low volatility
    MEDIUM = "MEDIUM"           # Medium volatility
    HIGH = "HIGH"               # High volatility


class DrawdownTracker:
    """
    Tracks portfolio drawdown and volatility for position size dampening.

    High-water mark: Peak portfolio value achieved
    Drawdown: Percentage decline from high-water mark
    Volatility: Rolling standard deviation of daily P&L
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_portfolio_value(
        self,
        user_id,
        current_value: Decimal
    ) -> Dict:
        """
        Update portfolio value and recalculate drawdown.

        Args:
            user_id: User ID
            current_value: Current total portfolio value

        Returns:
            {
                "high_water_mark": Decimal,
                "current_drawdown_pct": Decimal,
                "drawdown_level": str,
                "updated": bool
            }
        """
        # Get user config
        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config:
            logger.warning(f"No AI config found for user {user_id}")
            return {
                "high_water_mark": Decimal("0"),
                "current_drawdown_pct": Decimal("0"),
                "drawdown_level": DrawdownLevel.NORMAL,
                "updated": False
            }

        # Initialize high-water mark if not set
        if config.high_water_mark is None:
            config.high_water_mark = current_value
            logger.info(f"Initialized high-water mark for user {user_id}: {current_value}")

        # Update high-water mark if new peak
        if current_value > config.high_water_mark:
            config.high_water_mark = current_value
            config.current_drawdown_pct = Decimal("0")
            logger.info(f"New high-water mark for user {user_id}: {current_value}")
        else:
            # Calculate drawdown
            drawdown_amount = config.high_water_mark - current_value
            drawdown_pct = (drawdown_amount / config.high_water_mark) * 100
            config.current_drawdown_pct = drawdown_pct
            logger.info(
                f"Drawdown for user {user_id}: {drawdown_pct:.2f}% "
                f"(HWM: {config.high_water_mark}, Current: {current_value})"
            )

        await self.db.commit()
        await self.db.refresh(config)

        # Determine drawdown level
        drawdown_level = self._get_drawdown_level(
            config.current_drawdown_pct,
            config.drawdown_thresholds
        )

        return {
            "high_water_mark": config.high_water_mark,
            "current_drawdown_pct": config.current_drawdown_pct,
            "drawdown_level": drawdown_level,
            "updated": True
        }

    async def calculate_drawdown(self, user_id) -> Dict:
        """
        Get current drawdown metrics without updating.

        Returns:
            {
                "high_water_mark": Decimal,
                "current_portfolio_value": Decimal,
                "current_drawdown_pct": Decimal,
                "drawdown_level": str,
                "drawdown_multiplier": float
            }
        """
        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config or not config.enable_drawdown_sizing:
            return {
                "high_water_mark": Decimal("0"),
                "current_portfolio_value": Decimal("0"),
                "current_drawdown_pct": Decimal("0"),
                "drawdown_level": DrawdownLevel.NORMAL,
                "drawdown_multiplier": 1.0
            }

        # Get current portfolio value from recent trades
        current_value = await self._get_current_portfolio_value(user_id)

        # Get drawdown level and multiplier
        drawdown_level = self._get_drawdown_level(
            config.current_drawdown_pct,
            config.drawdown_thresholds
        )

        multiplier = self._get_drawdown_multiplier(
            config.current_drawdown_pct,
            config.drawdown_thresholds
        )

        return {
            "high_water_mark": config.high_water_mark or Decimal("0"),
            "current_portfolio_value": current_value,
            "current_drawdown_pct": config.current_drawdown_pct,
            "drawdown_level": drawdown_level,
            "drawdown_multiplier": multiplier
        }

    async def calculate_volatility(
        self,
        user_id,
        lookback_days: Optional[int] = None
    ) -> Dict:
        """
        Calculate P&L volatility (rolling standard deviation).

        Args:
            user_id: User ID
            lookback_days: Number of days to look back (from config if None)

        Returns:
            {
                "daily_pnl_volatility": float,
                "volatility_level": str,
                "volatility_multiplier": float,
                "sample_size": int
            }
        """
        # Get user config
        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config or not config.enable_volatility_sizing:
            return {
                "daily_pnl_volatility": 0.0,
                "volatility_level": VolatilityLevel.LOW,
                "volatility_multiplier": 1.0,
                "sample_size": 0
            }

        days = lookback_days or config.volatility_lookback_days
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get daily P&L for lookback period
        daily_pnl = await self._get_daily_pnl(user_id, cutoff_date)

        if len(daily_pnl) < 5:  # Minimum 5 data points for reliable std dev
            logger.warning(f"Insufficient data for volatility calculation: {len(daily_pnl)} days")
            return {
                "daily_pnl_volatility": 0.0,
                "volatility_level": VolatilityLevel.LOW,
                "volatility_multiplier": 1.0,
                "sample_size": len(daily_pnl)
            }

        # Calculate standard deviation
        volatility = float(statistics.stdev(daily_pnl))

        # Get volatility level and multiplier
        volatility_level = self._get_volatility_level(volatility, config.volatility_thresholds)
        multiplier = self._get_volatility_multiplier(volatility, config.volatility_thresholds)

        logger.info(
            f"Volatility for user {user_id}: {volatility:.2f} "
            f"(Level: {volatility_level}, Multiplier: {multiplier}, Sample: {len(daily_pnl)} days)"
        )

        return {
            "daily_pnl_volatility": volatility,
            "volatility_level": volatility_level,
            "volatility_multiplier": multiplier,
            "sample_size": len(daily_pnl)
        }

    async def should_pause_trading(self, user_id) -> Tuple[bool, str]:
        """
        Determine if trading should be paused due to excessive drawdown.

        Returns:
            (should_pause: bool, reason: str)
        """
        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config or not config.enable_drawdown_sizing:
            return False, ""

        if config.current_drawdown_pct >= config.max_drawdown_to_trade:
            reason = (
                f"Drawdown {config.current_drawdown_pct:.2f}% exceeds "
                f"max allowed {config.max_drawdown_to_trade:.2f}%"
            )
            logger.warning(f"Trading paused for user {user_id}: {reason}")
            return True, reason

        return False, ""

    async def reset_high_water_mark(self, user_id) -> Dict:
        """
        Reset high-water mark to current portfolio value (admin action).

        Returns:
            {
                "new_high_water_mark": Decimal,
                "previous_high_water_mark": Decimal,
                "current_drawdown_pct": Decimal
            }
        """
        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"No AI config found for user {user_id}")

        # Get current portfolio value
        current_value = await self._get_current_portfolio_value(user_id)

        previous_hwm = config.high_water_mark or Decimal("0")
        config.high_water_mark = current_value
        config.current_drawdown_pct = Decimal("0")

        await self.db.commit()

        logger.info(
            f"Reset high-water mark for user {user_id}: "
            f"Previous={previous_hwm}, New={current_value}"
        )

        return {
            "new_high_water_mark": current_value,
            "previous_high_water_mark": previous_hwm,
            "current_drawdown_pct": Decimal("0")
        }

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _get_current_portfolio_value(self, user_id) -> Decimal:
        """Get current portfolio value from cumulative realized P&L"""
        query = select(func.sum(AutoPilotOrder.realized_pnl)).where(
            and_(
                AutoPilotOrder.user_id == user_id,
                AutoPilotOrder.status == "COMPLETE"
            )
        )
        result = await self.db.execute(query)
        total_pnl = result.scalar() or Decimal("0")

        # Assume starting capital (could be made configurable)
        # For now, we use realized P&L as proxy for portfolio value change
        return total_pnl

    async def _get_daily_pnl(self, user_id, cutoff_date: datetime) -> List[float]:
        """Get daily P&L values for volatility calculation"""
        query = select(
            func.date(AutoPilotOrder.updated_at).label('trade_date'),
            func.sum(AutoPilotOrder.realized_pnl).label('daily_pnl')
        ).where(
            and_(
                AutoPilotOrder.user_id == user_id,
                AutoPilotOrder.status == "COMPLETE",
                AutoPilotOrder.updated_at >= cutoff_date
            )
        ).group_by(
            func.date(AutoPilotOrder.updated_at)
        ).order_by(
            func.date(AutoPilotOrder.updated_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [float(row.daily_pnl) for row in rows if row.daily_pnl is not None]

    def _get_drawdown_level(
        self,
        drawdown_pct: Decimal,
        thresholds: List[Dict]
    ) -> str:
        """Determine drawdown level based on thresholds"""
        dd = float(drawdown_pct)

        for threshold in thresholds:
            if threshold["min_dd"] <= dd < threshold["max_dd"]:
                return threshold["level"]

        return DrawdownLevel.SEVERE

    def _get_drawdown_multiplier(
        self,
        drawdown_pct: Decimal,
        thresholds: List[Dict]
    ) -> float:
        """Get position size multiplier based on drawdown"""
        dd = float(drawdown_pct)

        for threshold in thresholds:
            if threshold["min_dd"] <= dd < threshold["max_dd"]:
                return float(threshold["multiplier"])

        # If beyond max threshold, use smallest multiplier
        return float(min(t["multiplier"] for t in thresholds))

    def _get_volatility_level(
        self,
        volatility: float,
        thresholds: List[Dict]
    ) -> str:
        """Determine volatility level based on thresholds"""
        for threshold in thresholds:
            if volatility < threshold["max_volatility"]:
                return threshold["level"]

        return VolatilityLevel.HIGH

    def _get_volatility_multiplier(
        self,
        volatility: float,
        thresholds: List[Dict]
    ) -> float:
        """Get position size multiplier based on volatility"""
        for threshold in thresholds:
            if volatility < threshold["max_volatility"]:
                return float(threshold["multiplier"])

        # If beyond max threshold, use smallest multiplier
        return float(min(t["multiplier"] for t in thresholds))


__all__ = ["DrawdownTracker", "DrawdownLevel", "VolatilityLevel"]
