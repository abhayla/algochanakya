"""
Premium Tracking Service

Tracks option premium over time for monitoring and visualization.
Provides data for:
- Straddle premium charts
- Theta decay analysis
- Premium capture percentage calculations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotOrder,
    AutoPilotPositionLeg,
    StrategyStatus,
    OrderStatus,
    OrderPurpose
)
from app.services.legacy.market_data import MarketDataService
from app.services.options.greeks_calculator import GreeksCalculator
import logging

logger = logging.getLogger(__name__)


class PremiumSnapshot:
    """Single point-in-time premium snapshot"""

    def __init__(
        self,
        timestamp: datetime,
        total_premium: Decimal,
        ce_premium: Decimal,
        pe_premium: Decimal,
        legs_data: List[Dict[str, Any]]
    ):
        self.timestamp = timestamp
        self.total_premium = total_premium
        self.ce_premium = ce_premium
        self.pe_premium = pe_premium
        self.legs_data = legs_data


class StraddlePremium:
    """Current straddle premium with breakdown"""

    def __init__(
        self,
        ce_premium: Decimal,
        pe_premium: Decimal,
        total_premium: Decimal,
        ce_strike: Optional[int] = None,
        pe_strike: Optional[int] = None,
        underlying: Optional[str] = None
    ):
        self.ce_premium = ce_premium
        self.pe_premium = pe_premium
        self.total_premium = total_premium
        self.ce_strike = ce_strike
        self.pe_strike = pe_strike
        self.underlying = underlying


class DecayCurve:
    """Theta decay curve data"""

    def __init__(
        self,
        entry_premium: Decimal,
        current_premium: Decimal,
        expected_premium: Decimal,
        days_to_expiry: int,
        decay_rate: float,
        expected_decay_rate: float
    ):
        self.entry_premium = entry_premium
        self.current_premium = current_premium
        self.expected_premium = expected_premium
        self.days_to_expiry = days_to_expiry
        self.decay_rate = decay_rate
        self.expected_decay_rate = expected_decay_rate
        self.premium_captured_pct = self._calculate_captured_pct()

    def _calculate_captured_pct(self) -> float:
        """Calculate percentage of premium captured"""
        if self.entry_premium == 0:
            return 0.0
        captured = self.entry_premium - self.current_premium
        return float((captured / self.entry_premium) * 100)


class PremiumTracker:
    """
    Service for tracking option premiums over time

    Features:
    - Real-time straddle premium calculation
    - Historical premium tracking for charts
    - Theta decay analysis (expected vs actual)
    - Premium capture percentage tracking
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.market_data = MarketDataService()
        self.greeks_calculator = GreeksCalculator()

    async def get_straddle_premium(
        self,
        underlying: str,
        expiry: str,
        strike: int
    ) -> StraddlePremium:
        """
        Get current combined CE+PE premium for a strike

        Args:
            underlying: NIFTY, BANKNIFTY, FINNIFTY, SENSEX
            expiry: Expiry date (YYYY-MM-DD)
            strike: Strike price

        Returns:
            StraddlePremium with CE, PE, and total premium
        """
        try:
            # Fetch CE and PE LTP from market data
            ce_ltp = await self.market_data.get_ltp(underlying, expiry, strike, 'CE')
            pe_ltp = await self.market_data.get_ltp(underlying, expiry, strike, 'PE')

            ce_premium = Decimal(str(ce_ltp)) if ce_ltp else Decimal('0')
            pe_premium = Decimal(str(pe_ltp)) if pe_ltp else Decimal('0')
            total_premium = ce_premium + pe_premium

            return StraddlePremium(
                ce_premium=ce_premium,
                pe_premium=pe_premium,
                total_premium=total_premium,
                ce_strike=strike,
                pe_strike=strike,
                underlying=underlying
            )

        except Exception as e:
            logger.error(f"Error getting straddle premium: {e}")
            # Return zero premium on error
            return StraddlePremium(
                ce_premium=Decimal('0'),
                pe_premium=Decimal('0'),
                total_premium=Decimal('0'),
                ce_strike=strike,
                pe_strike=strike,
                underlying=underlying
            )

    async def get_strategy_current_premium(
        self,
        strategy_id: int
    ) -> Optional[PremiumSnapshot]:
        """
        Get current total premium for all positions in a strategy

        Args:
            strategy_id: AutoPilot strategy ID

        Returns:
            PremiumSnapshot with current premiums for all legs
        """
        try:
            # Load strategy with position legs
            stmt = (
                select(AutoPilotStrategy)
                .options(selectinload(AutoPilotStrategy.position_legs))
                .where(AutoPilotStrategy.id == strategy_id)
            )
            result = await self.db.execute(stmt)
            strategy = result.scalar_one_or_none()

            if not strategy:
                logger.warning(f"Strategy {strategy_id} not found")
                return None

            # If no active positions, return None
            if not strategy.position_legs:
                return None

            total_premium = Decimal('0')
            ce_premium = Decimal('0')
            pe_premium = Decimal('0')
            legs_data = []

            for leg in strategy.position_legs:
                if not leg.is_open:
                    continue

                # Get current LTP
                ltp = await self.market_data.get_ltp_by_token(leg.instrument_token)

                if ltp:
                    leg_premium = Decimal(str(ltp)) * abs(leg.quantity)
                    total_premium += leg_premium

                    # Categorize by type
                    if leg.contract_type == 'CE':
                        ce_premium += leg_premium
                    elif leg.contract_type == 'PE':
                        pe_premium += leg_premium

                    legs_data.append({
                        'leg_index': leg.leg_index,
                        'contract_type': leg.contract_type,
                        'strike': float(leg.strike),
                        'quantity': leg.quantity,
                        'ltp': float(ltp),
                        'premium': float(leg_premium)
                    })

            return PremiumSnapshot(
                timestamp=datetime.now(),
                total_premium=total_premium,
                ce_premium=ce_premium,
                pe_premium=pe_premium,
                legs_data=legs_data
            )

        except Exception as e:
            logger.error(f"Error getting strategy current premium: {e}")
            return None

    async def get_premium_history(
        self,
        strategy_id: int,
        interval: str = "1m",
        lookback_hours: int = 6
    ) -> List[PremiumSnapshot]:
        """
        Get historical premium snapshots for charting

        NOTE: This is a simplified implementation that returns current premium only.
        For production, you would need to:
        1. Create a new table autopilot_premium_snapshots to store historical data
        2. Have a background task that captures premium every N seconds
        3. Query that table for historical data

        Args:
            strategy_id: AutoPilot strategy ID
            interval: Time interval (1m, 5m, 15m, 1h)
            lookback_hours: How many hours of history to fetch

        Returns:
            List of PremiumSnapshot ordered by timestamp
        """
        # TODO: Implement actual historical tracking
        # For now, return just current snapshot
        current = await self.get_strategy_current_premium(strategy_id)
        if current:
            return [current]
        return []

    async def get_premium_decay_curve(
        self,
        strategy_id: int
    ) -> Optional[DecayCurve]:
        """
        Calculate expected vs actual theta decay

        Args:
            strategy_id: AutoPilot strategy ID

        Returns:
            DecayCurve with decay analysis
        """
        try:
            # Load strategy with orders
            stmt = (
                select(AutoPilotStrategy)
                .options(
                    selectinload(AutoPilotStrategy.orders),
                    selectinload(AutoPilotStrategy.position_legs)
                )
                .where(AutoPilotStrategy.id == strategy_id)
            )
            result = await self.db.execute(stmt)
            strategy = result.scalar_one_or_none()

            if not strategy:
                return None

            # Get entry orders (first executed orders)
            entry_orders = [
                order for order in strategy.orders
                if order.purpose == OrderPurpose.ENTRY
                and order.status == OrderStatus.COMPLETE
            ]

            if not entry_orders:
                logger.info(f"No entry orders found for strategy {strategy_id}")
                return None

            # Calculate entry premium (sum of all entry order prices)
            entry_premium = sum(
                (order.average_price or Decimal('0')) * abs(order.quantity)
                for order in entry_orders
            )

            # Get current premium
            current_snapshot = await self.get_strategy_current_premium(strategy_id)
            if not current_snapshot:
                return None

            current_premium = current_snapshot.total_premium

            # Calculate days to expiry
            if not strategy.expiry_date:
                return None

            days_to_expiry = (strategy.expiry_date - datetime.now().date()).days
            if days_to_expiry < 0:
                days_to_expiry = 0

            # Calculate time elapsed since entry
            entry_time = min(order.created_at for order in entry_orders)
            time_elapsed = datetime.now() - entry_time.replace(tzinfo=None)
            days_elapsed = time_elapsed.total_seconds() / 86400

            # Calculate expected premium based on linear theta decay
            # (This is simplified; real theta decay is not linear)
            if days_elapsed + days_to_expiry == 0:
                expected_decay_rate = 0
            else:
                expected_decay_rate = float(entry_premium) / (days_elapsed + days_to_expiry)

            expected_premium = Decimal(str(
                float(entry_premium) - (expected_decay_rate * days_elapsed)
            ))

            # Calculate actual decay rate
            if days_elapsed == 0:
                actual_decay_rate = 0
            else:
                actual_decay_rate = float(entry_premium - current_premium) / days_elapsed

            # Decay rate comparison (1.0 = as expected, >1.0 = faster than expected)
            if expected_decay_rate == 0:
                decay_rate_multiplier = 1.0
            else:
                decay_rate_multiplier = actual_decay_rate / expected_decay_rate

            return DecayCurve(
                entry_premium=entry_premium,
                current_premium=current_premium,
                expected_premium=expected_premium,
                days_to_expiry=days_to_expiry,
                decay_rate=decay_rate_multiplier,
                expected_decay_rate=expected_decay_rate
            )

        except Exception as e:
            logger.error(f"Error calculating decay curve: {e}")
            return None

    async def calculate_premium_capture_pct(
        self,
        strategy_id: int
    ) -> float:
        """
        Calculate percentage of premium captured

        Args:
            strategy_id: AutoPilot strategy ID

        Returns:
            Percentage (0-100) of premium captured
        """
        decay_curve = await self.get_premium_decay_curve(strategy_id)
        if decay_curve:
            return decay_curve.premium_captured_pct
        return 0.0
