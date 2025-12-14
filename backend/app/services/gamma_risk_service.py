"""
Gamma Risk Service - Phase 5E Feature #26, #35

Detect and warn about gamma explosion risk near expiry.

Key Insights from Research:
- Weekly options at 7 DTE have gamma that's 2x monthly options
- After a 2% move at 7 DTE, gamma can explode from -4 to 62
- Professional rule: Never hold short options through expiry week (DTE < 7)

Gamma Zones:
- Safe Zone: DTE > 7 (normal gamma behavior)
- Warning Zone: 4-7 DTE (gamma acceleration starts)
- Danger Zone: 0-3 DTE (gamma explosion risk)

This service helps prevent catastrophic losses from gamma risk near expiry.
"""
import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional, Literal
from decimal import Decimal

logger = logging.getLogger(__name__)

# Gamma risk zones
GAMMA_ZONE_SAFE = "safe"
GAMMA_ZONE_WARNING = "warning"
GAMMA_ZONE_DANGER = "danger"

# DTE thresholds
DTE_WARNING_THRESHOLD = 7  # Start warning at 7 DTE
DTE_DANGER_THRESHOLD = 3   # Critical zone at 3 DTE

# Gamma multipliers (research-based)
GAMMA_WEEKLY_MULTIPLIER = 2.0  # Weekly options have 2x gamma of monthlies
GAMMA_EXPLOSION_THRESHOLD = 10.0  # Gamma explosion if 10x initial gamma


