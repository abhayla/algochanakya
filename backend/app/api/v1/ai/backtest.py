"""
Backtesting API Endpoints

REST API for running historical strategy backtests and retrieving results.
"""

import logging
from typing import List, Optional
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.users import User
from app.utils.dependencies import get_current_user
from app.services.ai.backtester import Backtester, BacktestResult

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Request/Response Schemas =====

class BacktestCondition(BaseModel):
    """Entry or exit condition for backtest"""
    variable: str
    operator: str
    value: str
    description: Optional[str] = None


class BacktestRequest(BaseModel):
    """Request to run a new backtest"""
    strategy_name: str = Field(..., description="Name of strategy to backtest")
    underlying: str = Field(..., description="NIFTY, BANKNIFTY, or FINNIFTY")
    entry_conditions: List[BacktestCondition] = Field(default_factory=list)
    exit_conditions: List[BacktestCondition] = Field(default_factory=list)
    start_date: date = Field(..., description="Backtest start date")
    end_date: date = Field(..., description="Backtest end date")
    initial_capital: Decimal = Field(Decimal("100000"), description="Starting capital")
    max_concurrent_positions: int = Field(1, description="Max open positions at once", ge=1, le=5)
    base_lots: int = Field(1, description="Lots per trade", ge=1, le=10)


class BacktestTradeResponse(BaseModel):
    """Single trade from backtest"""
    entry_time: str
    exit_time: Optional[str]
    strategy_name: str
    underlying: str
    entry_price: Decimal
    exit_price: Optional[Decimal]
    quantity: int
    pnl: Optional[Decimal]
    regime_at_entry: str
    entry_confidence: float
    exit_reason: Optional[str] = None


class BacktestResultResponse(BaseModel):
    """Complete backtest results"""
    backtest_id: str
    strategy_name: str
    underlying: str
    start_date: date
    end_date: date

    # Performance metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    total_pnl: Decimal
    avg_pnl_per_trade: Decimal
    max_win: Decimal
    max_loss: Decimal
    max_drawdown: Decimal

    # Risk metrics
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    profit_factor: float

    # Execution metrics
    avg_holding_period_hours: float
    regime_performance: dict

    # Trade history (optional, can be paginated)
    trades: Optional[List[BacktestTradeResponse]] = None


# ===== API Endpoints =====

