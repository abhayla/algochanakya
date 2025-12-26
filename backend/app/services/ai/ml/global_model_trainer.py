"""
Global Model Trainer

Trains a global baseline ML model using data from ALL users.
Solves the cold-start problem by providing a fallback for new users
without enough personalized trading history.
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.ml.training_pipeline import TrainingPipeline
from app.services.ai.ml.model_registry import ModelRegistry
from app.models.ai import AILearningReport

logger = logging.getLogger(__name__)


class GlobalModelTrainer:
    """
    Trains global baseline models using aggregated data from all users.

    Global models serve as:
    1. Cold-start baseline for new users
    2. Blending component for personalization
    3. Performance benchmark for user models
    """

    def __init__(self, model_dir: Optional[str] = None):
        """
        Initialize global model trainer.

        Args:
            model_dir: Directory to save trained models (defaults to backend/models/ml/global)
        """
        # Model directory for global models
        if model_dir is None:
            backend_dir = Path(__file__).parent.parent.parent.parent
            model_dir = backend_dir / "models" / "ml" / "global"

        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_global_training_data(
        self,
        db: AsyncSession,
        min_trades_per_user: int = 10
    ) -> pd.DataFrame:
        """
        Fetch training data aggregated from ALL users.

        Args:
            db: Database session
            min_trades_per_user: Minimum trades required to include user's data

        Returns:
            DataFrame with columns: strategy_name, regime_type, vix, rsi_14, ...
                                   plus target column 'success' (1 if profitable, 0 otherwise)
        """
        logger.info("Fetching global training data from all users")

        # Fetch all learning reports (contains decision quality scores and outcomes)
        stmt = select(AILearningReport).where(
            AILearningReport.total_trades >= min_trades_per_user
        )
        result = await db.execute(stmt)
        learning_reports = result.scalars().all()

        if not learning_reports:
            logger.warning("No learning reports found for global training")
            return pd.DataFrame()

        # Convert to training data
        # Note: This is a simplified version. In production, you'd fetch more detailed
        # trade-level data with market conditions at entry time.
        training_data = []

        for report in learning_reports:
            # Extract features from report
            # In real implementation, fetch detailed trade data with regime, indicators, etc.
            # For now, create synthetic features based on report metrics

            # Simulate training samples from report
            for i in range(report.total_trades):
                # This is a placeholder - real implementation would fetch actual trade data
                sample = {
                    # Market state (would come from regime history)
                    'regime_TRENDING_BULLISH': np.random.randint(0, 2),
                    'regime_TRENDING_BEARISH': np.random.randint(0, 2),
                    'regime_RANGEBOUND': np.random.randint(0, 2),
                    'regime_VOLATILE': np.random.randint(0, 2),
                    'regime_PRE_EVENT': 0,
                    'regime_EVENT_DAY': 0,
                    'vix_level': np.random.uniform(0.3, 0.7),  # Normalized

                    # Technical indicators (would come from market data at entry time)
                    'rsi_14': np.random.uniform(0.3, 0.7),
                    'adx_14': np.random.uniform(0.2, 0.6),
                    'atr_14_pct': np.random.uniform(0.2, 0.8),
                    'bb_width_pct': np.random.uniform(0.1, 0.5),
                    'spot_distance_from_ema50_pct': np.random.uniform(0.3, 0.7),
                    'ema_9_21_cross': np.random.randint(0, 2),
                    'ema_21_50_cross': np.random.randint(0, 2),
                    'regime_confidence': np.random.uniform(0.6, 0.9),

                    # Options data placeholders
                    'iv_rank': 0.5,
                    'iv_percentile': 0.5,
                    'oi_pcr': 1.0,
                    'max_pain_distance_pct': 0.0,

                    # Time features
                    'day_of_week': np.random.uniform(0, 1),
                    'hour_of_day': np.random.uniform(0, 1),
                    'minutes_since_open': np.random.uniform(0, 1),
                    'is_first_hour': np.random.randint(0, 2),
                    'is_last_hour': np.random.randint(0, 2),
                    'dte': 0.5,

                    # Strategy features (one-hot encoded)
                    'strategy_iron_condor': np.random.randint(0, 2),
                    'strategy_spread': np.random.randint(0, 2),
                    'strategy_straddle': np.random.randint(0, 2),
                    'strategy_other': np.random.randint(0, 2),
                    'expected_premium_pct': 0.5,

                    # Target: success (1) or failure (0)
                    # Use win_rate as probability of success
                    'success': 1 if np.random.random() < (float(report.win_rate) / 100.0) else 0
                }

                training_data.append(sample)

        df = pd.DataFrame(training_data)

        logger.info(f"Collected {len(df)} training samples from {len(learning_reports)} users")

        return df

    async def train_global_model(
        self,
        db: AsyncSession,
        model_type: str = "xgboost",
        version: Optional[str] = None,
        test_size: float = 0.2,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Train a global baseline model on all users' data.

        Args:
            db: Database session
            model_type: Model type ("xgboost" or "lightgbm")
            version: Model version (auto-generated if not provided)
            test_size: Fraction for test set
            params: Model hyperparameters

        Returns:
            Dict with model info and metrics
        """
        logger.info(f"Training global {model_type} model")

        # Fetch global training data
        training_data = await self.fetch_global_training_data(db)

        if training_data.empty:
            raise ValueError("No training data available for global model")

        # Auto-generate version if not provided
        if version is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            version = f"global_{model_type}_v{timestamp}"

        # Initialize training pipeline
        pipeline = TrainingPipeline(
            model_type=model_type,
            model_dir=str(self.model_dir)
        )

        # Prepare training data
        X_train, X_test, y_train, y_test = pipeline.prepare_training_data(
            training_data,
            target_column='success',
            test_size=test_size
        )

        # Train model
        pipeline.train(X_train, y_train, params)

        # Evaluate model
        metrics = pipeline.evaluate(X_test, y_test)

        # Save model
        model_path = pipeline.save_model(
            version=version,
            metrics=metrics,
            description=f"Global baseline {model_type} model trained on {len(training_data)} samples"
        )

        # Register in database with scope='global'
        await ModelRegistry.register_model(
            version=version,
            model_type=model_type,
            file_path=str(model_path),
            metrics=metrics,
            description=f"Global baseline model (trained on {len(training_data)} samples)",
            db=db
        )

        # Update scope to 'global' and user_id to NULL
        # (ModelRegistry.register_model creates user-scope by default)
        from app.models.ai import AIModelRegistry
        stmt = select(AIModelRegistry).where(AIModelRegistry.version == version)
        result = await db.execute(stmt)
        model_entry = result.scalar_one()

        model_entry.scope = 'global'
        model_entry.user_id = None

        await db.commit()
        await db.refresh(model_entry)

        logger.info(f"Global model {version} trained and registered successfully")
        logger.info(f"Metrics: {metrics}")

        return {
            "version": version,
            "model_type": model_type,
            "scope": "global",
            "metrics": metrics,
            "training_samples": len(training_data),
            "model_path": str(model_path)
        }

    async def retrain_global_model(
        self,
        db: AsyncSession,
        model_type: str = "xgboost",
        activate: bool = True
    ) -> Dict:
        """
        Retrain global model with latest data and optionally activate it.

        Args:
            db: Database session
            model_type: Model type
            activate: Whether to activate the new model

        Returns:
            Dict with model info and metrics
        """
        logger.info("Retraining global model with latest data")

        # Train new global model
        result = await self.train_global_model(db, model_type=model_type)

        # Activate if requested
        if activate:
            await ModelRegistry.activate_model(result["version"], db)
            result["is_active"] = True
            logger.info(f"Activated global model {result['version']}")
        else:
            result["is_active"] = False

        return result


__all__ = ["GlobalModelTrainer"]
