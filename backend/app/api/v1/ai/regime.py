"""
AI Regime Classification API Routes

Endpoints for market regime classification and technical indicators.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.database import get_db, get_redis
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models import User, BrokerConnection
from app.schemas.ai import RegimeResponse, IndicatorsSnapshotResponse
from app.services.ai.market_regime import MarketRegimeClassifier
from app.services.legacy.market_data import MarketDataService
from app.constants.trading import UNDERLYINGS

router = APIRouter()
logger = logging.getLogger(__name__)


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    from app.config import settings
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.get("/current", response_model=RegimeResponse)
async def get_current_regime(
    underlying: str = Query(..., description="Index name (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)"),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current market regime classification for an underlying.

    Classifies the market into one of:
    - TRENDING_BULLISH
    - TRENDING_BEARISH
    - RANGEBOUND
    - VOLATILE
    - PRE_EVENT
    - EVENT_DAY

    Returns confidence score and reasoning.
    """
    try:
        # Validate underlying
        if underlying not in UNDERLYINGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid underlying: {underlying}. Must be one of {UNDERLYINGS}"
            )

        # Initialize services
        logger.info(f"DEBUG 1: Initializing services for {underlying}")
        redis_client = await get_redis()
        logger.info(f"DEBUG 2: Got redis client")
        market_data = MarketDataService(kite)
        logger.info(f"DEBUG 3: Created market data service")
        classifier = MarketRegimeClassifier(kite, market_data, redis_client)
        logger.info(f"DEBUG 4: Created classifier")

        # Classify regime
        logger.info(f"DEBUG 5: About to call classify()")
        result = await classifier.classify(underlying)
        logger.info(f"DEBUG 6: Classify returned successfully")

        # DEBUG: Log type and value of result.regime_type
        logger.info(f"DEBUG regime_type: type={type(result.regime_type)}, value={result.regime_type}, hasattr value={hasattr(result.regime_type, 'value')}")

        # Convert to response model
        indicators_response = IndicatorsSnapshotResponse(
            underlying=result.indicators.underlying,
            timestamp=result.indicators.timestamp,
            spot_price=result.indicators.spot_price,
            vix=result.indicators.vix,
            rsi_14=result.indicators.rsi_14,
            adx_14=result.indicators.adx_14,
            ema_9=result.indicators.ema_9,
            ema_21=result.indicators.ema_21,
            ema_50=result.indicators.ema_50,
            atr_14=result.indicators.atr_14,
            bb_upper=result.indicators.bb_upper,
            bb_middle=result.indicators.bb_middle,
            bb_lower=result.indicators.bb_lower,
            bb_width_pct=result.indicators.bb_width_pct
        )

        return RegimeResponse(
            regime_type=result.regime_type,
            confidence=result.confidence,
            indicators=indicators_response,
            reasoning=result.reasoning
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting regime for {underlying}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error classifying regime: {str(e)}"
        )


@router.get("/indicators", response_model=IndicatorsSnapshotResponse)
async def get_indicators(
    underlying: str = Query(..., description="Index name (NIFTY, BANKNIFTY, FINNIFTY, SENSEX)"),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all calculated technical indicators for an underlying.

    Returns:
    - Spot price and VIX
    - Trend indicators: RSI, ADX, EMAs
    - Volatility indicators: ATR, Bollinger Bands
    """
    try:
        # Validate underlying
        if underlying not in UNDERLYINGS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid underlying: {underlying}. Must be one of {UNDERLYINGS}"
            )

        # Initialize services
        redis_client = await get_redis()
        market_data = MarketDataService(kite)
        classifier = MarketRegimeClassifier(kite, market_data, redis_client)

        # Get indicators snapshot
        snapshot = await classifier.get_indicators_snapshot(underlying)

        return IndicatorsSnapshotResponse(
            underlying=snapshot.underlying,
            timestamp=snapshot.timestamp,
            spot_price=snapshot.spot_price,
            vix=snapshot.vix,
            rsi_14=snapshot.rsi_14,
            adx_14=snapshot.adx_14,
            ema_9=snapshot.ema_9,
            ema_21=snapshot.ema_21,
            ema_50=snapshot.ema_50,
            atr_14=snapshot.atr_14,
            bb_upper=snapshot.bb_upper,
            bb_middle=snapshot.bb_middle,
            bb_lower=snapshot.bb_lower,
            bb_width_pct=snapshot.bb_width_pct
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting indicators for {underlying}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting indicators: {str(e)}"
        )
