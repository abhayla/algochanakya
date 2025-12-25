"""
Strategy Recommendation Engine

Recommends option strategies based on market regime, user configuration, and strategy scoring.
"""

from typing import List, Optional, Dict, TYPE_CHECKING
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.strategy_templates import StrategyTemplate
from app.models.ai import AIUserConfig
from app.services.ai.market_regime import RegimeType

if TYPE_CHECKING:
    from app.schemas.ai import RegimeResponse, IndicatorsSnapshotResponse


# Strategy-Regime Scoring Matrix
# Maps regime types to strategy names with base confidence scores (0-100)
REGIME_STRATEGY_SCORES: Dict[RegimeType, Dict[str, float]] = {
    RegimeType.RANGEBOUND: {
        "iron_condor": 90.0,
        "short_strangle": 85.0,
        "iron_butterfly": 80.0,
        "short_straddle": 75.0,
        "butterfly_spread": 70.0,
    },
    RegimeType.TRENDING_BULLISH: {
        "bull_call_spread": 85.0,
        "bull_put_spread": 80.0,
        "call_ratio_backspread": 70.0,
        "long_call": 65.0,
        "short_put": 60.0,
    },
    RegimeType.TRENDING_BEARISH: {
        "bear_put_spread": 85.0,
        "bear_call_spread": 80.0,
        "put_ratio_backspread": 70.0,
        "long_put": 65.0,
        "short_call": 60.0,
    },
    RegimeType.VOLATILE: {
        "long_straddle": 80.0,
        "long_strangle": 75.0,
        "iron_butterfly": 70.0,  # Wide wings for safety
        "long_call": 60.0,
        "long_put": 60.0,
    },
    RegimeType.PRE_EVENT: {
        "iron_condor": 60.0,  # Far OTM only
        "butterfly_spread": 55.0,
    },
    RegimeType.EVENT_DAY: {
        # No new positions recommended on event days
    }
}


class StrategyRecommendation:
    """Single strategy recommendation with confidence score."""

    def __init__(
        self,
        template: StrategyTemplate,
        confidence: float,
        reasoning: str,
        regime_score: float,
        vix_adjustment: float = 0.0,
        trend_adjustment: float = 0.0,
    ):
        self.template = template
        self.confidence = min(100.0, max(0.0, confidence))  # Clamp to 0-100
        self.reasoning = reasoning
        self.regime_score = regime_score
        self.vix_adjustment = vix_adjustment
        self.trend_adjustment = trend_adjustment

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "template_id": str(self.template.id),
            "name": self.template.name,
            "display_name": self.template.display_name,
            "category": self.template.category,
            "confidence": round(self.confidence, 2),
            "reasoning": self.reasoning,
            "score_breakdown": {
                "regime_score": round(self.regime_score, 2),
                "vix_adjustment": round(self.vix_adjustment, 2),
                "trend_adjustment": round(self.trend_adjustment, 2),
            },
            "risk_level": self.template.risk_level,
            "market_outlook": self.template.market_outlook,
        }


