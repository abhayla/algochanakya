"""
Orders API Routes

Basket orders, positions, and order management via Kite Connect.
Market data endpoints route to SmartAPI or Kite based on user preference.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID
from kiteconnect.exceptions import TokenException

from app.database import get_db
from app.models import User, BrokerConnection, Strategy, StrategyLeg, Instrument
from app.models.user_preferences import UserPreferences, MarketDataSource
from app.models.smartapi_credentials import SmartAPICredentials
from app.schemas.strategies import (
    BasketOrderRequest,
    BasketOrderResponse,
    BasketOrderResult,
    ImportedPosition,
    ImportPositionsResponse,
    StrategyLegCreate,
    ContractType,
    TransactionType,
)
from app.services.kite_orders import KiteOrderService, parse_positions_to_legs
from app.services.smartapi_market_data import create_market_data_service
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_market_data_source(user_id, db: AsyncSession) -> str:
    """
    Get user's preferred market data source.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Market data source ('smartapi' or 'kite')
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()

    if preferences and preferences.market_data_source:
        return preferences.market_data_source

    return MarketDataSource.SMARTAPI  # Default to SmartAPI


async def get_smartapi_credentials(user_id, db: AsyncSession):
    """
    Get user's SmartAPI credentials if configured.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        SmartAPICredentials or None
    """
    result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user_id,
            SmartAPICredentials.is_active == True
        )
    )
    return result.scalar_one_or_none()


@router.post("/basket", response_model=BasketOrderResponse)
async def place_basket_order(
    request: BasketOrderRequest,
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Place basket order for strategy legs.

    Args:
        request: Basket order request with legs

    Returns:
        Order results for each leg
    """
    try:
        if not request.legs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one leg is required"
            )

        # Get trading symbols for instrument tokens
        instrument_tokens = [leg.instrument_token for leg in request.legs]
        result = await db.execute(
            select(Instrument).where(
                Instrument.instrument_token.in_(instrument_tokens)
            )
        )
        instruments = {inst.instrument_token: inst for inst in result.scalars().all()}

        # Build order legs with trading symbols
        order_legs = []
        for leg in request.legs:
            instrument = instruments.get(leg.instrument_token)
            if not instrument:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Instrument not found for token: {leg.instrument_token}"
                )

            order_legs.append({
                "tradingsymbol": instrument.tradingsymbol,
                "exchange": instrument.exchange,
                "transaction_type": leg.transaction_type.value,
                "quantity": leg.quantity,
                "price": float(leg.price) if leg.price else None,
                "order_type": leg.order_type,
            })

        # Place orders via Kite
        kite_service = KiteOrderService(broker.access_token)
        order_results = await kite_service.place_basket_order(order_legs)

        # Update strategy legs with order IDs if strategy_id provided
        if request.strategy_id:
            for i, order_result in enumerate(order_results):
                if order_result.get("success"):
                    leg_token = request.legs[i].instrument_token
                    await db.execute(
                        select(StrategyLeg).join(Strategy).where(
                            and_(
                                StrategyLeg.instrument_token == leg_token,
                                Strategy.id == request.strategy_id,
                                Strategy.user_id == user.id
                            )
                        )
                    )
                    # Update the first matching leg with order ID
                    leg_result = await db.execute(
                        select(StrategyLeg).join(Strategy).where(
                            and_(
                                StrategyLeg.instrument_token == leg_token,
                                Strategy.id == request.strategy_id,
                                Strategy.user_id == user.id,
                                StrategyLeg.order_id.is_(None)
                            )
                        )
                    )
                    leg = leg_result.scalar_one_or_none()
                    if leg:
                        leg.order_id = order_result.get("order_id")
                        leg.position_status = "executed"

            await db.commit()

        # Build response
        results = [
            BasketOrderResult(
                instrument_token=request.legs[i].instrument_token,
                success=r.get("success", False),
                order_id=r.get("order_id"),
                error=r.get("error")
            )
            for i, r in enumerate(order_results)
        ]

        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful

        return BasketOrderResponse(
            success=failed == 0,
            results=results,
            total_orders=len(results),
            successful_orders=successful,
            failed_orders=failed
        )

    except HTTPException:
        raise
    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place basket order: {str(e)}"
        )


@router.get("/positions")
async def get_positions(
    underlying: Optional[str] = Query(None, description="Filter by underlying"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection)
):
    """
    Get current positions from Kite.

    Args:
        underlying: Optional filter for underlying

    Returns:
        Positions data
    """
    try:
        kite_service = KiteOrderService(broker.access_token)
        positions = await kite_service.get_positions()

        # Parse to leg format if underlying specified
        if underlying:
            legs = parse_positions_to_legs(positions, underlying)
            return {
                "positions": positions,
                "legs": legs
            }

        return positions

    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )


@router.post("/import-positions", response_model=ImportPositionsResponse)
async def import_positions(
    underlying: str = Query(..., description="Underlying to import (NIFTY, BANKNIFTY, FINNIFTY)"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Import existing positions from broker as strategy legs.

    Args:
        underlying: Underlying to filter positions

    Returns:
        Imported positions and generated legs
    """
    try:
        underlying = underlying.upper()
        if underlying not in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Underlying must be NIFTY, BANKNIFTY, or FINNIFTY"
            )

        kite_service = KiteOrderService(broker.access_token)
        positions = await kite_service.get_positions()

        # Parse positions to legs
        position_legs = parse_positions_to_legs(positions, underlying)

        if not position_legs:
            return ImportPositionsResponse(positions=[], legs=[])

        # Get instrument details for positions
        instrument_tokens = [leg["instrument_token"] for leg in position_legs]
        result = await db.execute(
            select(Instrument).where(
                Instrument.instrument_token.in_(instrument_tokens)
            )
        )
        instruments = {inst.instrument_token: inst for inst in result.scalars().all()}

        # Build imported positions and strategy legs
        imported_positions = []
        strategy_legs = []

        for pos_leg in position_legs:
            instrument = instruments.get(pos_leg["instrument_token"])
            if not instrument:
                continue

            # Build imported position
            imported_positions.append(ImportedPosition(
                tradingsymbol=pos_leg["tradingsymbol"],
                instrument_token=pos_leg["instrument_token"],
                exchange=pos_leg["exchange"],
                quantity=pos_leg["quantity"],
                average_price=pos_leg["entry_price"],
                last_price=pos_leg["last_price"],
                pnl=pos_leg["pnl"]
            ))

            # Build strategy leg
            contract_type = ContractType.CE if instrument.instrument_type == "CE" else ContractType.PE
            transaction_type = TransactionType.BUY if pos_leg["transaction_type"] == "BUY" else TransactionType.SELL

            # Calculate lots
            lot_size = instrument.lot_size or 1
            lots = pos_leg["quantity"] // lot_size

            strategy_legs.append(StrategyLegCreate(
                expiry_date=instrument.expiry,
                contract_type=contract_type,
                transaction_type=transaction_type,
                strike_price=instrument.strike,
                lots=lots,
                entry_price=pos_leg["entry_price"],
                instrument_token=pos_leg["instrument_token"]
            ))

        return ImportPositionsResponse(
            positions=imported_positions,
            legs=strategy_legs
        )

    except HTTPException:
        raise
    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import positions: {str(e)}"
        )


