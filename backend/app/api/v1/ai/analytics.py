"""
AI Performance Analytics API

Provides performance metrics, regime/strategy analysis, decision quality trends,
and learning progress for the AI trading system.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, case
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.users import User
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Response Schemas =====

class PerformanceMetrics(BaseModel):
    """Overall AI performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float = Field(..., description="Win rate percentage")

    total_pnl: Decimal
    avg_pnl_per_trade: Decimal
    max_win: Decimal
    max_loss: Decimal

    avg_decision_score: float = Field(..., description="Average decision quality score 0-100")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio if calculable")

    total_days_active: int
    last_trade_date: Optional[date]


class RegimePerformance(BaseModel):
    """Performance breakdown by market regime."""
    regime_type: str
    trades_count: int
    win_rate: float
    avg_pnl: Decimal
    total_pnl: Decimal
    avg_score: float
    best_strategy: Optional[str] = None


class StrategyPerformance(BaseModel):
    """Performance breakdown by strategy type."""
    strategy_name: str
    trades_count: int
    win_rate: float
    avg_pnl: Decimal
    total_pnl: Decimal
    avg_score: float
    best_regime: Optional[str] = None


class DecisionQualityDataPoint(BaseModel):
    """Decision quality data point for time series."""
    date: date
    avg_score: float
    trades_count: int


class LearningProgressMetrics(BaseModel):
    """ML model learning progress metrics."""
    model_version: str
    trained_at: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float

    total_training_samples: int
    performance_trend: str = Field(..., description="improving, stable, or declining")


