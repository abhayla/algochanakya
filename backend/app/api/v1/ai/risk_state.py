"""
AI Risk State API Endpoints

REST API for autonomous drawdown control and risk state management.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.users import User
from app.models.ai_risk_state import AIRiskState, RiskState
from app.services.ai.risk_state_engine import RiskStateEngine
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# Response Schemas
class RiskStateResponse(BaseModel):
    """Current risk state response."""
    state: str = Field(..., description="Current risk state (NORMAL, DEGRADED, PAUSED)")
    previous_state: Optional[str] = Field(None, description="Previous risk state")
    reason: Optional[str] = Field(None, description="Reason for current state")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio at transition")
    current_drawdown: Optional[float] = Field(None, description="Current drawdown percentage")
    consecutive_losses: int = Field(0, description="Number of consecutive losses")
    triggered_at: datetime = Field(..., description="When state was triggered")
    resolved_at: Optional[datetime] = Field(None, description="When state was resolved")

    class Config:
        from_attributes = True


class RiskStateEvaluationResponse(BaseModel):
    """Risk state evaluation response."""
    current_state: str = Field(..., description="Current risk state")
    recommended_state: str = Field(..., description="Recommended risk state")
    transition_needed: bool = Field(..., description="Whether transition is needed")
    reason: Optional[str] = Field(None, description="Reason for recommendation")
    performance_metrics: dict = Field(..., description="Performance metrics")


# Endpoints

@router.get("/current", response_model=RiskStateResponse, summary="Get Current Risk State")
async def get_current_risk_state(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's risk state.

    Returns risk state with performance metrics and transition history.

    Returns:
        RiskStateResponse: Current risk state details
    """
    try:
        engine = RiskStateEngine(db)
        risk_state = await engine.get_current_state(user.id)

        return RiskStateResponse.model_validate(risk_state)

    except Exception as e:
        logger.error(f"Error getting risk state for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk state: {str(e)}"
        )


@router.get("/evaluate", response_model=RiskStateEvaluationResponse, summary="Evaluate Risk State")
async def evaluate_risk_state(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluate current risk state and get recommendation.

    Analyzes performance metrics and recommends state transition if needed.

    Returns:
        RiskStateEvaluationResponse: Evaluation results and recommendation
    """
    try:
        engine = RiskStateEngine(db)

        # Get current state
        current_state_record = await engine.get_current_state(user.id)
        current_state = RiskState(current_state_record.state)

        # Evaluate recommended state
        recommended_state, reason = await engine.evaluate_state(user.id)

        # Get performance metrics
        sharpe, drawdown, consecutive_losses = await engine._get_performance_metrics(user.id)

        return RiskStateEvaluationResponse(
            current_state=current_state.value,
            recommended_state=recommended_state.value,
            transition_needed=(recommended_state != current_state),
            reason=reason,
            performance_metrics={
                "sharpe_ratio": sharpe,
                "current_drawdown": float(drawdown) if drawdown else None,
                "consecutive_losses": consecutive_losses
            }
        )

    except Exception as e:
        logger.error(f"Error evaluating risk state for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate risk state: {str(e)}"
        )


@router.post("/reset", response_model=RiskStateResponse, summary="Reset Risk State to NORMAL")
async def reset_risk_state(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually reset risk state to NORMAL.

    Use this to override automatic state transitions after resolving issues.

    Returns:
        RiskStateResponse: Updated risk state
    """
    try:
        engine = RiskStateEngine(db)

        # Transition to NORMAL state
        updated_state = await engine.transition_state(
            user_id=user.id,
            new_state=RiskState.NORMAL,
            reason="Manually reset by user",
            sharpe_ratio=None,
            drawdown=None,
            consecutive_losses=0
        )

        logger.info(f"User {user.id} manually reset risk state to NORMAL")

        return RiskStateResponse.model_validate(updated_state)

    except Exception as e:
        logger.error(f"Error resetting risk state for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset risk state: {str(e)}"
        )


__all__ = ["router"]
