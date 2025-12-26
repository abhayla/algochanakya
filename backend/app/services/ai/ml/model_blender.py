"""
Model Blender

Implements Bayesian blending of global and user-specific ML models.
Gradually transitions from 100% global (cold-start) to personalized models
as user accumulates trading history.
"""

import logging
from typing import Dict, Optional, Tuple
from decimal import Decimal

import numpy as np

logger = logging.getLogger(__name__)


class ModelBlender:
    """
    Blends global and user-specific model predictions using Bayesian weighting.

    Formula: Final_Score = (alpha × Global_Score) + ((1-alpha) × User_Score)

    Alpha decay: alpha = max(alpha_min, alpha_start × (1 - trades_completed / trades_threshold))

    Examples:
    - 0 trades:   alpha = 1.0  (100% global, 0% user)
    - 50 trades:  alpha = 0.6  (60% global, 40% user) - assuming threshold=100, min=0.2
    - 100 trades: alpha = 0.2  (20% global, 80% user)
    - 200 trades: alpha = 0.2  (20% global, 80% user) - capped at minimum
    """

    def __init__(
        self,
        alpha_start: float = 1.0,
        alpha_min: float = 0.2,
        trades_threshold: int = 100
    ):
        """
        Initialize model blender.

        Args:
            alpha_start: Initial weight for global model (1.0 = 100% global)
            alpha_min: Minimum weight for global model (0.2 = 20% global, 80% user)
            trades_threshold: Number of trades needed for full personalization
        """
        self.alpha_start = alpha_start
        self.alpha_min = alpha_min
        self.trades_threshold = trades_threshold

        # Validate parameters
        if not (0 <= alpha_min <= alpha_start <= 1.0):
            raise ValueError("Invalid alpha values: 0 <= alpha_min <= alpha_start <= 1.0")
        if trades_threshold <= 0:
            raise ValueError("trades_threshold must be positive")

    def calculate_alpha(self, trades_completed: int) -> float:
        """
        Calculate blending coefficient (alpha) based on user's trade count.

        Alpha decays linearly from alpha_start to alpha_min as trades increase.

        Args:
            trades_completed: Number of completed trades by user

        Returns:
            Alpha value (global model weight) between alpha_min and alpha_start
        """
        if trades_completed <= 0:
            # Cold-start: 100% global
            return self.alpha_start

        if trades_completed >= self.trades_threshold:
            # Full personalization: use minimum global weight
            return self.alpha_min

        # Linear decay
        progress = trades_completed / self.trades_threshold
        alpha = self.alpha_start - (progress * (self.alpha_start - self.alpha_min))

        # Ensure alpha stays within bounds
        alpha = max(self.alpha_min, min(self.alpha_start, alpha))

        return alpha

    def blend_scores(
        self,
        global_score: float,
        user_score: Optional[float],
        trades_completed: int
    ) -> Tuple[float, Dict]:
        """
        Blend global and user model scores.

        Args:
            global_score: Score from global model (0-100)
            user_score: Score from user model (0-100), or None if no user model
            trades_completed: Number of completed trades by user

        Returns:
            Tuple of (blended_score, metadata)
            - blended_score: Final blended score (0-100)
            - metadata: Dict with alpha, weights, individual scores
        """
        # Calculate alpha
        alpha = self.calculate_alpha(trades_completed)

        # If no user model, use 100% global
        if user_score is None:
            blended_score = global_score
            metadata = {
                "alpha": alpha,
                "global_weight": 1.0,
                "user_weight": 0.0,
                "global_score": global_score,
                "user_score": None,
                "blended_score": blended_score,
                "trades_completed": trades_completed,
                "trades_threshold": self.trades_threshold,
                "personalization_progress": 0.0,
                "fallback_reason": "no_user_model"
            }
            logger.debug(f"No user model - using 100% global score: {global_score:.2f}")
            return blended_score, metadata

        # Blend scores
        global_weight = alpha
        user_weight = 1.0 - alpha

        blended_score = (global_weight * global_score) + (user_weight * user_score)

        # Calculate personalization progress (0% = all global, 100% = fully personalized)
        if self.trades_threshold > 0:
            progress = min(100.0, (trades_completed / self.trades_threshold) * 100.0)
        else:
            progress = 100.0

        metadata = {
            "alpha": alpha,
            "global_weight": global_weight,
            "user_weight": user_weight,
            "global_score": global_score,
            "user_score": user_score,
            "blended_score": blended_score,
            "trades_completed": trades_completed,
            "trades_threshold": self.trades_threshold,
            "personalization_progress": progress
        }

        logger.debug(
            f"Blended scores: global={global_score:.2f} ({global_weight:.1%}), "
            f"user={user_score:.2f} ({user_weight:.1%}) → {blended_score:.2f} "
            f"(progress={progress:.1f}%)"
        )

        return blended_score, metadata

    def blend_scores_batch(
        self,
        global_scores: Dict[str, float],
        user_scores: Dict[str, Optional[float]],
        trades_completed: int
    ) -> Dict[str, Tuple[float, Dict]]:
        """
        Blend multiple strategy scores in batch.

        Args:
            global_scores: Dict mapping strategy names to global scores
            user_scores: Dict mapping strategy names to user scores (can be None)
            trades_completed: Number of completed trades by user

        Returns:
            Dict mapping strategy names to (blended_score, metadata) tuples
        """
        results = {}

        for strategy_name in global_scores:
            global_score = global_scores[strategy_name]
            user_score = user_scores.get(strategy_name)

            blended_score, metadata = self.blend_scores(
                global_score, user_score, trades_completed
            )

            results[strategy_name] = (blended_score, metadata)

        return results

    def get_blending_status(self, trades_completed: int) -> Dict:
        """
        Get current blending status for a user.

        Args:
            trades_completed: Number of completed trades

        Returns:
            Dict with blending configuration and current status
        """
        alpha = self.calculate_alpha(trades_completed)
        global_weight = alpha
        user_weight = 1.0 - alpha

        if self.trades_threshold > 0:
            progress_pct = min(100.0, (trades_completed / self.trades_threshold) * 100.0)
        else:
            progress_pct = 100.0

        trades_remaining = max(0, self.trades_threshold - trades_completed)

        return {
            "trades_completed": trades_completed,
            "trades_threshold": self.trades_threshold,
            "trades_remaining_for_full_personalization": trades_remaining,
            "personalization_progress_pct": progress_pct,
            "current_alpha": alpha,
            "global_weight_pct": global_weight * 100.0,
            "user_weight_pct": user_weight * 100.0,
            "alpha_start": self.alpha_start,
            "alpha_min": self.alpha_min,
            "is_cold_start": trades_completed == 0,
            "is_fully_personalized": trades_completed >= self.trades_threshold
        }

    @classmethod
    def from_user_config(cls, user_config) -> "ModelBlender":
        """
        Create ModelBlender from AIUserConfig instance.

        Args:
            user_config: AIUserConfig model instance

        Returns:
            ModelBlender configured with user's settings
        """
        return cls(
            alpha_start=float(user_config.blending_alpha_start),
            alpha_min=float(user_config.blending_alpha_min),
            trades_threshold=user_config.blending_trades_threshold
        )


__all__ = ["ModelBlender"]
