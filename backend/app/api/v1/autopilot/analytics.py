"""
AutoPilot Analytics API Routes - Phase 5C + Phase 5G

Endpoints for payoff charts, risk metrics, position analysis, and adjustment cost tracking.

Phase 5G Additions:
- GET /{strategy_id}/adjustment-costs - Get adjustment cost summary
- GET /{strategy_id}/adjustment-costs/threshold-check - Check cost threshold
- POST /{strategy_id}/adjustment-costs/project - Project cost impact
"""
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from kiteconnect import KiteConnect

from app.database import get_db
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models import User, BrokerConnection
from app.models.autopilot import AutoPilotStrategy
from app.services.options.payoff_calculator import PayoffCalculator
from app.services.market_data import MarketDataService
from app.services.adjustment_cost_tracker import AdjustmentCostTracker
from app.schemas.autopilot import AdjustmentCostSummary, AdjustmentCostThresholdCheck

router = APIRouter()


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    from app.config import settings
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.get("/{strategy_id}/payoff")
async def get_payoff_chart(
    strategy_id: int,
    mode: str = Query("expiry", pattern="^(expiry|current)$"),
    spot_range_pct: float = Query(10.0, ge=1.0, le=30.0),
    num_points: int = Query(100, ge=50, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get payoff chart data for a strategy.

    Two modes:
    - 'expiry': Intrinsic value at expiry (no time value)
    - 'current': Current value with time value (Black-Scholes)

    Returns:
        P/L grid with 100+ data points, breakevens, max profit/loss, risk metrics

    Args:
        strategy_id: Strategy ID
        mode: 'expiry' or 'current'
        spot_range_pct: Spot price range percentage (default 10%)
        num_points: Number of data points (default 100)

    Returns:
        {
            "spot_prices": [...],
            "pnl_values": [...],
            "current_spot": 24500,
            "breakeven_points": [24758, 25242],
            "max_profit": 15000,
            "max_profit_at": 25000,
            "max_loss": -5000,
            "max_loss_at": 24500,
            "risk_reward_ratio": 3.0,
            "probability_of_profit": 68.5,
            "net_credit": 2500
        }
    """
    try:
        market_data = MarketDataService(kite)
        calculator = PayoffCalculator(kite, db, market_data)

        result = await calculator.calculate_payoff(
            strategy_id=strategy_id,
            mode=mode,
            spot_range_pct=spot_range_pct,
            num_points=num_points
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
            detail=f"Error calculating payoff: {str(e)}"
        )


@router.get("/{strategy_id}/risk-metrics")
async def get_risk_metrics(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get risk metrics for a strategy.

    Returns detailed risk analysis including:
    - Max profit/loss
    - Breakeven points
    - Risk/reward ratio
    - Probability of profit
    - Net credit/debit

    Args:
        strategy_id: Strategy ID

    Returns:
        {
            "max_profit": 15000,
            "max_profit_at": 25000,
            "max_loss": -5000,
            "max_loss_at": 24500,
            "breakeven_points": [24758, 25242],
            "risk_reward_ratio": 3.0,
            "probability_of_profit": 68.5,
            "net_credit": 2500,
            "margin_required": 45000,
            "roi_potential": 33.3
        }
    """
    try:
        market_data = MarketDataService(kite)
        calculator = PayoffCalculator(kite, db, market_data)

        # Calculate at expiry for risk metrics
        payoff = await calculator.calculate_payoff(
            strategy_id=strategy_id,
            mode='expiry'
        )

        # Extract risk metrics
        risk_metrics = {
            "max_profit": payoff.get("max_profit"),
            "max_profit_at": payoff.get("max_profit_at"),
            "max_loss": payoff.get("max_loss"),
            "max_loss_at": payoff.get("max_loss_at"),
            "breakeven_points": payoff.get("breakeven_points", []),
            "risk_reward_ratio": payoff.get("risk_reward_ratio"),
            "probability_of_profit": payoff.get("probability_of_profit"),
            "net_credit": payoff.get("net_credit")
        }

        # Add margin and ROI if available
        from sqlalchemy import select
        from app.models.autopilot import AutoPilotStrategy

        result = await db.execute(
            select(AutoPilotStrategy).where(
                AutoPilotStrategy.id == strategy_id,
                AutoPilotStrategy.user_id == user.id
            )
        )
        strategy = result.scalar_one_or_none()

        if strategy and strategy.runtime_state:
            margin = strategy.runtime_state.get('margin_required') or strategy.runtime_state.get('margin_used')
            if margin:
                risk_metrics['margin_required'] = margin
                if risk_metrics['max_profit'] and margin:
                    risk_metrics['roi_potential'] = round((risk_metrics['max_profit'] / margin) * 100, 2)

        return risk_metrics

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating risk metrics: {str(e)}"
        )


@router.get("/{strategy_id}/breakevens")
async def get_breakevens(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get breakeven points for a strategy.

    Returns accurate breakeven calculation using linear interpolation.

    Args:
        strategy_id: Strategy ID

    Returns:
        {
            "breakeven_points": [24758, 25242],
            "current_spot": 24500,
            "distance_to_lower": -258,
            "distance_to_upper": 742,
            "pct_to_lower": -1.05,
            "pct_to_upper": 3.03
        }
    """
    try:
        market_data = MarketDataService(kite)
        calculator = PayoffCalculator(kite, db, market_data)

        # Calculate at expiry
        payoff = await calculator.calculate_payoff(
            strategy_id=strategy_id,
            mode='expiry'
        )

        breakevens = payoff.get("breakeven_points", [])
        current_spot = payoff.get("current_spot")

        result = {
            "breakeven_points": breakevens,
            "current_spot": current_spot
        }

        if breakevens and current_spot:
            if len(breakevens) >= 1:
                lower = breakevens[0]
                result['distance_to_lower'] = round(current_spot - lower, 2)
                result['pct_to_lower'] = round((current_spot - lower) / lower * 100, 2)

            if len(breakevens) >= 2:
                upper = breakevens[-1]
                result['distance_to_upper'] = round(upper - current_spot, 2)
                result['pct_to_upper'] = round((upper - current_spot) / current_spot * 100, 2)

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating breakevens: {str(e)}"
        )


@router.post("/{strategy_id}/pnl-at-spot")
async def calculate_pnl_at_spot(
    strategy_id: int,
    spot_price: Decimal = Body(...),
    mode: str = Body("expiry"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Calculate P&L at a specific spot price.

    Useful for what-if analysis at custom spot prices.

    Args:
        strategy_id: Strategy ID
        spot_price: Target spot price
        mode: 'expiry' or 'current'

    Returns:
        {
            "spot_price": 25000,
            "pnl": 12500,
            "pnl_pct": 27.78,
            "is_profit": true,
            "distance_from_current": 500,
            "pct_move_required": 2.04
        }
    """
    try:
        market_data = MarketDataService(kite)
        calculator = PayoffCalculator(kite, db, market_data)

        result = await calculator.calculate_pnl_at_spot(
            strategy_id=strategy_id,
            spot_price=float(spot_price),
            mode=mode
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
            detail=f"Error calculating P&L at spot: {str(e)}"
        )


@router.get("/{strategy_id}/profit-zones")
async def get_profit_zones(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get profit/loss zones for a strategy.

    Identifies continuous ranges where strategy is profitable or losing.

    Args:
        strategy_id: Strategy ID

    Returns:
        {
            "profit_zones": [
                {"start": 24758, "end": 25242, "max_profit": 15000}
            ],
            "loss_zones": [
                {"start": 24000, "end": 24758, "max_loss": -5000},
                {"start": 25242, "end": 26000, "max_loss": -5000}
            ],
            "unlimited_profit": false,
            "unlimited_loss": false
        }
    """
    try:
        market_data = MarketDataService(kite)
        calculator = PayoffCalculator(kite, db, market_data)

        # Calculate payoff
        payoff = await calculator.calculate_payoff(
            strategy_id=strategy_id,
            mode='expiry'
        )

        spot_prices = payoff.get("spot_prices", [])
        pnl_values = payoff.get("pnl_values", [])

        if not spot_prices or not pnl_values:
            raise ValueError("No payoff data available")

        # Identify zones
        profit_zones = []
        loss_zones = []
        current_zone = None
        zone_start = None
        zone_max_pnl = None

        for i, (spot, pnl) in enumerate(zip(spot_prices, pnl_values)):
            if pnl >= 0:
                # Profit zone
                if current_zone != 'profit':
                    # Start new profit zone
                    if current_zone == 'loss' and zone_start is not None:
                        # Close previous loss zone
                        loss_zones.append({
                            "start": zone_start,
                            "end": spot_prices[i-1] if i > 0 else zone_start,
                            "max_loss": zone_max_pnl
                        })
                    current_zone = 'profit'
                    zone_start = spot
                    zone_max_pnl = pnl
                else:
                    # Continue profit zone
                    if pnl > zone_max_pnl:
                        zone_max_pnl = pnl
            else:
                # Loss zone
                if current_zone != 'loss':
                    # Start new loss zone
                    if current_zone == 'profit' and zone_start is not None:
                        # Close previous profit zone
                        profit_zones.append({
                            "start": zone_start,
                            "end": spot_prices[i-1] if i > 0 else zone_start,
                            "max_profit": zone_max_pnl
                        })
                    current_zone = 'loss'
                    zone_start = spot
                    zone_max_pnl = pnl
                else:
                    # Continue loss zone
                    if pnl < zone_max_pnl:
                        zone_max_pnl = pnl

        # Close final zone
        if current_zone == 'profit' and zone_start is not None:
            profit_zones.append({
                "start": zone_start,
                "end": spot_prices[-1],
                "max_profit": zone_max_pnl
            })
        elif current_zone == 'loss' and zone_start is not None:
            loss_zones.append({
                "start": zone_start,
                "end": spot_prices[-1],
                "max_loss": zone_max_pnl
            })

        return {
            "profit_zones": profit_zones,
            "loss_zones": loss_zones,
            "unlimited_profit": False,  # Can be enhanced with leg analysis
            "unlimited_loss": False
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating profit zones: {str(e)}"
        )


@router.get("/{strategy_id}/greeks-heatmap")
async def get_greeks_heatmap(
    strategy_id: int,
    greek: str = Query(..., pattern="^(delta|gamma|theta|vega)$"),
    spot_range_pct: float = Query(10.0, ge=1.0, le=30.0),
    num_points: int = Query(50, ge=20, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get Greeks heatmap data for a strategy.

    Shows how delta/gamma/theta/vega changes across spot price range.

    Args:
        strategy_id: Strategy ID
        greek: 'delta', 'gamma', 'theta', or 'vega'
        spot_range_pct: Spot price range percentage
        num_points: Number of data points

    Returns:
        {
            "spot_prices": [...],
            "greek_values": [...],
            "current_spot": 24500,
            "current_greek": 0.15,
            "greek_name": "delta"
        }
    """
    try:
        market_data = MarketDataService(kite)
        calculator = PayoffCalculator(kite, db, market_data)

        result = await calculator.calculate_greeks_heatmap(
            strategy_id=strategy_id,
            greek=greek,
            spot_range_pct=spot_range_pct,
            num_points=num_points
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
            detail=f"Error calculating Greeks heatmap: {str(e)}"
        )


# ============================================================================
# PHASE 5G: ADJUSTMENT COST TRACKING
# ============================================================================

@router.get("/{strategy_id}/adjustment-costs", response_model=dict)
async def get_adjustment_costs(
    strategy_id: int,
    warning_threshold_pct: float = Query(50.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get adjustment cost summary for a strategy (Phase 5G #46).

    Tracks cumulative cost of adjustments relative to original premium.
    Professional traders avoid exceeding 50% of original premium in adjustment costs.

    Args:
        strategy_id: Strategy ID
        warning_threshold_pct: Warning threshold percentage (default: 50%)

    Returns:
        AdjustmentCostSummary with:
        - original_premium: Initial premium collected
        - total_adjustment_cost: Sum of all adjustment costs
        - adjustment_cost_pct: Cost as percentage of original premium
        - net_potential_profit: Original premium - adjustment costs
        - adjustments: List of individual adjustments
        - alert_level: "success" | "info" | "warning" | "danger"
        - alert_message: Human-readable alert message
    """
    try:
        # Get strategy
        result = await db.execute(
            select(AutoPilotStrategy).where(
                AutoPilotStrategy.id == strategy_id,
                AutoPilotStrategy.user_id == user.id
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )

        # Get cost summary
        tracker = AdjustmentCostTracker(db)
        summary = await tracker.get_summary(strategy, warning_threshold_pct)

        return summary.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching adjustment costs: {str(e)}"
        )


@router.get("/{strategy_id}/adjustment-costs/threshold-check", response_model=dict)
async def check_adjustment_cost_threshold(
    strategy_id: int,
    threshold_pct: float = Query(50.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Check if adjustment costs exceed threshold (Phase 5G #46).

    Args:
        strategy_id: Strategy ID
        threshold_pct: Threshold percentage to check (default: 50%)

    Returns:
        {
            "threshold_exceeded": bool,
            "current_pct": float,
            "threshold_pct": float,
            "alert_level": str,
            "alert_message": str,
            "recommendation": str
        }
    """
    try:
        # Get strategy
        result = await db.execute(
            select(AutoPilotStrategy).where(
                AutoPilotStrategy.id == strategy_id,
                AutoPilotStrategy.user_id == user.id
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )

        # Check threshold
        tracker = AdjustmentCostTracker(db)
        result = await tracker.check_cost_threshold(strategy, threshold_pct)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking cost threshold: {str(e)}"
        )


@router.post("/{strategy_id}/adjustment-costs/project", response_model=dict)
async def project_adjustment_cost(
    strategy_id: int,
    action_type: str = Body(...),
    estimated_cost: Decimal = Body(...),
    notes: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Project cost impact of a new adjustment before execution (Phase 5G #46).

    Helps traders decide if an adjustment is worth the cost.

    Args:
        strategy_id: Strategy ID
        action_type: Type of adjustment action
        estimated_cost: Estimated cost of the adjustment
        notes: Optional notes about the adjustment

    Returns:
        {
            "current_cost": float,
            "current_pct": float,
            "estimated_new_cost": float,
            "projected_total_cost": float,
            "projected_cost_pct": float,
            "projected_profit": float,
            "recommendation": "proceed" | "reconsider" | "do_not_adjust"
        }
    """
    try:
        # Get strategy
        result = await db.execute(
            select(AutoPilotStrategy).where(
                AutoPilotStrategy.id == strategy_id,
                AutoPilotStrategy.user_id == user.id
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )

        # Project cost impact
        tracker = AdjustmentCostTracker(db)
        projection = await tracker.track_new_adjustment(
            strategy=strategy,
            action_type=action_type,
            estimated_cost=estimated_cost,
            notes=notes
        )

        return projection

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error projecting adjustment cost: {str(e)}"
        )
