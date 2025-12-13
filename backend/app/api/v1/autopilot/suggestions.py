"""
AutoPilot Suggestions API Routes - Phase 5C

Endpoints for fetching and managing AI-generated adjustment suggestions.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.database import get_db
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models import User, BrokerConnection
from app.schemas.autopilot import AdjustmentSuggestionResponse
from app.services.suggestion_engine import SuggestionEngine
from app.services.market_data import MarketDataService

router = APIRouter()


def get_kite_client(broker_connection: BrokerConnection = Depends(get_current_broker_connection)) -> KiteConnect:
    """Get Kite Connect client for current user."""
    kite = KiteConnect(api_key=broker_connection.api_key)
    kite.set_access_token(broker_connection.access_token)
    return kite


@router.get("/strategies/{strategy_id}", response_model=List[AdjustmentSuggestionResponse])
async def get_suggestions(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Get AI-generated adjustment suggestions for a strategy.

    Analyzes:
    - Net delta and position Greeks
    - P&L vs risk limits
    - Days to expiry (DTE)
    - Market conditions (spot, VIX)

    Returns suggestions ranked by priority (CRITICAL > HIGH > MEDIUM > LOW)

    Args:
        strategy_id: Strategy ID

    Returns:
        List of adjustment suggestions with reasoning and action params
    """
    try:
        # Initialize services
        market_data = MarketDataService(kite)
        suggestion_engine = SuggestionEngine(kite, db, market_data)

        # Generate suggestions
        suggestions = await suggestion_engine.generate_suggestions(
            strategy_id=strategy_id,
            user_id=user.id
        )

        return suggestions

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating suggestions: {str(e)}"
        )


