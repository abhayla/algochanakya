"""
Suggestion Engine - Phase 5C + Phase 5E Enhancements

Analyzes position state and generates intelligent adjustment suggestions.
Considers delta, P&L, DTE, market conditions, and position Greeks.

Phase 5E Enhancements:
- Gamma risk exit suggestions (Feature #26, #35)
- ATR-based trailing stop suggestions (Feature #27)
- Delta doubles alerts (Feature #28)
- Delta change alerts (Feature #29)
- DTE-based exit suggestions (Feature #33)
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
    SuggestionUrgency,
    SuggestionStatus
)
from app.services.legacy.market_data import MarketDataService
from app.services.position_leg_service import PositionLegService
from app.services.options.gamma_risk_service import get_gamma_risk_service
from app.services.dte_zone_service import get_dte_zone_service

logger = logging.getLogger(__name__)


class DTEZone(str, Enum):
    """DTE (Days to Expiry) zones with different adjustment thresholds."""
    EARLY = "early"      # > 14 days
    MIDDLE = "middle"    # 7-14 days
    LATE = "late"        # 3-7 days
    EXPIRY = "expiry"    # < 3 days


class AdjustmentCategory(str, Enum):
    """
    Adjustment categories based on risk impact (Phase 5H Feature #45).

    - DEFENSIVE: Reduces risk, decreases or maintains premium
    - OFFENSIVE: Increases risk for more premium
    - NEUTRAL: Rebalances without changing risk profile
    """
    DEFENSIVE = "defensive"
    OFFENSIVE = "offensive"
    NEUTRAL = "neutral"


# Mapping of suggestion types to categories
SUGGESTION_CATEGORY_MAP = {
    SuggestionType.EXIT: AdjustmentCategory.DEFENSIVE,
    SuggestionType.ROLL: AdjustmentCategory.NEUTRAL,
    SuggestionType.SHIFT: AdjustmentCategory.DEFENSIVE,  # Usually to reduce delta risk
    SuggestionType.BREAK: AdjustmentCategory.DEFENSIVE,  # Exit losing leg
    SuggestionType.ADD_HEDGE: AdjustmentCategory.DEFENSIVE,
    SuggestionType.NO_ACTION: AdjustmentCategory.NEUTRAL,
}


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
        # Phase 5E: New risk assessment services
        self.gamma_service = get_gamma_risk_service()
        self.dte_service = get_dte_zone_service()

    def _get_suggestion_category(self, suggestion_type: SuggestionType) -> str:
        """
        Get the category (offensive/defensive/neutral) for a suggestion type.

        Phase 5H Feature #45: Offensive/Defensive Categorization
        """
        return SUGGESTION_CATEGORY_MAP.get(suggestion_type, AdjustmentCategory.DEFENSIVE).value

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

            # 5. Theta-based suggestions
            theta_suggestions = await self._generate_theta_suggestions(
                strategy, position_legs, analysis, dte, dte_zone
            )
            suggestions.extend(theta_suggestions)

            # 6. Vega-based suggestions
            vega_suggestions = await self._generate_vega_suggestions(
                strategy, position_legs, analysis, dte_zone
            )
            suggestions.extend(vega_suggestions)

            # 7. Phase 5E: Gamma risk suggestions (Features #26, #35)
            gamma_suggestions = await self._generate_gamma_risk_suggestions(
                strategy, position_legs, analysis, dte
            )
            suggestions.extend(gamma_suggestions)

            # 8. Phase 5E: Delta tracking suggestions (Features #28, #29)
            delta_tracking_suggestions = await self._generate_delta_tracking_suggestions(
                strategy, position_legs, analysis
            )
            suggestions.extend(delta_tracking_suggestions)

            # 9. Phase 5E: DTE-aware exit suggestions (Feature #33)
            dte_exit_suggestions = await self._generate_dte_exit_suggestions(
                strategy, position_legs, analysis, dte
            )
            suggestions.extend(dte_exit_suggestions)

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

            # Sort by urgency
            urgency_order = {
                SuggestionUrgency.CRITICAL: 0,
                SuggestionUrgency.HIGH: 1,
                SuggestionUrgency.MEDIUM: 2,
                SuggestionUrgency.LOW: 3
            }
            suggestions.sort(key=lambda s: urgency_order.get(s.urgency, 999))

            return suggestions

        except Exception as e:
            logger.error(f"Error generating suggestions for strategy {strategy_id}: {e}")
            raise  # Re-raise to see the actual error in tests

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
        net_vega = strategy.net_vega or Decimal('0')

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
            "net_vega": float(net_vega),
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
        danger_threshold = float(user_settings.delta_danger_threshold or 0.50)
        warning_threshold = float(user_settings.delta_warning_threshold or 0.30)

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
                    urgency=SuggestionUrgency.CRITICAL,
                    category=self._get_suggestion_category(SuggestionType.SHIFT),
                    trigger_reason=f"Shift {target_leg.contract_type} leg to reduce delta",
                    description=f"Net delta ({abs_delta:.2f}) exceeds danger threshold. "
                               f"Shift the {target_leg.strike} {target_leg.contract_type} leg "
                               f"to reduce directional risk."
                             "Position is vulnerable to adverse spot price movement.",
                    action_params={
                        "leg_id": target_leg.leg_id,
                        "current_strike": float(target_leg.strike),
                        "current_delta": float(target_leg.delta),
                        "target_delta": 0.15,  # Safer delta
                        "shift_direction": "further",  # Move OTM
                        "execution_mode": "market"
                    }
                )
                suggestions.append(suggestion)

        # HIGH: Delta exceeds warning threshold
        elif abs_delta >= warning_threshold:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.SHIFT,
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.SHIFT),
                trigger_reason="Consider adjusting position delta",
                description=f"Net delta ({abs_delta:.2f}) is elevated. "
                           f"Consider shifting legs to reduce directional exposure.",
                action_params={
                    "execution_mode": "limit"
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
                urgency=SuggestionUrgency.CRITICAL,
                category=self._get_suggestion_category(SuggestionType.BREAK),
                trigger_reason=f"Break trade on losing {worst_leg.contract_type} leg",
                description=f"The {worst_leg.strike} {worst_leg.contract_type} leg has "
                           f"unrealized loss of ₹{abs(worst_pnl):.0f}. "
                           f"Break trade can help recover losses by creating a strangle."
                         "to sell two new positions (PUT + CALL) at safer strikes.",
                action_params={
                    "leg_id": worst_leg.leg_id,
                    "execution_mode": "market",
                    "new_positions": "auto",
                    "premium_split": "equal",
                    "prefer_round_strikes": True,
                    "max_delta": 0.25
                }
            )
            suggestions.append(suggestion)

        # HIGH: Overall P&L approaching max loss
        if max_loss and current_pnl < -float(max_loss) * 0.7:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.EXIT,
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.EXIT),
                trigger_reason="Consider exiting position",
                description=f"Current P&L (₹{current_pnl:.0f}) is approaching max loss limit "
                           f"(₹{max_loss}). Exit to preserve capital."
                         "than risk hitting max loss limit.",
                action_params={
                    "exit_type": "market",
                    "reason": "approaching_max_loss"
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
                urgency=SuggestionUrgency.MEDIUM,
                category=self._get_suggestion_category(SuggestionType.ROLL),
                trigger_reason="Roll to next expiry",
                description=f"Current expiry has only {dte} days remaining. "
                           f"Consider rolling positions to next expiry to maintain theta decay.",
                action_params={
                    "target_expiry": f"+{next_expiry_days}days",
                    "maintain_strikes": True,
                    "execution_mode": "limit"
                }
            )
            suggestions.append(suggestion)

        # HIGH/CRITICAL: Expiry approaching or expiry day - suggest exit
        if dte_zone == DTEZone.EXPIRY:
            urgency = SuggestionUrgency.CRITICAL if dte == 0 else SuggestionUrgency.HIGH
            trigger_msg = "EXIT NOW - Expiry day" if dte == 0 else f"Consider exit - {dte} days to expiry"
            description = ("Today is expiry day! Exit all positions to avoid assignment risk. "
                          "Exit positions before 3:30 PM to avoid complications.") if dte == 0 else (
                          f"Only {dte} days to expiry! Exit positions to avoid assignment risk and gamma exposure. "
                          "Close to expiry, adjustments are less effective.")

            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.EXIT,
                urgency=urgency,
                category=self._get_suggestion_category(SuggestionType.EXIT),
                trigger_reason=trigger_msg,
                description=description,
                action_params={
                    "exit_type": "market",
                    "reason": "expiry_day" if dte == 0 else "expiry_approaching",
                    "urgency": "immediate" if dte == 0 else "high"
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
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.ADD_HEDGE),
                trigger_reason="Add hedge to reduce gamma risk",
                description=f"High gamma ({abs(net_gamma):.3f}) with {analysis['dte']} DTE "
                           f"creates significant risk from spot moves.",
                action_params={
                    "hedge_type": "protective",
                    "execution_mode": "limit"
                }
            )
            suggestions.append(suggestion)

        # MEDIUM: High VIX
        if vix and vix > 20:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.NO_ACTION,
                urgency=SuggestionUrgency.LOW,
                category=self._get_suggestion_category(SuggestionType.NO_ACTION),
                trigger_reason="Monitor position - High volatility environment",
                description=f"VIX at {vix:.1f} indicates elevated market volatility. "
                           f"Monitor position closely but no immediate action needed."
                         "but also increases risk of large moves.",
                action_params={}
            )
            suggestions.append(suggestion)

        return suggestions

    async def _generate_theta_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte: int,
        dte_zone: DTEZone
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """Generate suggestions based on theta analysis."""

        suggestions = []
        net_theta = analysis.get("net_theta", 0)

        # HIGH: Negative theta (long options) near expiry - time working against you
        if dte_zone in [DTEZone.LATE, DTEZone.EXPIRY] and net_theta < -20:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.EXIT,
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.EXIT),
                trigger_reason="High theta burn on long positions",
                description=f"Net theta ({net_theta:.2f}/day) indicates significant time decay loss. "
                           f"With only {dte} DTE remaining, consider exiting long options "
                           f"or rolling to longer expiry.",
                action_params={
                    "reason": "theta_decay",
                    "execution_mode": "limit"
                }
            )
            suggestions.append(suggestion)

        # LOW: Positive net theta near expiry - favorable for short positions
        if dte_zone in [DTEZone.LATE, DTEZone.EXPIRY] and net_theta > 0:
            if dte <= 3:
                suggestion = AutoPilotAdjustmentSuggestion(
                    strategy_id=strategy.id,
                    suggestion_type=SuggestionType.NO_ACTION,
                    urgency=SuggestionUrgency.LOW,
                    category=self._get_suggestion_category(SuggestionType.NO_ACTION),
                    trigger_reason="Theta decay accelerating - favorable for short positions",
                    description=f"With {dte} DTE, theta decay is accelerating. "
                               f"Net theta (${net_theta:.2f}/day) is favorable. "
                               f"Consider holding positions to maximize time decay collection.",
                    action_params={}
                )
                suggestions.append(suggestion)

        return suggestions

    async def _generate_vega_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte_zone: DTEZone
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """Generate suggestions based on vega analysis."""

        suggestions = []
        net_vega = analysis.get("net_vega", 0)
        vix = analysis.get("vix")

        # MEDIUM: High positive vega exposure in low volatility environment
        if net_vega > 50 and vix and vix < 15:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.NO_ACTION,
                urgency=SuggestionUrgency.MEDIUM,
                category=self._get_suggestion_category(SuggestionType.NO_ACTION),
                trigger_reason="High vega exposure in low volatility environment",
                description=f"Net vega ({net_vega:.2f}) indicates significant volatility exposure. "
                           f"VIX is low ({vix:.1f}). If volatility increases, position will benefit. "
                           f"Consider maintaining position if expecting volatility expansion.",
                action_params={}
            )
            suggestions.append(suggestion)

        # HIGH: High negative vega (short options) with high VIX
        if net_vega < -50 and vix and vix > 20:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.ADD_HEDGE,
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.ADD_HEDGE),
                trigger_reason="High short vega exposure in elevated VIX environment",
                description=f"Net vega ({net_vega:.2f}) indicates significant short volatility exposure. "
                           f"VIX is elevated ({vix:.1f}). Position vulnerable to volatility spikes. "
                           f"Consider adding long options to reduce vega risk.",
                action_params={
                    "hedge_type": "long_option",
                    "reason": "vega_risk",
                    "execution_mode": "limit"
                }
            )
            suggestions.append(suggestion)

        # CRITICAL: Extreme vega exposure
        if abs(net_vega) > 100:
            urgency = SuggestionUrgency.CRITICAL if abs(net_vega) > 200 else SuggestionUrgency.HIGH
            direction = "long" if net_vega > 0 else "short"
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.SHIFT,
                urgency=urgency,
                category=self._get_suggestion_category(SuggestionType.SHIFT),
                trigger_reason=f"Extreme {direction} vega exposure",
                description=f"Net vega ({net_vega:.2f}) is extremely {direction}. "
                           f"Position has significant volatility sensitivity. "
                           f"Consider adjusting positions to reduce vega exposure.",
                action_params={
                    "target_vega": 50 if net_vega > 0 else -50,
                    "execution_mode": "limit"
                }
            )
            suggestions.append(suggestion)

        return suggestions

    async def _generate_gamma_risk_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte: int
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """
        Generate gamma risk exit suggestions (Phase 5E Features #26, #35).

        Uses gamma_risk_service to assess gamma explosion risk.
        """
        suggestions = []
        net_gamma = analysis.get("net_gamma", 0)

        # Get gamma risk assessment
        assessment = self.gamma_service.assess_gamma_risk(
            dte=dte,
            net_gamma=net_gamma,
            position_type="short"
        )

        # Critical: Danger zone (0-3 DTE)
        if assessment['zone'] == 'danger':
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.EXIT,
                urgency=SuggestionUrgency.CRITICAL,
                category=self._get_suggestion_category(SuggestionType.EXIT),
                trigger_reason="GAMMA EXPLOSION RISK",
                description=f"{assessment['recommendation']}. "
                           f"Gamma multiplier: {assessment['multiplier']:.1f}x. "
                           f"Exit immediately to avoid catastrophic losses from gamma risk.",
                action_params={
                    "exit_type": "market",
                    "reason": "gamma_explosion_risk",
                    "urgency": "immediate",
                    "gamma_zone": assessment['zone'],
                    "dte": dte
                }
            )
            suggestions.append(suggestion)

        # High: Warning zone (4-7 DTE)
        elif assessment['zone'] == 'warning':
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.ROLL,
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.ROLL),
                trigger_reason="Gamma risk increasing - expiry week",
                description=f"At {dte} DTE, gamma accelerating (multiplier: {assessment['multiplier']:.1f}x). "
                           f"Consider rolling to next expiry or exiting position. "
                           f"Adjustments become less effective in expiry week.",
                action_params={
                    "action_type": "roll_or_exit",
                    "target_expiry": "+7days",
                    "alternative": "exit_all",
                    "gamma_zone": assessment['zone']
                }
            )
            suggestions.append(suggestion)

        # Check gamma explosion probability
        prob = self.gamma_service.calculate_gamma_explosion_probability(
            dte=dte,
            net_gamma=net_gamma,
            volatility=0.20  # Default IV
        )

        if prob > 0.60 and assessment['zone'] != 'danger':  # Don't duplicate danger zone suggestion
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.EXIT,
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.EXIT),
                trigger_reason=f"High gamma explosion probability ({prob:.0%})",
                description=f"Based on current gamma ({net_gamma:.3f}) and DTE ({dte}), "
                           f"probability of gamma explosion is {prob:.0%}. "
                           f"Recommend exiting to avoid risk.",
                action_params={
                    "exit_type": "limit",
                    "reason": "high_gamma_probability",
                    "probability": prob
                }
            )
            suggestions.append(suggestion)

        return suggestions

    async def _generate_delta_tracking_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any]
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """
        Generate delta tracking suggestions (Phase 5E Features #28, #29).

        - Feature #28: Delta doubles from entry
        - Feature #29: Delta change > 0.10/day
        """
        suggestions = []
        net_delta = analysis.get("net_delta", 0)

        # Get entry delta from strategy runtime_state
        runtime_state = strategy.runtime_state or {}
        entry_delta = runtime_state.get('entry_delta', 0)
        previous_delta = runtime_state.get('previous_delta', entry_delta)

        # Feature #28: Delta doubles from entry
        if entry_delta != 0 and abs(net_delta) >= 2 * abs(entry_delta):
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.SHIFT,
                urgency=SuggestionUrgency.HIGH,
                category=self._get_suggestion_category(SuggestionType.SHIFT),
                trigger_reason=f"Delta doubled from entry",
                description=f"Position delta has doubled from entry "
                           f"({entry_delta:.3f} → {net_delta:.3f}). "
                           f"Directional risk has significantly increased. "
                           f"Consider shifting threatened leg or adding hedge.",
                action_params={
                    "action_type": "shift_or_hedge",
                    "entry_delta": float(entry_delta),
                    "current_delta": float(net_delta),
                    "delta_change_pct": float((abs(net_delta) / abs(entry_delta) - 1) * 100)
                }
            )
            suggestions.append(suggestion)

        # Feature #29: Delta change > 0.10/day
        delta_change = abs(net_delta - previous_delta)
        if delta_change > 0.10:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.SHIFT,
                urgency=SuggestionUrgency.MEDIUM,
                category=self._get_suggestion_category(SuggestionType.SHIFT),
                trigger_reason=f"Large delta shift ({delta_change:.3f})",
                description=f"Delta changed by {delta_change:.3f} "
                           f"({previous_delta:.3f} → {net_delta:.3f}). "
                           f"Significant spot movement detected. Monitor closely.",
                action_params={
                    "delta_change": float(delta_change),
                    "previous_delta": float(previous_delta),
                    "current_delta": float(net_delta)
                }
            )
            suggestions.append(suggestion)

        return suggestions

    async def _generate_dte_exit_suggestions(
        self,
        strategy: AutoPilotStrategy,
        position_legs: List[AutoPilotPositionLeg],
        analysis: Dict[str, Any],
        dte: int
    ) -> List[AutoPilotAdjustmentSuggestion]:
        """
        Generate DTE-aware exit suggestions (Phase 5E Feature #33).

        Uses dte_zone_service to determine if exit is preferred over adjustment.
        """
        suggestions = []

        # Get DTE zone configuration
        zone_config = self.dte_service.get_zone_config(dte)

        # Check if exit is preferred
        should_exit, reason = self.dte_service.should_exit_instead_of_adjust(dte)

        if should_exit:
            net_delta = analysis.get("net_delta", 0)

            # Determine urgency based on DTE and delta
            if zone_config['zone'] == 'expiry_week':
                if dte <= 3:
                    urgency = SuggestionUrgency.CRITICAL
                    time_frame = "immediately (within hours)"
                elif abs(net_delta) > 0.25:
                    urgency = SuggestionUrgency.CRITICAL
                    time_frame = "within 24 hours"
                else:
                    urgency = SuggestionUrgency.HIGH
                    time_frame = "within 1-2 days"

                suggestion = AutoPilotAdjustmentSuggestion(
                    strategy_id=strategy.id,
                    suggestion_type=SuggestionType.EXIT,
                    urgency=urgency,
                    trigger_reason=reason,
                    description=f"{reason}. "
                               f"Adjustments are only {zone_config['adjustment_effectiveness']['percentage']}% effective. "
                               f"Exit {time_frame} to avoid gamma risk.",
                    action_params={
                        "exit_type": "market" if urgency == SuggestionUrgency.CRITICAL else "limit",
                        "reason": "dte_based_exit",
                        "dte": dte,
                        "zone": zone_config['zone'],
                        "time_frame": time_frame
                    }
                )
                suggestions.append(suggestion)

        # Warn about restricted actions in current zone
        restricted_actions = []
        all_actions = ["roll_strike", "shift_strike", "break_trade", "add_hedge"]

        for action in all_actions:
            is_allowed, restriction_reason = self.dte_service.is_action_allowed(dte, action)
            if not is_allowed:
                restricted_actions.append(action)

        if restricted_actions and zone_config['zone'] in ['late', 'expiry_week']:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=strategy.id,
                suggestion_type=SuggestionType.NO_ACTION,
                urgency=SuggestionUrgency.LOW,
                category=self._get_suggestion_category(SuggestionType.NO_ACTION),
                trigger_reason=f"Limited adjustment options at {dte} DTE",
                description=f"In {zone_config['display']['label']}, "
                           f"actions {', '.join(restricted_actions)} are restricted. "
                           f"Only exit and roll actions recommended.",
                action_params={
                    "restricted_actions": restricted_actions,
                    "allowed_actions": zone_config['allowed_actions'],
                    "zone": zone_config['zone']
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