@router.get("/orders")
async def get_orders(
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection)
):
    """
    Get today's orders from Kite.

    Returns:
        List of orders
    """
    try:
        kite_service = KiteOrderService(broker.access_token)
        orders = await kite_service.get_orders()
        return orders

    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}"
        )


@router.get("/margins")
async def get_margins(
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection)
):
    """
    Get account margins from Kite.

    Returns:
        Margin details
    """
    try:
        kite_service = KiteOrderService(broker.access_token)
        margins = await kite_service.get_margins()
        return margins

    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get margins: {str(e)}"
        )


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection)
):
    """
    Cancel an order.

    Args:
        order_id: Kite order ID

    Returns:
        Cancellation result
    """
    try:
        kite_service = KiteOrderService(broker.access_token)
        result = await kite_service.cancel_order(order_id)
        return {"success": True, "order_id": result}

    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )


@router.get("/ltp")
async def get_ltp(
    instruments: str = Query(..., description="Comma-separated instruments (EXCHANGE:SYMBOL)"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Get LTP for instruments.
    Routes to SmartAPI or Kite based on user preference.

    Args:
        instruments: Comma-separated instruments

    Returns:
        LTP data
    """
    try:
        instrument_list = [i.strip() for i in instruments.split(",")]

        # Check user's preferred market data source
        market_data_source = await get_user_market_data_source(user.id, db)

        # Try SmartAPI if preferred
        if market_data_source == MarketDataSource.SMARTAPI:
            credentials = await get_smartapi_credentials(user.id, db)
            if credentials and credentials.jwt_token:
                try:
                    logger.info(f"[Orders] Using SmartAPI for LTP: {len(instrument_list)} instruments")
                    smartapi_service = create_market_data_service(
                        api_key=settings.ANGEL_API_KEY,
                        jwt_token=credentials.jwt_token
                    )
                    ltp_data = await smartapi_service.get_ltp(instrument_list)

                    # Convert to Kite-compatible format
                    result = {}
                    for key, ltp in ltp_data.items():
                        result[key] = {'last_price': float(ltp)}

                    return result
                except Exception as e:
                    logger.warning(f"[Orders] SmartAPI LTP failed, falling back to Kite: {e}")
                    # Fall through to Kite

        # Use Kite (either as primary or fallback)
        logger.info(f"[Orders] Using Kite for LTP: {len(instrument_list)} instruments")
        kite_service = KiteOrderService(broker.access_token)
        ltp = await kite_service.get_ltp(instrument_list)
        return ltp

    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LTP: {str(e)}"
        )


@router.get("/quote")
async def get_quote(
    instruments: str = Query(..., description="Comma-separated instruments (EXCHANGE:SYMBOL)"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Get full quote for instruments (OHLC, bid/ask, volume).
    Routes to SmartAPI or Kite based on user preference.

    Args:
        instruments: Comma-separated instruments (e.g., NSE:NIFTY 50,NSE:NIFTY BANK)

    Returns:
        Quote data with OHLC, bid/ask spreads, and volume
    """
    try:
        instrument_list = [i.strip() for i in instruments.split(",")]

        # Check user's preferred market data source
        market_data_source = await get_user_market_data_source(user.id, db)

        # Try SmartAPI if preferred
        if market_data_source == MarketDataSource.SMARTAPI:
            credentials = await get_smartapi_credentials(user.id, db)
            if credentials and credentials.jwt_token:
                try:
                    logger.info(f"[Orders] Using SmartAPI for quote: {len(instrument_list)} instruments")
                    smartapi_service = create_market_data_service(
                        api_key=settings.ANGEL_API_KEY,
                        jwt_token=credentials.jwt_token
                    )
                    quote_data = await smartapi_service.get_full_quote(instrument_list)

                    # Convert to Kite-compatible format
                    result = {}
                    for key, quote in quote_data.items():
                        result[key] = {
                            'instrument_token': quote.get('token'),
                            'last_price': float(quote.get('ltp', 0)),
                            'ohlc': {
                                'open': float(quote.get('open', 0)),
                                'high': float(quote.get('high', 0)),
                                'low': float(quote.get('low', 0)),
                                'close': float(quote.get('close', 0)),
                            },
                            'volume': quote.get('volume', 0),
                            'oi': quote.get('oi', 0),
                            'depth': quote.get('depth', {'buy': [], 'sell': []}),
                        }

                    return result
                except Exception as e:
                    logger.warning(f"[Orders] SmartAPI quote failed, falling back to Kite: {e}")
                    # Fall through to Kite

        # Use Kite (either as primary or fallback)
        logger.info(f"[Orders] Using Kite for quote: {len(instrument_list)} instruments")
        kite_service = KiteOrderService(broker.access_token)
        quote = await kite_service.get_quote(instrument_list)
        return quote

    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quote: {str(e)}"
        )


@router.get("/ohlc")
async def get_ohlc(
    instruments: str = Query(..., description="Comma-separated instruments (EXCHANGE:SYMBOL)"),
    user: User = Depends(get_current_user),
    broker: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Get OHLC data for instruments. Works even outside market hours.
    Routes to SmartAPI or Kite based on user preference.

    Args:
        instruments: Comma-separated instruments (e.g., NSE:NIFTY 50,NSE:NIFTY BANK)

    Returns:
        OHLC data with open, high, low, close, and last_price
    """
    try:
        instrument_list = [i.strip() for i in instruments.split(",")]

        # Check user's preferred market data source
        market_data_source = await get_user_market_data_source(user.id, db)

        # Try SmartAPI if preferred
        if market_data_source == MarketDataSource.SMARTAPI:
            credentials = await get_smartapi_credentials(user.id, db)
            if credentials and credentials.jwt_token:
                try:
                    logger.info(f"[Orders] Using SmartAPI for OHLC: {len(instrument_list)} instruments")
                    smartapi_service = create_market_data_service(
                        api_key=settings.ANGEL_API_KEY,
                        jwt_token=credentials.jwt_token
                    )
                    quote_data = await smartapi_service.get_full_quote(instrument_list)

                    # Convert to Kite-compatible OHLC format
                    result = {}
                    for key, quote in quote_data.items():
                        result[key] = {
                            'instrument_token': quote.get('token'),
                            'last_price': float(quote.get('ltp', 0)),
                            'ohlc': {
                                'open': float(quote.get('open', 0)),
                                'high': float(quote.get('high', 0)),
                                'low': float(quote.get('low', 0)),
                                'close': float(quote.get('close', 0)),
                            },
                        }

                    return result
                except Exception as e:
                    logger.warning(f"[Orders] SmartAPI OHLC failed, falling back to Kite: {e}")
                    # Fall through to Kite

        # Use Kite (either as primary or fallback)
        logger.info(f"[Orders] Using Kite for OHLC: {len(instrument_list)} instruments")
        kite_service = KiteOrderService(broker.access_token)
        ohlc = await kite_service.get_ohlc(instrument_list)
        return ohlc

    except TokenException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Broker session expired. Please login again. ({str(e)})"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OHLC: {str(e)}"
        )