@router.get("/strategies/{strategy_id}/suggestions/{suggestion_id}", response_model=AdjustmentSuggestionResponse)
async def get_suggestion(
    strategy_id: int,
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Get a single suggestion by ID.

    Args:
        strategy_id: Strategy ID
        suggestion_id: Suggestion ID

    Returns:
        Suggestion details
    """
    try:
        from app.models.autopilot import AutoPilotAdjustmentSuggestion
        from sqlalchemy import select

        result = await db.execute(
            select(AutoPilotAdjustmentSuggestion).where(
                AutoPilotAdjustmentSuggestion.id == suggestion_id,
                AutoPilotAdjustmentSuggestion.strategy_id == strategy_id
            )
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Suggestion {suggestion_id} not found"
            )

        return suggestion

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching suggestion: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/suggestions/{suggestion_id}/dismiss")
async def dismiss_suggestion(
    strategy_id: int,
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """
    Dismiss a suggestion (mark as not useful).

    Args:
        strategy_id: Strategy ID
        suggestion_id: Suggestion ID

    Returns:
        Success confirmation
    """
    try:
        from app.models.autopilot import AutoPilotAdjustmentSuggestion
        from sqlalchemy import delete

        # Delete the suggestion
        result = await db.execute(
            delete(AutoPilotAdjustmentSuggestion).where(
                AutoPilotAdjustmentSuggestion.id == suggestion_id,
                AutoPilotAdjustmentSuggestion.strategy_id == strategy_id
            )
        )

        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Suggestion {suggestion_id} not found"
            )

        return {
            "success": True,
            "message": f"Suggestion {suggestion_id} dismissed"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error dismissing suggestion: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/suggestions/{suggestion_id}/execute")
async def execute_suggestion(
    strategy_id: int,
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Execute a suggestion (perform the suggested adjustment).

    This is a one-click execution of the action suggested by the AI.

    Args:
        strategy_id: Strategy ID
        suggestion_id: Suggestion ID

    Returns:
        Execution result
    """
    try:
        from app.models.autopilot import AutoPilotAdjustmentSuggestion, SuggestionType
        from app.services.leg_actions_service import LegActionsService
        from app.services.break_trade_service import BreakTradeService
        from sqlalchemy import select

        # Get suggestion
        result = await db.execute(
            select(AutoPilotAdjustmentSuggestion).where(
                AutoPilotAdjustmentSuggestion.id == suggestion_id,
                AutoPilotAdjustmentSuggestion.strategy_id == strategy_id
            )
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Suggestion {suggestion_id} not found"
            )

        # Execute based on suggestion type
        action_params = suggestion.action_params or {}

        if suggestion.suggestion_type == SuggestionType.SHIFT:
            # Execute shift
            service = LegActionsService(kite, db, str(user.id))
            result = await service.shift_leg(
                strategy_id=strategy_id,
                leg_id=action_params.get('leg_id'),
                target_strike=action_params.get('target_strike'),
                target_delta=action_params.get('target_delta'),
                shift_direction=action_params.get('shift_direction'),
                shift_amount=action_params.get('shift_amount'),
                execution_mode=action_params.get('execution_mode', 'market')
            )

        elif suggestion.suggestion_type == SuggestionType.ROLL:
            # Execute roll
            service = LegActionsService(kite, db, str(user.id))
            result = await service.roll_leg(
                strategy_id=strategy_id,
                leg_id=action_params.get('leg_id'),
                target_expiry=action_params.get('target_expiry'),
                target_strike=action_params.get('target_strike'),
                execution_mode=action_params.get('execution_mode', 'market')
            )

        elif suggestion.suggestion_type == SuggestionType.BREAK:
            # Execute break trade
            service = BreakTradeService(kite, db, str(user.id))
            result = await service.break_trade(
                strategy_id=strategy_id,
                leg_id=action_params.get('leg_id'),
                execution_mode=action_params.get('execution_mode', 'market'),
                new_positions=action_params.get('new_positions', 'auto'),
                premium_split=action_params.get('premium_split', 'equal'),
                prefer_round_strikes=action_params.get('prefer_round_strikes', True),
                max_delta=action_params.get('max_delta', 0.30)
            )

        elif suggestion.suggestion_type == SuggestionType.EXIT:
            # Execute exit
            service = LegActionsService(kite, db, str(user.id))
            if action_params.get('leg_id'):
                # Exit specific leg
                result = await service.exit_leg(
                    strategy_id=strategy_id,
                    leg_id=action_params.get('leg_id'),
                    execution_mode=action_params.get('execution_mode', 'market')
                )
            else:
                # Exit all (would need to implement in service)
                raise HTTPException(
                    status_code=status.HTTP_501_NOT_IMPLEMENTED,
                    detail="Exit all not yet implemented"
                )

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Suggestion type {suggestion.suggestion_type} cannot be auto-executed"
            )

        # Delete the executed suggestion
        from sqlalchemy import delete
        await db.execute(
            delete(AutoPilotAdjustmentSuggestion).where(
                AutoPilotAdjustmentSuggestion.id == suggestion_id
            )
        )
        await db.commit()

        return {
            "success": True,
            "message": f"Suggestion executed: {suggestion.title}",
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing suggestion: {str(e)}"
        )


@router.post("/strategies/{strategy_id}/suggestions/refresh")
async def refresh_suggestions(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    kite: KiteConnect = Depends(get_kite_client)
):
    """
    Force refresh suggestions for a strategy.

    Clears old suggestions and generates new ones based on current market conditions.

    Args:
        strategy_id: Strategy ID

    Returns:
        Newly generated suggestions
    """
    try:
        # Initialize services
        market_data = MarketDataService(kite)
        suggestion_engine = SuggestionEngine(kite, db, market_data)

        # Generate fresh suggestions (this clears old ones automatically)
        suggestions = await suggestion_engine.generate_suggestions(
            strategy_id=strategy_id,
            user_id=user.id
        )

        return {
            "success": True,
            "count": len(suggestions),
            "suggestions": suggestions
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing suggestions: {str(e)}"
        )
