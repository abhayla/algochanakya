"""
Orders API Routes

Basket orders, positions, and order management via broker abstraction layer.
Market data endpoints route to SmartAPI or Kite based on user preference.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models import User, BrokerConnection, Strategy, StrategyLeg, Instrument
from app.models.user_preferences import UserPreferences, MarketDataSource
from app.models.broker_api_credentials import BrokerAPICredentials
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
from app.services.legacy.kite_orders import parse_positions_to_legs
from app.services.brokers import (
    get_broker_adapter,
    BrokerType,
    BrokerAdapter,
    positions_to_legacy_format,
    orders_to_legacy_format,
)
from app.utils.dependencies import get_current_user, get_current_broker_connection, get_broker_adapter_dep
from app.utils.smartapi_utils import get_valid_smartapi_credentials
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
    Get user's AngelOne market data credentials if configured.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        BrokerAPICredentials or None
    """
    result = await db.execute(
        select(BrokerAPICredentials).where(
            BrokerAPICredentials.user_id == user_id,
            BrokerAPICredentials.broker == "angelone",
            BrokerAPICredentials.is_active == True
        )
    )
    return result.scalar_one_or_none()


@router.post("/basket", response_model=BasketOrderResponse)
async def place_basket_order(
    request: BasketOrderRequest,
    user: User = Depends(get_current_user),
    adapter: BrokerAdapter = Depends(get_broker_adapter_dep),
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
        # Filter by source_broker to avoid duplicates from multiple instrument sources
        instrument_tokens = [leg.instrument_token for leg in request.legs]
        result = await db.execute(
            select(Instrument).where(
                and_(
                    Instrument.instrument_token.in_(instrument_tokens),
                    Instrument.source_broker == "kite",
                )
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

        # Place orders via broker adapter
        order_results = await adapter.place_basket_order(order_legs)

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
    except Exception as e:
        # Check for broker-specific token errors
        error_msg = str(e).lower()
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Broker session expired. Please login again. ({str(e)})"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to place basket order: {str(e)}"
        )


@router.get("/positions")
async def get_positions(
    underlying: Optional[str] = Query(None, description="Filter by underlying"),
    user: User = Depends(get_current_user),
    adapter: BrokerAdapter = Depends(get_broker_adapter_dep)
):
    """
    Get current positions from broker.

    Args:
        underlying: Optional filter for underlying

    Returns:
        Positions data
    """
    try:
        # Get positions via broker adapter (returns List[UnifiedPosition])
        unified_positions = await adapter.get_positions()

        # Convert to legacy format for backward compatibility
        positions = positions_to_legacy_format(unified_positions)

        # Parse to leg format if underlying specified
        if underlying:
            legs = parse_positions_to_legs(positions, underlying)
            return {
                "positions": positions,
                "legs": legs
            }

        return positions

    except Exception as e:
        # Check for broker-specific token errors
        error_msg = str(e).lower()
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Broker session expired. Please login again. ({str(e)})"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get positions: {str(e)}"
        )


@router.post("/import-positions", response_model=ImportPositionsResponse)
async def import_positions(
    underlying: str = Query(..., description="Underlying to import (NIFTY, BANKNIFTY, FINNIFTY)"),
    user: User = Depends(get_current_user),
    adapter: BrokerAdapter = Depends(get_broker_adapter_dep),
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

        # Get positions via broker adapter
        unified_positions = await adapter.get_positions()
        positions = positions_to_legacy_format(unified_positions)

        # Parse positions to legs
        position_legs = parse_positions_to_legs(positions, underlying)

        if not position_legs:
            return ImportPositionsResponse(positions=[], legs=[])

        # Get instrument details for positions
        # Filter by source_broker to avoid duplicates from multiple instrument sources
        instrument_tokens = [leg["instrument_token"] for leg in position_legs]
        result = await db.execute(
            select(Instrument).where(
                and_(
                    Instrument.instrument_token.in_(instrument_tokens),
                    Instrument.source_broker == "kite",
                )
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
    except Exception as e:
        # Check for broker-specific token errors
        error_msg = str(e).lower()
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Broker session expired. Please login again. ({str(e)})"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import positions: {str(e)}"
        )


@router.get("/orders")
async def get_orders(
    user: User = Depends(get_current_user),
    adapter: BrokerAdapter = Depends(get_broker_adapter_dep)
):
    """
    Get today's orders from broker.

    Returns:
        List of orders
    """
    try:
        # Get orders via broker adapter (returns List[UnifiedOrder])
        unified_orders = await adapter.get_orders()

        # Convert to legacy format for backward compatibility
        orders = orders_to_legacy_format(unified_orders)
        return orders

    except Exception as e:
        # Check for broker-specific token errors
        error_msg = str(e).lower()
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Broker session expired. Please login again. ({str(e)})"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get orders: {str(e)}"
        )


@router.get("/margins")
async def get_margins(
    user: User = Depends(get_current_user),
    adapter: BrokerAdapter = Depends(get_broker_adapter_dep)
):
    """
    Get account margins from broker.

    Returns:
        Margin details
    """
    try:
        # Get margins via broker adapter
        margins = await adapter.get_margins()
        return margins

    except Exception as e:
        # Check for broker-specific token errors
        error_msg = str(e).lower()
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Broker session expired. Please login again. ({str(e)})"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get margins: {str(e)}"
        )


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    user: User = Depends(get_current_user),
    adapter: BrokerAdapter = Depends(get_broker_adapter_dep)
):
    """
    Cancel an order.

    Args:
        order_id: Broker order ID

    Returns:
        Cancellation result
    """
    try:
        # Cancel order via broker adapter
        result = await adapter.cancel_order(order_id)
        return {"success": True, "order_id": result}

    except Exception as e:
        # Check for broker-specific token errors
        error_msg = str(e).lower()
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Broker session expired. Please login again. ({str(e)})"
            )
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
    Uses user's preferred market data broker (SmartAPI or Kite).

    Args:
        instruments: Comma-separated instruments (e.g., NFO:NIFTY25APR25000CE,NSE:NIFTY)

    Returns:
        LTP data in format: {"EXCHANGE:SYMBOL": {"last_price": float}}
    """
    from app.services.brokers.market_data import get_user_market_data_adapter

    try:
        instrument_list = [i.strip() for i in instruments.split(",")]

        # Get market data adapter (automatically uses user's preferred broker)
        adapter = await get_user_market_data_adapter(user.id, db)

        # Extract canonical symbols (remove EXCHANGE: prefix)
        canonical_symbols = []
        symbol_map = {}  # canonical -> original format
        for inst in instrument_list:
            if ":" in inst:
                exchange, symbol = inst.split(":", 1)
                canonical_symbols.append(symbol)
                symbol_map[symbol] = inst
            else:
                canonical_symbols.append(inst)
                symbol_map[inst] = inst

        # Get LTP via adapter (returns Decimal values)
        ltp_data = await adapter.get_ltp(canonical_symbols)

        # Convert to expected format with original keys
        result = {}
        for canonical_symbol, ltp_decimal in ltp_data.items():
            original_key = symbol_map.get(canonical_symbol, canonical_symbol)
            result[original_key] = {'last_price': float(ltp_decimal)}

        return result

    except Exception as e:
        logger.error(f"[Orders] Failed to get LTP: {e}")
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
    Uses user's preferred market data broker (SmartAPI or Kite).

    Args:
        instruments: Comma-separated instruments (e.g., NSE:NIFTY 50,NFO:NIFTY25APR25000CE)

    Returns:
        Quote data with OHLC, bid/ask spreads, volume, and depth
    """
    from app.services.brokers.market_data import get_user_market_data_adapter

    try:
        instrument_list = [i.strip() for i in instruments.split(",")]

        # Get market data adapter (automatically uses user's preferred broker)
        adapter = await get_user_market_data_adapter(user.id, db)

        # Extract canonical symbols (remove EXCHANGE: prefix)
        canonical_symbols = []
        symbol_map = {}  # canonical -> original format
        for inst in instrument_list:
            if ":" in inst:
                exchange, symbol = inst.split(":", 1)
                canonical_symbols.append(symbol)
                symbol_map[symbol] = inst
            else:
                canonical_symbols.append(inst)
                symbol_map[inst] = inst

        # Get quotes via adapter (returns UnifiedQuote objects)
        quote_data = await adapter.get_quote(canonical_symbols)

        # Convert to expected format with original keys
        result = {}
        for canonical_symbol, unified_quote in quote_data.items():
            original_key = symbol_map.get(canonical_symbol, canonical_symbol)
            result[original_key] = {
                'instrument_token': unified_quote.instrument_token,
                'last_price': float(unified_quote.last_price),
                'ohlc': {
                    'open': float(unified_quote.open),
                    'high': float(unified_quote.high),
                    'low': float(unified_quote.low),
                    'close': float(unified_quote.close),
                },
                'volume': unified_quote.volume,
                'oi': unified_quote.oi,
                'depth': {
                    'buy': [{'price': float(unified_quote.bid_price), 'quantity': unified_quote.bid_quantity}] if unified_quote.bid_price else [],
                    'sell': [{'price': float(unified_quote.ask_price), 'quantity': unified_quote.ask_quantity}] if unified_quote.ask_price else []
                },
            }

        return result

    except Exception as e:
        logger.error(f"[Orders] Failed to get quote: {e}")
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
    Uses user's preferred market data broker (SmartAPI or Kite).

    Args:
        instruments: Comma-separated instruments (e.g., NSE:NIFTY 50,NFO:NIFTY25APR25000CE)

    Returns:
        OHLC data with open, high, low, close, and last_price
    """
    from app.services.brokers.market_data import get_user_market_data_adapter

    try:
        instrument_list = [i.strip() for i in instruments.split(",")]

        # Get market data adapter (automatically uses user's preferred broker)
        adapter = await get_user_market_data_adapter(user.id, db)

        # Extract canonical symbols (remove EXCHANGE: prefix)
        canonical_symbols = []
        symbol_map = {}  # canonical -> original format
        for inst in instrument_list:
            if ":" in inst:
                exchange, symbol = inst.split(":", 1)
                canonical_symbols.append(symbol)
                symbol_map[symbol] = inst
            else:
                canonical_symbols.append(inst)
                symbol_map[inst] = inst

        # Get quotes via adapter (returns UnifiedQuote objects)
        quote_data = await adapter.get_quote(canonical_symbols)

        # Convert to OHLC format with original keys
        result = {}
        for canonical_symbol, unified_quote in quote_data.items():
            original_key = symbol_map.get(canonical_symbol, canonical_symbol)
            result[original_key] = {
                'instrument_token': unified_quote.instrument_token,
                'last_price': float(unified_quote.last_price),
                'ohlc': {
                    'open': float(unified_quote.open),
                    'high': float(unified_quote.high),
                    'low': float(unified_quote.low),
                    'close': float(unified_quote.close),
                },
            }

        return result

    except Exception as e:
        logger.error(f"[Orders] Failed to get OHLC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OHLC: {str(e)}"
        )
