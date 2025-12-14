"""
DTE Zone Service - Phase 5E Features #30, #31, #32, #34

Manage DTE-aware thresholds and adjustment restrictions.

DTE Zones (based on professional trading practices):
- Early Zone (21-45 DTE): Optimal entry zone, relaxed thresholds
- Middle Zone (14-21 DTE): Standard thresholds
- Late Zone (7-14 DTE): Tighter thresholds, limited adjustments
- Expiry Week (0-7 DTE): Very tight thresholds, exit preferred over adjustment

Key Principle:
As DTE decreases, risk increases exponentially. Thresholds must tighten,
and available actions must be restricted to prevent catastrophic losses.
"""
import logging
from datetime import datetime, date, timezone
from typing import Dict, Any, Optional, List, Literal
from enum import Enum

logger = logging.getLogger(__name__)


class DTEZone(str, Enum):
    """DTE zone classifications."""
    EARLY = "early"
    MIDDLE = "middle"
    LATE = "late"
    EXPIRY_WEEK = "expiry_week"


class DTEZoneService:
    """
    Service for managing DTE-aware thresholds and adjustment restrictions.

    As options approach expiry, gamma risk increases and adjustments become
    less effective. This service provides dynamic thresholds and action
    restrictions based on the current DTE zone.
    """

    # DTE zone boundaries (days)
    ZONE_BOUNDARIES = {
        DTEZone.EARLY: {"min": 21, "max": 45},
        DTEZone.MIDDLE: {"min": 14, "max": 21},
        DTEZone.LATE: {"min": 7, "max": 14},
        DTEZone.EXPIRY_WEEK: {"min": 0, "max": 7}
    }

    # Base delta warning thresholds by zone
    DELTA_THRESHOLDS = {
        DTEZone.EARLY: 0.35,
        DTEZone.MIDDLE: 0.30,
        DTEZone.LATE: 0.25,
        DTEZone.EXPIRY_WEEK: 0.20
    }

    # Allowed adjustment actions by zone
    ALLOWED_ACTIONS = {
        DTEZone.EARLY: ["roll_strike", "roll_expiry", "add_hedge", "close_leg", "shift_strike", "break_trade", "scale_down"],
        DTEZone.MIDDLE: ["roll_strike", "roll_expiry", "add_hedge", "close_leg", "shift_strike", "scale_down"],
        DTEZone.LATE: ["roll_expiry", "add_hedge", "close_leg", "scale_down"],  # No strike rolls in late zone
        DTEZone.EXPIRY_WEEK: ["close_leg", "exit_all"]  # Only exit actions allowed
    }

    def __init__(self):
        pass

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

    def get_dte_zone(self, dte: int) -> DTEZone:
        """
        Determine DTE zone based on days to expiry.

        Args:
            dte: Days to expiry

        Returns:
            DTEZone enum value
        """
        if dte >= 21:
            return DTEZone.EARLY
        elif dte >= 14:
            return DTEZone.MIDDLE
        elif dte >= 7:
            return DTEZone.LATE
        else:
            return DTEZone.EXPIRY_WEEK

    def get_zone_config(self, dte: int) -> Dict[str, Any]:
        """
        Get complete configuration for current DTE zone.

        Returns all thresholds, allowed actions, and warnings for the zone.

        Args:
            dte: Days to expiry

        Returns:
            Dict with zone configuration
        """
        zone = self.get_dte_zone(dte)

        config = {
            "zone": zone.value,
            "dte": dte,
            "delta_warning": self.DELTA_THRESHOLDS[zone],
            "allowed_actions": self.ALLOWED_ACTIONS[zone],
            "adjustment_effectiveness": self._get_adjustment_effectiveness(zone),
            "warnings": self._get_zone_warnings(zone, dte),
            "display": self._get_display_config(zone, dte)
        }

        return config

    def get_dynamic_delta_threshold(
        self,
        dte: int,
        base_threshold: Optional[float] = None
    ) -> float:
        """
        Get delta warning threshold adjusted for DTE.

        If base_threshold is provided, it will be scaled based on the zone.
        Otherwise, uses zone-specific threshold.

        Args:
            dte: Days to expiry
            base_threshold: Optional base threshold to scale

        Returns:
            Adjusted delta threshold
        """
        zone = self.get_dte_zone(dte)
        zone_threshold = self.DELTA_THRESHOLDS[zone]

        if base_threshold is not None:
            # Scale the provided threshold based on zone
            scaling_factor = zone_threshold / self.DELTA_THRESHOLDS[DTEZone.EARLY]
            return base_threshold * scaling_factor
        else:
            return zone_threshold

    def is_action_allowed(self, dte: int, action_type: str) -> tuple[bool, Optional[str]]:
        """
        Check if an adjustment action is allowed in current DTE zone.

        Args:
            dte: Days to expiry
            action_type: Type of adjustment action

        Returns:
            Tuple of (is_allowed: bool, reason: Optional[str])
        """
        zone = self.get_dte_zone(dte)
        allowed_actions = self.ALLOWED_ACTIONS[zone]

        if action_type in allowed_actions:
            return (True, None)
        else:
            if zone == DTEZone.EXPIRY_WEEK:
                reason = f"Action '{action_type}' not allowed in expiry week (DTE={dte}). Only exit actions permitted."
            elif zone == DTEZone.LATE:
                reason = f"Action '{action_type}' not allowed in late zone (DTE={dte}). Risk too high for complex adjustments."
            else:
                reason = f"Action '{action_type}' not allowed in {zone.value} zone (DTE={dte})."

            return (False, reason)

    def should_exit_instead_of_adjust(self, dte: int) -> tuple[bool, str]:
        """
        Determine if exit is preferred over adjustment based on DTE.

        Args:
            dte: Days to expiry

        Returns:
            Tuple of (should_exit: bool, reason: str)
        """
        zone = self.get_dte_zone(dte)

        if zone == DTEZone.EXPIRY_WEEK:
            return (
                True,
                f"Expiry week (DTE={dte}): Adjustments ineffective. Exit recommended to avoid gamma risk."
            )
        elif zone == DTEZone.LATE and dte <= 7:
            return (
                True,
                f"Near expiry (DTE={dte}): High gamma risk. Consider exit over adjustment."
            )
        else:
            return (False, "")

    def _get_adjustment_effectiveness(self, zone: DTEZone) -> Dict[str, Any]:
        """
        Get adjustment effectiveness rating for the zone.

        Returns:
            Dict with effectiveness metrics
        """
        effectiveness_map = {
            DTEZone.EARLY: {
                "rating": "high",
                "percentage": 90,
                "description": "Adjustments highly effective. Plenty of time for position to work."
            },
            DTEZone.MIDDLE: {
                "rating": "medium",
                "percentage": 70,
                "description": "Adjustments moderately effective. Monitor closely."
            },
            DTEZone.LATE: {
                "rating": "low",
                "percentage": 40,
                "description": "Adjustments less effective. Gamma risk increasing."
            },
            DTEZone.EXPIRY_WEEK: {
                "rating": "very_low",
                "percentage": 10,
                "description": "Adjustments ineffective. Exit preferred over adjustment."
            }
        }
        return effectiveness_map[zone]

    def _get_zone_warnings(self, zone: DTEZone, dte: int) -> List[str]:
        """
        Get warnings specific to the DTE zone.

        Args:
            zone: DTE zone
            dte: Days to expiry

        Returns:
            List of warning messages
        """
        warnings = []

        if zone == DTEZone.EXPIRY_WEEK:
            warnings.append(f"CRITICAL: Expiry in {dte} days. Gamma explosion risk.")
            warnings.append("Adjustments ineffective. Consider exiting position.")
            if dte <= 3:
                warnings.append("URGENT: Exit recommended within 24 hours.")

        elif zone == DTEZone.LATE:
            warnings.append(f"WARNING: {dte} DTE. Gamma risk increasing.")
            warnings.append("Complex adjustments not recommended.")
            warnings.append("Consider rolling to next expiry if maintaining position.")

        elif zone == DTEZone.MIDDLE:
            if dte <= 16:
                warnings.append(f"NOTICE: {dte} DTE. Monitor position closely.")
                warnings.append("Prepare exit strategy if position moves against you.")

        return warnings

    def _get_display_config(self, zone: DTEZone, dte: int) -> Dict[str, str]:
        """
        Get display configuration for UI components.

        Args:
            zone: DTE zone
            dte: Days to expiry

        Returns:
            Dict with display settings (color, icon, label)
        """
        display_map = {
            DTEZone.EARLY: {
                "color": "green",
                "icon": "check-circle",
                "label": f"Early Zone ({dte} DTE)",
                "badge_variant": "success"
            },
            DTEZone.MIDDLE: {
                "color": "blue",
                "icon": "info-circle",
                "label": f"Middle Zone ({dte} DTE)",
                "badge_variant": "info"
            },
            DTEZone.LATE: {
                "color": "yellow",
                "icon": "exclamation-triangle",
                "label": f"Late Zone ({dte} DTE)",
                "badge_variant": "warning"
            },
            DTEZone.EXPIRY_WEEK: {
                "color": "red",
                "icon": "exclamation-circle",
                "label": f"Expiry Week ({dte} DTE)",
                "badge_variant": "danger"
            }
        }
        return display_map[zone]

    def get_optimal_entry_dte(self) -> Dict[str, Any]:
        """
        Get recommended DTE range for new entries.

        Based on research: Optimal entry at 30-45 DTE.

        Returns:
            Dict with optimal entry DTE info
        """
        return {
            "min_dte": 30,
            "max_dte": 45,
            "optimal_dte": 35,
            "reason": "30-45 DTE provides optimal balance of premium and time value"
        }


# Singleton instance
_dte_zone_service = None


def get_dte_zone_service() -> DTEZoneService:
    """Get singleton instance of DTEZoneService."""
    global _dte_zone_service
    if _dte_zone_service is None:
        _dte_zone_service = DTEZoneService()
    return _dte_zone_service
