"""
AI Strategy Recommendations API Routes

Endpoints for strategy recommendations based on market regime.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.database import get_db, get_redis
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models import User, BrokerConnection
from app.models.ai import AIUserConfig
from app.schemas.ai import RegimeResponse, IndicatorsSnapshotResponse
from app.services.ai.market_regime import MarketRegimeClassifier
from app.services.ai.strategy_recommender import StrategyRecommender
from app.services.ai.config_service import AIConfigService
from app.services.market_data import MarketDataService
from app.constants.trading import UNDERLYINGS

router = APIRouter()
logger = logging.getLogger(__name__)


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    from app.config import settings
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.get("/")
async def get_strategy_recommendations(
    underlying: str = Query(..., description="Index name (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)"),
    top_n: int = Query(3, ge=1, le=10, description="Number of recommendations to return"),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI strategy recommendations based on current market regime.

    Returns top N strategy recommendations with:
    - Confidence scores (0-100)
    - Reasoning for each recommendation
    - Score breakdown (regime score, VIX adjustment, trend adjustment)
    - Strategy risk level and market outlook

    The recommendations are filtered by:
    - User's allowed strategies (if configured)
    - User's minimum confidence threshold
    - Current market conditions
    """
    try:
        # Validate underlying
        if underlying not in UNDERLYINGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid underlying: {underlying}. Must be one of {UNDERLYINGS}"
            )

        # Get user's AI configuration
        user_config = await AIConfigService.get_or_create_config(user.id, db)

        if not user_config.ai_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI features are not enabled for this user. Enable them in AI Settings."
            )

        # Get current market regime
        redis_client = await get_redis()
        market_data = MarketDataService(kite)
        classifier = MarketRegimeClassifier(kite, market_data, redis_client)
        regime_result = await classifier.classify(underlying)

        # Convert to response model
        indicators_response = IndicatorsSnapshotResponse(
            underlying=regime_result.indicators.underlying,
            timestamp=regime_result.indicators.timestamp,
            spot_price=regime_result.indicators.spot_price,
            vix=regime_result.indicators.vix,
            rsi_14=regime_result.indicators.rsi_14,
            adx_14=regime_result.indicators.adx_14,
            ema_9=regime_result.indicators.ema_9,
            ema_21=regime_result.indicators.ema_21,
            ema_50=regime_result.indicators.ema_50,
            atr_14=regime_result.indicators.atr_14,
            bb_upper=regime_result.indicators.bb_upper,
            bb_middle=regime_result.indicators.bb_middle,
            bb_lower=regime_result.indicators.bb_lower,
            bb_width_pct=regime_result.indicators.bb_width_pct
        )

        regime_response = RegimeResponse(
            regime_type=regime_result.regime_type,
            confidence=regime_result.confidence,
            indicators=indicators_response,
            reasoning=regime_result.reasoning
        )

        # Get strategy recommendations
        recommender = StrategyRecommender(db)
        recommendations = await recommender.get_recommendations(
            underlying=underlying,
            regime=regime_response,
            user_config=user_config,
            top_n=top_n
        )

        # Convert to response format
        return {
            "underlying": underlying,
            "regime": {
                "type": regime_response.regime_type.value if hasattr(regime_response.regime_type, 'value') else regime_response.regime_type,
                "confidence": regime_response.confidence,
                "reasoning": regime_response.reasoning,
            },
            "recommendations": [rec.to_dict() for rec in recommendations],
            "total_recommendations": len(recommendations),
            "filters_applied": {
                "min_confidence": user_config.min_confidence_to_trade,
                "max_vix": user_config.max_vix_to_trade if regime_response.indicators.vix else None,
                "allowed_strategies_count": len(user_config.allowed_strategies) if user_config.allowed_strategies else "all",
            }
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting recommendations for {underlying}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting strategy recommendations: {str(e)}"
        )
