"""
ML Model Management API

API endpoints for global/user model management, training, and blending configuration.
Priority 2.1: Global → Personalized ML Blending
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.models.ai import AIUserConfig, AIModelRegistry
from app.utils.dependencies import get_current_user
from app.services.ai.ml.model_registry import ModelRegistry
from app.services.ai.ml.global_model_trainer import GlobalModelTrainer
from app.services.ai.ml.model_blender import ModelBlender
from app.services.ai.ml.retraining_scheduler import RetrainingScheduler
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class ModelInfoResponse(BaseModel):
    """Model information response."""
    id: int
    version: str
    model_type: str
    scope: str
    user_id: Optional[UUID]
    is_active: bool
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    roc_auc: Optional[float]
    trained_at: str
    description: Optional[str]

    class Config:
        from_attributes = True


class GlobalModelTrainRequest(BaseModel):
    """Request to train a new global model."""
    model_type: str = Field("xgboost", description="Model type (xgboost or lightgbm)")
    activate: bool = Field(True, description="Activate after training")


class GlobalModelTrainResponse(BaseModel):
    """Response after training global model."""
    version: str
    model_type: str
    scope: str
    metrics: dict
    training_samples: int
    is_active: bool
    model_path: str


class BlendingStatusResponse(BaseModel):
    """Blending status for a user."""
    enabled: bool
    trades_completed: int
    trades_threshold: int
    trades_remaining_for_full_personalization: int
    personalization_progress_pct: float
    current_alpha: float
    global_weight_pct: float
    user_weight_pct: float
    alpha_start: float
    alpha_min: float
    is_cold_start: bool
    is_fully_personalized: bool


class BlendingConfigRequest(BaseModel):
    """Request to update blending configuration."""
    enable_ml_blending: Optional[bool] = None
    blending_alpha_start: Optional[float] = Field(None, ge=0, le=1)
    blending_alpha_min: Optional[float] = Field(None, ge=0, le=1)
    blending_trades_threshold: Optional[int] = Field(None, gt=0)


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/models/global", response_model=List[ModelInfoResponse])
async def list_global_models(
    limit: int = 10,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all global baseline models.

    Args:
        limit: Maximum number of models to return
        include_inactive: Include inactive models
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of global model information
    """
    models = await ModelRegistry.list_global_models(
        db=db,
        limit=limit,
        include_inactive=include_inactive
    )

    return [
        ModelInfoResponse(
            id=m.id,
            version=m.version,
            model_type=m.model_type,
            scope=m.scope,
            user_id=m.user_id,
            is_active=m.is_active,
            accuracy=float(m.accuracy) if m.accuracy else None,
            precision=float(m.precision) if m.precision else None,
            recall=float(m.recall) if m.recall else None,
            f1_score=float(m.f1_score) if m.f1_score else None,
            roc_auc=float(m.roc_auc) if m.roc_auc else None,
            trained_at=m.trained_at.isoformat(),
            description=m.description
        )
        for m in models
    ]


