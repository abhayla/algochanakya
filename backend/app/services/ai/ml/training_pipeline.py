"""
ML Training Pipeline

Handles model training, evaluation, and persistence for strategy scoring.
Supports XGBoost and LightGBM with hyperparameter tuning.
"""

import pickle
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report
)

from app.services.ai.ml.feature_extractor import FeatureExtractor, FEATURE_NAMES

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """
    ML model training pipeline for strategy scoring.

    Handles data preparation, training, evaluation, and model persistence.
    """

    def __init__(
        self,
        model_type: str = "xgboost",
        model_dir: Optional[str] = None
    ):
        """
        Initialize training pipeline.

        Args:
            model_type: Model type ("xgboost" or "lightgbm")
            model_dir: Directory to save trained models
        """
        self.model_type = model_type.lower()
        self.feature_extractor = FeatureExtractor()

        # Model directory
        if model_dir is None:
            backend_dir = Path(__file__).parent.parent.parent.parent
            model_dir = backend_dir / "models" / "ml"

        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Model instance
        self.model = None

    def prepare_training_data(
        self,
        data: pd.DataFrame,
        target_column: str = "success",
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare training and test data from DataFrame.

        Args:
            data: DataFrame with columns matching FEATURE_NAMES + target_column
            target_column: Name of target column (binary: 0/1)
            test_size: Fraction of data for testing
            random_state: Random seed for reproducibility

        Returns:
            (X_train, X_test, y_train, y_test)
        """
        # Validate required columns
        required_cols = set(FEATURE_NAMES + [target_column])
        missing_cols = required_cols - set(data.columns)

        if missing_cols:
            raise ValueError(f"Missing columns in training data: {missing_cols}")

        # Extract features and target
        X = data[FEATURE_NAMES].values
        y = data[target_column].values

        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y  # Preserve class distribution
        )

        logger.info(
            f"Prepared training data: {len(X_train)} train, {len(X_test)} test samples"
        )

        return X_train, X_test, y_train, y_test

    def train_xgboost(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        params: Optional[Dict] = None
    ):
        """
        Train XGBoost classifier.

        Args:
            X_train: Training features
            y_train: Training labels
            params: XGBoost hyperparameters (optional)
        """
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError(
                "XGBoost not installed. Install with: pip install xgboost"
            )

        # Default parameters
        default_params = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42
        }

        if params:
            default_params.update(params)

        # Train model
        self.model = xgb.XGBClassifier(**default_params)
        self.model.fit(X_train, y_train)

        logger.info("XGBoost model trained successfully")

    def train_lightgbm(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        params: Optional[Dict] = None
    ):
        """
        Train LightGBM classifier.

        Args:
            X_train: Training features
            y_train: Training labels
            params: LightGBM hyperparameters (optional)
        """
        try:
            import lightgbm as lgb
        except ImportError:
            raise ImportError(
                "LightGBM not installed. Install with: pip install lightgbm"
            )

        # Default parameters
        default_params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "max_depth": 6,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "verbose": -1  # Suppress output
        }

        if params:
            default_params.update(params)

        # Train model
        self.model = lgb.LGBMClassifier(**default_params)
        self.model.fit(X_train, y_train)

        logger.info("LightGBM model trained successfully")

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        params: Optional[Dict] = None
    ):
        """
        Train model based on model_type.

        Args:
            X_train: Training features
            y_train: Training labels
            params: Model hyperparameters
        """
        if self.model_type == "xgboost":
            self.train_xgboost(X_train, y_train, params)
        elif self.model_type == "lightgbm":
            self.train_lightgbm(X_train, y_train, params)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate trained model on test data.

        Args:
            X_test: Test features
            y_test: Test labels

        Returns:
            Dict with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Predictions
        y_pred = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)[:, 1]

        # Calculate metrics
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_proba)
        }

        # Log results
        logger.info("Model Evaluation Metrics:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")

        # Classification report
        report = classification_report(y_test, y_pred)
        logger.info(f"\nClassification Report:\n{report}")

        return metrics

    def save_model(
        self,
        version: str,
        metrics: Dict[str, float],
        description: Optional[str] = None
    ) -> Path:
        """
        Save trained model to disk.

        Args:
            version: Model version (e.g., "v1", "v2")
            metrics: Evaluation metrics from evaluate()
            description: Optional model description

        Returns:
            Path to saved model file
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_{version}_{timestamp}.pkl"
        filepath = self.model_dir / filename

        # Package model with metadata
        model_package = {
            "model": self.model,
            "metadata": {
                "version": version,
                "model_type": self.model_type,
                "trained_at": datetime.now().isoformat(),
                "accuracy": metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1_score": metrics.get("f1_score"),
                "roc_auc": metrics.get("roc_auc"),
                "feature_names": FEATURE_NAMES,
                "feature_count": len(FEATURE_NAMES),
                "description": description
            }
        }

        # Save to disk
        with open(filepath, "wb") as f:
            pickle.dump(model_package, f)

        logger.info(f"Model saved to {filepath}")

        return filepath

    def get_feature_importance(self, top_n: int = 10) -> pd.DataFrame:
        """
        Get feature importance from trained model.

        Args:
            top_n: Number of top features to return

        Returns:
            DataFrame with feature names and importance scores
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        if not hasattr(self.model, "feature_importances_"):
            raise ValueError("Model does not support feature importance")

        # Get importance scores
        importance = self.model.feature_importances_

        # Create DataFrame
        importance_df = pd.DataFrame({
            "feature": FEATURE_NAMES,
            "importance": importance
        })

        # Sort by importance
        importance_df = importance_df.sort_values("importance", ascending=False)

        logger.info(f"\nTop {top_n} Features:")
        for idx, row in importance_df.head(top_n).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        return importance_df.head(top_n)


def train_model_from_csv(
    csv_path: str,
    model_type: str = "xgboost",
    version: str = "v1",
    test_size: float = 0.2,
    params: Optional[Dict] = None
) -> Tuple[TrainingPipeline, Dict[str, float]]:
    """
    Convenience function to train model from CSV file.

    Args:
        csv_path: Path to training data CSV
        model_type: Model type ("xgboost" or "lightgbm")
        version: Model version string
        test_size: Fraction for test set
        params: Model hyperparameters

    Returns:
        (TrainingPipeline instance, evaluation metrics)
    """
    # Load data
    data = pd.read_csv(csv_path)
    logger.info(f"Loaded {len(data)} samples from {csv_path}")

    # Initialize pipeline
    pipeline = TrainingPipeline(model_type=model_type)

    # Prepare data
    X_train, X_test, y_train, y_test = pipeline.prepare_training_data(
        data, test_size=test_size
    )

    # Train model
    pipeline.train(X_train, y_train, params)

    # Evaluate
    metrics = pipeline.evaluate(X_test, y_test)

    # Save model
    pipeline.save_model(version, metrics)

    # Show feature importance
    pipeline.get_feature_importance(top_n=10)

    return pipeline, metrics


__all__ = ["TrainingPipeline", "train_model_from_csv"]
