"""
Delta Band Service

Monitors net delta and maintains position within configured bands.
Suggests rebalancing actions when delta exceeds thresholds.
Phase 5B Feature #49.

Delta Bands Example:
- Band: ±0.15
- If net delta > 0.15 (too bullish) → Shift CE closer or add PE
- If net delta < -0.15 (too bearish) → Shift PE closer or add CE
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass

from app.services.legacy.market_data import MarketDataService

logger = logging.getLogger(__name__)


@dataclass
class DeltaBandStatus:
    """Status of delta band monitoring."""
    net_delta: float
    band_threshold: float
    out_of_band: bool
    severity: str  # "ok", "warning", "critical"
    suggested_action: Optional[str] = None
    alternative_action: Optional[str] = None


@dataclass
class RebalanceSuggestion:
    """Suggested rebalancing action."""
    action_type: str  # "shift_leg", "add_hedge", "exit_leg", "no_action"
    leg_id: Optional[str] = None
    description: str = ""
    expected_delta_change: float = 0.0
    confidence: float = 0.0  # 0-1


class DeltaBandService:
    """
    Monitor and maintain delta within configurable bands.

    Implements delta band monitoring with automatic rebalance suggestions.
    """

    # Default delta band threshold (±0.15 is common for neutral strategies)
    DEFAULT_BAND_THRESHOLD = 0.15

    # Cooldown period between rebalance suggestions (minutes)
    REBALANCE_COOLDOWN = 30

    def __init__(self, market_data: MarketDataService):
        self.market_data = market_data
        self._last_rebalance_suggestion: Dict[int, datetime] = {}

    async def check_delta_band(
        self,
        strategy_id: int,
        net_delta: float,
        band_threshold: Optional[float] = None,
        leg_greeks: Optional[List[Dict]] = None
    ) -> DeltaBandStatus:
        """
        Check if delta is within allowed band.

        Args:
            strategy_id: Strategy ID
            net_delta: Current net delta of position
            band_threshold: Custom threshold (defaults to 0.15)
            leg_greeks: Optional list of individual leg Greeks for rebalance suggestions

        Returns:
            DeltaBandStatus with out_of_band flag and suggestions
        """
        threshold = band_threshold or self.DEFAULT_BAND_THRESHOLD
        abs_delta = abs(net_delta)

        # Determine severity
        if abs_delta <= threshold:
            severity = "ok"
            out_of_band = False
        elif abs_delta <= threshold * 1.5:
            severity = "warning"
            out_of_band = True
        else:
            severity = "critical"
            out_of_band = True

        # Generate suggestion if out of band
        suggested_action = None
        alternative_action = None

        if out_of_band:
            # Check cooldown
            if self._is_in_cooldown(strategy_id):
                logger.debug(f"Strategy {strategy_id} in rebalance cooldown")
            else:
                suggested_action, alternative_action = await self._suggest_rebalance(
                    net_delta=net_delta,
                    threshold=threshold,
                    leg_greeks=leg_greeks
                )
                self._last_rebalance_suggestion[strategy_id] = datetime.now()

        return DeltaBandStatus(
            net_delta=net_delta,
            band_threshold=threshold,
            out_of_band=out_of_band,
            severity=severity,
            suggested_action=suggested_action,
            alternative_action=alternative_action
        )

    async def _suggest_rebalance(
        self,
        net_delta: float,
        threshold: float,
        leg_greeks: Optional[List[Dict]] = None
    ) -> Tuple[str, str]:
        """
        Suggest rebalancing action based on delta deviation.

        Returns:
            Tuple of (primary_suggestion, alternative_suggestion)
        """
        if net_delta > threshold:
            # Too bullish - reduce delta
            primary = f"Shift CALL closer to ATM (current delta: {net_delta:+.3f}, target: ±{threshold:.3f})"
            alternative = "Add PUT hedge to reduce delta"

        elif net_delta < -threshold:
            # Too bearish - reduce negative delta
            primary = f"Shift PUT closer to ATM (current delta: {net_delta:+.3f}, target: ±{threshold:.3f})"
            alternative = "Add CALL hedge to reduce negative delta"

        else:
            primary = "Delta within band - no action needed"
            alternative = None

        return primary, alternative

    def get_rebalance_actions(
        self,
        net_delta: float,
        leg_greeks: List[Dict],
        threshold: float
    ) -> List[RebalanceSuggestion]:
        """
        Generate detailed rebalance action suggestions.

        Args:
            net_delta: Current net delta
            leg_greeks: List of leg Greeks with delta per leg
            threshold: Band threshold

        Returns:
            List of RebalanceSuggestion objects ranked by effectiveness
        """
        suggestions = []
        delta_excess = abs(net_delta) - threshold

        if delta_excess <= 0:
            return [RebalanceSuggestion(
                action_type="no_action",
                description="Delta within acceptable band",
                confidence=1.0
            )]

        # Analyze legs to find best rebalance targets
        if net_delta > 0:
            # Too bullish - find CE legs to shift closer
            ce_legs = [lg for lg in leg_greeks if lg.get('contract_type') == 'CE']
            for leg in ce_legs:
                leg_delta = abs(float(leg.get('delta', 0)))
                if leg_delta < 0.20:  # Low delta CE can be shifted closer
                    suggestions.append(RebalanceSuggestion(
                        action_type="shift_leg",
                        leg_id=leg.get('leg_id'),
                        description=f"Shift {leg.get('strike')} CE closer to ATM (current delta: {leg_delta:.3f})",
                        expected_delta_change=-0.10,  # Approximate
                        confidence=0.8
                    ))

            # Alternative: Add PUT hedge
            suggestions.append(RebalanceSuggestion(
                action_type="add_hedge",
                description=f"Buy PUT to reduce {delta_excess:.3f} delta exposure",
                expected_delta_change=-delta_excess,
                confidence=0.7
            ))

        else:
            # Too bearish - find PE legs to shift closer
            pe_legs = [lg for lg in leg_greeks if lg.get('contract_type') == 'PE']
            for leg in pe_legs:
                leg_delta = abs(float(leg.get('delta', 0)))
                if leg_delta < 0.20:  # Low delta PE can be shifted closer
                    suggestions.append(RebalanceSuggestion(
                        action_type="shift_leg",
                        leg_id=leg.get('leg_id'),
                        description=f"Shift {leg.get('strike')} PE closer to ATM (current delta: {leg_delta:.3f})",
                        expected_delta_change=+0.10,
                        confidence=0.8
                    ))

            # Alternative: Add CALL hedge
            suggestions.append(RebalanceSuggestion(
                action_type="add_hedge",
                description=f"Buy CALL to reduce {abs(delta_excess):.3f} delta exposure",
                expected_delta_change=abs(delta_excess),
                confidence=0.7
            ))

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions

    def _is_in_cooldown(self, strategy_id: int) -> bool:
        """Check if strategy is in rebalance cooldown period."""
        last_suggestion = self._last_rebalance_suggestion.get(strategy_id)
        if not last_suggestion:
            return False

        cooldown_end = last_suggestion + timedelta(minutes=self.REBALANCE_COOLDOWN)
        return datetime.now() < cooldown_end

    def get_delta_band_config(self, strategy_config: Dict) -> float:
        """
        Extract delta band threshold from strategy configuration.

        Args:
            strategy_config: Strategy configuration dict

        Returns:
            Delta band threshold (default 0.15)
        """
        # Check if strategy has custom delta band setting
        delta_band_threshold = strategy_config.get('delta_band_threshold')

        if delta_band_threshold:
            try:
                threshold = float(delta_band_threshold)
                # Validate range (0.05 to 0.30 is reasonable)
                if 0.05 <= threshold <= 0.30:
                    return threshold
                logger.warning(f"Delta band threshold {threshold} out of range, using default")
            except (ValueError, TypeError):
                logger.warning("Invalid delta band threshold, using default")

        return self.DEFAULT_BAND_THRESHOLD

    def calculate_target_delta(self, band_threshold: float = None) -> float:
        """
        Calculate target delta for neutral strategies.

        For delta-neutral strategies, target is 0.
        Some traders prefer slight bullish bias (e.g., +0.05).

        Args:
            band_threshold: Band threshold (informational)

        Returns:
            Target delta (0.0 for neutral)
        """
        return 0.0  # Delta-neutral target


# Service instance cache
_delta_band_services: Dict[str, DeltaBandService] = {}


def get_delta_band_service(market_data: MarketDataService) -> DeltaBandService:
    """Get or create DeltaBandService instance."""
    token_key = market_data.kite.access_token or "default"

    if token_key not in _delta_band_services:
        _delta_band_services[token_key] = DeltaBandService(market_data)

    return _delta_band_services[token_key]


def clear_delta_band_services():
    """Clear all cached service instances."""
    global _delta_band_services
    _delta_band_services.clear()
