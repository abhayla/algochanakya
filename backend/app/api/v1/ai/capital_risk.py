"""
Capital-at-Risk API Endpoints - Priority 3.3

Provides REST API for capital-at-risk monitoring and alerts.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.users import User
from app.services.ai.capital_risk_meter import (
    CapitalRiskMeter,
    CapitalRiskMetrics,
    CapitalRiskAlert
)
from app.services.ai.stress_greeks_engine import StressGreeksEngine
from app.services.options.greeks_calculator import GreeksCalculatorService

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Response Models ====================

class CapitalRiskResponse(BaseModel):
    """Response model for capital-at-risk metrics."""
    user_id: str
    max_daily_capital: float
    deployed_capital: float
    capital_utilization_pct: float
    worst_case_loss: float
    capital_at_risk: float
    capital_at_risk_pct: float
    var_95: float
    expected_shortfall: float
    stress_risk_score: float
    open_positions_count: int
    total_exposure: float
    alert_level: str
    alerts: List[dict]
    warning_threshold_pct: float
    critical_threshold_pct: float
    calculated_at: str

    class Config:
        from_attributes = True


class ThresholdsResponse(BaseModel):
    """Response model for risk thresholds."""
    max_daily_capital: float
    warning_threshold_pct: float
    critical_threshold_pct: float
    max_strategies_per_day: int
    max_lots_per_strategy: int
    description: dict


class AlertResponse(BaseModel):
    """Response model for a single alert."""
    severity: str
    message: str
    metric: str
    current_value: float
    threshold: float
    triggered_at: str


class AlertsListResponse(BaseModel):
    """Response model for alerts list."""
    total_alerts: int
    critical_count: int
    high_count: int
    elevated_count: int
    alerts: List[AlertResponse]
    overall_alert_level: str


class DeploymentCheckRequest(BaseModel):
    """Request model for deployment check."""
    margin_required: float = Field(..., description="Margin required for new position")
    lot_size: int = Field(1, description="Lot size")
    current_spot: float = Field(..., description="Current spot price")
    legs: Optional[List[dict]] = Field(None, description="Position legs for stress testing")


class DeploymentCheckResponse(BaseModel):
    """Response model for deployment check."""
    can_deploy: bool
    current_capital_at_risk_pct: float
    projected_capital_utilization_pct: float
    current_alert_level: str
    violations: List[str]
    recommendation: str


# ==================== Endpoints ====================

@router.get(
    "/current",
    response_model=CapitalRiskResponse,
    summary="Get current capital-at-risk metrics",
    description="Calculate and return real-time capital-at-risk metrics for the user"
)
async def get_capital_risk_current(
    current_spot: Optional[float] = Query(None, description="Current spot price for stress calculations"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current capital-at-risk metrics.

    Returns comprehensive risk metrics including:
    - Capital utilization
    - Worst-case loss under stress scenarios
    - VaR and expected shortfall
    - Active alerts
    """
    try:
        # Initialize services
        greeks_calculator = GreeksCalculatorService(db, user.id)
        stress_engine = StressGreeksEngine(greeks_calculator)
        meter = CapitalRiskMeter(db, stress_engine)

        # Calculate metrics
        # Note: In production, positions would come from Kite API or database
        metrics = await meter.calculate_capital_at_risk(
            user_id=user.id,
            positions=None,  # Will be populated from active positions
            current_spot=current_spot
        )

        return CapitalRiskResponse(**metrics.to_dict())

    except Exception as e:
        logger.error(f"Error getting capital risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/alerts",
    response_model=AlertsListResponse,
    summary="Get active risk alerts",
    description="Get list of active capital risk alerts for the user"
)
async def get_capital_risk_alerts(
    severity_filter: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, ELEVATED"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get active risk alerts.

    Returns list of alerts with severity levels and recommendations.
    """
    try:
        # Initialize services
        greeks_calculator = GreeksCalculatorService(db, user.id)
        stress_engine = StressGreeksEngine(greeks_calculator)
        meter = CapitalRiskMeter(db, stress_engine)

        # Calculate metrics to get alerts
        metrics = await meter.calculate_capital_at_risk(
            user_id=user.id,
            positions=None,
            current_spot=None
        )

        # Filter alerts if severity specified
        alerts = metrics.alerts
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter.upper()]

        # Count by severity
        critical_count = sum(1 for a in metrics.alerts if a.severity == 'CRITICAL')
        high_count = sum(1 for a in metrics.alerts if a.severity == 'HIGH')
        elevated_count = sum(1 for a in metrics.alerts if a.severity == 'ELEVATED')

        return AlertsListResponse(
            total_alerts=len(alerts),
            critical_count=critical_count,
            high_count=high_count,
            elevated_count=elevated_count,
            alerts=[AlertResponse(**a.to_dict()) for a in alerts],
            overall_alert_level=metrics.alert_level
        )

    except Exception as e:
        logger.error(f"Error getting capital risk alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/thresholds",
    response_model=ThresholdsResponse,
    summary="Get risk thresholds configuration",
    description="Get user's configured risk thresholds"
)
async def get_risk_thresholds(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's risk threshold configuration.

    Returns current threshold settings and their descriptions.
    """
    try:
        meter = CapitalRiskMeter(db)
        thresholds = await meter.get_risk_thresholds(user.id)

        return ThresholdsResponse(**thresholds)

    except Exception as e:
        logger.error(f"Error getting risk thresholds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/check-deployment",
    response_model=DeploymentCheckResponse,
    summary="Check if new deployment is safe",
    description="Validate if deploying a new position would breach risk limits"
)
async def check_deployment_risk(
    request: DeploymentCheckRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if deploying a new position would breach risk limits.

    Pre-flight check before strategy deployment to ensure:
    - Capital utilization stays within limits
    - Stress risk remains acceptable
    - No critical alerts would be triggered
    """
    try:
        # Initialize services
        greeks_calculator = GreeksCalculatorService(db, user.id)
        stress_engine = StressGreeksEngine(greeks_calculator)
        meter = CapitalRiskMeter(db, stress_engine)

        # Check deployment
        new_position = {
            'margin_required': request.margin_required,
            'lot_size': request.lot_size,
            'legs': request.legs
        }

        result = await meter.check_deployment_risk(
            user_id=user.id,
            new_position=new_position,
            current_spot=request.current_spot
        )

        return DeploymentCheckResponse(**result)

    except Exception as e:
        logger.error(f"Error checking deployment risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/summary",
    summary="Get risk summary for dashboard",
    description="Get condensed risk summary suitable for dashboard display"
)
async def get_risk_summary(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get condensed risk summary for dashboard widget.

    Returns key metrics optimized for quick display:
    - Capital at risk percentage
    - Alert level
    - Key alerts (if any)
    """
    try:
        # Initialize services
        greeks_calculator = GreeksCalculatorService(db, user.id)
        stress_engine = StressGreeksEngine(greeks_calculator)
        meter = CapitalRiskMeter(db, stress_engine)

        # Calculate metrics
        metrics = await meter.calculate_capital_at_risk(
            user_id=user.id,
            positions=None,
            current_spot=None
        )

        # Return condensed summary
        return {
            'capital_at_risk_pct': round(metrics.capital_at_risk_pct, 1),
            'capital_utilization_pct': round(metrics.capital_utilization_pct, 1),
            'alert_level': metrics.alert_level,
            'stress_risk_score': round(metrics.stress_risk_score, 1),
            'has_critical_alerts': any(a.severity == 'CRITICAL' for a in metrics.alerts),
            'alerts_count': len(metrics.alerts),
            'open_positions': metrics.open_positions_count,
            'status_color': _get_status_color(metrics.alert_level),
            'status_message': _get_status_message(metrics.alert_level, metrics.capital_at_risk_pct)
        }

    except Exception as e:
        logger.error(f"Error getting risk summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

def _get_status_color(alert_level: str) -> str:
    """Get color code for alert level."""
    colors = {
        'CRITICAL': '#e53935',  # Red
        'HIGH': '#ff9800',      # Orange
        'ELEVATED': '#ffeb3b',  # Yellow
        'NORMAL': '#4caf50',    # Green
        'LOW': '#00b386'        # Kite green
    }
    return colors.get(alert_level, '#666666')


def _get_status_message(alert_level: str, capital_at_risk_pct: float) -> str:
    """Get human-readable status message."""
    messages = {
        'CRITICAL': 'High risk - reduce exposure immediately',
        'HIGH': 'Elevated risk - consider reducing positions',
        'ELEVATED': 'Moderate risk - monitor closely',
        'NORMAL': 'Within normal risk parameters',
        'LOW': 'Low risk exposure'
    }
    return messages.get(alert_level, f'{capital_at_risk_pct:.1f}% capital at risk')
