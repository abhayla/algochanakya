"""
Regime Quality API

API endpoints for regime-conditioned decision quality scoring and analysis.
Priority 2.2: Regime-Conditioned Decision Quality
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.utils.dependencies import get_current_user
from app.services.ai.regime_quality_scorer import RegimeQualityScorer

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================

class RegimePerformanceResponse(BaseModel):
    """Performance metrics for a specific regime."""
    regime_type: str
    avg_overall_score: float
    avg_pnl_score: float
    avg_risk_score: float
    avg_entry_score: float
    avg_adjustment_score: float
    avg_exit_score: float
    avg_win_rate: float
    avg_pnl_per_trade: float
    sample_size: int
    lookback_days: int


class RegimeComparisonItem(BaseModel):
    """Performance comparison for a single regime."""
    regime_type: str
    avg_score: float
    avg_win_rate: float
    avg_pnl: float
    total_trades: int
    days_traded: int


class RegimeComparisonResponse(BaseModel):
    """Performance comparison across all regimes."""
    regimes: List[RegimeComparisonItem]
    lookback_days: int
    total_regimes: int


class RegimeStrengthsResponse(BaseModel):
    """Regime strengths and weaknesses analysis."""
    strongest_regimes: List[RegimeComparisonItem]
    weakest_regimes: List[RegimeComparisonItem]
    all_regimes: List[RegimeComparisonItem]
    insights: List[str]
    lookback_days: int


class NormalizeScoreRequest(BaseModel):
    """Request to normalize a score."""
    current_score: float = Field(..., ge=0, le=100, description="Current score (0-100)")
    regime_type: str = Field(..., description="Current regime type (e.g., 'TRENDING_BULLISH')")
    score_type: str = Field("overall", description="Type of score (overall, pnl, risk, entry, adjustment, exit, win_rate)")


class NormalizeScoreResponse(BaseModel):
    """Normalized score response."""
    raw_score: float
    normalized_score: float
    historical_avg: Optional[float]
    diff_from_avg: float
    percentile: float
    interpretation: str
    sample_size: int
    regime_type: str
    score_type: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/regime-performance/{regime_type}", response_model=RegimePerformanceResponse)
async def get_regime_performance(
    regime_type: str,
    lookback_days: int = Query(90, gt=0, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get performance metrics for a specific regime.

    Args:
        regime_type: Regime type (e.g., 'TRENDING_BULLISH', 'VOLATILE')
        lookback_days: Number of days to look back (default: 90)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Performance metrics for the specified regime
    """
    scorer = RegimeQualityScorer(lookback_days=lookback_days)

    historical_avg = await scorer.get_historical_regime_averages(
        user_id=current_user.id,
        regime_type=regime_type,
        db=db
    )

    if not historical_avg:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data found for {regime_type} regime in the last {lookback_days} days"
        )

    return RegimePerformanceResponse(
        regime_type=regime_type,
        avg_overall_score=historical_avg['avg_overall_score'],
        avg_pnl_score=historical_avg['avg_pnl_score'],
        avg_risk_score=historical_avg['avg_risk_score'],
        avg_entry_score=historical_avg['avg_entry_score'],
        avg_adjustment_score=historical_avg['avg_adjustment_score'],
        avg_exit_score=historical_avg['avg_exit_score'],
        avg_win_rate=historical_avg['avg_win_rate'],
        avg_pnl_per_trade=historical_avg['avg_pnl_per_trade'],
        sample_size=historical_avg['sample_size'],
        lookback_days=lookback_days
    )


@router.get("/regime-performance/comparison", response_model=RegimeComparisonResponse)
async def compare_regime_performance(
    lookback_days: int = Query(90, gt=0, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare performance across all regimes.

    Args:
        lookback_days: Number of days to look back (default: 90)
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of regimes sorted by performance
    """
    scorer = RegimeQualityScorer(lookback_days=lookback_days)

    result = await scorer.get_regime_strengths_weaknesses(
        user_id=current_user.id,
        db=db,
        lookback_days=lookback_days
    )

    regimes = [
        RegimeComparisonItem(**regime)
        for regime in result['all_regimes']
    ]

    return RegimeComparisonResponse(
        regimes=regimes,
        lookback_days=lookback_days,
        total_regimes=len(regimes)
    )


@router.get("/regime-strengths", response_model=RegimeStrengthsResponse)
async def get_regime_strengths(
    lookback_days: int = Query(90, gt=0, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get strengths and weaknesses analysis for regimes.

    Identifies which regimes the user performs best and worst in,
    along with actionable insights.

    Args:
        lookback_days: Number of days to look back (default: 90)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Strongest regimes, weakest regimes, and insights
    """
    scorer = RegimeQualityScorer(lookback_days=lookback_days)

    result = await scorer.get_regime_strengths_weaknesses(
        user_id=current_user.id,
        db=db,
        lookback_days=lookback_days
    )

    # Convert to response models
    strongest = [RegimeComparisonItem(**r) for r in result['strongest_regimes']]
    weakest = [RegimeComparisonItem(**r) for r in result['weakest_regimes']]
    all_regimes = [RegimeComparisonItem(**r) for r in result['all_regimes']]

    return RegimeStrengthsResponse(
        strongest_regimes=strongest,
        weakest_regimes=weakest,
        all_regimes=all_regimes,
        insights=result['insights'],
        lookback_days=lookback_days
    )


@router.post("/regime-performance/normalize", response_model=NormalizeScoreResponse)
async def normalize_score(
    request: NormalizeScoreRequest,
    lookback_days: int = Query(90, gt=0, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Normalize a score for the current regime.

    Calculates how a score compares to the historical average for that regime,
    accounting for regime-specific difficulty.

    Args:
        request: Score normalization request
        lookback_days: Number of days to look back (default: 90)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Normalized score, percentile, and interpretation
    """
    scorer = RegimeQualityScorer(lookback_days=lookback_days)

    result = await scorer.normalize_score(
        current_score=request.current_score,
        regime_type=request.regime_type,
        user_id=current_user.id,
        db=db,
        score_type=request.score_type
    )

    return NormalizeScoreResponse(
        raw_score=result['raw_score'],
        normalized_score=result['normalized_score'],
        historical_avg=result['historical_avg'],
        diff_from_avg=result['diff_from_avg'],
        percentile=result['percentile'],
        interpretation=result['interpretation'],
        sample_size=result['sample_size'],
        regime_type=request.regime_type,
        score_type=request.score_type
    )
