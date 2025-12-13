"""
Suggestion Engine - Phase 5C

Analyzes position state and generates intelligent adjustment suggestions.
Considers delta, P&L, DTE, market conditions, and position Greeks.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from kiteconnect import KiteConnect

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotPositionLeg,
    AutoPilotAdjustmentSuggestion,
    AutoPilotUserSettings,
    PositionLegStatus,
    SuggestionType,
    SuggestionPriority
)
from app.services.market_data import MarketDataService
from app.services.position_leg_service import PositionLegService

logger = logging.getLogger(__name__)


class DTEZone(str, Enum):
    """DTE (Days to Expiry) zones with different adjustment thresholds."""
    EARLY = "early"      # > 14 days
    MIDDLE = "middle"    # 7-14 days
    LATE = "late"        # 3-7 days
    EXPIRY = "expiry"    # < 3 days


class SuggestionEngine:
    """
    Generates intelligent adjustment suggestions based on position analysis.

    Analyzes:
    - Net delta and individual leg deltas
    - P&L vs risk limits
    - Days to expiry (DTE)
    - Market conditions (spot movement, VIX)
    - Position Greeks (gamma, theta, vega)

    Suggests:
    - Shift legs to adjust delta
    - Break trade on losing legs
    - Roll to new expiry
    - Exit positions
    - Add hedges
    """

    def __init__(
        self,
        kite: KiteConnect,
        db: AsyncSession,
        market_data: MarketDataService
    ):
        self.kite = kite
        self.db = db
        self.market_data = market_data
        self.position_leg_service = PositionLegService(kite, db)

    async def generate_suggestions(
        self,
        strategy_id: int,
        user_id: int
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """
        Generate all suggestions for a strategy.

        Returns list of suggestions ordered by priority.
        """
        try:
            # Get strategy
            strategy = await self.db.get(AutoPilotStrategy, strategy_id)
            if not strategy or strategy.status != "active":
                return []

            # Get user settings
            user_settings = await self._get_user_settings(user_id)
            if not user_settings or not user_settings.suggestions_enabled:
                return []

            # Get position legs
            result = await self.db.execute(
                select(AutoPilotPositionLeg).where(
                    AutoPilotPositionLeg.strategy_id == strategy_id,
                    AutoPilotPositionLeg.status == PositionLegStatus.OPEN.value
                )
            )
            position_legs = result.scalars().all()

            if not position_legs:
                return []

            # Calculate DTE
            dte = self._calculate_dte(position_legs)
            dte_zone = self._get_dte_zone(dte)

            # Get market data
            spot_price = await self.market_data.get_spot_price(strategy.underlying)
            vix = await self.market_data.get_vix()

            # Analyze position state
            analysis = await self._analyze_position(
                strategy=strategy,
                position_legs=position_legs,
                spot_price=spot_price,
                vix=vix,
                dte=dte,
                dte_zone=dte_zone
            )

            # Generate suggestions based on analysis
            suggestions = []

            # 1. Delta-based suggestions
            delta_suggestions = await self._generate_delta_suggestions(
                strategy, position_legs, analysis, dte_zone, user_settings
            )
            suggestions.extend(delta_suggestions)

            # 2. P&L-based suggestions
            pnl_suggestions = await self._generate_pnl_suggestions(
                strategy, position_legs, analysis, dte_zone
            )
            suggestions.extend(pnl_suggestions)

            # 3. DTE-based suggestions
            dte_suggestions = await self._generate_dte_suggestions(
                strategy, position_legs, analysis, dte, dte_zone
            )
            suggestions.extend(dte_suggestions)

            # 4. Risk-based suggestions
            risk_suggestions = await self._generate_risk_suggestions(
                strategy, position_legs, analysis, dte_zone
            )
            suggestions.extend(risk_suggestions)

            # Clear old suggestions for this strategy
            await self.db.execute(
                delete(AutoPilotAdjustmentSuggestion).where(
                    AutoPilotAdjustmentSuggestion.strategy_id == strategy_id
                )
            )

            # Save new suggestions
            for suggestion in suggestions:
                self.db.add(suggestion)

            await self.db.commit()

            # Sort by priority
            priority_order = {
                SuggestionPriority.CRITICAL: 0,
                SuggestionPriority.HIGH: 1,
                SuggestionPriority.MEDIUM: 2,
                SuggestionPriority.LOW: 3
            }
            suggestions.sort(key=lambda s: priority_order.get(s.priority, 999))

            return suggestions

        except Exception as e:
            logger.error(f"Error generating suggestions for strategy {strategy_id}: {e}")
            return []

    async def _analyze_position(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        spot_price: Optional[Decimal],
        vix: Optional[Decimal],
        dte: int,
        dte_zone: DTEZone
    ) -> Dict[str, Any]:
        """Analyze current position state."""

        runtime_state = strategy.runtime_state or {}
        current_pnl = runtime_state.get('current_pnl', 0)

        # Calculate net Greeks
        net_delta = strategy.net_delta or Decimal('0')
        net_theta = strategy.net_theta or Decimal('0')
        net_gamma = strategy.net_gamma or Decimal('0')

        # Find worst performing leg
        worst_leg = None
        worst_pnl = 0
        for leg in position_legs:
            if leg.unrealized_pnl and float(leg.unrealized_pnl) < worst_pnl:
                worst_pnl = float(leg.unrealized_pnl)
                worst_leg = leg

        # Calculate spot movement from entry
        entry_spot = None
        if spot_price and position_legs:
            # Try to estimate entry spot from first leg
            first_leg = position_legs[0]
            if first_leg.strike and first_leg.contract_type:
                # Rough estimate: assume entered near ATM
                entry_spot = first_leg.strike

        spot_movement_pct = 0
        if entry_spot and spot_price:
            spot_movement_pct = float((spot_price - entry_spot) / entry_spot * 100)

        return {
            "net_delta": float(net_delta),
            "net_theta": float(net_theta),
            "net_gamma": float(net_gamma),
            "current_pnl": current_pnl,
            "worst_leg": worst_leg,
            "worst_pnl": worst_pnl,
            "spot_price": float(spot_price) if spot_price else None,
            "vix": float(vix) if vix else None,
            "spot_movement_pct": spot_movement_pct,
            "dte": dte,
            "dte_zone": dte_zone,
            "num_legs": len(position_legs)
        }

    async def _generate_delta_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte_zone: DTEZone,
        user_settings: AutoPilotUserSettings
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """Generate suggestions based on delta analysis."""

        suggestions = []
        net_delta = analysis["net_delta"]
        abs_delta = abs(net_delta)

        # Get delta thresholds from user settings
        danger_threshold = user_settings.delta_danger_threshold or 0.50
        warning_threshold = user_settings.delta_warning_threshold or 0.30

        # Adjust thresholds by DTE zone
        if dte_zone == DTEZone.LATE or dte_zone == DTEZone.EXPIRY:
            # Tighter thresholds near expiry
            danger_threshold *= 0.7
            warning_threshold *= 0.7

        # CRITICAL: Delta exceeds danger threshold
        if abs_delta >= danger_threshold:
            # Find legs with highest delta contribution
            high_delta_legs = [
                leg for leg in position_legs
                if leg.delta and abs(float(leg.delta)) > 0.20
            ]

            if high_delta_legs:
                # Sort by absolute delta
                high_delta_legs.sort(key=lambda l: abs(float(l.delta)), reverse=True)
                target_leg = high_delta_legs[0]

                suggestion = AutoPilotAdjustmentSuggestion(
                    strategy_id=strategy.id,
                    suggestion_type=SuggestionType.SHIFT,
                    priority=SuggestionPriority.CRITICAL,
                    title=f"Shift {target_leg.contract_type} leg to reduce delta",
                    description=f"Net delta ({abs_delta:.2f}) exceeds danger threshold. "
                               f"Shift the {target_leg.strike} {target_leg.contract_type} leg "
                               f"to reduce directional risk.",
                    reasoning="High delta exposure creates significant directional risk. "
                             "Position is vulnerable to adverse spot price movement.",
                    action_params={
                        "leg_id": target_leg.leg_id,
                        "current_strike": float(target_leg.strike),
                        "current_delta": float(target_leg.delta),
                        "target_delta": 0.15,  # Safer delta
                        "shift_direction": "further",  # Move OTM
                        "execution_mode": "market"
                    },
                    estimated_impact={
                        "delta_change": -abs(float(target_leg.delta)) * 0.5,
                        "cost": "~₹20-50 per lot (depends on market)"
                    }
                )
                suggestions.append(suggestion)

        # HIGH: Delta exceeds warning threshold
        elif abs_delta >= warning_threshold:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.SHIFT,
                priority=SuggestionPriority.HIGH,
                title="Consider adjusting position delta",
                description=f"Net delta ({abs_delta:.2f}) is elevated. "
                           f"Consider shifting legs to reduce directional exposure.",
                reasoning="Moderate delta exposure. Position is showing directional bias.",
                action_params={
                    "execution_mode": "limit"
                },
                estimated_impact={
                    "delta_change": -abs_delta * 0.3,
                    "risk_reduction": "moderate"
                }
            )
            suggestions.append(suggestion)

        return suggestions

    async def _generate_pnl_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte_zone: DTEZone
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """Generate suggestions based on P&L analysis."""

        suggestions = []
        worst_leg = analysis["worst_leg"]
        worst_pnl = analysis["worst_pnl"]
        current_pnl = analysis["current_pnl"]

        # Get risk limits
        risk_settings = strategy.risk_settings or {}
        max_loss = risk_settings.get('max_loss', 0)

        # CRITICAL: Worst leg losing significantly
        if worst_leg and worst_pnl < -500:  # ₹500 loss threshold
            # Break trade suggestion
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.BREAK,
                priority=SuggestionPriority.CRITICAL,
                title=f"Break trade on losing {worst_leg.contract_type} leg",
                description=f"The {worst_leg.strike} {worst_leg.contract_type} leg has "
                           f"unrealized loss of ₹{abs(worst_pnl):.0f}. "
                           f"Break trade can help recover losses by creating a strangle.",
                reasoning="Break/split trade technique: exit losing leg, use exit premium "
                         "to sell two new positions (PUT + CALL) at safer strikes.",
                action_params={
                    "leg_id": worst_leg.leg_id,
                    "execution_mode": "market",
                    "new_positions": "auto",
                    "premium_split": "equal",
                    "prefer_round_strikes": True,
                    "max_delta": 0.25
                },
                estimated_impact={
                    "exit_cost": abs(worst_pnl),
                    "recovery_target": abs(worst_pnl) / 2,
                    "new_positions": 2,
                    "strategy": "strangle"
                }
            )
            suggestions.append(suggestion)

        # HIGH: Overall P&L approaching max loss
        if max_loss and current_pnl < -float(max_loss) * 0.7:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.EXIT,
                priority=SuggestionPriority.HIGH,
                title="Consider exiting position",
                description=f"Current P&L (₹{current_pnl:.0f}) is approaching max loss limit "
                           f"(₹{max_loss}). Exit to preserve capital.",
                reasoning="Position is deteriorating. Better to exit with controlled loss "
                         "than risk hitting max loss limit.",
                action_params={
                    "exit_type": "market",
                    "reason": "approaching_max_loss"
                },
                estimated_impact={
                    "realized_pnl": current_pnl,
                    "capital_preserved": float(max_loss) - current_pnl
                }
            )
            suggestions.append(suggestion)

        return suggestions

    async def _generate_dte_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte: int,
        dte_zone: DTEZone
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """Generate suggestions based on DTE analysis."""

        suggestions = []

        # MEDIUM: Expiry approaching, consider rolling
        if dte_zone == DTEZone.LATE and dte <= 5:
            # Get next expiry (rough estimate: weekly = +7 days, monthly = +30 days)
            next_expiry_days = 7 if dte <= 7 else 30

            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.ROLL,
                priority=SuggestionPriority.MEDIUM,
                title="Roll to next expiry",
                description=f"Current expiry has only {dte} days remaining. "
                           f"Consider rolling positions to next expiry to maintain theta decay.",
                reasoning=f"With {dte} DTE, gamma risk increases and theta decay accelerates. "
                         "Rolling extends the position and reduces gamma risk.",
                action_params={
                    "target_expiry": f"+{next_expiry_days}days",
                    "maintain_strikes": True,
                    "execution_mode": "limit"
                },
                estimated_impact={
                    "new_dte": next_expiry_days,
                    "roll_cost": "~₹10-30 per lot (typical)",
                    "gamma_risk": "reduced",
                    "theta_decay": "moderated"
                }
            )
            suggestions.append(suggestion)

        # HIGH: Expiry day - suggest exit
        if dte_zone == DTEZone.EXPIRY and dte == 0:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.EXIT,
                priority=SuggestionPriority.CRITICAL,
                title="EXIT NOW - Expiry day",
                description="Today is expiry day! Exit all positions to avoid assignment risk.",
                reasoning="Expiry day carries extreme gamma risk and assignment risk. "
                         "Exit positions before 3:30 PM to avoid complications.",
                action_params={
                    "exit_type": "market",
                    "reason": "expiry_day",
                    "urgency": "immediate"
                },
                estimated_impact={
                    "assignment_risk": "eliminated",
                    "time_remaining": "< 1 hour" if datetime.now().hour >= 14 else "few hours"
                }
            )
            suggestions.append(suggestion)

        return suggestions

    async def _generate_risk_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte_zone: DTEZone
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """Generate suggestions based on risk analysis."""

        suggestions = []
        net_gamma = analysis.get("net_gamma", 0)
        vix = analysis.get("vix")

        # HIGH: High gamma with low DTE
        if abs(net_gamma) > 0.05 and dte_zone in [DTEZone.LATE, DTEZone.EXPIRY]:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.ADD_HEDGE,
                priority=SuggestionPriority.HIGH,
                title="Add hedge to reduce gamma risk",
                description=f"High gamma ({abs(net_gamma):.3f}) with {analysis['dte']} DTE "
                           f"creates significant risk from spot moves.",
                reasoning="High gamma amplifies P&L swings. Adding a hedge can stabilize the position.",
                action_params={
                    "hedge_type": "protective",
                    "execution_mode": "limit"
                },
                estimated_impact={
                    "gamma_reduction": "~50%",
                    "hedge_cost": "₹50-100 per lot"
                }
            )
            suggestions.append(suggestion)

        # MEDIUM: High VIX
        if vix and vix > 20:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.NO_ACTION,
                priority=SuggestionPriority.LOW,
                title="Monitor position - High volatility environment",
                description=f"VIX at {vix:.1f} indicates elevated market volatility. "
                           f"Monitor position closely but no immediate action needed.",
                reasoning="High VIX can benefit option sellers through higher premiums "
                         "but also increases risk of large moves.",
                action_params={},
                estimated_impact={
                    "volatility_impact": "positive for option sellers",
                    "risk_level": "elevated"
                }
            )
            suggestions.append(suggestion)

        return suggestions

    def _calculate_dte(self, position_legs: List[AutoPilotPositionLeg]) -> int:
        """Calculate days to expiry."""
        if not position_legs or not position_legs[0].expiry:
            return 0

        expiry_date = position_legs[0].expiry
        today = date.today()

        return (expiry_date - today).days

    def _get_dte_zone(self, dte: int) -> DTEZone:
        """Determine DTE zone."""
        if dte > 14:
            return DTEZone.EARLY
        elif dte > 7:
            return DTEZone.MIDDLE
        elif dte > 3:
            return DTEZone.LATE
        else:
            return DTEZone.EXPIRY

    async def _get_user_settings(self, user_id: int) -> Optional[AutoPilotUserSettings]:
        """Get user settings."""
        result = await self.db.execute(
            select(AutoPilotUserSettings).where(
                AutoPilotUserSettings.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