# ===== API Endpoints =====

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    start_date: Optional[date] = Query(None, description="Start date for analysis"),
    end_date: Optional[date] = Query(None, description="End date for analysis"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall AI performance metrics.

    Returns total trades, win rate, P&L, decision quality scores, and Sharpe ratio.
    """
    from app.models import AutoPilotTradeJournal, AILearningReport
    import numpy as np

    # Default to last 30 days if no dates provided
    if end_date is None:
        end_date = date.today()

    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Query completed trades from trade journal
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(AutoPilotTradeJournal)
        .where(
            and_(
                AutoPilotTradeJournal.user_id == user.id,
                AutoPilotTradeJournal.entry_time >= start_datetime,
                AutoPilotTradeJournal.entry_time <= end_datetime,
                AutoPilotTradeJournal.exit_time.isnot(None)  # Only completed trades
            )
        )
    )
    trades = result.scalars().all()

    # Calculate metrics
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if (t.total_pnl or 0) > 0)
    losing_trades = total_trades - winning_trades
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    total_pnl = sum(t.total_pnl or 0 for t in trades)
    avg_pnl = (total_pnl / total_trades) if total_trades > 0 else Decimal('0')
    max_win = max((t.total_pnl or 0 for t in trades), default=Decimal('0'))
    max_loss = min((t.total_pnl or 0 for t in trades), default=Decimal('0'))

    # Calculate average decision score from learning reports
    reports_result = await db.execute(
        select(AILearningReport)
        .where(
            and_(
                AILearningReport.user_id == user.id,
                AILearningReport.report_date >= start_date,
                AILearningReport.report_date <= end_date
            )
        )
    )
    reports = reports_result.scalars().all()

    avg_decision_score = np.mean([r.avg_overall_score for r in reports]) if reports else 0.0

    # Calculate Sharpe ratio (simplified)
    if total_trades > 1:
        pnl_values = [float(t.total_pnl or 0) for t in trades]
        returns_std = np.std(pnl_values)
        sharpe_ratio = (float(avg_pnl) / returns_std * np.sqrt(252)) if returns_std > 0 else None
    else:
        sharpe_ratio = None

    # Get unique days active
    unique_dates = set(t.entry_time.date() for t in trades if t.entry_time)
    total_days_active = len(unique_dates)

    # Get last trade date
    last_trade_date = max((t.exit_time.date() for t in trades if t.exit_time), default=None)

    metrics = PerformanceMetrics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=round(win_rate, 2),
        total_pnl=Decimal(str(total_pnl)),
        avg_pnl_per_trade=Decimal(str(avg_pnl)),
        max_win=Decimal(str(max_win)),
        max_loss=Decimal(str(max_loss)),
        avg_decision_score=round(avg_decision_score, 2),
        sharpe_ratio=round(sharpe_ratio, 2) if sharpe_ratio else None,
        total_days_active=total_days_active,
        last_trade_date=last_trade_date
    )

    logger.info(
        f"Performance metrics for user {user.id}: "
        f"{metrics.total_trades} trades, {metrics.win_rate:.2f}% win rate"
    )

    return metrics


@router.get("/by-regime", response_model=List[RegimePerformance])
async def get_performance_by_regime(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance breakdown by market regime.

    Shows which market conditions the AI performs best in.
    """
    from app.models import AutoPilotTradeJournal
    from collections import defaultdict

    # Default dates
    if end_date is None:
        end_date = date.today()

    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Query completed trades grouped by entry regime
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(AutoPilotTradeJournal)
        .where(
            and_(
                AutoPilotTradeJournal.user_id == user.id,
                AutoPilotTradeJournal.entry_time >= start_datetime,
                AutoPilotTradeJournal.entry_time <= end_datetime,
                AutoPilotTradeJournal.exit_time.isnot(None)
            )
        )
    )
    trades = result.scalars().all()

    # Group by regime
    regime_data = defaultdict(lambda: {
        'trades': [],
        'strategy_pnl': defaultdict(Decimal)
    })

    for trade in trades:
        regime = trade.entry_regime or "UNKNOWN"
        regime_data[regime]['trades'].append(trade)

        # Track P&L by strategy within this regime
        strategy = trade.strategy_type or "UNKNOWN"
        regime_data[regime]['strategy_pnl'][strategy] += (trade.total_pnl or 0)

    # Calculate metrics for each regime
    regime_performance = []
    for regime_type, data in regime_data.items():
        trades_list = data['trades']
        trades_count = len(trades_list)

        if trades_count == 0:
            continue

        winning_trades = sum(1 for t in trades_list if (t.total_pnl or 0) > 0)
        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0.0

        total_pnl = sum(t.total_pnl or 0 for t in trades_list)
        avg_pnl = total_pnl / trades_count if trades_count > 0 else Decimal('0')

        # Calculate average decision score
        avg_score = sum(t.confidence_at_entry or 0 for t in trades_list if hasattr(t, 'confidence_at_entry')) / trades_count if trades_count > 0 else 0.0

        # Find best performing strategy in this regime
        best_strategy = max(data['strategy_pnl'].items(), key=lambda x: x[1])[0] if data['strategy_pnl'] else None

        regime_performance.append(RegimePerformance(
            regime_type=regime_type,
            trades_count=trades_count,
            win_rate=round(win_rate, 2),
            avg_pnl=Decimal(str(avg_pnl)),
            total_pnl=Decimal(str(total_pnl)),
            avg_score=round(float(avg_score), 2),
            best_strategy=best_strategy
        ))

    # Sort by total P&L descending
    regime_performance.sort(key=lambda x: x.total_pnl, reverse=True)

    logger.info(f"Regime performance for user {user.id}: {len(regime_performance)} regimes analyzed")

    return regime_performance


