"""
ML Model Registry

Manages model versions, metadata, and lifecycle in the database.
Supports model activation, rollback, and A/B testing.
"""

import logging
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, desc
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


__all__ = ["ModelRegistry"]
