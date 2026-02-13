"""
Delta Neutral Rebalance Service - Phase 5F Feature #38

Professional delta band management with automatic rebalancing.

What is Delta Neutral Rebalancing?
-----------------------------------
Maintain a delta-neutral position by automatically adjusting when net delta
drifts outside acceptable bands. This prevents excessive directional risk
and keeps the strategy market-neutral.

Example:
--------
1. Iron Condor starts at net delta = 0.05 (nearly neutral)
2. Market moves, net delta drifts to +0.35 (too bullish)
3. Auto-rebalance triggered (delta band = ±0.30)
4. Options:
   a) Add contracts to opposite side (sell more PUTs if delta too positive)
   b) Shift threatened leg farther OTM
   c) Close profitable leg
5. Result: Delta back to ±0.10 range

Key Benefits:
-------------
- Maintains market-neutral positioning
- Prevents excessive directional exposure
- Professional risk management
- Automated position monitoring

Delta Bands:
------------
- Conservative: ±0.15 (tight control)
- Moderate: ±0.30 (standard)
- Aggressive: ±0.50 (loose)

Implementation:
---------------
This service monitors net delta and triggers rebalancing actions when
thresholds are breached.
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.models.autopilot import AutoPilotStrategy, AutoPilotPositionLeg
from app.services.legacy.market_data import MarketDataService
from app.services.options.greeks_calculator import GreeksCalculatorService
from app.services.strike_finder_service import StrikeFinderService

logger = logging.getLogger(__name__)


class DeltaRebalanceService:
    """
    Service for delta-neutral position rebalancing.

    Monitors position delta and suggests/executes rebalancing actions
    when delta drifts outside acceptable bands.
    """

    # Delta band presets (professional standards)
    DELTA_BANDS = {
        "conservative": {"warning": 0.15, "critical": 0.20, "description": "Tight delta control"},
        "moderate": {"warning": 0.25, "critical": 0.30, "description": "Standard delta management"},
        "aggressive": {"warning": 0.40, "critical": 0.50, "description": "Loose delta tolerance"}
    }

    def __init__(self, kite: KiteConnect, db: AsyncSession):
        self.kite = kite
        self.db = db
        self.market_data = MarketDataService(kite)
        self.greeks_calc = GreeksCalculatorService()
        self.strike_finder = StrikeFinderService(kite, db)

    async def assess_delta_risk(
        self,
        strategy: AutoPilotStrategy,
        delta_band_type: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Assess current delta risk and rebalancing needs.

        Args:
            strategy: AutoPilot strategy to assess
            delta_band_type: Delta band preset (conservative/moderate/aggressive)

        Returns:
            Dict with delta assessment:
            {
                "current_delta": float,
                "delta_status": str,  # "safe", "warning", "critical"
                "band_type": str,
                "warning_threshold": float,
                "critical_threshold": float,
                "rebalance_needed": bool,
                "suggested_actions": List[Dict],
                "directional_bias": str  # "bullish", "bearish", "neutral"
            }
        """
        # Get delta band thresholds
        if delta_band_type not in self.DELTA_BANDS:
            delta_band_type = "moderate"

        band = self.DELTA_BANDS[delta_band_type]
        warning_threshold = band["warning"]
        critical_threshold = band["critical"]

        # Get current net delta
        net_delta = float(strategy.net_delta) if strategy.net_delta else 0.0

        # Determine delta status
        abs_delta = abs(net_delta)

        if abs_delta <= warning_threshold:
            delta_status = "safe"
            rebalance_needed = False
        elif abs_delta <= critical_threshold:
            delta_status = "warning"
            rebalance_needed = True
        else:
            delta_status = "critical"
            rebalance_needed = True

        # Determine directional bias
        if net_delta > warning_threshold:
            directional_bias = "bullish"  # Positive delta = benefits from up move
        elif net_delta < -warning_threshold:
            directional_bias = "bearish"  # Negative delta = benefits from down move
        else:
            directional_bias = "neutral"

        # Generate suggested actions if rebalance needed
        suggested_actions = []
        if rebalance_needed:
            suggested_actions = await self._generate_rebalance_actions(
                strategy=strategy,
                current_delta=net_delta,
                target_delta=0.0,
                delta_status=delta_status
            )

        return {
            "current_delta": net_delta,
            "delta_status": delta_status,
            "band_type": delta_band_type,
            "warning_threshold": warning_threshold,
            "critical_threshold": critical_threshold,
            "rebalance_needed": rebalance_needed,
            "suggested_actions": suggested_actions,
            "directional_bias": directional_bias,
            "delta_distance": abs_delta - warning_threshold  # How far outside band
        }

    async def _generate_rebalance_actions(
        self,
        strategy: AutoPilotStrategy,
        current_delta: float,
        target_delta: float,
        delta_status: str
    ) -> List[Dict[str, Any]]:
        """
        Generate suggested rebalancing actions.

        Actions prioritized by:
        1. Least cost
        2. Least complexity
        3. Best delta correction

        Returns list of actions sorted by priority.
        """
        actions = []

        # Calculate delta imbalance
        delta_imbalance = current_delta - target_delta

        # Action 1: Add to opposite side
        # If delta too positive (+), sell more PUTs
        # If delta too negative (-), sell more CEslls
        if abs(delta_imbalance) > 0.15:
            opposite_side_action = await self._suggest_add_opposite_side(
                strategy=strategy,
                delta_imbalance=delta_imbalance
            )
            if opposite_side_action:
                actions.append(opposite_side_action)

        # Action 2: Shift threatened leg
        # Move the leg causing delta drift farther OTM
        shift_action = await self._suggest_shift_threatened_leg(
            strategy=strategy,
            delta_imbalance=delta_imbalance
        )
        if shift_action:
            actions.append(shift_action)

        # Action 3: Close profitable leg
        # If one side is very profitable, consider closing it
        close_action = await self._suggest_close_profitable_leg(
            strategy=strategy,
            delta_imbalance=delta_imbalance
        )
        if close_action:
            actions.append(close_action)

        # Sort by priority (cost, effectiveness)
        actions.sort(key=lambda x: (x.get('cost', 999), -x.get('effectiveness', 0)))

        return actions

    async def _suggest_add_opposite_side(
        self,
        strategy: AutoPilotStrategy,
        delta_imbalance: float
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest adding contracts to opposite side.

        If delta too positive → sell more PUTs
        If delta too negative → sell more CEs
        """
        if delta_imbalance > 0.15:
            # Too bullish, add PUT side
            option_type = "PE"
            action_text = "Add more PUT contracts to reduce bullish delta"
        elif delta_imbalance < -0.15:
            # Too bearish, add CALL side
            option_type = "CE"
            action_text = "Add more CALL contracts to reduce bearish delta"
        else:
            return None

        # Find appropriate strike
        # Target delta for new leg: approximately half the imbalance
        target_leg_delta = abs(delta_imbalance) / 2

        # Find strike matching target delta
        spot_price = await self.market_data.get_spot_price(strategy.underlying)
        if not spot_price:
            return None

        # Get expiry from existing legs
        expiry = await self._get_strategy_expiry(strategy)
        if not expiry:
            return None

        try:
            strike_result = await self.strike_finder.find_strike_by_delta(
                underlying=strategy.underlying,
                expiry=expiry,
                option_type=option_type,
                target_delta=Decimal(str(target_leg_delta)),
                prefer_round_strike=True
            )

            if not strike_result:
                return None

            return {
                "action_type": "add_opposite_side",
                "option_type": option_type,
                "strike": strike_result['strike'],
                "premium": strike_result.get('ltp', 0),
                "delta": strike_result.get('delta', 0),
                "description": action_text,
                "cost": strike_result.get('ltp', 0),  # Premium received (negative cost)
                "effectiveness": 0.8,  # High effectiveness
                "priority": 1
            }
        except Exception as e:
            logger.error(f"Error suggesting add opposite side: {e}")
            return None

    async def _suggest_shift_threatened_leg(
        self,
        strategy: AutoPilotStrategy,
        delta_imbalance: float
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest shifting the threatened leg farther OTM.

        If delta too positive → shift CE farther up
        If delta too negative → shift PE farther down
        """
        # Find the threatened leg
        legs = await self._get_strategy_legs(strategy)
        if not legs:
            return None

        if delta_imbalance > 0.15:
            # Too bullish, shift CE farther up
            threatened_legs = [leg for leg in legs if leg.contract_type == "CE"]
            direction = "farther_up"
            action_text = "Shift CALL leg farther OTM (higher strike)"
        elif delta_imbalance < -0.15:
            # Too bearish, shift PE farther down
            threatened_legs = [leg for leg in legs if leg.contract_type == "PE"]
            direction = "farther_down"
            action_text = "Shift PUT leg farther OTM (lower strike)"
        else:
            return None

        if not threatened_legs:
            return None

        # Find leg with highest delta (most threatened)
        threatened_leg = max(threatened_legs, key=lambda leg: abs(float(leg.delta or 0)))

        return {
            "action_type": "shift_leg",
            "leg_id": threatened_leg.leg_id,
            "current_strike": float(threatened_leg.strike) if threatened_leg.strike else 0,
            "direction": direction,
            "description": action_text,
            "cost": 50,  # Estimated cost (debit to roll)
            "effectiveness": 0.7,  # Moderate effectiveness
            "priority": 2
        }

    async def _suggest_close_profitable_leg(
        self,
        strategy: AutoPilotStrategy,
        delta_imbalance: float
    ) -> Optional[Dict[str, Any]]:
        """
        Suggest closing a profitable leg to rebalance delta.

        Only suggest if one side is significantly profitable.
        """
        legs = await self._get_strategy_legs(strategy)
        if not legs:
            return None

        # Find profitable legs
        profitable_legs = [
            leg for leg in legs
            if leg.unrealized_pnl and float(leg.unrealized_pnl) > 0
        ]

        if not profitable_legs:
            return None

        # Find most profitable leg
        most_profitable = max(
            profitable_legs,
            key=lambda leg: float(leg.unrealized_pnl or 0)
        )

        profit = float(most_profitable.unrealized_pnl or 0)

        # Only suggest if profit is significant (> ₹1000)
        if profit < 1000:
            return None

        return {
            "action_type": "close_leg",
            "leg_id": most_profitable.leg_id,
            "strike": float(most_profitable.strike) if most_profitable.strike else 0,
            "option_type": most_profitable.contract_type,
            "description": f"Close profitable {most_profitable.contract_type} leg (₹{profit:.0f} profit)",
            "cost": -profit,  # Realizes profit (negative cost)
            "effectiveness": 0.6,  # Lower effectiveness for delta correction
            "priority": 3
        }

    async def _get_strategy_legs(self, strategy: AutoPilotStrategy) -> List[AutoPilotPositionLeg]:
        """Get all open position legs for strategy."""
        from sqlalchemy import select
        stmt = select(AutoPilotPositionLeg).where(
            AutoPilotPositionLeg.strategy_id == strategy.id,
            AutoPilotPositionLeg.status == "open"
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _get_strategy_expiry(self, strategy: AutoPilotStrategy) -> Optional[date]:
        """Get expiry date from strategy legs."""
        legs = await self._get_strategy_legs(strategy)
        if not legs:
            return None
        return legs[0].expiry if legs[0].expiry else None


# Singleton instance
def get_delta_rebalance_service(kite: KiteConnect, db: AsyncSession) -> DeltaRebalanceService:
    """Get delta rebalance service instance."""
    return DeltaRebalanceService(kite, db)