@router.get("/by-strategy", response_model=List[StrategyPerformance])
async def get_performance_by_strategy(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance breakdown by strategy type.

    Shows which strategies work best for the AI.
    """
    from app.models import AutoPilotTradeJournal
    from collections import defaultdict

    # Default dates
    if end_date is None:
        end_date = date.today()

    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Query completed trades grouped by strategy
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    result = await db.execute(
        select(AutoPilotTradeJournal)
        .where(
            and_(
                AutoPilotTradeJournal.user_id == user.id,
                AutoPilotTradeJournal.entry_time >= start_datetime,
                AutoPilotTradeJournal.entry_time <= end_datetime,
                AutoPilotTradeJournal.exit_time.isnot(None)
            )
        )
    )
    trades = result.scalars().all()

    # Group by strategy
    strategy_data = defaultdict(lambda: {
        'trades': [],
        'regime_pnl': defaultdict(Decimal)
    })

    for trade in trades:
        strategy = trade.strategy_type or "UNKNOWN"
        strategy_data[strategy]['trades'].append(trade)

        # Track P&L by regime within this strategy
        regime = trade.entry_regime or "UNKNOWN"
        strategy_data[strategy]['regime_pnl'][regime] += (trade.total_pnl or 0)

    # Calculate metrics for each strategy
    strategy_performance = []
    for strategy_name, data in strategy_data.items():
        trades_list = data['trades']
        trades_count = len(trades_list)

        if trades_count == 0:
            continue

        winning_trades = sum(1 for t in trades_list if (t.total_pnl or 0) > 0)
        win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0.0

        total_pnl = sum(t.total_pnl or 0 for t in trades_list)
        avg_pnl = total_pnl / trades_count if trades_count > 0 else Decimal('0')

        # Calculate average decision score
        avg_score = sum(t.confidence_at_entry or 0 for t in trades_list if hasattr(t, 'confidence_at_entry')) / trades_count if trades_count > 0 else 0.0

        # Find best performing regime for this strategy
        best_regime = max(data['regime_pnl'].items(), key=lambda x: x[1])[0] if data['regime_pnl'] else None

        strategy_performance.append(StrategyPerformance(
            strategy_name=strategy_name,
            trades_count=trades_count,
            win_rate=round(win_rate, 2),
            avg_pnl=Decimal(str(avg_pnl)),
            total_pnl=Decimal(str(total_pnl)),
            avg_score=round(float(avg_score), 2),
            best_regime=best_regime
        ))

    # Sort by total P&L descending
    strategy_performance.sort(key=lambda x: x.total_pnl, reverse=True)

    logger.info(f"Strategy performance for user {user.id}: {len(strategy_performance)} strategies analyzed")

    return strategy_performance


@router.get("/decisions", response_model=List[DecisionQualityDataPoint])
async def get_decision_quality_trend(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get decision quality trend over time.

    Returns daily average decision quality scores for charting.
    """
    from app.models import AILearningReport

    # Default to last 30 days
    if end_date is None:
        end_date = date.today()

    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Query daily learning reports
    result = await db.execute(
        select(AILearningReport)
        .where(
            and_(
                AILearningReport.user_id == user.id,
                AILearningReport.report_date >= start_date,
                AILearningReport.report_date <= end_date
            )
        )
        .order_by(AILearningReport.report_date)
    )
    reports = result.scalars().all()

    # Create map of dates to scores
    reports_map = {r.report_date: r for r in reports}

    # Generate complete time series (including days with no trades)
    quality_trend = []
    current_date = start_date

    while current_date <= end_date:
        if current_date in reports_map:
            report = reports_map[current_date]
            quality_trend.append(
                DecisionQualityDataPoint(
                    date=current_date,
                    avg_score=round(float(report.avg_overall_score), 2),
                    trades_count=report.total_trades
                )
            )
        else:
            # No trades on this day
            quality_trend.append(
                DecisionQualityDataPoint(
                    date=current_date,
                    avg_score=0.0,
                    trades_count=0
                )
            )

        current_date += timedelta(days=1)

    logger.info(
        f"Decision quality trend for user {user.id}: "
        f"{len(quality_trend)} data points from {start_date} to {end_date}"
    )

    return quality_trend


@router.get("/learning", response_model=LearningProgressMetrics)
async def get_learning_progress(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ML model learning progress metrics.

    Shows active model performance and improvement trend.
    """
    from app.models.ai import AIModelRegistry

    # Query active model from registry (system-wide, not per-user)
    result = await db.execute(
        select(AIModelRegistry)
        .where(AIModelRegistry.is_active == True)
        .order_by(desc(AIModelRegistry.trained_at))
        .limit(1)
    )
    active_model = result.scalar_one_or_none()

    if not active_model:
        # Return default/placeholder if no model trained yet
        progress = LearningProgressMetrics(
            model_version="not_trained",
            trained_at=datetime.now(),
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            total_training_samples=0,
            performance_trend="not_available"
        )
        logger.info(f"No trained model found for user {user.id}")
        return progress

    # Get previous model for trend comparison (system-wide)
    previous_result = await db.execute(
        select(AIModelRegistry)
        .where(AIModelRegistry.trained_at < active_model.trained_at)
        .order_by(desc(AIModelRegistry.trained_at))
        .limit(1)
    )
    previous_model = previous_result.scalar_one_or_none()

    # Determine performance trend
    if previous_model:
        if active_model.f1_score > previous_model.f1_score + 0.02:
            performance_trend = "improving"
        elif active_model.f1_score < previous_model.f1_score - 0.02:
            performance_trend = "declining"
        else:
            performance_trend = "stable"
    else:
        performance_trend = "baseline"

    progress = LearningProgressMetrics(
        model_version=active_model.version,  # Use 'version' not 'model_version'
        trained_at=active_model.trained_at,
        accuracy=float(active_model.accuracy or 0),
        precision=float(active_model.precision or 0),
        recall=float(active_model.recall or 0),
        f1_score=float(active_model.f1_score or 0),
        total_training_samples=0,  # Field doesn't exist in model - use default 0
        performance_trend=performance_trend
    )

    logger.info(
        f"Learning progress for user {user.id}: "
        f"model {progress.model_version}, accuracy: {progress.accuracy:.4f}"
    )

    return progress


@router.get("/portfolio", summary="Get Portfolio Overview")
async def get_portfolio_overview(
    total_capital: float = Query(100000, description="Total available capital"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete portfolio overview for multi-strategy management.

    Returns aggregated portfolio Greeks, correlation analysis, risk assessment,
    and rebalancing recommendations for all active AutoPilot strategies.

    Args:
        total_capital: Total available capital for trading (default: 100000)

    Returns:
        {
            "total_strategies": int,
            "active_strategies": int,
            "total_capital_deployed": Decimal,
            "available_capital": Decimal,
            "total_pnl": Decimal,
            "portfolio_greeks": {
                "total_delta": Decimal,
                "total_gamma": Decimal,
                "total_theta": Decimal,
                "total_vega": Decimal
            },
            "risk_level": str,  # LOW, MODERATE, HIGH, CRITICAL
            "risk_score": float,
            "strategy_summary": List[Dict],
            "correlations": List[Dict],
            "rebalance_recommendations": List[Dict]
        }
    """
    try:
        from app.services.ai.portfolio_manager import PortfolioManager

        portfolio_mgr = PortfolioManager(db)

        summary = await portfolio_mgr.get_portfolio_summary(
            user_id=user.id,
            total_capital=Decimal(str(total_capital))
        )

        logger.info(
            f"Portfolio overview for user {user.id}: "
            f"{summary.active_strategies} active strategies, "
            f"risk={summary.risk_level}, "
            f"total_pnl={summary.total_pnl}"
        )

        return {
            "total_strategies": summary.total_strategies,
            "active_strategies": summary.active_strategies,
            "total_capital_deployed": float(summary.total_capital_deployed),
            "available_capital": float(summary.available_capital),
            "total_pnl": float(summary.total_pnl),
            "total_realized_pnl": float(summary.total_realized_pnl),
            "total_unrealized_pnl": float(summary.total_unrealized_pnl),
            "portfolio_greeks": {
                "total_delta": float(summary.portfolio_greeks.total_delta),
                "total_gamma": float(summary.portfolio_greeks.total_gamma),
                "total_theta": float(summary.portfolio_greeks.total_theta),
                "total_vega": float(summary.portfolio_greeks.total_vega),
                "delta_exposure": float(summary.portfolio_greeks.delta_exposure),
                "gamma_risk": float(summary.portfolio_greeks.gamma_risk),
                "theta_decay": float(summary.portfolio_greeks.theta_decay),
                "vega_exposure": float(summary.portfolio_greeks.vega_exposure)
            },
            "risk_level": summary.risk_level,
            "risk_score": summary.risk_score,
            "strategy_summary": summary.strategy_summary,
            "correlations": [
                {
                    "strategy1_id": corr.strategy1_id,
                    "strategy2_id": corr.strategy2_id,
                    "strategy1_name": corr.strategy1_name,
                    "strategy2_name": corr.strategy2_name,
                    "correlation": corr.correlation,
                    "diversification_benefit": corr.diversification_benefit
                }
                for corr in summary.correlations
            ],
            "rebalance_recommendations": [
                {
                    "action": rec.action,
                    "strategy_id": rec.strategy_id,
                    "strategy_name": rec.strategy_name,
                    "current_allocation": float(rec.current_allocation),
                    "recommended_allocation": float(rec.recommended_allocation),
                    "reason": rec.reason,
                    "priority": rec.priority
                }
                for rec in summary.rebalance_recommendations
            ]
        }

    except Exception as e:
        logger.error(f"Error getting portfolio overview for user {user.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get portfolio overview: {str(e)}"
        )


__all__ = ["router"]
