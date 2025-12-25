"""
AI API Router - Centralized AI Service Endpoints

Includes sub-routers for regime classification, predictions, recommendations, and analytics.
"""

from fastapi import APIRouter
import logging

# Import sub-routers
from app.api.v1.ai import regime, config, recommendations, analytics, backtest

router = APIRouter(tags=["ai"])
logger = logging.getLogger(__name__)

# Include sub-routers with prefixes and tags
router.include_router(regime.router, prefix="/regime", tags=["ai-regime"])
router.include_router(config.router, prefix="/config", tags=["ai-config"])
router.include_router(recommendations.router, prefix="/recommendations", tags=["ai-recommendations"])
router.include_router(analytics.router, prefix="/analytics", tags=["ai-analytics"])
router.include_router(backtest.router, prefix="/backtest", tags=["ai-backtest"])
