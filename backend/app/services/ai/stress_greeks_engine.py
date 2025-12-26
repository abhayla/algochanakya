"""
Stress Greeks Engine - Priority 1.1

Simulates portfolio Greeks and P&L under multiple spot price scenarios
to assess tail risk and provide deployment gating for AI strategies.

Key Features:
- Multi-scenario stress testing (±1% to ±5% spot moves)
- Stress risk score calculation (0-100, higher = riskier)
- Portfolio-level stress analysis
- Deployment risk evaluation
- Integration with GreeksCalculatorService

Usage:
    engine = StressGreeksEngine(greeks_calculator)
    stress_result = await engine.calculate_stress_scenarios(legs, current_spot)
    risk_score = stress_result.stress_risk_score

    # Gate deployment
    if risk_score > 75:
        # Reject deployment - too risky
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal

from app.services.greeks_calculator import GreeksCalculatorService

logger = logging.getLogger(__name__)

# Stress test scenarios (spot price changes as percentages)
DEFAULT_STRESS_SCENARIOS = [
    -5.0,  # -5% down
    -4.0,  # -4% down
    -3.0,  # -3% down
    -2.0,  # -2% down
    -1.0,  # -1% down
    0.0,   # Current spot
    1.0,   # +1% up
    2.0,   # +2% up
    3.0,   # +3% up
    4.0,   # +4% up
    5.0,   # +5% up
]

# Risk score weights
DELTA_RISK_WEIGHT = 0.30
GAMMA_RISK_WEIGHT = 0.30
MAX_LOSS_WEIGHT = 0.25
VOLATILITY_WEIGHT = 0.15


@dataclass
class StressScenario:
    """Represents a single stress test scenario."""
    spot_change_pct: float  # Percentage change from current spot
    stressed_spot: float    # Spot price at this scenario
    delta: float           # Portfolio delta at this scenario
    gamma: float           # Portfolio gamma at this scenario
    theta: float           # Portfolio theta at this scenario
    vega: float            # Portfolio vega at this scenario
    estimated_pnl: float   # Estimated P&L for this scenario

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StressTestResult:
    """Aggregated stress test results."""
    current_spot: float
    scenarios: List[StressScenario]
    stress_risk_score: float  # 0-100, higher = riskier
    max_loss_scenario: Optional[StressScenario]
    max_gain_scenario: Optional[StressScenario]
    delta_range: tuple  # (min_delta, max_delta)
    gamma_range: tuple  # (min_gamma, max_gamma)
    risk_metrics: Dict[str, float]
    calculated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_spot': self.current_spot,
            'scenarios': [s.to_dict() for s in self.scenarios],
            'stress_risk_score': round(self.stress_risk_score, 2),
            'max_loss_scenario': self.max_loss_scenario.to_dict() if self.max_loss_scenario else None,
            'max_gain_scenario': self.max_gain_scenario.to_dict() if self.max_gain_scenario else None,
            'delta_range': self.delta_range,
            'gamma_range': self.gamma_range,
            'risk_metrics': self.risk_metrics,
            'calculated_at': self.calculated_at.isoformat()
        }


class StressGreeksEngine:
    """
    Engine for stress testing portfolio Greeks under multiple scenarios.

    Provides:
    - Multi-scenario stress testing
    - Risk score calculation
    - Deployment gating
    - Portfolio-level analysis
    """

    def __init__(
        self,
        greeks_calculator: GreeksCalculatorService,
        stress_scenarios: Optional[List[float]] = None
    ):
        """
        Initialize stress Greeks engine.

        Args:
            greeks_calculator: GreeksCalculatorService instance
            stress_scenarios: List of spot change percentages (default: ±1% to ±5%)
        """
        self.greeks_calculator = greeks_calculator
        self.stress_scenarios = stress_scenarios or DEFAULT_STRESS_SCENARIOS

    async def calculate_stress_scenarios(
        self,
        legs: List[Dict[str, Any]],
        current_spot: float,
        lot_size: int = 1,
        current_time: Optional[datetime] = None
    ) -> StressTestResult:
        """
        Calculate stress scenarios for a position.

        Args:
            legs: List of position legs (same format as GreeksCalculatorService)
            current_spot: Current spot price
            lot_size: Lot size for P&L scaling
            current_time: Current time (defaults to now)

        Returns:
            StressTestResult with all scenarios and aggregate metrics
        """
        if current_time is None:
            current_time = datetime.utcnow()

        scenarios = []

        # Calculate Greeks for each stress scenario
        for spot_change_pct in self.stress_scenarios:
            stressed_spot = current_spot * (1 + spot_change_pct / 100)

            # Calculate Greeks at stressed spot price
            greeks_result = await self.greeks_calculator.calculate_position_greeks(
                legs=legs,
                spot_price=stressed_spot,
                current_time=current_time
            )

            # Estimate P&L using delta-gamma approximation
            spot_change = stressed_spot - current_spot

            # Get current Greeks (at spot_change_pct = 0) for P&L estimation
            if spot_change_pct == 0.0:
                current_delta = greeks_result.total_delta
                current_gamma = greeks_result.total_gamma

            # Estimate P&L
            if spot_change_pct == 0.0:
                estimated_pnl = 0.0
            else:
                # Use delta-gamma approximation from current spot
                estimated_pnl = self.greeks_calculator.estimate_pnl_for_spot_change(
                    current_delta=current_delta,
                    current_gamma=current_gamma,
                    spot_change=spot_change,
                    lot_size=lot_size
                )

            scenario = StressScenario(
                spot_change_pct=spot_change_pct,
                stressed_spot=round(stressed_spot, 2),
                delta=greeks_result.total_delta,
                gamma=greeks_result.total_gamma,
                theta=greeks_result.total_theta,
                vega=greeks_result.total_vega,
                estimated_pnl=round(estimated_pnl, 2)
            )

            scenarios.append(scenario)

        # Calculate aggregate risk metrics
        stress_risk_score = self._calculate_stress_risk_score(scenarios, current_spot)
        max_loss_scenario = min(scenarios, key=lambda s: s.estimated_pnl)
        max_gain_scenario = max(scenarios, key=lambda s: s.estimated_pnl)

        delta_values = [s.delta for s in scenarios]
        gamma_values = [s.gamma for s in scenarios]

        delta_range = (min(delta_values), max(delta_values))
        gamma_range = (min(gamma_values), max(gamma_values))

        # Additional risk metrics
        risk_metrics = {
            'max_loss': max_loss_scenario.estimated_pnl,
            'max_gain': max_gain_scenario.estimated_pnl,
            'pnl_range': max_gain_scenario.estimated_pnl - max_loss_scenario.estimated_pnl,
            'delta_volatility': max(delta_values) - min(delta_values),
            'gamma_exposure': max(abs(g) for g in gamma_values),
            'downside_scenarios': sum(1 for s in scenarios if s.estimated_pnl < 0),
            'upside_scenarios': sum(1 for s in scenarios if s.estimated_pnl > 0),
        }

        return StressTestResult(
            current_spot=current_spot,
            scenarios=scenarios,
            stress_risk_score=stress_risk_score,
            max_loss_scenario=max_loss_scenario,
            max_gain_scenario=max_gain_scenario,
            delta_range=delta_range,
            gamma_range=gamma_range,
            risk_metrics=risk_metrics,
            calculated_at=current_time
        )

    def _calculate_stress_risk_score(
        self,
        scenarios: List[StressScenario],
        current_spot: float
    ) -> float:
        """
        Calculate aggregate stress risk score (0-100).

        Higher score = riskier position

        Components:
        - Delta risk (30%): Directional exposure volatility
        - Gamma risk (30%): Convexity risk
        - Max loss (25%): Worst-case scenario impact
        - Volatility (15%): P&L variability across scenarios

        Args:
            scenarios: List of stress scenarios
            current_spot: Current spot price

        Returns:
            Risk score from 0 (safe) to 100 (very risky)
        """
        if not scenarios:
            return 0.0

        # 1. Delta Risk: Measure directional exposure variability
        delta_values = [s.delta for s in scenarios]
        delta_range = max(delta_values) - min(delta_values)
        delta_max = max(abs(d) for d in delta_values)

        # Normalize to 0-100 (assume max delta of 1.0 per lot is normal)
        delta_risk = min(100, (delta_max + delta_range / 2) * 100)

        # 2. Gamma Risk: Measure convexity exposure
        gamma_values = [abs(s.gamma) for s in scenarios]
        gamma_max = max(gamma_values)

        # Normalize to 0-100 (assume max gamma of 0.05 is normal)
        gamma_risk = min(100, gamma_max / 0.05 * 100)

        # 3. Max Loss Risk: Worst-case scenario impact
        pnl_values = [s.estimated_pnl for s in scenarios]
        max_loss = abs(min(pnl_values))

        # Normalize to 0-100 (assume max loss of 10,000 is very risky)
        max_loss_risk = min(100, max_loss / 10000 * 100)

        # 4. Volatility Risk: P&L variability
        pnl_range = max(pnl_values) - min(pnl_values)

        # Normalize to 0-100 (assume P&L range of 20,000 is very risky)
        volatility_risk = min(100, pnl_range / 20000 * 100)

        # Weighted aggregate score
        stress_risk_score = (
            DELTA_RISK_WEIGHT * delta_risk +
            GAMMA_RISK_WEIGHT * gamma_risk +
            MAX_LOSS_WEIGHT * max_loss_risk +
            VOLATILITY_WEIGHT * volatility_risk
        )

        return round(stress_risk_score, 2)

    def evaluate_deployment_risk(
        self,
        portfolio_stress_result: StressTestResult,
        new_strategy_stress_result: StressTestResult,
        max_stress_risk_score: float = 75.0,
        max_portfolio_delta: float = 1.0,
        max_portfolio_gamma: float = 0.05
    ) -> Dict[str, Any]:
        """
        Evaluate if adding a new strategy to portfolio is acceptable.

        Args:
            portfolio_stress_result: Current portfolio stress test result
            new_strategy_stress_result: New strategy stress test result
            max_stress_risk_score: Maximum acceptable stress risk score
            max_portfolio_delta: Maximum portfolio delta (absolute)
            max_portfolio_gamma: Maximum portfolio gamma (absolute)

        Returns:
            Dict with decision and reasons
        """
        # Calculate combined stress scenarios
        combined_scenarios = []

        for i, portfolio_scenario in enumerate(portfolio_stress_result.scenarios):
            new_scenario = new_strategy_stress_result.scenarios[i]

            # Add Greeks and P&L
            combined_scenario = StressScenario(
                spot_change_pct=portfolio_scenario.spot_change_pct,
                stressed_spot=portfolio_scenario.stressed_spot,
                delta=portfolio_scenario.delta + new_scenario.delta,
                gamma=portfolio_scenario.gamma + new_scenario.gamma,
                theta=portfolio_scenario.theta + new_scenario.theta,
                vega=portfolio_scenario.vega + new_scenario.vega,
                estimated_pnl=portfolio_scenario.estimated_pnl + new_scenario.estimated_pnl
            )
            combined_scenarios.append(combined_scenario)

        # Calculate combined risk score
        combined_risk_score = self._calculate_stress_risk_score(
            combined_scenarios,
            portfolio_stress_result.current_spot
        )

        # Check limits
        violations = []

        if combined_risk_score > max_stress_risk_score:
            violations.append(
                f"Combined stress risk score ({combined_risk_score:.1f}) "
                f"exceeds limit ({max_stress_risk_score:.1f})"
            )

        # Check delta limits across scenarios
        max_combined_delta = max(abs(s.delta) for s in combined_scenarios)
        if max_combined_delta > max_portfolio_delta:
            violations.append(
                f"Max portfolio delta ({max_combined_delta:.3f}) "
                f"exceeds limit ({max_portfolio_delta:.3f})"
            )

        # Check gamma limits
        max_combined_gamma = max(abs(s.gamma) for s in combined_scenarios)
        if max_combined_gamma > max_portfolio_gamma:
            violations.append(
                f"Max portfolio gamma ({max_combined_gamma:.5f}) "
                f"exceeds limit ({max_portfolio_gamma:.5f})"
            )

        # Decision
        acceptable = len(violations) == 0

        return {
            'acceptable': acceptable,
            'combined_stress_risk_score': round(combined_risk_score, 2),
            'portfolio_stress_risk_score': round(portfolio_stress_result.stress_risk_score, 2),
            'new_strategy_stress_risk_score': round(new_strategy_stress_result.stress_risk_score, 2),
            'violations': violations,
            'combined_scenarios': [s.to_dict() for s in combined_scenarios],
            'max_combined_delta': round(max_combined_delta, 4),
            'max_combined_gamma': round(max_combined_gamma, 6),
        }

    def get_risk_assessment(self, stress_risk_score: float) -> str:
        """
        Get human-readable risk assessment.

        Args:
            stress_risk_score: Stress risk score (0-100)

        Returns:
            Risk assessment string
        """
        if stress_risk_score < 25:
            return "LOW"
        elif stress_risk_score < 50:
            return "MODERATE"
        elif stress_risk_score < 75:
            return "HIGH"
        else:
            return "VERY_HIGH"


__all__ = ["StressGreeksEngine", "StressTestResult", "StressScenario"]
