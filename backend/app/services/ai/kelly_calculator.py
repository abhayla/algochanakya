"""
Kelly Criterion Position Sizing Calculator

Implements Kelly Criterion formula for optimal position sizing based on
historical trading performance. Uses conservative half-Kelly approach for safety.
"""

import logging
from typing import Optional, Dict, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.autopilot import AutoPilotPositionLeg, AutoPilotStrategy
from app.constants.trading import get_lot_size

logger = logging.getLogger(__name__)


class KellyCalculator:
    """
    Calculate optimal position sizes using Kelly Criterion.

    Kelly Fraction = (Win Rate × Avg Win / Avg Loss) - (1 - Win Rate)
                     ───────────────────────────────────────────────
                                  Avg Win / Avg Loss

    Uses half-Kelly (0.5x) for safety to reduce variance.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.MIN_TRADES_REQUIRED = 100  # Minimum trades before Kelly is reliable
        self.KELLY_SAFETY_FACTOR = 0.5  # Half-Kelly for safety
        self.MAX_KELLY_FRACTION = 0.25  # Cap at 25% of capital per trade

    async def get_historical_performance(
        self,
        user_id,
        strategy_name: Optional[str] = None,
        underlying: Optional[str] = None,
        days: int = 90
    ) -> Dict:
        """
        Extract historical performance metrics for Kelly calculation.

        Returns:
            {
                "total_trades": int,
                "winning_trades": int,
                "losing_trades": int,
                "win_rate": float (0.0 to 1.0),
                "avg_win": Decimal,
                "avg_loss": Decimal,
                "avg_win_loss_ratio": float
            }
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query AutoPilotPositionLeg (which has realized_pnl) joined to AutoPilotStrategy
        # for user scoping and optional strategy/underlying filtering.
        query = (
            select(AutoPilotPositionLeg)
            .join(AutoPilotStrategy, AutoPilotPositionLeg.strategy_id == AutoPilotStrategy.id)
            .where(
                and_(
                    AutoPilotStrategy.user_id == user_id,
                    AutoPilotPositionLeg.created_at >= cutoff_date,
                    AutoPilotPositionLeg.status.in_(["exited", "closed"]),
                    AutoPilotPositionLeg.realized_pnl.isnot(None),
                )
            )
        )

        # Filter by strategy name if provided
        if strategy_name:
            query = query.where(AutoPilotStrategy.name == strategy_name)

        # Filter by underlying if provided (underlying is on AutoPilotStrategy)
        if underlying:
            query = query.where(AutoPilotStrategy.underlying == underlying)

        result = await self.db.execute(query)
        legs = result.scalars().all()

        if not legs:
            logger.warning(f"No closed position legs found for user {user_id}")
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": Decimal("0"),
                "avg_loss": Decimal("0"),
                "avg_win_loss_ratio": 0.0
            }

        # Calculate wins and losses
        wins = []
        losses = []

        for leg in legs:
            pnl = leg.realized_pnl

            if pnl > 0:
                wins.append(pnl)
            elif pnl < 0:
                losses.append(abs(pnl))

        total_trades = len(legs)
        winning_trades = len(wins)
        losing_trades = len(losses)

        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        avg_win = Decimal(sum(wins) / len(wins)) if wins else Decimal("0")
        avg_loss = Decimal(sum(losses) / len(losses)) if losses else Decimal("1")  # Avoid div by zero

        avg_win_loss_ratio = float(avg_win / avg_loss) if avg_loss > 0 else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "avg_win_loss_ratio": avg_win_loss_ratio
        }

    def calculate_kelly_fraction(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> Tuple[float, bool]:
        """
        Calculate Kelly Criterion fraction.

        Formula:
            f* = (p × b - q) / b

        Where:
            p = win rate (probability of winning)
            q = 1 - p (probability of losing)
            b = avg_win / avg_loss (win/loss ratio)
            f* = fraction of capital to risk

        Returns:
            (kelly_fraction, is_reliable)

        is_reliable is False if:
        - Win rate < 0.5 (negative edge)
        - Avg loss is 0 (invalid data)
        - Kelly fraction is negative (negative edge)
        """
        if avg_loss == 0:
            logger.warning("Avg loss is zero, cannot calculate Kelly fraction")
            return 0.0, False

        if win_rate < 0.5:
            logger.info(f"Win rate {win_rate:.2%} below 50%, Kelly suggests no position")
            return 0.0, False

        b = avg_win / avg_loss  # Win/loss ratio
        p = win_rate
        q = 1 - win_rate

        # Kelly formula
        kelly_fraction = (p * b - q) / b

        if kelly_fraction <= 0:
            logger.info(f"Negative Kelly fraction {kelly_fraction:.4f}, no edge detected")
            return 0.0, False

        # Apply safety factor (half-Kelly)
        kelly_fraction *= self.KELLY_SAFETY_FACTOR

        # Cap at maximum allowed
        kelly_fraction = min(kelly_fraction, self.MAX_KELLY_FRACTION)

        logger.info(
            f"Kelly calculation: win_rate={win_rate:.2%}, "
            f"win/loss_ratio={b:.2f}, kelly_fraction={kelly_fraction:.4f} (half-Kelly)"
        )

        return kelly_fraction, True

    def calculate_optimal_lots(
        self,
        kelly_fraction: float,
        capital: float,
        max_loss_per_lot: float,
        underlying: str = "NIFTY"
    ) -> int:
        """
        Calculate optimal number of lots based on Kelly fraction.

        Formula:
            Optimal Lots = (Kelly Fraction × Capital) / Max Loss per Lot

        Args:
            kelly_fraction: Kelly fraction (0.0 to 1.0)
            capital: Total available capital
            max_loss_per_lot: Maximum expected loss per lot
            underlying: NIFTY, BANKNIFTY, FINNIFTY (for lot size)

        Returns:
            Number of lots (minimum 1 if kelly_fraction > 0)
        """
        if kelly_fraction <= 0 or capital <= 0 or max_loss_per_lot <= 0:
            return 0

        # Calculate raw lots
        risk_amount = kelly_fraction * capital
        raw_lots = risk_amount / max_loss_per_lot

        # Round down to nearest integer
        optimal_lots = int(raw_lots)

        # Ensure at least 1 lot if Kelly suggests any position
        if optimal_lots == 0 and kelly_fraction > 0:
            optimal_lots = 1

        # Get lot size for underlying
        lot_size = get_lot_size(underlying)

        logger.info(
            f"Optimal lots calculation: kelly={kelly_fraction:.4f}, "
            f"capital={capital:.2f}, max_loss_per_lot={max_loss_per_lot:.2f}, "
            f"optimal_lots={optimal_lots}, lot_size={lot_size}"
        )

        return optimal_lots

    async def get_kelly_recommendation(
        self,
        user_id,
        capital: float,
        max_loss_per_lot: float,
        underlying: str = "NIFTY",
        strategy_name: Optional[str] = None,
        lookback_days: int = 90
    ) -> Dict:
        """
        Get complete Kelly recommendation with all metrics.

        Returns:
            {
                "enabled": bool,
                "kelly_fraction": float,
                "optimal_lots": int,
                "historical_performance": Dict,
                "recommendation": str,
                "warnings": List[str]
            }
        """
        # Get historical performance
        perf = await self.get_historical_performance(
            user_id=user_id,
            strategy_name=strategy_name,
            underlying=underlying,
            days=lookback_days
        )

        warnings = []

        # Check if we have enough data
        if perf["total_trades"] < self.MIN_TRADES_REQUIRED:
            warnings.append(
                f"Only {perf['total_trades']} trades found. "
                f"Kelly sizing requires at least {self.MIN_TRADES_REQUIRED} trades for reliability."
            )

            return {
                "enabled": False,
                "kelly_fraction": 0.0,
                "optimal_lots": 0,
                "historical_performance": perf,
                "recommendation": "NOT_ENOUGH_DATA",
                "warnings": warnings
            }

        # Calculate Kelly fraction
        kelly_fraction, is_reliable = self.calculate_kelly_fraction(
            win_rate=perf["win_rate"],
            avg_win=float(perf["avg_win"]),
            avg_loss=float(perf["avg_loss"])
        )

        if not is_reliable:
            warnings.append(
                "Kelly fraction is not reliable due to negative edge or insufficient win rate."
            )

            return {
                "enabled": False,
                "kelly_fraction": kelly_fraction,
                "optimal_lots": 0,
                "historical_performance": perf,
                "recommendation": "NEGATIVE_EDGE",
                "warnings": warnings
            }

        # Calculate optimal lots
        optimal_lots = self.calculate_optimal_lots(
            kelly_fraction=kelly_fraction,
            capital=capital,
            max_loss_per_lot=max_loss_per_lot,
            underlying=underlying
        )

        # Generate recommendation text
        if kelly_fraction < 0.05:
            recommendation = "VERY_CONSERVATIVE"
            warnings.append("Kelly suggests very small position size due to low edge.")
        elif kelly_fraction < 0.10:
            recommendation = "CONSERVATIVE"
        elif kelly_fraction < 0.15:
            recommendation = "MODERATE"
        elif kelly_fraction < 0.20:
            recommendation = "AGGRESSIVE"
        else:
            recommendation = "VERY_AGGRESSIVE"
            warnings.append("Kelly suggests large position size. Consider scaling back for safety.")

        return {
            "enabled": True,
            "kelly_fraction": kelly_fraction,
            "optimal_lots": optimal_lots,
            "historical_performance": perf,
            "recommendation": recommendation,
            "warnings": warnings
        }


__all__ = ["KellyCalculator"]
