"""
Drawdown Metrics API

Provides endpoints for tracking portfolio drawdown and volatility metrics.
Part of Priority 1.2: Drawdown-Aware Position Sizing.
"""

import logging
from typing import Dict, Any
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import User
from app.utils.dependencies import get_current_user
from app.services.ai.drawdown_tracker import DrawdownTracker
from app.services.ai.position_sizing_engine import PositionSizingEngine

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Request/Response Models
# ============================================================================

class DrawdownMetricsResponse(BaseModel):
    """Current drawdown metrics"""
    high_water_mark: Decimal = Field(..., description="Peak portfolio value")
    current_portfolio_value: Decimal = Field(..., description="Current portfolio value")
    current_drawdown_pct: Decimal = Field(..., description="Current drawdown percentage (0-100)")
    drawdown_level: str = Field(..., description="Drawdown severity level")
    drawdown_multiplier: float = Field(..., description="Position size multiplier based on drawdown")


class VolatilityMetricsResponse(BaseModel):
    """P&L volatility metrics"""
    daily_pnl_volatility: float = Field(..., description="Daily P&L standard deviation")
    volatility_level: str = Field(..., description="Volatility severity level")
    volatility_multiplier: float = Field(..., description="Position size multiplier based on volatility")
    sample_size: int = Field(..., description="Number of data points used")


class PositionSizeRequest(BaseModel):
    """Request for position size calculation"""
    confidence_score: float = Field(..., ge=0, le=100, description="AI confidence score")
    underlying: str = Field(default="NIFTY", description="Underlying symbol")
    strategy_name: str | None = Field(None, description="Strategy name for Kelly sizing")
    capital: float | None = Field(None, description="Total capital for Kelly sizing")
    max_loss_per_lot: float | None = Field(None, description="Max expected loss per lot for Kelly sizing")


class PositionSizeResponse(BaseModel):
    """Position size calculation result"""
    final_lots: int = Field(..., description="Final recommended lot size")
    base_lots: int = Field(..., description="Base lots before adjustments")
    sizing_mode: str = Field(..., description="Sizing mode used")
    confidence_multiplier: float = Field(..., description="Confidence-based multiplier")
    drawdown_dampener: float = Field(..., description="Drawdown dampening factor")
    volatility_scaler: float = Field(..., description="Volatility scaling factor")
    breakdown: Dict[str, Any] = Field(..., description="Step-by-step calculation breakdown")
    warnings: list[str] = Field(..., description="Warnings or notes")
    disabled_reason: str | None = Field(None, description="Reason if sizing is disabled")


class ResetHighWaterMarkResponse(BaseModel):
    """Response for high-water mark reset"""
    new_high_water_mark: Decimal
    previous_high_water_mark: Decimal
    current_drawdown_pct: Decimal
    message: str


# ============================================================================
# API Endpoints
# ============================================================================

@router.get(
    "/metrics",
    response_model=DrawdownMetricsResponse,
    summary="Get current drawdown metrics",
    description="Retrieve current drawdown metrics including high-water mark and drawdown percentage"
)
async def get_drawdown_metrics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current drawdown metrics for the user"""
    try:
        tracker = DrawdownTracker(db)
        metrics = await tracker.calculate_drawdown(user.id)

        return DrawdownMetricsResponse(
            high_water_mark=metrics["high_water_mark"],
            current_portfolio_value=metrics["current_portfolio_value"],
            current_drawdown_pct=metrics["current_drawdown_pct"],
            drawdown_level=metrics["drawdown_level"],
            drawdown_multiplier=metrics["drawdown_multiplier"]
        )

    except Exception as e:
        logger.error(f"Error getting drawdown metrics for user {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get drawdown metrics: {str(e)}")


@router.get(
    "/volatility",
    response_model=VolatilityMetricsResponse,
    summary="Get P&L volatility metrics",
    description="Retrieve P&L volatility metrics for the specified lookback period"
)
async def get_volatility_metrics(
    lookback_days: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get P&L volatility metrics"""
    try:
        tracker = DrawdownTracker(db)
        metrics = await tracker.calculate_volatility(user.id, lookback_days=lookback_days)

        return VolatilityMetricsResponse(
            daily_pnl_volatility=metrics["daily_pnl_volatility"],
            volatility_level=metrics["volatility_level"],
            volatility_multiplier=metrics["volatility_multiplier"],
            sample_size=metrics["sample_size"]
        )

    except Exception as e:
        logger.error(f"Error getting volatility metrics for user {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get volatility metrics: {str(e)}")


@router.post(
    "/calculate-position-size",
    response_model=PositionSizeResponse,
    summary="Calculate optimal position size",
    description="Calculate position size with drawdown and volatility dampening"
)
async def calculate_position_size(
    request: PositionSizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate optimal position size considering:
    - Sizing mode (fixed, tiered, kelly)
    - Confidence score
    - Drawdown dampening
    - Volatility scaling
    """
    try:
        engine = PositionSizingEngine(db)

        result = await engine.calculate_position_size(
            user_id=user.id,
            confidence_score=request.confidence_score,
            underlying=request.underlying,
            strategy_name=request.strategy_name,
            capital=request.capital,
            max_loss_per_lot=request.max_loss_per_lot
        )

        return PositionSizeResponse(**result)

    except ValueError as e:
        logger.warning(f"Invalid position size request for user {user.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating position size for user {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate position size: {str(e)}")


@router.get(
    "/should-pause",
    summary="Check if trading should be paused",
    description="Determine if trading should be paused due to excessive drawdown"
)
async def check_should_pause(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check if trading should be paused due to drawdown limits"""
    try:
        tracker = DrawdownTracker(db)
        should_pause, reason = await tracker.should_pause_trading(user.id)

        return {
            "should_pause": should_pause,
            "reason": reason if should_pause else "Trading allowed",
            "status": "PAUSED" if should_pause else "ACTIVE"
        }

    except Exception as e:
        logger.error(f"Error checking pause status for user {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check pause status: {str(e)}")


@router.post(
    "/reset-high-water-mark",
    response_model=ResetHighWaterMarkResponse,
    summary="Reset high-water mark (Admin)",
    description="Reset high-water mark to current portfolio value. Use with caution."
)
async def reset_high_water_mark(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reset high-water mark to current portfolio value.
    This should only be used when recovering from a known issue or by admin.
    """
    try:
        tracker = DrawdownTracker(db)
        result = await tracker.reset_high_water_mark(user.id)

        return ResetHighWaterMarkResponse(
            new_high_water_mark=result["new_high_water_mark"],
            previous_high_water_mark=result["previous_high_water_mark"],
            current_drawdown_pct=result["current_drawdown_pct"],
            message="High-water mark has been reset successfully"
        )

    except ValueError as e:
        logger.warning(f"Invalid reset request for user {user.id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resetting high-water mark for user {user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset high-water mark: {str(e)}")


__all__ = ["router"]
