"""
Regime Drift Detection API

Provides endpoints for tracking regime stability and detecting drift.
Part of Priority 1.3: Regime Drift Detection.
"""

import logging
from typing import List, Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User
from app.utils.dependencies import get_current_user
from app.services.ai.regime_drift_tracker import RegimeDriftTracker, DriftSeverity

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class StabilityMetricsResponse(BaseModel):
    """Regime stability metrics"""
    stability_score: float = Field(..., description="Stability score (0-100)")
    total_periods: int = Field(..., description="Total periods analyzed")
    regime_changes: int = Field(..., description="Number of regime changes")
    change_rate: float = Field(..., description="Change rate (0-1)")
    current_regime: str = Field(..., description="Current regime type")
    drift_severity: str = Field(..., description="Drift severity level")


class DriftDetectionResponse(BaseModel):
    """Drift detection result"""
    is_drifting: bool = Field(..., description="Whether drift is detected")
    reason: str = Field(..., description="Reason for drift status")
    stability_score: float = Field(..., description="Current stability score")
    drift_severity: str = Field(..., description="Drift severity level")
    regime_changes: int = Field(..., description="Recent regime changes")
    total_periods: int = Field(..., description="Periods analyzed")


class ConfidenceAdjustmentResponse(BaseModel):
    """Confidence adjustment result"""
    adjusted_confidence: float = Field(..., description="Adjusted confidence score")
    confidence_penalty: float = Field(..., description="Applied penalty percentage")
    drift_detected: bool = Field(..., description="Whether drift was detected")
    stability_score: float = Field(..., description="Current stability score")


class RegimeHistoryItem(BaseModel):
    """Single regime history item"""
    id: int
    regime_type: str
    confidence: float
    classified_at: str
    regime_changed: bool
    indicators: Dict[str, Any]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get(
    "/stability-metrics",
    response_model=StabilityMetricsResponse,
    summary="Get regime stability metrics",
    description="Calculate stability score based on recent regime changes"
)
async def get_stability_metrics(
    underlying: str = Query(default="NIFTY", description="Underlying symbol"),
    lookback_periods: int | None = Query(None, description="Number of periods to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get regime stability metrics"""
    try:
        tracker = RegimeDriftTracker(db)
        metrics = await tracker.calculate_stability_score(
            underlying=underlying,
            lookback_periods=lookback_periods
        )

        return StabilityMetricsResponse(
            stability_score=metrics["stability_score"],
            total_periods=metrics["total_periods"],
            regime_changes=metrics["regime_changes"],
            change_rate=metrics["change_rate"],
            current_regime=metrics["current_regime"],
            drift_severity=metrics["drift_severity"]
        )

    except Exception as e:
        logger.error(f"Error getting stability metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stability metrics: {str(e)}")


@router.get(
    "/detect",
    response_model=DriftDetectionResponse,
    summary="Detect regime drift",
    description="Detect if regime drift is occurring (frequent regime changes)"
)
async def detect_drift(
    underlying: str = Query(default="NIFTY", description="Underlying symbol"),
    lookback_periods: int | None = Query(None, description="Number of periods to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Detect regime drift"""
    try:
        tracker = RegimeDriftTracker(db)
        is_drifting, reason, metrics = await tracker.detect_drift(
            underlying=underlying,
            lookback_periods=lookback_periods
        )

        return DriftDetectionResponse(
            is_drifting=is_drifting,
            reason=reason,
            stability_score=metrics["stability_score"],
            drift_severity=metrics["drift_severity"],
            regime_changes=metrics["regime_changes"],
            total_periods=metrics["total_periods"]
        )

    except Exception as e:
        logger.error(f"Error detecting drift: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to detect drift: {str(e)}")


@router.get(
    "/confidence-adjustment",
    response_model=ConfidenceAdjustmentResponse,
    summary="Get confidence adjustment for drift",
    description="Calculate confidence adjustment based on regime drift"
)
async def get_confidence_adjustment(
    base_confidence: float = Query(..., ge=0, le=100, description="Base confidence score"),
    underlying: str = Query(default="NIFTY", description="Underlying symbol"),
    db: AsyncSession = Depends(get_db)
):
    """Get confidence adjustment based on drift"""
    try:
        tracker = RegimeDriftTracker(db)
        result = await tracker.get_confidence_adjustment(
            base_confidence=base_confidence,
            underlying=underlying
        )

        return ConfidenceAdjustmentResponse(
            adjusted_confidence=result["adjusted_confidence"],
            confidence_penalty=result["confidence_penalty"],
            drift_detected=result["drift_detected"],
            stability_score=result["stability_score"]
        )

    except Exception as e:
        logger.error(f"Error getting confidence adjustment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get confidence adjustment: {str(e)}")


@router.get(
    "/history",
    response_model=List[RegimeHistoryItem],
    summary="Get regime history",
    description="Retrieve recent regime classification history"
)
async def get_regime_history(
    underlying: str = Query(default="NIFTY", description="Underlying symbol"),
    limit: int = Query(default=50, ge=1, le=200, description="Number of records to fetch"),
    db: AsyncSession = Depends(get_db)
):
    """Get regime history"""
    try:
        tracker = RegimeDriftTracker(db)
        history = await tracker.get_regime_history(
            underlying=underlying,
            limit=limit
        )

        return [RegimeHistoryItem(**item) for item in history]

    except Exception as e:
        logger.error(f"Error getting regime history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get regime history: {str(e)}")


@router.get(
    "/should-pause",
    summary="Check if trading should be paused due to drift",
    description="Determine if trading should be paused due to excessive regime instability"
)
async def check_should_pause_due_to_drift(
    underlying: str = Query(default="NIFTY", description="Underlying symbol"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if trading should be paused due to drift"""
    try:
        tracker = RegimeDriftTracker(db)
        should_pause, reason = await tracker.should_pause_due_to_drift(
            user_id=user.id,
            underlying=underlying
        )

        return {
            "should_pause": should_pause,
            "reason": reason if should_pause else "Regime is stable",
            "status": "PAUSED" if should_pause else "ACTIVE"
        }

    except Exception as e:
        logger.error(f"Error checking pause status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check pause status: {str(e)}")


@router.post(
    "/clear-history",
    summary="Clear old regime history (Admin)",
    description="Clear regime history older than specified days"
)
async def clear_old_history(
    underlying: str = Query(default="NIFTY", description="Underlying symbol"),
    days_to_keep: int = Query(default=90, ge=1, le=365, description="Number of days to keep"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear old regime history (admin operation)"""
    try:
        tracker = RegimeDriftTracker(db)
        deleted_count = await tracker.clear_old_history(
            underlying=underlying,
            days_to_keep=days_to_keep
        )

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleared {deleted_count} old regime history records"
        }

    except Exception as e:
        logger.error(f"Error clearing history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")


__all__ = ["router"]
