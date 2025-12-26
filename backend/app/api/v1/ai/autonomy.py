"""
AI Autonomy Status API Endpoints (Priority 3.1)

REST API for Autonomy Trust Ladder - tracking user progression through:
- Sandbox (Paper trading)
- Supervised (Live + Semi-auto)
- Autonomous (Live + Full auto)

Provides status, progress tracking, and degradation alerts.
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.users import User
from app.services.ai.autonomy_status import (
    AutonomyStatusService,
    AutonomyLevel,
    GRADUATION_THRESHOLDS,
    DEGRADATION_THRESHOLDS,
)
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Schemas

class LevelDetailsResponse(BaseModel):
    """Details about an autonomy level."""
    name: str = Field(..., description="Display name of the level")
    description: str = Field(..., description="Description of the level")
    icon: str = Field(..., description="Icon identifier")
    color: str = Field(..., description="Color theme")
    features: List[str] = Field(..., description="List of features at this level")


class CriterionProgressResponse(BaseModel):
    """Progress for a single criterion."""
    current: float = Field(..., description="Current value")
    required: float = Field(..., description="Required value")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    met: bool = Field(..., description="Whether criterion is met")


class ProgressResponse(BaseModel):
    """Progress toward next level."""
    overall_percent: float = Field(..., description="Overall progress percentage")
    next_level: Optional[str] = Field(None, description="Next level identifier")
    next_level_name: Optional[str] = Field(None, description="Next level display name")
    criteria: Dict[str, CriterionProgressResponse] = Field(
        default_factory=dict,
        description="Progress for each criterion"
    )


class UnlockCriteriaResponse(BaseModel):
    """Unlock criterion for next level."""
    id: str = Field(..., description="Criterion identifier")
    label: str = Field(..., description="Display label")
    description: str = Field(..., description="Current status description")
    met: bool = Field(..., description="Whether criterion is met")
    icon: str = Field(..., description="Icon identifier")


class WarningResponse(BaseModel):
    """Degradation warning."""
    type: str = Field(..., description="Warning type: warning or critical")
    reason: str = Field(..., description="Reason identifier")
    message: str = Field(..., description="Human-readable message")
    threshold: Optional[float] = Field(None, description="Threshold that triggered warning")


class StatsResponse(BaseModel):
    """Trading statistics."""
    trades_completed: int = Field(0, description="Number of completed trades")
    win_rate: float = Field(0, description="Win rate percentage")
    total_pnl: float = Field(0, description="Total P&L")
    days_trading: int = Field(0, description="Days since started trading")
    current_drawdown: float = Field(0, description="Current drawdown percentage")


class AutonomyStatusResponse(BaseModel):
    """Complete autonomy status response."""
    current_level: str = Field(..., description="Current autonomy level")
    level_index: int = Field(..., description="Level index (0-2)")
    level_details: LevelDetailsResponse = Field(..., description="Details about current level")
    progress: ProgressResponse = Field(..., description="Progress toward next level")
    unlock_criteria: List[UnlockCriteriaResponse] = Field(
        default_factory=list,
        description="Criteria to unlock next level"
    )
    warnings: List[WarningResponse] = Field(
        default_factory=list,
        description="Active warnings"
    )
    is_paused: bool = Field(False, description="Whether trading is paused")
    pause_reason: Optional[str] = Field(None, description="Reason for pause")
    ai_enabled: bool = Field(False, description="Whether AI is enabled")
    graduation_approved: bool = Field(False, description="Whether graduation is approved")
    stats: StatsResponse = Field(..., description="Trading statistics")


class LevelHistoryResponse(BaseModel):
    """Level change history entry."""
    level: str = Field(..., description="Level identifier")
    level_name: str = Field(..., description="Level display name")
    timestamp: str = Field(..., description="ISO timestamp")
    reason: str = Field(..., description="Reason for level")


class ThresholdsResponse(BaseModel):
    """Graduation and degradation thresholds."""
    graduation: Dict[str, Any] = Field(..., description="Graduation thresholds")
    degradation: Dict[str, Any] = Field(..., description="Degradation thresholds")


class AllLevelsResponse(BaseModel):
    """Information about all autonomy levels."""
    levels: List[Dict[str, Any]] = Field(..., description="All autonomy levels")
    current_level: str = Field(..., description="User's current level")


# Endpoints

@router.get(
    "/status",
    response_model=AutonomyStatusResponse,
    summary="Get Autonomy Status"
)
async def get_autonomy_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's autonomy status including level, progress, and warnings.

    Returns comprehensive status for the Autonomy Trust Ladder:
    - Current autonomy level (Sandbox/Supervised/Autonomous)
    - Progress toward next level
    - Unlock criteria checklist
    - Any active warnings or pause status

    Returns:
        AutonomyStatusResponse: Complete autonomy status
    """
    try:
        service = AutonomyStatusService(db)
        status = await service.get_autonomy_status(user.id)

        return AutonomyStatusResponse(**status)

    except Exception as e:
        logger.error(f"Error getting autonomy status for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get autonomy status: {str(e)}"
        )


