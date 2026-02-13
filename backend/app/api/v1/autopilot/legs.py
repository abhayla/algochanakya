"""
AutoPilot Leg Management API Routes - Phase 5B

Endpoints for per-leg actions: exit, shift, roll, break trade.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.database import get_db
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models import User, BrokerConnection
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
from app.services.delta_rebalance_service import DeltaRebalanceService

router = APIRouter()


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    from app.config import settings
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.get("/strategies/{strategy_id}/legs", response_model=List[PositionLegResponse])
async def get_strategy_legs(
    strategy_id: int,
    status_filter: str = None,
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
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
        from app.services.legacy.market_data import MarketDataService
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


@router.post("/strategies/{strategy_id}/assess-delta-risk")
async def assess_delta_risk(
    strategy_id: int,
    delta_band_type: str = "moderate",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Assess delta risk for a strategy.

    Feature #38: Delta Neutral Rebalance

    Analyzes current delta and determines if rebalancing is needed.
    Returns suggested actions if delta has drifted outside acceptable bands.

    Args:
        strategy_id: Strategy ID
        delta_band_type: Band preset ('conservative', 'moderate', 'aggressive')

    Returns:
        {
            "current_delta": float,
            "delta_status": str,  # "safe", "warning", "critical"
            "band_type": str,
            "warning_threshold": float,
            "critical_threshold": float,
            "rebalance_needed": bool,
            "suggested_actions": List[Dict],
            "directional_bias": str  # "bullish", "bearish", "neutral"
        }
    """
    try:
        from app.models.autopilot import AutoPilotStrategy

        # Get strategy
        strategy = await db.get(AutoPilotStrategy, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )

        # Verify ownership
        if strategy.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this strategy"
            )

        # Assess delta risk
        service = DeltaRebalanceService(kite, db)
        assessment = await service.assess_delta_risk(
            strategy=strategy,
            delta_band_type=delta_band_type
        )

        return assessment

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error assessing delta risk: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/rebalance-delta")
async def rebalance_delta(
    strategy_id: int,
    action_index: int = 0,
    delta_band_type: str = "moderate",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Execute delta rebalancing action.

    Feature #38: Delta Neutral Rebalance

    Executes one of the suggested rebalancing actions to bring
    delta back to neutral range.

    Args:
        strategy_id: Strategy ID
        action_index: Index of suggested action to execute (default 0 = highest priority)
        delta_band_type: Band preset used for assessment

    Returns:
        {
            "action_executed": str,
            "previous_delta": float,
            "new_delta": float,
            "delta_change": float,
            "execution_details": Dict
        }
    """
    try:
        from app.models.autopilot import AutoPilotStrategy

        # Get strategy
        strategy = await db.get(AutoPilotStrategy, strategy_id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )

        # Verify ownership
        if strategy.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this strategy"
            )

        # Get assessment and suggested actions
        service = DeltaRebalanceService(kite, db)
        assessment = await service.assess_delta_risk(
            strategy=strategy,
            delta_band_type=delta_band_type
        )

        if not assessment.get('rebalance_needed'):
            return {
                "action_executed": "none",
                "message": "Delta is within acceptable range, no rebalancing needed",
                "current_delta": assessment['current_delta'],
                "delta_status": assessment['delta_status']
            }

        suggested_actions = assessment.get('suggested_actions', [])
        if not suggested_actions or action_index >= len(suggested_actions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action_index: {action_index}. Available actions: {len(suggested_actions)}"
            )

        # Get the selected action
        selected_action = suggested_actions[action_index]
        action_type = selected_action['action_type']
        previous_delta = assessment['current_delta']

        # Execute the action via adjustment engine
        from app.services.adjustment_engine import AdjustmentEngine
        adj_engine = AdjustmentEngine(kite, db, str(user.id))

        execution_result = None

        if action_type == "add_opposite_side":
            # Execute add to opposite side action
            execution_result = await adj_engine._action_add_to_opposite(
                strategy=strategy,
                params={
                    'option_type': selected_action['option_type'],
                    'strike': selected_action['strike'],
                    'lots': 1,
                    'execution_mode': 'market'
                }
            )

        elif action_type == "shift_leg":
            # Execute shift leg action
            from app.services.leg_actions_service import LegActionsService
            leg_service = LegActionsService(kite, db, str(user.id))

            direction = selected_action['direction']
            current_strike = selected_action['current_strike']

            # Determine shift amount (move 1 strike in direction)
            shift_amount = 100 if direction == "farther_up" else -100

            execution_result = await leg_service.shift_leg(
                strategy_id=strategy_id,
                leg_id=selected_action['leg_id'],
                shift_direction=direction,
                shift_amount=shift_amount,
                execution_mode='market'
            )

        elif action_type == "close_leg":
            # Execute close leg action
            from app.services.leg_actions_service import LegActionsService
            leg_service = LegActionsService(kite, db, str(user.id))

            execution_result = await leg_service.exit_leg(
                strategy_id=strategy_id,
                leg_id=selected_action['leg_id'],
                execution_mode='market'
            )

        # Refresh strategy to get new delta
        await db.refresh(strategy)
        new_delta = float(strategy.net_delta) if strategy.net_delta else 0.0
        delta_change = new_delta - previous_delta

        return {
            "action_executed": action_type,
            "action_description": selected_action.get('description', ''),
            "previous_delta": previous_delta,
            "new_delta": new_delta,
            "delta_change": delta_change,
            "execution_details": execution_result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing delta rebalance: {str(e)}"
        )