@router.get("/models/user", response_model=List[ModelInfoResponse])
async def list_user_models(
    limit: int = 10,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all models for the current user.

    Args:
        limit: Maximum number of models to return
        include_inactive: Include inactive models
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of user model information
    """
    models = await ModelRegistry.list_user_models(
        db=db,
        user_id=current_user.id,
        limit=limit,
        include_inactive=include_inactive
    )

    return [
        ModelInfoResponse(
            id=m.id,
            version=m.version,
            model_type=m.model_type,
            scope=m.scope,
            user_id=m.user_id,
            is_active=m.is_active,
            accuracy=float(m.accuracy) if m.accuracy else None,
            precision=float(m.precision) if m.precision else None,
            recall=float(m.recall) if m.recall else None,
            f1_score=float(m.f1_score) if m.f1_score else None,
            roc_auc=float(m.roc_auc) if m.roc_auc else None,
            trained_at=m.trained_at.isoformat(),
            description=m.description
        )
        for m in models
    ]


@router.post("/models/global/train", response_model=GlobalModelTrainResponse)
async def train_global_model(
    request: GlobalModelTrainRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Train a new global baseline model (admin only).

    This endpoint trains a global model using data from ALL users.
    Training runs in the background.

    Args:
        request: Training request parameters
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user

    Returns:
        Training result with model info and metrics
    """
    # TODO: Add admin permission check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")

    logger.info(f"Training global {request.model_type} model (requested by {current_user.id})")

    try:
        trainer = GlobalModelTrainer()

        # Train model
        result = await trainer.retrain_global_model(
            db=db,
            model_type=request.model_type,
            activate=request.activate
        )

        return GlobalModelTrainResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error training global model: {e}")
        raise HTTPException(status_code=500, detail="Error training global model")


@router.get("/blending/status", response_model=BlendingStatusResponse)
async def get_blending_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current blending status for the user.

    Shows personalization progress and current blending weights.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Blending status information
    """
    # Get user config
    stmt = select(AIUserConfig).where(AIUserConfig.user_id == current_user.id)
    result = await db.execute(stmt)
    user_config = result.scalar_one_or_none()

    if not user_config:
        raise HTTPException(status_code=404, detail="AI configuration not found")

    # Create blender
    blender = ModelBlender.from_user_config(user_config)

    # Get status
    status = blender.get_blending_status(user_config.total_trades_completed)
    status["enabled"] = user_config.enable_ml_blending

    return BlendingStatusResponse(**status)


@router.put("/blending/config")
async def update_blending_config(
    request: BlendingConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update blending configuration for the user.

    Args:
        request: Blending configuration update
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message
    """
    # Get user config
    stmt = select(AIUserConfig).where(AIUserConfig.user_id == current_user.id)
    result = await db.execute(stmt)
    user_config = result.scalar_one_or_none()

    if not user_config:
        raise HTTPException(status_code=404, detail="AI configuration not found")

    # Update fields
    if request.enable_ml_blending is not None:
        user_config.enable_ml_blending = request.enable_ml_blending

    if request.blending_alpha_start is not None:
        user_config.blending_alpha_start = request.blending_alpha_start

    if request.blending_alpha_min is not None:
        user_config.blending_alpha_min = request.blending_alpha_min

    if request.blending_trades_threshold is not None:
        user_config.blending_trades_threshold = request.blending_trades_threshold

    # Validate alpha values
    if user_config.blending_alpha_min > user_config.blending_alpha_start:
        raise HTTPException(
            status_code=400,
            detail="alpha_min must be <= alpha_start"
        )

    await db.commit()
    await db.refresh(user_config)

    logger.info(f"Updated blending config for user {current_user.id}")

    return {
        "message": "Blending configuration updated successfully",
        "enable_ml_blending": user_config.enable_ml_blending,
        "blending_alpha_start": float(user_config.blending_alpha_start),
        "blending_alpha_min": float(user_config.blending_alpha_min),
        "blending_trades_threshold": user_config.blending_trades_threshold
    }


# ============================================================================
# Retraining Management (Priority 2.3)
# ============================================================================

class RetrainingStatusResponse(BaseModel):
    """Retraining status for a user."""
    cadence: str
    volume_threshold: int
    high_volume_threshold: int
    trades_since_last_retrain: int
    last_retrain_at: Optional[str]
    should_retrain: bool
    retrain_reason: str
    next_retrain_date: Optional[str]
    weekly_trade_volume: int
    is_high_volume_user: bool
    enable_confidence_weighting: bool
    min_stability_threshold: float


class RetrainingConfigRequest(BaseModel):
    """Request to update retraining configuration."""
    retraining_cadence: Optional[str] = Field(None, pattern="^(daily|weekly|volume_based)$")
    retraining_volume_threshold: Optional[int] = Field(None, gt=0)
    high_volume_trades_per_week: Optional[int] = Field(None, gt=0)
    min_model_stability_threshold: Optional[float] = Field(None, ge=0, le=100)
    enable_confidence_weighting: Optional[bool] = None


@router.get("/retraining/status", response_model=RetrainingStatusResponse)
async def get_retraining_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get retraining status and schedule for the current user.

    Shows when the next model retrain is due, trade volume, and configuration.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Retraining status information
    """
    scheduler = RetrainingScheduler()
    status = await scheduler.get_retraining_status(current_user.id, db)

    if 'error' in status:
        raise HTTPException(status_code=404, detail="AI configuration not found")

    return RetrainingStatusResponse(**status)


@router.put("/retraining/config")
async def update_retraining_config(
    request: RetrainingConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update retraining configuration for the user.

    Args:
        request: Retraining configuration update
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message with updated configuration
    """
    # Get user config
    stmt = select(AIUserConfig).where(AIUserConfig.user_id == current_user.id)
    result = await db.execute(stmt)
    user_config = result.scalar_one_or_none()

    if not user_config:
        raise HTTPException(status_code=404, detail="AI configuration not found")

    # Update fields
    if request.retraining_cadence is not None:
        user_config.retraining_cadence = request.retraining_cadence

    if request.retraining_volume_threshold is not None:
        user_config.retraining_volume_threshold = request.retraining_volume_threshold

    if request.high_volume_trades_per_week is not None:
        user_config.high_volume_trades_per_week = request.high_volume_trades_per_week

    if request.min_model_stability_threshold is not None:
        user_config.min_model_stability_threshold = request.min_model_stability_threshold

    if request.enable_confidence_weighting is not None:
        user_config.enable_confidence_weighting = request.enable_confidence_weighting

    await db.commit()
    await db.refresh(user_config)

    logger.info(f"Updated retraining config for user {current_user.id}")

    return {
        "message": "Retraining configuration updated successfully",
        "retraining_cadence": user_config.retraining_cadence,
        "retraining_volume_threshold": user_config.retraining_volume_threshold,
        "high_volume_trades_per_week": user_config.high_volume_trades_per_week,
        "min_model_stability_threshold": float(user_config.min_model_stability_threshold),
        "enable_confidence_weighting": user_config.enable_confidence_weighting
    }


@router.post("/retraining/check")
async def check_retrain_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if user model is due for retraining.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Retraining check result
    """
    scheduler = RetrainingScheduler()
    result = await scheduler.should_retrain_user_model(current_user.id, db)

    return result
