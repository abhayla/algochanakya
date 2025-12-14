"""
Theta Curve Service - Phase 5D Feature #25

Analyzes theta decay curves to determine optimal exit timing.

The theta decay curve shows how time decay changes over time:
- Theta accelerates as expiry approaches (peak around 21-30 DTE)
- Theta slows in final days (gamma becomes dominant)
- Optimal exit: When theta decay rate starts slowing

Professional Insights:
- Exit at 21 DTE captures 75-80% of max profit
- Theta decay is fastest between 21-45 DTE
- After 21 DTE, theta decay slows and gamma risk increases
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class ThetaCurveService:
    """
    Service for analyzing theta decay curves and suggesting optimal exit timing.

    Key Concepts:
    - Theta Decay Rate: How fast theta is changing (second derivative)
    - Optimal Zone: When theta decay is fastest (typically 21-45 DTE)
    - Slowdown Threshold: When theta decay rate drops below threshold
    """

    # Theta decay zones based on DTE
    THETA_ZONES = [
        {"name": "early", "dte_min": 45, "dte_max": 90, "decay_rate": "slow", "action": "hold"},
        {"name": "optimal", "dte_min": 21, "dte_max": 45, "decay_rate": "fast", "action": "hold"},
        {"name": "exit_zone", "dte_min": 14, "dte_max": 21, "decay_rate": "slowing", "action": "consider_exit"},
        {"name": "expiry_week", "dte_min": 0, "dte_max": 14, "decay_rate": "slow", "action": "exit"}
    ]

    def __init__(self):
        """Initialize theta curve service"""
        pass

    def get_theta_zone(self, dte: int) -> Dict[str, Any]:
        """
        Get the current theta decay zone based on DTE.

        Args:
            dte: Days to expiry

        Returns:
            Zone information dict
        """
        for zone in self.THETA_ZONES:
            if zone['dte_min'] <= dte <= zone['dte_max']:
                return zone

        # If DTE > 90, return early zone
        if dte > 90:
            return {
                "name": "very_early",
                "dte_min": 90,
                "dte_max": 365,
                "decay_rate": "very_slow",
                "action": "wait"
            }

        # Default to expiry week
        return self.THETA_ZONES[-1]

    def calculate_theta_decay_rate(
        self,
        current_theta: float,
        previous_theta: float,
        time_delta_days: float = 1.0
    ) -> float:
        """
        Calculate theta decay rate (change in theta per day).

        Args:
            current_theta: Current net theta (negative value)
            previous_theta: Previous net theta (negative value)
            time_delta_days: Time elapsed in days

        Returns:
            Theta decay rate (positive = accelerating, negative = slowing)
        """
        if time_delta_days == 0:
            return 0.0

        # Theta values are typically negative (time decay reduces option value)
        # We want to know if theta is becoming more negative (accelerating)
        # or less negative (slowing)
        theta_change = current_theta - previous_theta
        decay_rate = theta_change / time_delta_days

        return decay_rate

    def should_exit_based_on_theta_curve(
        self,
        dte: int,
        current_theta: float,
        profit_captured_pct: float,
        theta_slowdown_threshold: float = 0.1
    ) -> Dict[str, Any]:
        """
        Determine if strategy should exit based on theta decay curve analysis.

        Args:
            dte: Days to expiry
            current_theta: Current net theta
            profit_captured_pct: Percentage of max profit already captured
            theta_slowdown_threshold: Threshold for theta slowdown detection

        Returns:
            Dict with exit recommendation
        """
        zone = self.get_theta_zone(dte)

        # Build recommendation
        recommendation = {
            "should_exit": False,
            "reason": "",
            "confidence": 0.0,
            "zone": zone['name'],
            "decay_rate": zone['decay_rate'],
            "suggested_action": zone['action']
        }

        # Exit Zone Logic (14-21 DTE)
        if zone['name'] == 'exit_zone':
            if profit_captured_pct >= 50:
                recommendation["should_exit"] = True
                recommendation["reason"] = (
                    f"In exit zone ({dte} DTE) with {profit_captured_pct:.1f}% profit captured. "
                    f"Theta decay slowing, recommend exit to lock in profit."
                )
                recommendation["confidence"] = 0.85
            else:
                recommendation["reason"] = (
                    f"In exit zone ({dte} DTE) but only {profit_captured_pct:.1f}% profit captured. "
                    f"Consider holding or exiting based on risk tolerance."
                )
                recommendation["confidence"] = 0.6

        # Expiry Week Logic (0-14 DTE)
        elif zone['name'] == 'expiry_week':
            recommendation["should_exit"] = True
            recommendation["reason"] = (
                f"Expiry week ({dte} DTE) - theta decay minimal, gamma risk high. "
                f"Recommend exit regardless of profit."
            )
            recommendation["confidence"] = 0.95

        # Optimal Zone Logic (21-45 DTE)
        elif zone['name'] == 'optimal':
            if profit_captured_pct >= 75:
                recommendation["should_exit"] = True
                recommendation["reason"] = (
                    f"In optimal theta zone ({dte} DTE) with {profit_captured_pct:.1f}% profit captured. "
                    f"Most of potential profit realized, recommend exit."
                )
                recommendation["confidence"] = 0.8
            else:
                recommendation["reason"] = (
                    f"In optimal theta zone ({dte} DTE) - theta decay is fastest. "
                    f"Hold position to capture more time decay."
                )
                recommendation["confidence"] = 0.7

        # Early Zone Logic (45-90 DTE)
        elif zone['name'] == 'early':
            recommendation["reason"] = (
                f"Early zone ({dte} DTE) - theta decay just beginning. "
                f"Too early to exit, hold position."
            )
            recommendation["confidence"] = 0.9

        # Very Early Zone (> 90 DTE)
        else:
            recommendation["reason"] = (
                f"Very early ({dte} DTE) - minimal theta decay. "
                f"Wait for position to mature."
            )
            recommendation["confidence"] = 0.95

        return recommendation

    def estimate_optimal_exit_dte(
        self,
        entry_dte: int,
        strategy_type: str = "iron_condor"
    ) -> Dict[str, Any]:
        """
        Estimate the optimal DTE to exit based on strategy type.

        Args:
            entry_dte: DTE when strategy was entered
            strategy_type: Type of strategy (iron_condor, strangle, etc.)

        Returns:
            Dict with optimal exit DTE and reasoning
        """
        # Default optimal exit points by strategy type
        exit_dte_map = {
            "iron_condor": 21,
            "short_strangle": 21,
            "credit_spread": 14,
            "iron_butterfly": 14,
            "naked_put": 30,
            "naked_call": 30,
            "covered_call": 7
        }

        optimal_exit_dte = exit_dte_map.get(strategy_type, 21)

        # If entry DTE is less than optimal, adjust
        if entry_dte < optimal_exit_dte:
            optimal_exit_dte = max(int(entry_dte * 0.5), 7)

        # Calculate expected profit capture at optimal exit
        if entry_dte >= 45:
            expected_profit_pct = 75  # 75-80% of max profit
        elif entry_dte >= 30:
            expected_profit_pct = 70
        elif entry_dte >= 21:
            expected_profit_pct = 60
        else:
            expected_profit_pct = 50

        return {
            "optimal_exit_dte": optimal_exit_dte,
            "expected_profit_captured_pct": expected_profit_pct,
            "reasoning": (
                f"For {strategy_type} entered at {entry_dte} DTE, "
                f"optimal exit is {optimal_exit_dte} DTE to capture "
                f"~{expected_profit_pct}% of max profit while avoiding gamma risk."
            )
        }

    def calculate_theta_efficiency(
        self,
        current_theta: float,
        dte: int,
        initial_theta: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate theta efficiency - how effectively position is capturing time decay.

        Args:
            current_theta: Current net theta
            dte: Days to expiry
            initial_theta: Initial theta when position was opened

        Returns:
            Dict with efficiency metrics
        """
        # Expected theta based on DTE (theoretical)
        # Theta should be highest around 21-30 DTE for ATM options
        if dte >= 45:
            expected_theta_multiplier = 0.5
        elif dte >= 30:
            expected_theta_multiplier = 0.7
        elif dte >= 21:
            expected_theta_multiplier = 1.0  # Peak theta
        elif dte >= 14:
            expected_theta_multiplier = 0.9
        elif dte >= 7:
            expected_theta_multiplier = 0.6
        else:
            expected_theta_multiplier = 0.3

        # Calculate efficiency
        if initial_theta is not None and initial_theta != 0:
            # Compare current theta to initial
            theta_ratio = current_theta / initial_theta
            efficiency = theta_ratio * 100
        else:
            # Use DTE-based expected value
            efficiency = expected_theta_multiplier * 100

        # Determine efficiency status
        if efficiency >= 90:
            status = "excellent"
            recommendation = "Theta decay is optimal, hold position"
        elif efficiency >= 70:
            status = "good"
            recommendation = "Theta decay is good, continue holding"
        elif efficiency >= 50:
            status = "moderate"
            recommendation = "Theta decay slowing, consider exit if profit target met"
        else:
            status = "poor"
            recommendation = "Theta decay minimal, recommend exit"

        return {
            "efficiency_pct": round(efficiency, 2),
            "status": status,
            "recommendation": recommendation,
            "expected_multiplier": expected_theta_multiplier,
            "dte": dte
        }

    def get_theta_curve_visualization(
        self,
        start_dte: int,
        end_dte: int = 0,
        step: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Generate theta curve data points for visualization.

        Args:
            start_dte: Starting DTE
            end_dte: Ending DTE (default 0)
            step: DTE step size

        Returns:
            List of data points for curve plotting
        """
        curve_data = []

        for dte in range(start_dte, end_dte - 1, -step):
            zone = self.get_theta_zone(dte)

            # Theoretical theta decay rate (normalized 0-100)
            if dte >= 45:
                decay_intensity = 30 + (dte - 45) * 0.2
            elif dte >= 21:
                decay_intensity = 50 + (45 - dte) * 1.5  # Accelerating
            elif dte >= 14:
                decay_intensity = 85 + (21 - dte) * 2
            elif dte >= 7:
                decay_intensity = 80 - (14 - dte) * 3  # Slowing
            else:
                decay_intensity = 50 - (7 - dte) * 5  # Rapid slowdown

            curve_data.append({
                "dte": dte,
                "decay_intensity": min(max(decay_intensity, 0), 100),
                "zone": zone['name'],
                "action": zone['action']
            })

        return curve_data


# Singleton instance
_theta_curve_service = None


def get_theta_curve_service() -> ThetaCurveService:
    """Get singleton instance of ThetaCurveService"""
    global _theta_curve_service
    if _theta_curve_service is None:
        _theta_curve_service = ThetaCurveService()
    return _theta_curve_service
