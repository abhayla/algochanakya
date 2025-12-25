"""
ML Strategy Scorer

Uses trained XGBoost/LightGBM models to predict strategy success probability.
Integrates with rule-based StrategyRecommender to enhance scoring.
"""

import os
import pickle
import logging
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

import numpy as np

from app.services.ai.strategy_recommender import StrategyRecommendation
from app.services.ai.ml.feature_extractor import FeatureExtractor

if TYPE_CHECKING:
    from app.schemas.ai import RegimeResponse

logger = logging.getLogger(__name__)


class MLStrategyScorer:
    """
    ML-based strategy scorer using XGBoost/LightGBM models.

    Predicts strategy success probability based on market conditions.
    """

    def __init__(self, model_dir: Optional[str] = None):
        """
        Initialize ML scorer.

        Args:
            model_dir: Directory containing trained models (defaults to backend/models/)
        """
        self.feature_extractor = FeatureExtractor()

        # Default model directory
        if model_dir is None:
            backend_dir = Path(__file__).parent.parent.parent.parent
            model_dir = backend_dir / "models" / "ml"

        self.model_dir = Path(model_dir)
        self.model = None
        self.model_metadata = None

        # Try to load latest model
        self._load_latest_model()

    def _load_latest_model(self):
        """Load the latest trained model from disk."""
        try:
            if not self.model_dir.exists():
                logger.warning(f"Model directory does not exist: {self.model_dir}")
                return

            # Find latest model file (format: model_v{version}_{timestamp}.pkl)
            model_files = list(self.model_dir.glob("model_v*.pkl"))

            if not model_files:
                logger.warning("No trained models found in model directory")
                return

            # Sort by modification time (most recent first)
            latest_model_file = max(model_files, key=lambda p: p.stat().st_mtime)

            # Load model
            with open(latest_model_file, "rb") as f:
                model_data = pickle.load(f)

            self.model = model_data["model"]
            self.model_metadata = model_data["metadata"]

            logger.info(
                f"Loaded model version {self.model_metadata.get('version', 'unknown')} "
                f"from {latest_model_file.name}"
            )

        except Exception as e:
            logger.error(f"Error loading ML model: {e}")
            self.model = None

    def is_model_loaded(self) -> bool:
        """Check if a trained model is loaded."""
        return self.model is not None

    async def score_strategy(
        self,
        strategy_name: str,
        regime: "RegimeResponse",
        current_time: Optional[datetime] = None
    ) -> float:
        """
        Score a strategy using ML model.

        Args:
            strategy_name: Name of strategy to score
            regime: Current market regime
            current_time: Current timestamp (defaults to now)

        Returns:
            ML confidence score (0-100), or 50.0 if model not available
        """
        if not self.is_model_loaded():
            logger.warning("ML model not loaded, returning neutral score")
            return 50.0

        try:
            # Extract features
            features = self.feature_extractor.extract_features(
                regime=regime,
                strategy_name=strategy_name,
                current_time=current_time
            )

            # Predict probability
            # XGBoost/LightGBM predict_proba returns [[prob_class_0, prob_class_1]]
            features_2d = features.reshape(1, -1)

            # Get prediction
            if hasattr(self.model, "predict_proba"):
                # Classification model (XGBoost, LightGBM, sklearn)
                proba = self.model.predict_proba(features_2d)[0]

                # Assume binary classification: class 1 = success
                if len(proba) >= 2:
                    success_probability = proba[1]
                else:
                    success_probability = proba[0]
            else:
                # Regression model (direct score prediction)
                prediction = self.model.predict(features_2d)[0]
                success_probability = np.clip(prediction, 0.0, 1.0)

            # Convert to 0-100 scale
            ml_score = success_probability * 100.0

            return float(ml_score)

        except Exception as e:
            logger.error(f"Error scoring strategy with ML model: {e}")
            return 50.0

    async def score_strategies_batch(
        self,
        strategy_names: List[str],
        regime: "RegimeResponse",
        current_time: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        Score multiple strategies in batch.

        Args:
            strategy_names: List of strategy names
            regime: Current market regime
            current_time: Current timestamp

        Returns:
            Dict mapping strategy names to ML scores (0-100)
        """
        if not self.is_model_loaded():
            logger.warning("ML model not loaded, returning neutral scores")
            return {name: 50.0 for name in strategy_names}

        try:
            # Extract features for all strategies
            features_list = []
            for strategy_name in strategy_names:
                features = self.feature_extractor.extract_features(
                    regime=regime,
                    strategy_name=strategy_name,
                    current_time=current_time
                )
                features_list.append(features)

            # Stack into batch (N, 30)
            features_batch = np.array(features_list)

            # Get predictions
            if hasattr(self.model, "predict_proba"):
                # Classification model
                proba_batch = self.model.predict_proba(features_batch)

                # Extract success probabilities (class 1)
                if proba_batch.shape[1] >= 2:
                    success_probs = proba_batch[:, 1]
                else:
                    success_probs = proba_batch[:, 0]
            else:
                # Regression model
                predictions = self.model.predict(features_batch)
                success_probs = np.clip(predictions, 0.0, 1.0)

            # Convert to 0-100 scale and create dict
            scores = {
                name: float(prob * 100.0)
                for name, prob in zip(strategy_names, success_probs)
            }

            return scores

        except Exception as e:
            logger.error(f"Error scoring strategies batch: {e}")
            return {name: 50.0 for name in strategy_names}

    async def enhance_recommendations(
        self,
        recommendations: List[StrategyRecommendation],
        regime: "RegimeResponse",
        ml_weight: float = 0.3
    ) -> List[StrategyRecommendation]:
        """
        Enhance rule-based recommendations with ML scores.

        Args:
            recommendations: List of rule-based recommendations
            regime: Current market regime
            ml_weight: Weight for ML score (0-1), default 0.3
                      Final score = (1-ml_weight)*rule_score + ml_weight*ml_score

        Returns:
            Enhanced recommendations with adjusted scores
        """
        if not self.is_model_loaded() or not recommendations:
            return recommendations

        try:
            # Get ML scores for all strategies
            strategy_names = [rec.strategy_name for rec in recommendations]
            ml_scores = await self.score_strategies_batch(strategy_names, regime)

            # Enhance each recommendation
            enhanced = []
            for rec in recommendations:
                ml_score = ml_scores.get(rec.strategy_name, 50.0)

                # Combine rule-based and ML scores
                original_score = rec.confidence
                combined_score = (1 - ml_weight) * original_score + ml_weight * ml_score

                # Create enhanced recommendation
                enhanced_rec = StrategyRecommendation(
                    strategy_name=rec.strategy_name,
                    confidence=combined_score,
                    reasoning=rec.reasoning,
                    strikes=rec.strikes,
                    lot_size=rec.lot_size,
                    entry_range=rec.entry_range,
                    underlying=rec.underlying,
                    expiry=rec.expiry
                )

                enhanced.append(enhanced_rec)

            # Re-sort by combined score
            enhanced.sort(key=lambda x: x.confidence, reverse=True)

            logger.info(
                f"Enhanced {len(enhanced)} recommendations with ML (weight={ml_weight})"
            )

            return enhanced

        except Exception as e:
            logger.error(f"Error enhancing recommendations with ML: {e}")
            return recommendations

    def get_model_info(self) -> Optional[Dict]:
        """
        Get information about the loaded model.

        Returns:
            Dict with model metadata, or None if no model loaded
        """
        if not self.is_model_loaded():
            return None

        return {
            "version": self.model_metadata.get("version", "unknown"),
            "trained_at": self.model_metadata.get("trained_at"),
            "accuracy": self.model_metadata.get("accuracy"),
            "features_count": self.feature_extractor.feature_count,
            "model_type": type(self.model).__name__
        }


__all__ = ["MLStrategyScorer"]