@router.get(
    "/levels",
    response_model=AllLevelsResponse,
    summary="Get All Autonomy Levels"
)
async def get_all_levels(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about all autonomy levels.

    Returns details for each level in the Trust Ladder to display
    the full progression path.

    Returns:
        AllLevelsResponse: Information about all levels
    """
    try:
        service = AutonomyStatusService(db)
        status = await service.get_autonomy_status(user.id)

        # Build level info for each level
        levels = []
        for level in AutonomyLevel:
            level_details = service._get_level_details(level)
            level_index = service._get_level_index(level)

            levels.append({
                "id": level.value,
                "index": level_index,
                "name": level_details["name"],
                "description": level_details["description"],
                "icon": level_details["icon"],
                "color": level_details["color"],
                "features": level_details["features"],
                "is_current": level.value == status["current_level"],
                "is_unlocked": level_index <= status["level_index"],
            })

        return AllLevelsResponse(
            levels=levels,
            current_level=status["current_level"]
        )

    except Exception as e:
        logger.error(f"Error getting autonomy levels for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get autonomy levels: {str(e)}"
        )


@router.get(
    "/history",
    response_model=List[LevelHistoryResponse],
    summary="Get Level History"
)
async def get_level_history(
    days: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get history of autonomy level changes.

    Args:
        days: Number of days of history to retrieve (default: 30)

    Returns:
        List[LevelHistoryResponse]: Level change history
    """
    try:
        service = AutonomyStatusService(db)
        history = await service.get_level_history(user.id, days)

        return [LevelHistoryResponse(**entry) for entry in history]

    except Exception as e:
        logger.error(f"Error getting level history for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get level history: {str(e)}"
        )


@router.get(
    "/thresholds",
    response_model=ThresholdsResponse,
    summary="Get Graduation/Degradation Thresholds"
)
async def get_thresholds(
    user: User = Depends(get_current_user)
):
    """
    Get the thresholds used for graduation and degradation.

    Returns the configured thresholds for:
    - Graduation criteria (trades, win rate, P&L)
    - Degradation triggers (drawdown, consecutive losses)

    Returns:
        ThresholdsResponse: Threshold configurations
    """
    return ThresholdsResponse(
        graduation={
            "min_trades": GRADUATION_THRESHOLDS["min_trades"],
            "min_win_rate": GRADUATION_THRESHOLDS["min_win_rate"],
            "min_pnl": float(GRADUATION_THRESHOLDS["min_pnl"]),
            "min_days_trading": GRADUATION_THRESHOLDS.get("min_days_trading", 7),
        },
        degradation={
            "max_drawdown": float(DEGRADATION_THRESHOLDS["max_drawdown"]),
            "max_consecutive_losses": DEGRADATION_THRESHOLDS["max_consecutive_losses"],
            "min_win_rate_maintenance": DEGRADATION_THRESHOLDS["min_win_rate_maintenance"],
        }
    )


__all__ = ["router"]
