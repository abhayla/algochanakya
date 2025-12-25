"""
Feedback Scorer

Multi-factor decision quality scoring for AI learning:
- P&L Outcome: 40%
- Risk Management: 25%
- Entry Quality: 15%
- Adjustment Quality: 15%
- Exit Quality: 5%

Used by learning pipeline to evaluate decision effectiveness.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

logger = logging.getLogger(__name__)


@dataclass
class TradeOutcome:
    """Complete trade outcome data for scoring."""
    # Basic Info
    decision_id: int
    strategy_id: int
    strategy_name: str

    # P&L
    realized_pnl: Decimal
    max_profit_seen: Decimal
    max_loss_seen: Decimal
    initial_margin: Decimal

    # Entry Metrics
    entry_spot: float
    entry_vix: float
    entry_regime: str
    entry_confidence: float

    # During Trade
    max_delta_exposure: float
    max_gamma_risk: float
    adjustments_count: int
    days_in_trade: int

    # Exit Metrics
    exit_spot: float
    exit_reason: str
    exit_timing_score: float  # 0-100

    # Risk Management
    breached_stop_loss: bool
    breached_profit_target: bool
    hit_margin_call: bool


class FeedbackScorer:
    """
    Scores AI trading decisions using multi-factor analysis.

    Combines P&L, risk management, entry/exit quality, and adjustment
    effectiveness into a single quality score (0-100).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

        # Scoring weights
        self.weights = {
            "pnl_outcome": 0.40,
            "risk_management": 0.25,
            "entry_quality": 0.15,
            "adjustment_quality": 0.15,
            "exit_quality": 0.05
        }

    def score_decision(
        self,
        outcome: TradeOutcome
    ) -> Dict[str, float]:
        """
        Score a completed trading decision.

        Args:
            outcome: Complete trade outcome data

        Returns:
            Dict with component scores and overall score
        """
        # Calculate component scores
        pnl_score = self._score_pnl_outcome(outcome)
        risk_score = self._score_risk_management(outcome)
        entry_score = self._score_entry_quality(outcome)
        adjustment_score = self._score_adjustment_quality(outcome)
        exit_score = self._score_exit_quality(outcome)

        # Calculate weighted overall score
        overall_score = (
            pnl_score * self.weights["pnl_outcome"] +
            risk_score * self.weights["risk_management"] +
            entry_score * self.weights["entry_quality"] +
            adjustment_score * self.weights["adjustment_quality"] +
            exit_score * self.weights["exit_quality"]
        )

        return {
            "overall_score": round(overall_score, 2),
            "pnl_score": round(pnl_score, 2),
            "risk_score": round(risk_score, 2),
            "entry_score": round(entry_score, 2),
            "adjustment_score": round(adjustment_score, 2),
            "exit_score": round(exit_score, 2),
            "component_weights": self.weights
        }

    def _score_pnl_outcome(self, outcome: TradeOutcome) -> float:
        """
        Score P&L outcome (0-100).

        Factors:
        - Absolute P&L vs margin
        - P&L efficiency (captured vs max possible)
        - Win/loss magnitude
        """
        # P&L as % of margin
        roi = (outcome.realized_pnl / outcome.initial_margin) * 100

        # Base score from ROI
        if roi > 10:  # >10% profit
            base_score = 100
        elif roi > 5:  # 5-10% profit
            base_score = 85
        elif roi > 2:  # 2-5% profit
            base_score = 70
        elif roi > 0:  # Small profit
            base_score = 60
        elif roi > -2:  # Small loss
            base_score = 40
        elif roi > -5:  # Medium loss
            base_score = 20
        else:  # Large loss
            base_score = 0

        # Penalty for leaving money on table
        if outcome.max_profit_seen > 0:
            capture_rate = float(outcome.realized_pnl / outcome.max_profit_seen)
            if capture_rate < 0.5:  # Captured <50% of max profit
                base_score *= 0.8

        return base_score

    def _score_risk_management(self, outcome: TradeOutcome) -> float:
        """
        Score risk management (0-100).

        Factors:
        - Stop loss adherence
        - Delta/gamma exposure control
        - Margin usage
        - Risk events avoided
        """
        score = 100.0

        # Penalties for risk violations
        if outcome.hit_margin_call:
            score -= 50  # Major penalty

        if outcome.breached_stop_loss:
            score -= 20  # Allowed loss to run

        # Delta exposure penalty
        if abs(outcome.max_delta_exposure) > 0.5:
            score -= 15

        # Gamma risk penalty
        if abs(outcome.max_gamma_risk) > 0.02:
            score -= 10

        # Bonus for good risk management
        if (not outcome.breached_stop_loss and
            abs(outcome.max_delta_exposure) < 0.3):
            score += 10

        return max(0, min(100, score))

    def _score_entry_quality(self, outcome: TradeOutcome) -> float:
        """
        Score entry decision quality (0-100).

        Factors:
        - Regime confidence at entry
        - VIX appropriateness
        - Entry timing relative to outcome
        """
        score = 50.0  # Neutral baseline

        # Confidence bonus
        if outcome.entry_confidence > 80:
            score += 25
        elif outcome.entry_confidence > 70:
            score += 15
        elif outcome.entry_confidence > 60:
            score += 5
        else:
            score -= 10

        # VIX appropriateness (prefer low VIX for selling premium)
        if outcome.entry_vix < 15:
            score += 10
        elif outcome.entry_vix > 25:
            score -= 15

        # Result validation (good entry should lead to profit)
        if outcome.realized_pnl > 0:
            score += 15  # Entry was validated by outcome

        return max(0, min(100, score))

    def _score_adjustment_quality(self, outcome: TradeOutcome) -> float:
        """
        Score adjustment decisions (0-100).

        Factors:
        - Number of adjustments (too many = reactive)
        - Adjustment effectiveness
        - Cost vs benefit
        """
        score = 70.0  # Neutral baseline

        # Too many adjustments = reactive/panicky
        if outcome.adjustments_count > 3:
            score -= 20
        elif outcome.adjustments_count > 2:
            score -= 10
        elif outcome.adjustments_count == 0:
            # No adjustments when needed?
            if outcome.max_delta_exposure > 0.5:
                score -= 20  # Should have adjusted

        # Bonus for profitable trade with adjustments
        if outcome.adjustments_count > 0 and outcome.realized_pnl > 0:
            score += 15  # Adjustments helped

        # Penalty for loss despite adjustments
        if outcome.adjustments_count > 0 and outcome.realized_pnl < 0:
            score -= 10  # Adjustments didn't help

        return max(0, min(100, score))

    def _score_exit_quality(self, outcome: TradeOutcome) -> float:
        """
        Score exit decision quality (0-100).

        Factors:
        - Exit timing (DTE, time of day)
        - Profit capture efficiency
        - Exit reason appropriateness
        """
        # Use provided exit timing score as base
        score = outcome.exit_timing_score

        # Adjust based on exit reason
        good_exits = ["profit_target", "premium_captured", "time_based"]
        bad_exits = ["stop_loss", "margin_call", "panic"]

        if outcome.exit_reason in good_exits:
            score += 10
        elif outcome.exit_reason in bad_exits:
            score -= 15

        # Days in trade appropriateness
        if outcome.days_in_trade < 1:
            score -= 10  # Too quick
        elif outcome.days_in_trade > 20:
            score -= 10  # Held too long

        return max(0, min(100, score))

    async def should_retrain_model(
        self,
        window_days: int = 30,
        min_trades: int = 50
    ) -> bool:
        """
        Determine if ML model should be retrained.

        Criteria:
        - At least min_trades completed
        - Recent performance degradation detected
        - Sufficient new data accumulated

        Args:
            window_days: Look back period
            min_trades: Minimum trades required

        Returns:
            True if model should be retrained
        """
        # This would query ai_decisions_log for recent completed trades
        # and analyze if model predictions are degrading

        # Placeholder logic:
        # In production, would:
        # 1. Count completed trades in window
        # 2. Compare predicted scores vs actual scores
        # 3. Detect if prediction error is increasing
        # 4. Return True if degradation detected

        return False

    def calculate_rolling_accuracy(
        self,
        predictions: List[float],
        actuals: List[float],
        window: int = 20
    ) -> float:
        """
        Calculate rolling prediction accuracy.

        Args:
            predictions: Predicted success scores
            actuals: Actual outcome scores
            window: Rolling window size

        Returns:
            Mean absolute error over window
        """
        if len(predictions) < window or len(actuals) < window:
            return 0.0

        recent_preds = predictions[-window:]
        recent_actuals = actuals[-window:]

        errors = [abs(p - a) for p, a in zip(recent_preds, recent_actuals)]
        mae = sum(errors) / len(errors)

        return mae


__all__ = ["FeedbackScorer", "TradeOutcome"]
