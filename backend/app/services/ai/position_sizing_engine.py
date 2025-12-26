"""
Position Sizing Engine

Unified position sizing service that combines:
- Fixed sizing
- Tiered (confidence-based) sizing
- Kelly Criterion sizing
- Drawdown dampening (Priority 1.2)
- Volatility scaling (Priority 1.2)

Final Formula:
    Final Lots = Base Lots × Confidence Multiplier × Drawdown Dampener × Volatility Scaler
"""

import logging
from typing import Dict, Optional
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIUserConfig
from app.services.ai.kelly_calculator import KellyCalculator
from app.services.ai.drawdown_tracker import DrawdownTracker
from app.constants.trading import get_lot_size

logger = logging.getLogger(__name__)


class SizingMode:
    """Position sizing modes"""
    FIXED = "fixed"       # Fixed lot size (base_lots)
    TIERED = "tiered"     # Confidence-based tiering
    KELLY = "kelly"       # Kelly Criterion (requires historical data)


class PositionSizingEngine:
    """
    Unified position sizing engine with drawdown and volatility dampening.

    Integrates all sizing modes and applies dynamic risk adjustments.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.kelly_calculator = KellyCalculator(db)
        self.drawdown_tracker = DrawdownTracker(db)

    async def calculate_position_size(
        self,
        user_id,
        confidence_score: float,
        underlying: str = "NIFTY",
        strategy_name: Optional[str] = None,
        capital: Optional[float] = None,
        max_loss_per_lot: Optional[float] = None
    ) -> Dict:
        """
        Calculate optimal position size considering all factors.

        Args:
            user_id: User ID
            confidence_score: AI confidence score (0-100)
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            strategy_name: Strategy name for Kelly calculation
            capital: Total capital (required for Kelly mode)
            max_loss_per_lot: Max expected loss per lot (required for Kelly mode)

        Returns:
            {
                "final_lots": int,
                "base_lots": int,
                "sizing_mode": str,
                "confidence_multiplier": float,
                "drawdown_dampener": float,
                "volatility_scaler": float,
                "breakdown": {
                    "base_lots": int,
                    "after_confidence": float,
                    "after_drawdown": float,
                    "after_volatility": int,
                    "final": int
                },
                "warnings": List[str],
                "disabled_reason": Optional[str]
            }
        """
        warnings = []

        # Get user configuration
        config = await self._get_user_config(user_id)

        if not config.ai_enabled:
            return {
                "final_lots": 0,
                "base_lots": 0,
                "sizing_mode": config.sizing_mode,
                "confidence_multiplier": 0.0,
                "drawdown_dampener": 1.0,
                "volatility_scaler": 1.0,
                "breakdown": {},
                "warnings": ["AI trading is disabled"],
                "disabled_reason": "AI_DISABLED"
            }

        # Step 1: Get base lots based on sizing mode
        base_lots_result = await self._calculate_base_lots(
            config=config,
            confidence_score=confidence_score,
            underlying=underlying,
            strategy_name=strategy_name,
            capital=capital,
            max_loss_per_lot=max_loss_per_lot
        )

        if base_lots_result["disabled"]:
            return {
                "final_lots": 0,
                "base_lots": 0,
                "sizing_mode": config.sizing_mode,
                "confidence_multiplier": base_lots_result.get("multiplier", 0.0),
                "drawdown_dampener": 1.0,
                "volatility_scaler": 1.0,
                "breakdown": {},
                "warnings": base_lots_result.get("warnings", []),
                "disabled_reason": base_lots_result.get("reason")
            }

        base_lots = base_lots_result["base_lots"]
        confidence_multiplier = base_lots_result.get("multiplier", 1.0)
        warnings.extend(base_lots_result.get("warnings", []))

        # Step 2: Apply confidence multiplier (for tiered mode)
        lots_after_confidence = base_lots * confidence_multiplier

        # Step 3: Apply drawdown dampening
        drawdown_dampener = 1.0
        if config.enable_drawdown_sizing:
            drawdown_metrics = await self.drawdown_tracker.calculate_drawdown(user_id)
            drawdown_dampener = drawdown_metrics["drawdown_multiplier"]

            if drawdown_metrics["drawdown_level"] != "NORMAL":
                warnings.append(
                    f"Drawdown dampening active: {drawdown_metrics['drawdown_level']} "
                    f"({drawdown_metrics['current_drawdown_pct']:.2f}%) - "
                    f"reducing size by {(1 - drawdown_dampener) * 100:.0f}%"
                )

        lots_after_drawdown = lots_after_confidence * drawdown_dampener

        # Step 4: Apply volatility scaling
        volatility_scaler = 1.0
        if config.enable_volatility_sizing:
            volatility_metrics = await self.drawdown_tracker.calculate_volatility(user_id)
            volatility_scaler = volatility_metrics["volatility_multiplier"]

            if volatility_metrics["volatility_level"] != "LOW":
                warnings.append(
                    f"Volatility scaling active: {volatility_metrics['volatility_level']} "
                    f"(σ={volatility_metrics['daily_pnl_volatility']:.2f}) - "
                    f"reducing size by {(1 - volatility_scaler) * 100:.0f}%"
                )

        lots_after_volatility = lots_after_drawdown * volatility_scaler

        # Step 5: Round to integer lots (always round down for safety)
        final_lots = int(lots_after_volatility)

        # Ensure at least 1 lot if base lots > 0
        if final_lots == 0 and base_lots > 0:
            final_lots = 1
            warnings.append("Rounded up to minimum 1 lot")

        logger.info(
            f"Position sizing for user {user_id}: "
            f"Base={base_lots}, Confidence={confidence_multiplier:.2f}, "
            f"Drawdown={drawdown_dampener:.2f}, Volatility={volatility_scaler:.2f}, "
            f"Final={final_lots} lots"
        )

        return {
            "final_lots": final_lots,
            "base_lots": base_lots,
            "sizing_mode": config.sizing_mode,
            "confidence_multiplier": confidence_multiplier,
            "drawdown_dampener": drawdown_dampener,
            "volatility_scaler": volatility_scaler,
            "breakdown": {
                "base_lots": base_lots,
                "after_confidence": lots_after_confidence,
                "after_drawdown": lots_after_drawdown,
                "after_volatility": lots_after_volatility,
                "final": final_lots
            },
            "warnings": warnings,
            "disabled_reason": None
        }

    async def should_skip_trade(
        self,
        user_id,
        confidence_score: float
    ) -> tuple[bool, str]:
        """
        Determine if a trade should be skipped due to:
        - Low confidence
        - Excessive drawdown
        - Other risk limits

        Returns:
            (should_skip: bool, reason: str)
        """
        config = await self._get_user_config(user_id)

        # Check confidence threshold
        if confidence_score < config.min_confidence_to_trade:
            return True, f"Confidence {confidence_score:.1f} below minimum {config.min_confidence_to_trade}"

        # Check drawdown limit
        if config.enable_drawdown_sizing:
            should_pause, reason = await self.drawdown_tracker.should_pause_trading(user_id)
            if should_pause:
                return True, reason

        return False, ""

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _get_user_config(self, user_id) -> AIUserConfig:
        """Get user AI configuration"""
        from sqlalchemy import select

        query = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await self.db.execute(query)
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"No AI configuration found for user {user_id}")

        return config

    async def _calculate_base_lots(
        self,
        config: AIUserConfig,
        confidence_score: float,
        underlying: str,
        strategy_name: Optional[str],
        capital: Optional[float],
        max_loss_per_lot: Optional[float]
    ) -> Dict:
        """
        Calculate base lots based on sizing mode.

        Returns:
            {
                "base_lots": int,
                "multiplier": float,  # For tiered mode
                "warnings": List[str],
                "disabled": bool,
                "reason": Optional[str]
            }
        """
        warnings = []

        # FIXED MODE: Simple base lots
        if config.sizing_mode == SizingMode.FIXED:
            return {
                "base_lots": config.base_lots,
                "multiplier": 1.0,
                "warnings": [],
                "disabled": False,
                "reason": None
            }

        # TIERED MODE: Confidence-based multiplier
        elif config.sizing_mode == SizingMode.TIERED:
            tier = self._get_confidence_tier(confidence_score, config.confidence_tiers)

            if tier["multiplier"] == 0:
                return {
                    "base_lots": 0,
                    "multiplier": 0.0,
                    "warnings": [f"Confidence {confidence_score:.1f} in SKIP tier"],
                    "disabled": True,
                    "reason": "LOW_CONFIDENCE"
                }

            base_lots = int(config.base_lots * tier["multiplier"])

            return {
                "base_lots": base_lots,
                "multiplier": tier["multiplier"],
                "warnings": [f"Tiered sizing: {tier['name']} (multiplier={tier['multiplier']})"],
                "disabled": False,
                "reason": None
            }

        # KELLY MODE: Historical performance-based
        elif config.sizing_mode == SizingMode.KELLY:
            if capital is None or max_loss_per_lot is None:
                warnings.append("Kelly mode requires capital and max_loss_per_lot - falling back to fixed")
                return {
                    "base_lots": config.base_lots,
                    "multiplier": 1.0,
                    "warnings": warnings,
                    "disabled": False,
                    "reason": None
                }

            kelly_result = await self.kelly_calculator.get_kelly_recommendation(
                user_id=config.user_id,
                capital=capital,
                max_loss_per_lot=max_loss_per_lot,
                underlying=underlying,
                strategy_name=strategy_name,
                lookback_days=90
            )

            if not kelly_result["enabled"]:
                warnings.append(f"Kelly: {kelly_result['recommendation']} - falling back to fixed")
                warnings.extend(kelly_result["warnings"])

                return {
                    "base_lots": config.base_lots,
                    "multiplier": 1.0,
                    "warnings": warnings,
                    "disabled": False,
                    "reason": None
                }

            warnings.append(
                f"Kelly sizing: {kelly_result['recommendation']} "
                f"(fraction={kelly_result['kelly_fraction']:.4f})"
            )
            warnings.extend(kelly_result["warnings"])

            return {
                "base_lots": kelly_result["optimal_lots"],
                "multiplier": 1.0,
                "warnings": warnings,
                "disabled": False,
                "reason": None
            }

        else:
            # Unknown mode - default to fixed
            warnings.append(f"Unknown sizing mode '{config.sizing_mode}' - using fixed")
            return {
                "base_lots": config.base_lots,
                "multiplier": 1.0,
                "warnings": warnings,
                "disabled": False,
                "reason": None
            }

    def _get_confidence_tier(
        self,
        confidence_score: float,
        tiers: list
    ) -> Dict:
        """Get confidence tier for given score"""
        for tier in tiers:
            if tier["min"] <= confidence_score < tier["max"]:
                return tier

        # Default to SKIP if no tier matches
        return {
            "name": "SKIP",
            "min": 0,
            "max": 100,
            "multiplier": 0
        }


__all__ = ["PositionSizingEngine", "SizingMode"]