class GammaRiskService:
    """
    Service for detecting and managing gamma explosion risk near expiry.

    Gamma risk increases exponentially as options approach expiry, especially
    for short positions. This service helps traders avoid catastrophic losses
    by providing timely warnings and risk assessments.
    """

    def __init__(self):
        self.warning_dte = DTE_WARNING_THRESHOLD
        self.danger_dte = DTE_DANGER_THRESHOLD

    def calculate_dte(self, expiry: date, current_date: Optional[date] = None) -> int:
        """
        Calculate Days To Expiry (DTE).

        Args:
            expiry: Expiry date
            current_date: Current date (defaults to today)

        Returns:
            Number of days until expiry
        """
        if current_date is None:
            current_date = datetime.now(timezone.utc).date()

        delta = expiry - current_date
        return max(0, delta.days)

    def get_gamma_zone(self, dte: int) -> Literal["safe", "warning", "danger"]:
        """
        Determine gamma risk zone based on DTE.

        Zones:
        - safe: DTE > 7 (normal gamma behavior)
        - warning: 4-7 DTE (gamma acceleration starts)
        - danger: 0-3 DTE (gamma explosion risk)

        Args:
            dte: Days to expiry

        Returns:
            Gamma zone identifier
        """
        if dte <= self.danger_dte:
            return GAMMA_ZONE_DANGER
        elif dte <= self.warning_dte:
            return GAMMA_ZONE_WARNING
        else:
            return GAMMA_ZONE_SAFE

    def assess_gamma_risk(
        self,
        dte: int,
        net_gamma: float,
        position_type: str = "short"
    ) -> Dict[str, Any]:
        """
        Assess gamma explosion risk for a position.

        Args:
            dte: Days to expiry
            net_gamma: Net position gamma (negative for short positions)
            position_type: "short" or "long"

        Returns:
            Dict with risk assessment:
            {
                "zone": "safe|warning|danger",
                "risk_level": "low|medium|high|critical",
                "multiplier": float,
                "recommendation": str,
                "dte": int
            }
        """
        zone = self.get_gamma_zone(dte)

        # Calculate gamma multiplier (how much gamma increases near expiry)
        if dte <= 1:
            multiplier = 20.0  # Extreme gamma at 0-1 DTE
        elif dte <= 3:
            multiplier = 10.0  # High gamma at 2-3 DTE
        elif dte <= 7:
            multiplier = 3.0   # Moderate gamma at 4-7 DTE
        else:
            multiplier = 1.0   # Normal gamma

        # Determine risk level
        if zone == GAMMA_ZONE_DANGER:
            risk_level = "critical"
            recommendation = "URGENT: Exit position immediately to avoid gamma explosion"
        elif zone == GAMMA_ZONE_WARNING:
            if position_type == "short":
                risk_level = "high"
                recommendation = "Consider exiting position. Adjustments become ineffective."
            else:
                risk_level = "medium"
                recommendation = "Monitor closely. Gamma risk increasing."
        else:
            risk_level = "low"
            recommendation = "Normal gamma behavior. Safe to hold."

        # For short positions, gamma risk is more severe
        if position_type == "short" and abs(net_gamma) > 0.05:
            if zone == GAMMA_ZONE_WARNING:
                risk_level = "high"
            elif zone == GAMMA_ZONE_DANGER:
                risk_level = "critical"

        return {
            "zone": zone,
            "risk_level": risk_level,
            "multiplier": multiplier,
            "recommendation": recommendation,
            "dte": dte,
            "net_gamma": net_gamma,
            "position_type": position_type
        }

    def should_exit_for_gamma_risk(
        self,
        dte: int,
        net_gamma: float,
        position_type: str = "short"
    ) -> tuple[bool, str]:
        """
        Determine if position should be exited due to gamma risk.

        Args:
            dte: Days to expiry
            net_gamma: Net position gamma
            position_type: "short" or "long"

        Returns:
            Tuple of (should_exit: bool, reason: str)
        """
        assessment = self.assess_gamma_risk(dte, net_gamma, position_type)

        # Force exit in danger zone for short positions
        if assessment["zone"] == GAMMA_ZONE_DANGER and position_type == "short":
            return (
                True,
                f"Gamma explosion risk: {dte} DTE (danger zone). "
                f"Gamma multiplier: {assessment['multiplier']:.1f}x"
            )

        # Suggest exit in warning zone for high gamma short positions
        if assessment["zone"] == GAMMA_ZONE_WARNING and position_type == "short":
            if abs(net_gamma) > 0.03:  # High gamma threshold
                return (
                    True,
                    f"High gamma risk: {dte} DTE (warning zone). "
                    f"Net gamma: {net_gamma:.3f}"
                )

        return (False, "")

    def get_gamma_zone_config(self, dte: int) -> Dict[str, Any]:
        """
        Get configuration and thresholds for current gamma zone.

        Returns configuration that can be used to adjust other risk parameters
        based on the current gamma zone.

        Args:
            dte: Days to expiry

        Returns:
            Dict with zone configuration:
            {
                "zone": str,
                "delta_warning": float,
                "adjustment_allowed": bool,
                "suggested_action": str,
                "description": str
            }
        """
        zone = self.get_gamma_zone(dte)

        if zone == GAMMA_ZONE_DANGER:
            return {
                "zone": zone,
                "delta_warning": 0.15,  # Tighter delta threshold
                "adjustment_allowed": False,
                "suggested_action": "exit",
                "description": "Danger Zone (0-3 DTE): Gamma explosion risk. Exit recommended.",
                "color": "red"
            }
        elif zone == GAMMA_ZONE_WARNING:
            return {
                "zone": zone,
                "delta_warning": 0.20,
                "adjustment_allowed": True,  # But not recommended
                "suggested_action": "exit_or_roll",
                "description": "Warning Zone (4-7 DTE): Gamma accelerating. Consider exit.",
                "color": "yellow"
            }
        else:
            return {
                "zone": zone,
                "delta_warning": 0.30,
                "adjustment_allowed": True,
                "suggested_action": "adjust_or_hold",
                "description": f"Safe Zone ({dte} DTE): Normal gamma behavior.",
                "color": "green"
            }

    def calculate_gamma_explosion_probability(
        self,
        dte: int,
        net_gamma: float,
        volatility: float = 0.20
    ) -> float:
        """
        Calculate probability of gamma explosion based on DTE and current gamma.

        This is a heuristic calculation based on professional trading rules.

        Args:
            dte: Days to expiry
            net_gamma: Net position gamma
            volatility: Implied volatility (0-1)

        Returns:
            Probability (0-1) of gamma explosion
        """
        # Base probability by zone
        zone = self.get_gamma_zone(dte)

        if zone == GAMMA_ZONE_DANGER:
            base_prob = 0.80  # 80% chance of issues in danger zone
        elif zone == GAMMA_ZONE_WARNING:
            base_prob = 0.40  # 40% chance in warning zone
        else:
            base_prob = 0.05  # 5% base risk

        # Adjust for gamma magnitude
        gamma_adjustment = min(abs(net_gamma) * 5, 0.2)  # Up to +20%

        # Adjust for volatility (higher vol = higher risk)
        vol_adjustment = max(0, (volatility - 0.15) * 0.5)  # +0 to +10%

        probability = min(1.0, base_prob + gamma_adjustment + vol_adjustment)

        return probability


# Singleton instance
_gamma_risk_service = None


def get_gamma_risk_service() -> GammaRiskService:
    """Get singleton instance of GammaRiskService."""
    global _gamma_risk_service
    if _gamma_risk_service is None:
        _gamma_risk_service = GammaRiskService()
    return _gamma_risk_service