class StrategyRecommender:
    """Recommends option strategies based on market conditions and user preferences."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_recommendations(
        self,
        underlying: str,
        regime: "RegimeResponse",
        user_config: AIUserConfig,
        top_n: int = 3
    ) -> List[StrategyRecommendation]:
        """
        Get top N strategy recommendations based on current market regime and user config.

        Args:
            underlying: Index symbol (NIFTY, BANKNIFTY, FINNIFTY)
            regime: Current market regime classification
            user_config: User's AI configuration
            top_n: Number of recommendations to return (default 3)

        Returns:
            List of StrategyRecommendation objects, sorted by confidence (highest first)
        """
        # Get all strategy templates
        result = await self.session.execute(select(StrategyTemplate))
        all_templates = result.scalars().all()

        if not all_templates:
            return []

        # Filter by user's allowed strategies if configured
        if user_config.allowed_strategies:
            # allowed_strategies is a JSONB array of template names
            allowed_names = user_config.allowed_strategies
            templates = [t for t in all_templates if t.name in allowed_names]
        else:
            templates = all_templates

        if not templates:
            return []

        # Score each strategy
        recommendations: List[StrategyRecommendation] = []

        for template in templates:
            score = await self.score_strategy(template, regime, user_config)

            if score >= user_config.min_confidence_to_trade:
                reasoning = self._generate_reasoning(template, regime, score)

                recommendation = StrategyRecommendation(
                    template=template,
                    confidence=score,
                    reasoning=reasoning,
                    regime_score=self._get_regime_base_score(template.name, regime.regime_type),
                )

                recommendations.append(recommendation)

        # Sort by confidence (descending) and return top N
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        return recommendations[:top_n]

    async def score_strategy(
        self,
        template: StrategyTemplate,
        regime: "RegimeResponse",
        user_config: AIUserConfig
    ) -> float:
        """
        Score a strategy's suitability for current market conditions.

        Args:
            template: Strategy template to score
            regime: Current market regime
            user_config: User configuration (for limit checks)

        Returns:
            Confidence score (0-100)
        """
        # Start with regime-based base score
        base_score = self._get_regime_base_score(template.name, regime.regime_type)

        if base_score == 0:
            return 0.0  # Strategy not suitable for this regime

        # Apply adjustments based on indicators
        vix_adjustment = self._calculate_vix_adjustment(template, regime.indicators.vix)
        trend_adjustment = self._calculate_trend_adjustment(template, regime.indicators)
        regime_confidence_factor = regime.confidence / 100.0  # Regime certainty

        # Calculate final score
        final_score = base_score + vix_adjustment + trend_adjustment

        # Apply regime confidence as a multiplier
        # If regime confidence is low, reduce strategy confidence
        final_score = final_score * (0.5 + (regime_confidence_factor * 0.5))

        # Clamp to 0-100
        return min(100.0, max(0.0, final_score))

    def _get_regime_base_score(self, strategy_name: str, regime_type: RegimeType) -> float:
        """Get base score for strategy-regime combination."""
        regime_scores = REGIME_STRATEGY_SCORES.get(regime_type, {})
        return regime_scores.get(strategy_name, 0.0)

    def _calculate_vix_adjustment(
        self,
        template: StrategyTemplate,
        vix: Optional[float]
    ) -> float:
        """
        Calculate VIX-based adjustment to strategy score.

        Returns adjustment in range [-15, +15]
        """
        if vix is None:
            return 0.0

        adjustment = 0.0

        # High IV strategies (sellers, theta strategies)
        if template.theta_positive:
            if vix > 20:  # High VIX favors theta strategies
                adjustment += 10.0
            elif vix < 12:  # Low VIX reduces theta opportunity
                adjustment -= 10.0

        # Low IV strategies (buyers, vega strategies)
        if template.vega_positive:
            if vix < 15:  # Low VIX favors buying (cheaper premiums)
                adjustment += 10.0
            elif vix > 25:  # High VIX makes buying expensive
                adjustment -= 10.0

        # Delta neutral strategies
        if template.delta_neutral:
            if 15 <= vix <= 22:  # Moderate VIX is ideal for neutral strategies
                adjustment += 5.0

        return adjustment

    def _calculate_trend_adjustment(
        self,
        template: StrategyTemplate,
        indicators: "IndicatorsSnapshotResponse"
    ) -> float:
        """
        Calculate trend-based adjustment using RSI and ADX.

        Returns adjustment in range [-10, +10]
        """
        if indicators.rsi_14 is None or indicators.adx_14 is None:
            return 0.0

        adjustment = 0.0
        rsi = indicators.rsi_14
        adx = indicators.adx_14

        # Directional strategies benefit from strong trends
        if template.market_outlook in ["bullish", "bearish"]:
            if adx > 25:  # Strong trend
                adjustment += 5.0
            elif adx < 20:  # Weak trend hurts directional plays
                adjustment -= 5.0

            # Check if RSI aligns with strategy outlook
            if template.market_outlook == "bullish" and rsi > 55:
                adjustment += 5.0
            elif template.market_outlook == "bearish" and rsi < 45:
                adjustment += 5.0

        # Neutral strategies benefit from weak trends
        if template.market_outlook == "neutral":
            if adx < 20:  # Weak trend
                adjustment += 5.0
            elif adx > 30:  # Strong trend hurts neutral strategies
                adjustment -= 5.0

        return adjustment

    def _generate_reasoning(
        self,
        template: StrategyTemplate,
        regime: "RegimeResponse",
        score: float
    ) -> str:
        """
        Generate human-readable reasoning for the recommendation.

        Args:
            template: Strategy template
            regime: Market regime
            score: Calculated confidence score

        Returns:
            Reasoning string
        """
        reasons = []

        # Regime match
        # Handle both RegimeType enum and string
        regime_name = regime.regime_type.value if hasattr(regime.regime_type, 'value') else regime.regime_type
        regime_name = regime_name.replace('_', ' ').title()
        reasons.append(f"Market is {regime_name}")

        # VIX-based reasoning
        if regime.indicators.vix:
            vix = regime.indicators.vix
            if template.theta_positive and vix > 20:
                reasons.append(f"High VIX ({vix:.1f}) favors premium selling")
            elif template.vega_positive and vix < 15:
                reasons.append(f"Low VIX ({vix:.1f}) offers cheap option buying")

        # Trend-based reasoning
        if regime.indicators.rsi_14 and regime.indicators.adx_14:
            rsi = regime.indicators.rsi_14
            adx = regime.indicators.adx_14

            if adx > 25:
                reasons.append(f"Strong trend (ADX {adx:.1f})")
            elif adx < 20:
                reasons.append(f"Weak trend (ADX {adx:.1f}) suits range-bound strategies")

        # Strategy characteristics
        if template.delta_neutral:
            reasons.append("Direction-neutral strategy")
        if template.theta_positive:
            reasons.append("Benefits from time decay")

        # Risk level
        reasons.append(f"{template.risk_level.capitalize()} risk")

        return ". ".join(reasons) + "."
