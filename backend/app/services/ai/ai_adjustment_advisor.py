"""
AI-Powered Adjustment Advisor

Intelligently selects the best adjustment action using:
- What-if P&L simulation
- ML-based success prediction
- Multi-factor scoring (P&L, Greeks, margin, cost)
- Risk-adjusted decision making

Integrates with existing adjustment_engine.py for execution.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotPositionLeg,
    AdjustmentActionType,
    AdjustmentTriggerType
)
from app.services.options.pnl_calculator import PnLCalculator
from app.services.legacy.market_data import MarketDataService
from app.services.position_leg_service import PositionLegService
from app.services.adjustment_engine import AdjustmentCategory, ADJUSTMENT_CATEGORIES
from app.constants.trading import get_lot_size

logger = logging.getLogger(__name__)


@dataclass
class AdjustmentSimulation:
    """Results from simulating an adjustment."""
    action_type: str
    action_params: Dict

    # P&L Impact
    expected_pnl: Decimal
    max_profit: Decimal
    max_loss: Decimal
    breakevens: List[float]

    # Greeks Impact
    new_delta: float
    new_gamma: float
    new_theta: float
    new_vega: float

    # Cost Impact
    margin_impact: Decimal
    execution_cost: Decimal

    # Risk Metrics
    risk_score: float  # 0-100, lower is better
    reward_score: float  # 0-100, higher is better


@dataclass
class AdjustmentRecommendation:
    """Final AI-selected adjustment recommendation."""
    action_type: str
    action_params: Dict

    # Scores
    overall_score: float  # 0-100, higher is better
    ml_confidence: float  # 0-100
    simulation: AdjustmentSimulation

    # Reasoning
    category: str  # defensive, offensive, neutral
    rationale: str

    # Ranking
    rank: int  # 1 = best option


class AIAdjustmentAdvisor:
    """
    AI-powered adjustment advisor for AutoPilot strategies.

    Evaluates all possible adjustments and selects the optimal action
    using ML predictions and what-if simulations.
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
        self.pnl_calculator = PnLCalculator()
        self.leg_service = PositionLegService(kite, db, market_data)

    async def evaluate_adjustments(
        self,
        strategy: AutoPilotStrategy,
        trigger_type: AdjustmentTriggerType,
        trigger_value: Optional[Decimal] = None
    ) -> List[AdjustmentRecommendation]:
        """
        Evaluate all possible adjustments for a strategy.

        Args:
            strategy: AutoPilot strategy needing adjustment
            trigger_type: What triggered the adjustment need
            trigger_value: Value that triggered (e.g., delta, P&L)

        Returns:
            List of recommendations ranked by score (best first)
        """
        logger.info(
            f"Evaluating adjustments for strategy {strategy.id}, "
            f"trigger: {trigger_type}, value: {trigger_value}"
        )

        # Get current position state
        position_legs = await self.leg_service.get_strategy_legs(strategy.id)
        current_state = await self._get_position_state(strategy, position_legs)

        # Generate possible actions based on trigger
        possible_actions = self._generate_possible_actions(
            strategy, trigger_type, current_state
        )

        # Simulate each action
        simulations = []
        for action_type, action_params in possible_actions:
            try:
                simulation = await self._simulate_adjustment(
                    strategy, position_legs, action_type, action_params, current_state
                )
                simulations.append((action_type, action_params, simulation))
            except Exception as e:
                logger.error(f"Error simulating {action_type}: {e}")
                continue

        # Score and rank adjustments
        recommendations = []
        for action_type, action_params, simulation in simulations:
            score = self._calculate_adjustment_score(
                simulation, strategy, trigger_type
            )

            # Get ML confidence (placeholder - would use trained model)
            ml_confidence = 50.0

            # Create recommendation
            category = self._categorize_action(action_type)
            rationale = self._generate_rationale(
                action_type, simulation, trigger_type, category
            )

            recommendation = AdjustmentRecommendation(
                action_type=action_type,
                action_params=action_params,
                overall_score=score,
                ml_confidence=ml_confidence,
                simulation=simulation,
                category=category,
                rationale=rationale,
                rank=0  # Will be set after sorting
            )

            recommendations.append(recommendation)

        # Sort by score (descending) and assign ranks
        recommendations.sort(key=lambda r: r.overall_score, reverse=True)
        for i, rec in enumerate(recommendations):
            rec.rank = i + 1

        logger.info(
            f"Evaluated {len(recommendations)} adjustments for strategy {strategy.id}. "
            f"Top recommendation: {recommendations[0].action_type if recommendations else 'NONE'}"
        )

        return recommendations

    async def _get_position_state(
        self,
        strategy: AutoPilotStrategy,
        legs: List[AutoPilotPositionLeg]
    ) -> Dict:
        """Get current position state for analysis."""
        # Calculate current Greeks
        total_delta = sum(leg.current_delta or 0 for leg in legs)
        total_gamma = sum(leg.current_gamma or 0 for leg in legs)
        total_theta = sum(leg.current_theta or 0 for leg in legs)
        total_vega = sum(leg.current_vega or 0 for leg in legs)

        # Get spot price
        spot_price = await self.market_data.get_spot_price(strategy.underlying)

        return {
            "spot_price": spot_price,
            "delta": total_delta,
            "gamma": total_gamma,
            "theta": total_theta,
            "vega": total_vega,
            "current_pnl": strategy.current_pnl or Decimal('0'),
            "legs_count": len(legs),
            "margin_used": strategy.margin_used or Decimal('0')
        }

    def _generate_possible_actions(
        self,
        strategy: AutoPilotStrategy,
        trigger_type: AdjustmentTriggerType,
        current_state: Dict
    ) -> List[Tuple[str, Dict]]:
        """
        Generate list of possible adjustment actions based on trigger.

        Returns:
            List of (action_type, action_params) tuples
        """
        actions = []

        # Delta-based adjustments
        if trigger_type == AdjustmentTriggerType.DELTA_BREACH:
            delta = current_state.get("delta", 0)

            if abs(delta) > 0.3:  # High delta - defensive actions
                actions.append(("add_hedge", {"side": "CE" if delta > 0 else "PE"}))
                actions.append(("roll_strike_farther", {"leg_type": "short"}))
                actions.append(("scale_down", {"reduction_pct": 50}))

            if abs(delta) < 0.1:  # Low delta - offensive actions
                actions.append(("roll_strike_closer", {"leg_type": "short"}))
                actions.append(("scale_up", {"increase_pct": 50}))

        # P&L-based adjustments
        elif trigger_type == AdjustmentTriggerType.PNL_BREACH:
            pnl = current_state.get("current_pnl", Decimal('0'))

            if pnl < 0:  # Loss - defensive
                actions.append(("exit_all", {}))
                actions.append(("close_losing_leg", {}))
                actions.append(("add_hedge", {"side": "both"}))

            if pnl > 0:  # Profit - take profit or let run
                actions.append(("exit_all", {}))
                actions.append(("scale_down", {"reduction_pct": 50}))

        # Time-based adjustments
        elif trigger_type == AdjustmentTriggerType.TIME_BASED:
            actions.append(("roll_expiry", {"target_dte": 7}))
            actions.append(("exit_all", {}))

        # Premium-based adjustments
        elif trigger_type == AdjustmentTriggerType.PREMIUM_DECAY:
            actions.append(("exit_all", {}))  # Premium captured
            actions.append(("roll_expiry", {"target_dte": 7}))  # Roll forward

        # VIX-based adjustments
        elif trigger_type == AdjustmentTriggerType.VIX_BREACH:
            actions.append(("add_hedge", {"side": "both"}))
            actions.append(("roll_strike_farther", {"leg_type": "short"}))
            actions.append(("scale_down", {"reduction_pct": 50}))

        # Always include "do nothing" as an option
        actions.append(("no_action", {}))

        return actions

    async def _simulate_adjustment(
        self,
        strategy: AutoPilotStrategy,
        current_legs: List[AutoPilotPositionLeg],
        action_type: str,
        action_params: Dict,
        current_state: Dict
    ) -> AdjustmentSimulation:
        """
        Simulate the impact of an adjustment action.

        Uses P&L calculator to project outcomes.
        """
        # Create modified leg configuration
        modified_legs = self._apply_action_to_legs(
            current_legs, action_type, action_params
        )

        # Calculate P&L for modified position
        spot_price = current_state["spot_price"]

        # Simplified P&L calculation (would use full PnLCalculator in production)
        expected_pnl = Decimal('0')
        max_profit = Decimal('0')
        max_loss = Decimal('0')

        # Calculate new Greeks using GreeksCalculatorService
        from app.services.options.greeks_calculator import GreeksCalculatorService

        greeks_calculator = GreeksCalculatorService(self.db, strategy.user_id)

        # Calculate Greeks for modified position
        modified_greeks = await greeks_calculator.calculate_position_greeks(
            legs=modified_legs,
            spot_price=float(spot_price)
        )

        new_delta = modified_greeks.total_delta
        new_gamma = modified_greeks.total_gamma
        new_theta = modified_greeks.total_theta
        new_vega = modified_greeks.total_vega

        # Calculate costs
        execution_cost = self._estimate_execution_cost(action_type, action_params)
        margin_impact = self._estimate_margin_impact(
            current_state["margin_used"], action_type
        )

        # Calculate risk/reward scores
        risk_score = self._calculate_risk_score(new_delta, new_gamma, max_loss)
        reward_score = self._calculate_reward_score(max_profit, expected_pnl)

        return AdjustmentSimulation(
            action_type=action_type,
            action_params=action_params,
            expected_pnl=expected_pnl,
            max_profit=max_profit,
            max_loss=max_loss,
            breakevens=[],
            new_delta=new_delta,
            new_gamma=new_gamma,
            new_theta=new_theta,
            new_vega=new_vega,
            margin_impact=margin_impact,
            execution_cost=execution_cost,
            risk_score=risk_score,
            reward_score=reward_score
        )

    def _apply_action_to_legs(
        self,
        legs: List[AutoPilotPositionLeg],
        action_type: str,
        action_params: Dict
    ) -> List[Dict]:
        """
        Apply adjustment action to legs and return modified configuration.
        """
        modified_legs = []

        for leg in legs:
            leg_dict = {
                "delta": leg.current_delta or 0,
                "gamma": leg.current_gamma or 0,
                "theta": leg.current_theta or 0,
                "vega": leg.current_vega or 0,
                "quantity": leg.quantity,
                "side": leg.side
            }

            # Apply modifications based on action type
            if action_type == "scale_down":
                pct = action_params.get("reduction_pct", 50)
                leg_dict["quantity"] = int(leg.quantity * (1 - pct / 100))

            elif action_type == "scale_up":
                pct = action_params.get("increase_pct", 50)
                leg_dict["quantity"] = int(leg.quantity * (1 + pct / 100))

            elif action_type == "exit_all":
                leg_dict["quantity"] = 0

            modified_legs.append(leg_dict)

        # Add new legs if needed (e.g., hedge)
        if action_type == "add_hedge":
            side = action_params.get("side", "CE")
            modified_legs.append({
                "delta": 0.3 if side == "CE" else -0.3,
                "gamma": 0.01,
                "theta": -50,
                "vega": 15,
                "quantity": 25,  # Default lot size
                "side": side
            })

        return modified_legs

    def _estimate_execution_cost(
        self,
        action_type: str,
        action_params: Dict
    ) -> Decimal:
        """Estimate cost of executing the adjustment."""
        # Simplified cost estimation
        cost_map = {
            "add_hedge": Decimal('500'),  # Brokerage + slippage
            "close_leg": Decimal('300'),
            "roll_strike": Decimal('600'),  # Close + Open
            "roll_expiry": Decimal('600'),
            "exit_all": Decimal('1000'),
            "scale_down": Decimal('400'),
            "scale_up": Decimal('400'),
            "no_action": Decimal('0')
        }

        return cost_map.get(action_type, Decimal('500'))

    def _estimate_margin_impact(
        self,
        current_margin: Decimal,
        action_type: str
    ) -> Decimal:
        """Estimate change in margin requirement."""
        if action_type == "add_hedge":
            return current_margin * Decimal('0.3')  # 30% increase
        elif action_type == "scale_down":
            return current_margin * Decimal('-0.5')  # 50% decrease
        elif action_type == "scale_up":
            return current_margin * Decimal('0.5')  # 50% increase
        elif action_type == "exit_all":
            return -current_margin  # Release all margin
        else:
            return Decimal('0')

    def _calculate_risk_score(
        self,
        delta: float,
        gamma: float,
        max_loss: Decimal
    ) -> float:
        """
        Calculate risk score (0-100, lower is better).

        Considers delta exposure, gamma risk, and max loss.
        """
        # Delta risk (0-40 points)
        delta_risk = min(abs(delta) * 100, 40)

        # Gamma risk (0-30 points)
        gamma_risk = min(abs(gamma) * 1000, 30)

        # Max loss risk (0-30 points)
        loss_risk = min(abs(float(max_loss)) / 1000, 30)

        return delta_risk + gamma_risk + loss_risk

    def _calculate_reward_score(
        self,
        max_profit: Decimal,
        expected_pnl: Decimal
    ) -> float:
        """
        Calculate reward score (0-100, higher is better).

        Considers max profit and expected P&L.
        """
        # Max profit potential (0-60 points)
        profit_score = min(float(max_profit) / 100, 60)

        # Expected P&L (0-40 points)
        expected_score = min(float(expected_pnl) / 50, 40)

        return profit_score + expected_score

    def _calculate_adjustment_score(
        self,
        simulation: AdjustmentSimulation,
        strategy: AutoPilotStrategy,
        trigger_type: AdjustmentTriggerType
    ) -> float:
        """
        Calculate overall adjustment score (0-100).

        Weighted combination of:
        - Risk/Reward ratio: 40%
        - Cost efficiency: 20%
        - Greek improvement: 20%
        - P&L impact: 20%
        """
        # Risk/Reward (40 points)
        risk_reward = (simulation.reward_score - simulation.risk_score) / 2 + 50
        risk_reward_points = (risk_reward / 100) * 40

        # Cost efficiency (20 points)
        cost_impact = float(simulation.execution_cost + abs(simulation.margin_impact))
        cost_efficiency = max(0, 100 - (cost_impact / 100))
        cost_points = (cost_efficiency / 100) * 20

        # Greek improvement (20 points)
        # Lower delta/gamma is better
        greek_score = 100 - min(abs(simulation.new_delta) * 50 + abs(simulation.new_gamma) * 50, 100)
        greek_points = (greek_score / 100) * 20

        # P&L impact (20 points)
        pnl_score = min(float(simulation.expected_pnl) / 10, 100)
        pnl_points = (max(0, pnl_score) / 100) * 20

        total_score = risk_reward_points + cost_points + greek_points + pnl_points

        return round(total_score, 2)

    def _categorize_action(self, action_type: str) -> str:
        """Categorize action as defensive, offensive, or neutral."""
        return ADJUSTMENT_CATEGORIES.get(action_type, AdjustmentCategory.NEUTRAL)

    def _generate_rationale(
        self,
        action_type: str,
        simulation: AdjustmentSimulation,
        trigger_type: AdjustmentTriggerType,
        category: str
    ) -> str:
        """Generate human-readable rationale for the recommendation."""
        parts = []

        # Action description
        action_desc = {
            "add_hedge": "Add protective hedge",
            "exit_all": "Exit entire position",
            "scale_down": "Reduce position size",
            "scale_up": "Increase position size",
            "roll_strike_closer": "Roll strike closer to ATM",
            "roll_strike_farther": "Roll strike farther from ATM",
            "roll_expiry": "Roll to next expiry",
            "close_losing_leg": "Close losing leg",
            "no_action": "Maintain current position"
        }

        parts.append(action_desc.get(action_type, action_type))

        # Trigger context
        parts.append(f"triggered by {trigger_type.value}")

        # Impact summary
        if simulation.expected_pnl > 0:
            parts.append(f"Expected gain: ₹{simulation.expected_pnl:.2f}")
        elif simulation.expected_pnl < 0:
            parts.append(f"Expected cost: ₹{abs(simulation.expected_pnl):.2f}")

        # Greek impact
        if abs(simulation.new_delta) < 0.2:
            parts.append("Low delta risk")

        # Category
        parts.append(f"({category} action)")

        return ". ".join(parts) + "."


__all__ = ["AIAdjustmentAdvisor", "AdjustmentRecommendation", "AdjustmentSimulation"]
