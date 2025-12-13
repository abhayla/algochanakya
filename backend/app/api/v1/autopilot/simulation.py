"""
AutoPilot Simulation API Routes - Phase 5C

Endpoints for What-If simulation and scenario comparison.
"""
from datetime import date
from decimal import Decimal
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.database import get_async_db
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models.user import User
from app.models.broker import BrokerConnection
from app.services.whatif_simulator import WhatIfSimulator
from app.services.market_data import MarketDataService

router = APIRouter()


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    kite = KiteConnect(api_key=broker_connection.api_key)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.post("/{strategy_id}/shift")
async def simulate_shift(
    strategy_id: int,
    leg_id: str = Body(...),
    target_strike: Decimal = Body(None),
    target_delta: Decimal = Body(None),
    shift_amount: int = Body(None),
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Simulate shifting a leg to a new strike.

    Shows before/after comparison with impact metrics.

    Args:
        strategy_id: Strategy ID
        leg_id: Leg to shift
        target_strike: Specific target strike
        target_delta: Target delta for new strike
        shift_amount: Points to shift

    Returns:
        Simulation result with before/after comparison
    """
    try:
        market_data = MarketDataService(kite)
        simulator = WhatIfSimulator(kite, db, market_data)

        result = await simulator.simulate_shift(
            strategy_id=strategy_id,
            leg_id=leg_id,
            target_strike=target_strike,
            target_delta=target_delta,
            shift_amount=shift_amount
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
            detail=f"Error simulating shift: {str(e)}"
        )


@router.post("/{strategy_id}/roll")
async def simulate_roll(
    strategy_id: int,
    leg_id: str = Body(...),
    target_expiry: date = Body(...),
    target_strike: Decimal = Body(None),
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Simulate rolling a leg to new expiry.

    Shows roll cost, DTE analysis, and impact metrics.

    Args:
        strategy_id: Strategy ID
        leg_id: Leg to roll
        target_expiry: New expiry date
        target_strike: Optional new strike

    Returns:
        Simulation result with roll cost and impact
    """
    try:
        market_data = MarketDataService(kite)
        simulator = WhatIfSimulator(kite, db, market_data)

        result = await simulator.simulate_roll(
            strategy_id=strategy_id,
            leg_id=leg_id,
            target_expiry=target_expiry,
            target_strike=target_strike
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
            detail=f"Error simulating roll: {str(e)}"
        )


@router.post("/{strategy_id}/break")
async def simulate_break_trade(
    strategy_id: int,
    leg_id: str = Body(...),
    premium_split: str = Body("equal"),
    max_delta: Decimal = Body(Decimal('0.30')),
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Simulate break/split trade on a losing leg.

    Shows exit cost, recovery plan, and new positions.

    Args:
        strategy_id: Strategy ID
        leg_id: Leg to break
        premium_split: 'equal' or 'weighted'
        max_delta: Maximum delta for new positions

    Returns:
        Detailed simulation with exit cost and recovery strikes
    """
    try:
        market_data = MarketDataService(kite)
        simulator = WhatIfSimulator(kite, db, market_data)

        result = await simulator.simulate_break_trade(
            strategy_id=strategy_id,
            leg_id=leg_id,
            premium_split=premium_split,
            max_delta=max_delta
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


@router.post("/{strategy_id}/exit")
async def simulate_exit(
    strategy_id: int,
    exit_type: str = Body("full"),
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Simulate exiting the position (full or partial).

    Shows realized P&L impact.

    Args:
        strategy_id: Strategy ID
        exit_type: 'full' or 'partial'

    Returns:
        Exit simulation with P&L impact
    """
    try:
        market_data = MarketDataService(kite)
        simulator = WhatIfSimulator(kite, db, market_data)

        result = await simulator.simulate_exit(
            strategy_id=strategy_id,
            exit_type=exit_type
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
            detail=f"Error simulating exit: {str(e)}"
        )


@router.post("/{strategy_id}/compare")
async def compare_scenarios(
    strategy_id: int,
    scenarios: List[Dict[str, Any]] = Body(...),
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Compare multiple adjustment scenarios side-by-side.

    Automatically ranks scenarios by effectiveness.

    Args:
        strategy_id: Strategy ID
        scenarios: List of scenario configs, e.g.:
            [
                {"type": "shift", "leg_id": "leg1", "target_delta": 0.15},
                {"type": "break", "leg_id": "leg1"},
                {"type": "exit"}
            ]

    Returns:
        Side-by-side comparison with rankings
    """
    try:
        market_data = MarketDataService(kite)
        simulator = WhatIfSimulator(kite, db, market_data)

        result = await simulator.compare_scenarios(
            strategy_id=strategy_id,
            scenarios=scenarios
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
            detail=f"Error comparing scenarios: {str(e)}"
        )
