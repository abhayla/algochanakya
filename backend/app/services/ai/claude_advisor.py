"""
Claude AI Advisor Service

Provides AI-powered explanations, insights, and recommendations using Anthropic's Claude API.

Features:
- Strategy explanation and education
- Market analysis and regime interpretation
- Position review and suggestions
- Risk assessment and warnings
- Natural language Q&A about options trading
"""

import anthropic
from typing import Optional, Dict, List, TYPE_CHECKING
from datetime import datetime

from app.config import settings
from app.services.ai.strategy_recommender import StrategyRecommendation

if TYPE_CHECKING:
    from app.schemas.ai import RegimeResponse


class ClaudeAdvisor:
    """
    AI-powered trading advisor using Claude.

    Provides natural language explanations, insights, and educational content
    about option strategies, market conditions, and trading decisions.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = "claude-sonnet-4-5-20250929"  # Latest Claude Sonnet
        self.max_tokens = 1024

    async def explain_recommendation(
        self,
        recommendation: StrategyRecommendation,
        regime: "RegimeResponse",
        user_context: Optional[Dict] = None
    ) -> str:
        """
        Generate a detailed explanation for why a strategy is recommended.

        Args:
            recommendation: The strategy recommendation
            regime: Current market regime
            user_context: Optional user-specific context (risk tolerance, capital, etc.)

        Returns:
            Natural language explanation
        """
        prompt = self._build_recommendation_prompt(recommendation, regime, user_context)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            return response.content[0].text
        except Exception as e:
            return f"Unable to generate explanation: {str(e)}"

    async def analyze_market_conditions(
        self,
        regime: "RegimeResponse",
        underlying: str
    ) -> str:
        """
        Provide market analysis based on current regime and indicators.

        Args:
            regime: Current market regime classification
            underlying: Index name (NIFTY, BANKNIFTY, etc.)

        Returns:
            Market analysis and outlook
        """
        prompt = f"""You are an expert options trader analyzing market conditions for {underlying}.

Current Market Regime: {regime.regime_type.value if hasattr(regime.regime_type, 'value') else regime.regime_type}
Confidence: {regime.confidence}%

Technical Indicators:
- Spot Price: {regime.indicators.spot_price}
- VIX: {regime.indicators.vix}
- RSI (14): {regime.indicators.rsi_14}
- ADX (14): {regime.indicators.adx_14}
- ATR (14): {regime.indicators.atr_14}
- EMA (9): {regime.indicators.ema_9}
- EMA (21): {regime.indicators.ema_21}
- EMA (50): {regime.indicators.ema_50}
- Bollinger Bands Width: {regime.indicators.bb_width_pct}%

Regime Classification Reasoning:
{regime.reasoning}

Task: Provide a concise 3-4 sentence market analysis explaining:
1. What the current regime means for options traders
2. Key risks to watch out for
3. General trading approach (e.g., "favor neutral strategies", "expect directional moves")

Keep it practical and actionable. Avoid jargon where possible."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text
        except Exception as e:
            return f"Unable to analyze market: {str(e)}"

    async def explain_strategy_basics(
        self,
        strategy_name: str
    ) -> str:
        """
        Explain a strategy in simple terms (educational).

        Args:
            strategy_name: Name of the strategy (e.g., "iron_condor")

        Returns:
            Educational explanation
        """
        prompt = f"""Explain the "{strategy_name}" options strategy in simple terms.

Include:
1. What it is (structure and setup)
2. When to use it (market outlook)
3. Max profit and max loss
4. Breakeven points
5. Key risks
6. One real-world example

Keep it concise (5-6 sentences) and beginner-friendly."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text
        except Exception as e:
            return f"Unable to explain strategy: {str(e)}"

    async def review_position(
        self,
        position_data: Dict,
        current_market: Dict
    ) -> str:
        """
        Review an existing position and suggest improvements or exits.

        Args:
            position_data: Position details (strikes, qty, P&L, entry date, etc.)
            current_market: Current market data (spot, VIX, regime)

        Returns:
            Position review and suggestions
        """
        prompt = f"""You are reviewing an existing options position.

Position Details:
{self._format_position_data(position_data)}

Current Market:
{self._format_market_data(current_market)}

Task: Provide a brief review (3-4 sentences) covering:
1. Current position status (profit/loss, risk exposure)
2. Should the trader hold, adjust, or exit?
3. Specific action if adjustment needed (e.g., "roll up short call", "exit and take profit")

Be concise and actionable."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text
        except Exception as e:
            return f"Unable to review position: {str(e)}"

    async def answer_question(
        self,
        question: str,
        context: Optional[Dict] = None
    ) -> str:
        """
        Answer a general trading question using Claude.

        Args:
            question: User's question
            context: Optional context (current positions, market data, etc.)

        Returns:
            Claude's answer
        """
        context_str = ""
        if context:
            context_str = f"\nContext:\n{self._format_context(context)}\n"

        prompt = f"""You are an expert options trading advisor for Indian markets (NSE).

{context_str}
Question: {question}

Provide a clear, concise answer (3-5 sentences). Be practical and India-specific where relevant."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text
        except Exception as e:
            return f"Unable to answer question: {str(e)}"

    # Helper methods for prompt formatting

    def _build_recommendation_prompt(
        self,
        recommendation: StrategyRecommendation,
        regime: "RegimeResponse",
        user_context: Optional[Dict]
    ) -> str:
        """Build prompt for strategy recommendation explanation."""
        context_str = ""
        if user_context:
            context_str = f"\nUser Profile:\n{self._format_context(user_context)}\n"

        return f"""You are explaining why a specific options strategy is recommended.

Strategy: {recommendation.template.name}
Confidence Score: {recommendation.confidence}%

Market Regime: {regime.regime_type.value if hasattr(regime.regime_type, 'value') else regime.regime_type}
Regime Confidence: {regime.confidence}%

Key Indicators:
- VIX: {regime.indicators.vix}
- RSI: {regime.indicators.rsi_14}
- Trend: {"Bullish" if regime.indicators.ema_9 > regime.indicators.ema_50 else "Bearish"}
{context_str}
Scoring Breakdown:
- Regime Score: {recommendation.regime_score}
- Final Confidence: {recommendation.confidence}%

Reasoning (from system):
{recommendation.reasoning}

Task: Provide a clear 3-4 sentence explanation in simple terms:
1. Why this strategy fits the current market
2. What the trader can expect (profit potential, risks)
3. Any precautions to take

Be conversational and practical."""

    def _format_position_data(self, data: Dict) -> str:
        """Format position data for prompts."""
        lines = []
        for key, value in data.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _format_market_data(self, data: Dict) -> str:
        """Format market data for prompts."""
        lines = []
        for key, value in data.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def _format_context(self, context: Dict) -> str:
        """Format generic context dictionary."""
        lines = []
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)


__all__ = ["ClaudeAdvisor"]
