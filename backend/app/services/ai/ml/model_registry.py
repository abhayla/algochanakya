"""
ML Model Registry

Manages model versions, metadata, and lifecycle in the database.
Supports model activation, rollback, and A/B testing.
Handles both global (all-user) and user-specific models.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIModelRegistry

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    ML model registry service.

    Tracks model versions, metadata, and deployment status in database.
    """

    @staticmethod
    async def register_model(
        version: str,
        model_type: str,
        file_path: str,
        metrics: Dict[str, float],
        description: Optional[str] = None,
        db: AsyncSession = None
    ) -> AIModelRegistry:
        """
        Register a new model version in the registry.

        Args:
            version: Model version (e.g., "v1", "v2")
            model_type: Model type ("xgboost", "lightgbm")
            file_path: Path to saved model file
            metrics: Evaluation metrics dict
            description: Optional model description
            db: Database session

        Returns:
            Created AIModelRegistry instance
        """
        # Create model registry entry
        model_entry = AIModelRegistry(
            version=version,
            model_type=model_type,
            file_path=str(file_path),
            accuracy=metrics.get("accuracy"),
            precision=metrics.get("precision"),
            recall=metrics.get("recall"),
            f1_score=metrics.get("f1_score"),
            roc_auc=metrics.get("roc_auc"),
            description=description,
            is_active=False,  # New models start inactive
            trained_at=datetime.now()
        )

        db.add(model_entry)
        await db.commit()
        await db.refresh(model_entry)

        logger.info(f"Registered model {version} ({model_type}) in registry")

        return model_entry

    @staticmethod
    async def activate_model(
        version: str,
        db: AsyncSession
    ) -> AIModelRegistry:
        """
        Activate a model version (deactivates all others).

        Args:
            version: Model version to activate
            db: Database session

        Returns:
            Activated model instance
        """
        # Deactivate all models
        stmt = select(AIModelRegistry).where(AIModelRegistry.is_active == True)
        result = await db.execute(stmt)
        active_models = result.scalars().all()

        for model in active_models:
            model.is_active = False

        # Activate target version
        stmt = select(AIModelRegistry).where(AIModelRegistry.version == version)
        result = await db.execute(stmt)
        target_model = result.scalar_one_or_none()

        if not target_model:
            raise ValueError(f"Model version {version} not found in registry")

        target_model.is_active = True
        target_model.activated_at = datetime.now()

        await db.commit()
        await db.refresh(target_model)

        logger.info(f"Activated model version {version}")

        return target_model

    @staticmethod
    async def get_active_model(db: AsyncSession) -> Optional[AIModelRegistry]:
        """
        Get the currently active model.

        Args:
            db: Database session

        Returns:
            Active model instance, or None if no active model
        """
        stmt = select(AIModelRegistry).where(AIModelRegistry.is_active == True)
        result = await db.execute(stmt)
        active_model = result.scalar_one_or_none()

        return active_model

    @staticmethod
    async def get_model_by_version(
        version: str,
        db: AsyncSession
    ) -> Optional[AIModelRegistry]:
        """
        Get model by version string.

        Args:
            version: Model version
            db: Database session

        Returns:
            Model instance, or None if not found
        """
        stmt = select(AIModelRegistry).where(AIModelRegistry.version == version)
        result = await db.execute(stmt)
        model = result.scalar_one_or_none()

        return model

    @staticmethod
    async def list_models(
        limit: int = 10,
        include_inactive: bool = True,
        db: AsyncSession = None
    ) -> List[AIModelRegistry]:
        """
        List all registered models.

        Args:
            limit: Maximum number of models to return
            include_inactive: Include inactive models
            db: Database session

        Returns:
            List of model instances, sorted by trained_at desc
        """
        stmt = select(AIModelRegistry).order_by(desc(AIModelRegistry.trained_at))

        if not include_inactive:
            stmt = stmt.where(AIModelRegistry.is_active == True)

        stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        models = result.scalars().all()

        return list(models)

    @staticmethod
    async def get_model_metrics(version: str, db: AsyncSession) -> Dict[str, float]:
        """
        Get evaluation metrics for a model version.

        Args:
            version: Model version
            db: Database session

        Returns:
            Dict with metrics (accuracy, precision, recall, f1, roc_auc)
        """
        model = await ModelRegistry.get_model_by_version(version, db)

        if not model:
            raise ValueError(f"Model version {version} not found")

        return {
            "accuracy": float(model.accuracy) if model.accuracy else None,
            "precision": float(model.precision) if model.precision else None,
            "recall": float(model.recall) if model.recall else None,
            "f1_score": float(model.f1_score) if model.f1_score else None,
            "roc_auc": float(model.roc_auc) if model.roc_auc else None
        }

    @staticmethod
    async def compare_models(
        version1: str,
        version2: str,
        db: AsyncSession
    ) -> Dict[str, Dict[str, float]]:
        """
        Compare metrics between two model versions.

        Args:
            version1: First model version
            version2: Second model version
            db: Database session

        Returns:
            Dict with metrics for both versions
        """
        metrics1 = await ModelRegistry.get_model_metrics(version1, db)
        metrics2 = await ModelRegistry.get_model_metrics(version2, db)

        return {
            version1: metrics1,
            version2: metrics2
        }

    @staticmethod
    async def delete_model(version: str, db: AsyncSession):
        """
        Delete a model from registry.

        Args:
            version: Model version to delete
            db: Database session
        """
        model = await ModelRegistry.get_model_by_version(version, db)

        if not model:
            raise ValueError(f"Model version {version} not found")

        if model.is_active:
            raise ValueError("Cannot delete active model. Activate another version first.")

        # Delete model file if it exists
        model_path = Path(model.file_path)
        if model_path.exists():
            model_path.unlink()
            logger.info(f"Deleted model file: {model.file_path}")

        # Delete from database
        await db.delete(model)
        await db.commit()

        logger.info(f"Deleted model version {version} from registry")

    # ============================================================================
    # Global/User Model Management (Priority 2.1)
    # ============================================================================

    @staticmethod
    async def get_global_model(
        db: AsyncSession,
        model_type: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[AIModelRegistry]:
        """
        Get global baseline model.

        Args:
            db: Database session
            model_type: Filter by model type (xgboost, lightgbm), or None for any
            active_only: Only return active global model

        Returns:
            Global model instance, or None if not found
        """
        stmt = select(AIModelRegistry).where(AIModelRegistry.scope == 'global')

        if model_type:
            stmt = stmt.where(AIModelRegistry.model_type == model_type)

        if active_only:
            stmt = stmt.where(AIModelRegistry.is_active == True)

        stmt = stmt.order_by(desc(AIModelRegistry.trained_at)).limit(1)

        result = await db.execute(stmt)
        global_model = result.scalar_one_or_none()

        return global_model

    @staticmethod
    async def get_user_model(
        db: AsyncSession,
        user_id: UUID,
        model_type: Optional[str] = None,
        active_only: bool = True
    ) -> Optional[AIModelRegistry]:
        """
        Get user-specific model.

        Args:
            db: Database session
            user_id: User ID
            model_type: Filter by model type, or None for any
            active_only: Only return active user model

        Returns:
            User model instance, or None if not found
        """
        stmt = select(AIModelRegistry).where(
            and_(
                AIModelRegistry.scope == 'user',
                AIModelRegistry.user_id == user_id
            )
        )

        if model_type:
            stmt = stmt.where(AIModelRegistry.model_type == model_type)

        if active_only:
            stmt = stmt.where(AIModelRegistry.is_active == True)

        stmt = stmt.order_by(desc(AIModelRegistry.trained_at)).limit(1)

        result = await db.execute(stmt)
        user_model = result.scalar_one_or_none()

        return user_model

    @staticmethod
    async def list_global_models(
        db: AsyncSession,
        limit: int = 10,
        include_inactive: bool = True
    ) -> List[AIModelRegistry]:
        """
        List all global models.

        Args:
            db: Database session
            limit: Maximum number of models to return
            include_inactive: Include inactive models

        Returns:
            List of global model instances
        """
        stmt = select(AIModelRegistry).where(AIModelRegistry.scope == 'global')

        if not include_inactive:
            stmt = stmt.where(AIModelRegistry.is_active == True)

        stmt = stmt.order_by(desc(AIModelRegistry.trained_at)).limit(limit)

        result = await db.execute(stmt)
        models = result.scalars().all()

        return list(models)

    @staticmethod
    async def list_user_models(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 10,
        include_inactive: bool = True
    ) -> List[AIModelRegistry]:
        """
        List all models for a specific user.

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of models to return
            include_inactive: Include inactive models

        Returns:
            List of user model instances
        """
        stmt = select(AIModelRegistry).where(
            and_(
                AIModelRegistry.scope == 'user',
                AIModelRegistry.user_id == user_id
            )
        )

        if not include_inactive:
            stmt = stmt.where(AIModelRegistry.is_active == True)

        stmt = stmt.order_by(desc(AIModelRegistry.trained_at)).limit(limit)

        result = await db.execute(stmt)
        models = result.scalars().all()

        return list(models)

    @staticmethod
    async def activate_global_model(version: str, db: AsyncSession) -> AIModelRegistry:
        """
        Activate a global model (deactivates other global models).

        Args:
            version: Global model version to activate
            db: Database session

        Returns:
            Activated model instance
        """
        # Deactivate all global models
        stmt = select(AIModelRegistry).where(
            and_(
                AIModelRegistry.scope == 'global',
                AIModelRegistry.is_active == True
            )
        )
        result = await db.execute(stmt)
        active_models = result.scalars().all()

        for model in active_models:
            model.is_active = False

        # Activate target version
        stmt = select(AIModelRegistry).where(
            and_(
                AIModelRegistry.scope == 'global',
                AIModelRegistry.version == version
            )
        )
        result = await db.execute(stmt)
        target_model = result.scalar_one_or_none()

        if not target_model:
            raise ValueError(f"Global model version {version} not found")

        target_model.is_active = True
        target_model.activated_at = datetime.now()

        await db.commit()
        await db.refresh(target_model)

        logger.info(f"Activated global model version {version}")

        return target_model

    @staticmethod
    async def activate_user_model(
        version: str,
        user_id: UUID,
        db: AsyncSession
    ) -> AIModelRegistry:
        """
        Activate a user-specific model (deactivates other user models).

        Args:
            version: User model version to activate
            user_id: User ID
            db: Database session

        Returns:
            Activated model instance
        """
        # Deactivate all user models for this user
        stmt = select(AIModelRegistry).where(
            and_(
                AIModelRegistry.scope == 'user',
                AIModelRegistry.user_id == user_id,
                AIModelRegistry.is_active == True
            )
        )
        result = await db.execute(stmt)
        active_models = result.scalars().all()

        for model in active_models:
            model.is_active = False

        # Activate target version
        stmt = select(AIModelRegistry).where(
            and_(
                AIModelRegistry.scope == 'user',
                AIModelRegistry.user_id == user_id,
                AIModelRegistry.version == version
            )
        )
        result = await db.execute(stmt)
        target_model = result.scalar_one_or_none()

        if not target_model:
            raise ValueError(f"User model version {version} not found for user {user_id}")

        target_model.is_active = True
        target_model.activated_at = datetime.now()

        await db.commit()
        await db.refresh(target_model)

        logger.info(f"Activated user model version {version} for user {user_id}")

        return target_model

    # ============================================================================
    # Model Stability Checking (Priority 2.3)
    # ============================================================================

    @staticmethod
    async def check_model_stability(
        new_model: AIModelRegistry,
        old_model: AIModelRegistry,
        stability_threshold_pct: float = 5.0
    ) -> Dict:
        """
        Check if new model is stable compared to old model.

        A new model is considered "stable" if it doesn't degrade performance
        significantly compared to the active model.

        Args:
            new_model: Newly trained model
            old_model: Currently active model
            stability_threshold_pct: Max allowed performance degradation (%)

        Returns:
            Dict with:
                - is_stable (bool): Whether new model is stable
                - performance_change_pct (float): Performance delta (positive = improvement)
                - meets_threshold (bool): Whether change is within threshold
                - recommendation (str): 'activate', 'reject', or 'manual_review'
                - details (dict): Metric-by-metric comparison
        """
        # Use F1 score as primary stability metric (balanced precision/recall)
        old_f1 = float(old_model.f1_score) if old_model.f1_score else 0.0
        new_f1 = float(new_model.f1_score) if new_model.f1_score else 0.0

        # Calculate performance change
        if old_f1 > 0:
            performance_change_pct = ((new_f1 - old_f1) / old_f1) * 100
        else:
            performance_change_pct = 0.0

        # Check if degradation exceeds threshold
        degradation = -performance_change_pct  # Negative change = degradation
        exceeds_threshold = degradation > stability_threshold_pct

        # Determine recommendation
        if performance_change_pct >= 0:
            # New model is better or equal
            recommendation = 'activate'
            is_stable = True
        elif exceeds_threshold:
            # Significant degradation
            recommendation = 'reject'
            is_stable = False
        else:
            # Small degradation within threshold
            recommendation = 'manual_review'
            is_stable = True

        # Detailed metric comparison
        details = {
            'f1_score': {
                'old': old_f1,
                'new': new_f1,
                'change_pct': performance_change_pct
            },
            'accuracy': {
                'old': float(old_model.accuracy) if old_model.accuracy else 0.0,
                'new': float(new_model.accuracy) if new_model.accuracy else 0.0,
                'change_pct': ModelRegistry._calc_pct_change(
                    float(old_model.accuracy) if old_model.accuracy else 0.0,
                    float(new_model.accuracy) if new_model.accuracy else 0.0
                )
            },
            'precision': {
                'old': float(old_model.precision) if old_model.precision else 0.0,
                'new': float(new_model.precision) if new_model.precision else 0.0,
                'change_pct': ModelRegistry._calc_pct_change(
                    float(old_model.precision) if old_model.precision else 0.0,
                    float(new_model.precision) if new_model.precision else 0.0
                )
            },
            'recall': {
                'old': float(old_model.recall) if old_model.recall else 0.0,
                'new': float(new_model.recall) if new_model.recall else 0.0,
                'change_pct': ModelRegistry._calc_pct_change(
                    float(old_model.recall) if old_model.recall else 0.0,
                    float(new_model.recall) if new_model.recall else 0.0
                )
            },
            'roc_auc': {
                'old': float(old_model.roc_auc) if old_model.roc_auc else 0.0,
                'new': float(new_model.roc_auc) if new_model.roc_auc else 0.0,
                'change_pct': ModelRegistry._calc_pct_change(
                    float(old_model.roc_auc) if old_model.roc_auc else 0.0,
                    float(new_model.roc_auc) if new_model.roc_auc else 0.0
                )
            }
        }

        return {
            'is_stable': is_stable,
            'performance_change_pct': round(performance_change_pct, 2),
            'degradation_pct': round(degradation, 2),
            'meets_threshold': not exceeds_threshold,
            'threshold_pct': stability_threshold_pct,
            'recommendation': recommendation,
            'details': details
        }

    @staticmethod
    def _calc_pct_change(old_value: float, new_value: float) -> float:
        """Calculate percentage change between two values."""
        if old_value > 0:
            return round(((new_value - old_value) / old_value) * 100, 2)
        return 0.0

    @staticmethod
    async def should_activate_new_model(
        new_model: AIModelRegistry,
        old_model: Optional[AIModelRegistry],
        stability_threshold_pct: float = 5.0
    ) -> bool:
        """
        Determine if new model should be activated.

        Args:
            new_model: Newly trained model
            old_model: Currently active model (None if no active model)
            stability_threshold_pct: Max allowed performance degradation (%)

        Returns:
            True if new model should be activated, False otherwise
        """
        # If no old model exists, activate new model
        if not old_model:
            logger.info("No active model exists, activating new model")
            return True

        # Check stability
        stability_check = await ModelRegistry.check_model_stability(
            new_model=new_model,
            old_model=old_model,
            stability_threshold_pct=stability_threshold_pct
        )

        if stability_check['recommendation'] == 'activate':
            logger.info(
                f"New model performs better ({stability_check['performance_change_pct']:+.2f}% change), activating"
            )
            return True
        elif stability_check['recommendation'] == 'reject':
            logger.warning(
                f"New model degrades performance by {stability_check['degradation_pct']:.2f}% "
                f"(threshold: {stability_threshold_pct}%), rejecting"
            )
            return False
        else:
            # Manual review - activate cautiously
            logger.info(
                f"New model has minor degradation ({stability_check['degradation_pct']:.2f}%), "
                f"activating for manual review"
            )
            return True


__all__ = ["ModelRegistry"]
