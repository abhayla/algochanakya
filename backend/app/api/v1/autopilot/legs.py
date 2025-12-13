"""
AutoPilot Leg Management API Routes - Phase 5B

Endpoints for per-leg actions: exit, shift, roll, break trade.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.database import get_async_db
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models.user import User
from app.models.broker import BrokerConnection
from app.schemas.autopilot import (
    PositionLegResponse,
    ExitLegRequest,
    ShiftLegRequest,
    RollLegRequest,
    BreakTradeRequest,
    BreakTradeResponse
)
from app.services.position_leg_service import PositionLegService
from app.services.leg_actions_service import LegActionsService
from app.services.break_trade_service import BreakTradeService

router = APIRouter()


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    kite = KiteConnect(api_key=broker_connection.api_key)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.get("/strategies/{strategy_id}/legs", response_model=List[PositionLegResponse])
async def get_strategy_legs(
    strategy_id: int,
    status_filter: str = None,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get all position legs for a strategy.

    Args:
        strategy_id: Strategy ID
        status_filter: Optional filter (open, closed, pending, rolled)

    Returns:
        List of position legs
    """
    try:
        service = PositionLegService(kite, db)
        legs = await service.get_all_strategy_legs(
            strategy_id=strategy_id,
            status_filter=status_filter
        )
        return legs

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching strategy legs: {str(e)}"
        )


@router.get("/strategies/{strategy_id}/legs/{leg_id}", response_model=PositionLegResponse)
async def get_position_leg(
    strategy_id: int,
    leg_id: str,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get a single position leg.

    Args:
        strategy_id: Strategy ID
        leg_id: Leg identifier

    Returns:
        Position leg details
    """
    try:
        service = PositionLegService(kite, db)
        leg = await service.get_position_leg(strategy_id, leg_id)

        if not leg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Position leg {leg_id} not found"
            )

        return leg

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching position leg: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/legs/{leg_id}/exit")
async def exit_leg(
    strategy_id: int,
    leg_id: str,
    request: ExitLegRequest,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Exit a single position leg.

    Args:
        strategy_id: Strategy ID
        leg_id: Leg identifier
        request: Exit request with execution mode and limit price

    Returns:
        Exit result with order details
    """
    try:
        service = LegActionsService(kite, db, str(user.id))
        result = await service.exit_leg(
            strategy_id=strategy_id,
            leg_id=leg_id,
            execution_mode=request.execution_mode,
            limit_price=request.limit_price
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exiting leg: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/legs/{leg_id}/shift")
async def shift_leg(
    strategy_id: int,
    leg_id: str,
    request: ShiftLegRequest,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Shift a leg to a new strike (same expiry).

    Can specify:
    - target_strike: Specific strike to move to
    - target_delta: Find strike by delta
    - shift_direction + shift_amount: Move closer/further by points

    Args:
        strategy_id: Strategy ID
        leg_id: Leg identifier
        request: Shift request parameters

    Returns:
        Shift result with old and new leg details
    """
    try:
        service = LegActionsService(kite, db, str(user.id))
        result = await service.shift_leg(
            strategy_id=strategy_id,
            leg_id=leg_id,
            target_strike=request.target_strike,
            target_delta=request.target_delta,
            shift_direction=request.shift_direction,
            shift_amount=request.shift_amount,
            execution_mode=request.execution_mode,
            limit_offset=request.limit_offset
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error shifting leg: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/legs/{leg_id}/roll")
async def roll_leg(
    strategy_id: int,
    leg_id: str,
    request: RollLegRequest,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Roll a leg to a new expiry (and optionally new strike).

    Args:
        strategy_id: Strategy ID
        leg_id: Leg identifier
        request: Roll request with target expiry and optional strike

    Returns:
        Roll result with cost/credit
    """
    try:
        service = LegActionsService(kite, db, str(user.id))
        result = await service.roll_leg(
            strategy_id=strategy_id,
            leg_id=leg_id,
            target_expiry=request.target_expiry,
            target_strike=request.target_strike,
            execution_mode=request.execution_mode
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rolling leg: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/legs/{leg_id}/break", response_model=BreakTradeResponse)
async def break_trade(
    strategy_id: int,
    leg_id: str,
    request: BreakTradeRequest,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Execute break/split trade on a losing leg.

    The break trade algorithm:
    1. Exit the losing leg at current market price
    2. Calculate recovery premium = exit_price / 2
    3. Find new PUT strike with ~recovery premium
    4. Find new CALL strike with ~recovery premium
    5. Sell both new strikes to create a strangle

    Args:
        strategy_id: Strategy ID
        leg_id: Leg to break
        request: Break trade parameters

    Returns:
        Break trade result with new positions
    """
    try:
        service = BreakTradeService(kite, db, str(user.id))
        result = await service.break_trade(
            strategy_id=strategy_id,
            leg_id=leg_id,
            execution_mode=request.execution_mode,
            new_positions=request.new_positions,
            new_put_strike=request.new_put_strike,
            new_call_strike=request.new_call_strike,
            premium_split=request.premium_split,
            prefer_round_strikes=request.prefer_round_strikes,
            max_delta=request.max_delta
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing break trade: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/legs/{leg_id}/break/simulate")
async def simulate_break_trade(
    strategy_id: int,
    leg_id: str,
    premium_split: str = "equal",
    prefer_round_strikes: bool = True,
    max_delta: float = 0.30,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Simulate a break trade without executing.

    Shows what would happen if the break trade is executed:
    - Exit cost
    - Suggested new strikes
    - Expected premium received
    - Net cost

    Args:
        strategy_id: Strategy ID
        leg_id: Leg to simulate breaking
        premium_split: 'equal' or 'weighted'
        prefer_round_strikes: Prefer round strikes
        max_delta: Maximum delta for new positions

    Returns:
        Simulation results
    """
    try:
        from decimal import Decimal

        service = BreakTradeService(kite, db, str(user.id))
        result = await service.simulate_break_trade(
            strategy_id=strategy_id,
            leg_id=leg_id,
            premium_split=premium_split,
            prefer_round_strikes=prefer_round_strikes,
            max_delta=Decimal(str(max_delta))
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error simulating break trade: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/legs/update-greeks")
async def update_all_legs_greeks(
    strategy_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Update Greeks for all open legs in a strategy.

    Fetches current market prices and calculates:
    - Delta, Gamma, Theta, Vega
    - Implied Volatility
    - Unrealized P&L

    Args:
        strategy_id: Strategy ID

    Returns:
        Updated legs count
    """
    try:
        from app.models.autopilot import AutoPilotStrategy

        # Get strategy to get underlying
        strategy = await db.get(AutoPilotStrategy, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )

        # Get spot price
        from app.services.market_data import MarketDataService
        market_data = MarketDataService(kite)
        spot_data = await market_data.get_spot_price(strategy.underlying)

        if not spot_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot get spot price for {strategy.underlying}"
            )

        # Update all legs
        service = PositionLegService(kite, db)
        updated_legs = await service.update_all_legs_greeks(
            strategy_id=strategy_id,
            spot_price=spot_data.ltp
        )

        return {
            "strategy_id": strategy_id,
            "legs_updated": len(updated_legs),
            "spot_price": spot_data.ltp,
            "updated_at": str(updated_legs[0].updated_at) if updated_legs else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating legs Greeks: {str(e)}"
        )
