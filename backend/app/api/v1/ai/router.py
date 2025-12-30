"""
AI API Router - Centralized AI Service Endpoints

Includes sub-routers for regime classification, predictions, recommendations, analytics, risk state, and ML model management.
"""

from fastapi import APIRouter
import logging

# Import sub-routers
from app.api.v1.ai import (
    regime, config, recommendations, analytics, backtest,
    risk_state, stress, drawdown, regime_drift, ml, regime_quality,
    autonomy, capital_risk, websocket_health, deploy
)

router = APIRouter(tags=["ai"])
logger = logging.getLogger(__name__)

# Include sub-routers with prefixes and tags
router.include_router(regime.router, prefix="/regime", tags=["ai-regime"])
router.include_router(config.router, prefix="/config", tags=["ai-config"])
router.include_router(recommendations.router, prefix="/recommendations", tags=["ai-recommendations"])
router.include_router(analytics.router, prefix="/analytics", tags=["ai-analytics"])
router.include_router(backtest.router, prefix="/backtest", tags=["ai-backtest"])
router.include_router(risk_state.router, prefix="/risk-state", tags=["ai-risk-state"])
router.include_router(stress.router, prefix="/stress", tags=["ai-stress"])
router.include_router(drawdown.router, prefix="/drawdown", tags=["ai-drawdown"])
router.include_router(regime_drift.router, prefix="/regime-drift", tags=["ai-regime-drift"])
router.include_router(ml.router, prefix="/ml", tags=["ai-ml"])
router.include_router(regime_quality.router, prefix="/regime-quality", tags=["ai-regime-quality"])
router.include_router(autonomy.router, prefix="/autonomy", tags=["ai-autonomy"])
router.include_router(capital_risk.router, prefix="/capital-risk", tags=["ai-capital-risk"])
router.include_router(websocket_health.router, tags=["ai-websocket-health"])
router.include_router(deploy.router, prefix="/deploy", tags=["ai-deploy"])