@router.post("/run", response_model=BacktestResultResponse)
async def run_backtest(
    request: BacktestRequest,
    include_trades: bool = Query(False, description="Include full trade history in response"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a backtest for a strategy against historical data.

    Tests the strategy's entry/exit conditions against past market data
    and returns comprehensive performance metrics including P&L, win rate,
    Sharpe ratio, and regime-specific performance.

    Args:
        request: Backtest configuration
        include_trades: If true, includes full trade history (can be large)

    Returns:
        BacktestResultResponse: Complete backtest results

    Raises:
        HTTPException 400: Invalid parameters or date range
        HTTPException 500: Backtest execution failed
    """
    try:
        # Validate date range
        if request.start_date >= request.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date must be before end_date"
            )

        # Limit backtest period to 1 year
        max_period = timedelta(days=365)
        if (request.end_date - request.start_date) > max_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Backtest period cannot exceed 1 year"
            )

        # Convert conditions to dict format expected by backtester
        entry_conditions = [
            {
                "variable": cond.variable,
                "operator": cond.operator,
                "value": cond.value,
                "description": cond.description
            }
            for cond in request.entry_conditions
        ]

        exit_conditions = [
            {
                "variable": cond.variable,
                "operator": cond.operator,
                "value": cond.value,
                "description": cond.description
            }
            for cond in request.exit_conditions
        ]

        # Run backtest
        logger.info(
            f"Running backtest for user {user.id}: {request.strategy_name} "
            f"on {request.underlying} from {request.start_date} to {request.end_date}"
        )

        backtester = Backtester(db)

        result = await backtester.run_backtest(
            strategy_name=request.strategy_name,
            underlying=request.underlying,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            max_concurrent_positions=request.max_concurrent_positions,
            base_lots=request.base_lots
        )

        logger.info(
            f"Backtest completed for user {user.id}: "
            f"{result.total_trades} trades, win_rate={result.win_rate:.2%}, "
            f"total_pnl={result.total_pnl}"
        )

        # Convert to response model
        response = BacktestResultResponse(
            backtest_id=result.backtest_id,
            strategy_name=result.strategy_name,
            underlying=result.underlying,
            start_date=result.start_date,
            end_date=result.end_date,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            total_pnl=result.total_pnl,
            avg_pnl_per_trade=result.avg_pnl_per_trade,
            max_win=result.max_win,
            max_loss=result.max_loss,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            profit_factor=result.profit_factor,
            avg_holding_period_hours=result.avg_holding_period_hours,
            regime_performance=result.regime_performance
        )

        # Include trades if requested
        if include_trades:
            response.trades = [
                BacktestTradeResponse(
                    entry_time=trade.entry_time.isoformat(),
                    exit_time=trade.exit_time.isoformat() if trade.exit_time else None,
                    strategy_name=trade.strategy_name,
                    underlying=trade.underlying,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    quantity=trade.quantity,
                    pnl=trade.pnl,
                    regime_at_entry=trade.regime_at_entry,
                    entry_confidence=trade.entry_confidence,
                    exit_reason=trade.exit_reason
                )
                for trade in result.trades
            ]

        return response

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error running backtest for user {user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest execution failed: {str(e)}"
        )


@router.get("/quick", response_model=BacktestResultResponse)
async def run_quick_backtest(
    underlying: str = Query(..., description="NIFTY, BANKNIFTY, or FINNIFTY"),
    lookback_days: int = Query(90, description="Days to look back", ge=30, le=365),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a quick backtest with default simple strategy.

    Uses a basic trend-following strategy:
    - Entry: REGIME = TRENDING_BULLISH AND TIME > 09:30
    - Exit: TIME >= 15:15 (end of day)

    Args:
        underlying: Index to backtest
        lookback_days: Historical period in days

    Returns:
        BacktestResultResponse: Backtest results without trade history
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Simple trend-following strategy
        entry_conditions = [
            {
                "variable": "REGIME",
                "operator": "==",
                "value": "TRENDING_BULLISH",
                "description": "Enter on bullish trends"
            },
            {
                "variable": "TIME",
                "operator": ">",
                "value": "09:30",
                "description": "After market opens"
            }
        ]

        exit_conditions = [
            {
                "variable": "TIME",
                "operator": ">=",
                "value": "15:15",
                "description": "Exit before market close"
            }
        ]

        backtester = Backtester(db)

        result = await backtester.run_backtest(
            strategy_name="Quick Trend Following",
            underlying=underlying,
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal("100000"),
            max_concurrent_positions=1,
            base_lots=1
        )

        logger.info(
            f"Quick backtest completed for user {user.id}: "
            f"{result.total_trades} trades, win_rate={result.win_rate:.2%}"
        )

        return BacktestResultResponse(
            backtest_id=result.backtest_id,
            strategy_name=result.strategy_name,
            underlying=result.underlying,
            start_date=result.start_date,
            end_date=result.end_date,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            win_rate=result.win_rate,
            total_pnl=result.total_pnl,
            avg_pnl_per_trade=result.avg_pnl_per_trade,
            max_win=result.max_win,
            max_loss=result.max_loss,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            profit_factor=result.profit_factor,
            avg_holding_period_hours=result.avg_holding_period_hours,
            regime_performance=result.regime_performance,
            trades=None  # Quick backtest doesn't include trade history
        )

    except Exception as e:
        logger.error(f"Error running quick backtest for user {user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick backtest failed: {str(e)}"
        )


__all__ = ["router"]
