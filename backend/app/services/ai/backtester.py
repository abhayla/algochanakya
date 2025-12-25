"""
Strategy Backtesting Engine

Test AutoPilot strategies against historical market data to validate performance
before deploying with real capital. Simulates regime classification, entry/exit
conditions, and calculates hypothetical P&L.
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.historical_data import HistoricalDataService
from app.services.ai.market_regime import MarketRegimeClassifier
from app.services.condition_engine import ConditionEngine
from app.constants.trading import get_lot_size

logger = logging.getLogger(__name__)


class BacktestStatus(str, Enum):
    """Backtest execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class BacktestTrade:
    """Represents a simulated trade in backtest"""
    entry_time: datetime
    exit_time: Optional[datetime]
    strategy_name: str
    underlying: str
    entry_price: Decimal
    exit_price: Optional[Decimal]
    quantity: int
    pnl: Optional[Decimal]
    regime_at_entry: str
    entry_confidence: float
    exit_reason: Optional[str] = None


@dataclass
class BacktestResult:
    """Results of a completed backtest"""
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
    profit_factor: float  # Gross profit / Gross loss

    # Execution metrics
    avg_holding_period_hours: float
    regime_performance: Dict[str, Dict]  # Performance by regime type

    # Trade history
    trades: List[BacktestTrade]


class Backtester:
    """
    Historical strategy backtesting engine.

    Simulates AutoPilot strategy execution against past market data,
    including regime classification, condition evaluation, and P&L calculation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.historical_service = HistoricalDataService()
        self.regime_classifier = MarketRegimeClassifier()
        self.condition_engine = ConditionEngine(db)

    async def run_backtest(
        self,
        strategy_name: str,
        underlying: str,
        entry_conditions: List[Dict],
        exit_conditions: List[Dict],
        start_date: date,
        end_date: date,
        initial_capital: Decimal = Decimal("100000"),
        max_concurrent_positions: int = 1,
        base_lots: int = 1
    ) -> BacktestResult:
        """
        Execute backtest for a strategy over historical period.

        Args:
            strategy_name: Name of strategy being tested
            underlying: NIFTY, BANKNIFTY, FINNIFTY
            entry_conditions: List of entry condition rules
            exit_conditions: List of exit condition rules
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital
            max_concurrent_positions: Maximum open positions at once
            base_lots: Number of lots per trade

        Returns:
            BacktestResult with complete performance metrics
        """
        logger.info(
            f"Starting backtest: {strategy_name} on {underlying} "
            f"from {start_date} to {end_date}"
        )

        # Fetch historical data
        historical_data = await self.historical_service.get_daily_candles(
            underlying=underlying,
            from_date=start_date,
            to_date=end_date
        )

        if not historical_data:
            raise ValueError(f"No historical data found for {underlying} from {start_date} to {end_date}")

        logger.info(f"Loaded {len(historical_data)} days of historical data")

        # Simulate trading
        trades: List[BacktestTrade] = []
        current_capital = initial_capital
        open_positions: List[BacktestTrade] = []

        for i, candle in enumerate(historical_data):
            current_date = candle.timestamp.date()

            # Classify regime for this day
            regime_result = await self.regime_classifier.classify_historical(
                underlying=underlying,
                historical_data=historical_data[:i+1]  # Only use data up to current day
            )

            # Check exit conditions for open positions
            for position in open_positions[:]:
                should_exit, exit_reason = await self._evaluate_exit_conditions(
                    position=position,
                    current_candle=candle,
                    exit_conditions=exit_conditions,
                    regime=regime_result
                )

                if should_exit:
                    # Close position
                    position.exit_time = candle.timestamp
                    position.exit_price = candle.close
                    position.exit_reason = exit_reason

                    # Calculate P&L (simplified - assumes all premium strategies)
                    lot_size = get_lot_size(underlying)
                    position.pnl = (position.exit_price - position.entry_price) * position.quantity * lot_size

                    current_capital += position.pnl

                    open_positions.remove(position)
                    trades.append(position)

                    logger.debug(
                        f"Closed position at {candle.timestamp}: "
                        f"P&L={position.pnl}, reason={exit_reason}"
                    )

            # Check entry conditions if we can take new positions
            if len(open_positions) < max_concurrent_positions:
                should_enter, entry_confidence = await self._evaluate_entry_conditions(
                    current_candle=candle,
                    entry_conditions=entry_conditions,
                    regime=regime_result
                )

                if should_enter:
                    # Open new position
                    lot_size = get_lot_size(underlying)
                    quantity = base_lots * lot_size

                    new_trade = BacktestTrade(
                        entry_time=candle.timestamp,
                        exit_time=None,
                        strategy_name=strategy_name,
                        underlying=underlying,
                        entry_price=candle.close,
                        exit_price=None,
                        quantity=quantity,
                        pnl=None,
                        regime_at_entry=regime_result.regime.value,
                        entry_confidence=entry_confidence
                    )

                    open_positions.append(new_trade)

                    logger.debug(
                        f"Opened position at {candle.timestamp}: "
                        f"price={candle.close}, regime={regime_result.regime.value}, "
                        f"confidence={entry_confidence:.2f}"
                    )

        # Close any remaining open positions at backtest end
        for position in open_positions:
            position.exit_time = historical_data[-1].timestamp
            position.exit_price = historical_data[-1].close
            position.exit_reason = "BACKTEST_END"

            lot_size = get_lot_size(underlying)
            position.pnl = (position.exit_price - position.entry_price) * position.quantity * lot_size

            trades.append(position)

        # Calculate performance metrics
        result = self._calculate_metrics(
            strategy_name=strategy_name,
            underlying=underlying,
            start_date=start_date,
            end_date=end_date,
            trades=trades,
            initial_capital=initial_capital
        )

        logger.info(
            f"Backtest completed: {result.total_trades} trades, "
            f"win_rate={result.win_rate:.2%}, total_pnl={result.total_pnl}"
        )

        return result

    async def _evaluate_entry_conditions(
        self,
        current_candle,
        entry_conditions: List[Dict],
        regime
    ) -> Tuple[bool, float]:
        """
        Evaluate if entry conditions are met.

        Returns:
            (should_enter, confidence_score)
        """
        if not entry_conditions:
            return False, 0.0

        # Build context for condition evaluation
        context = {
            "SPOT": float(current_candle.close),
            "VIX": 15.0,  # TODO: Fetch historical VIX data
            "TIME": current_candle.timestamp.strftime("%H:%M"),
            "REGIME": regime.regime.value,
            "REGIME_CONFIDENCE": regime.confidence
        }

        # Evaluate all entry conditions
        all_met = True
        total_confidence = 0.0

        for condition in entry_conditions:
            is_met = await self.condition_engine.evaluate_condition_historical(
                condition, context
            )

            if not is_met:
                all_met = False
                break

            total_confidence += regime.confidence

        if all_met:
            avg_confidence = total_confidence / len(entry_conditions) if entry_conditions else 0.0
            return True, avg_confidence

        return False, 0.0

    async def _evaluate_exit_conditions(
        self,
        position: BacktestTrade,
        current_candle,
        exit_conditions: List[Dict],
        regime
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate if exit conditions are met.

        Returns:
            (should_exit, exit_reason)
        """
        if not exit_conditions:
            return False, None

        # Check holding period (default max 5 days)
        holding_hours = (current_candle.timestamp - position.entry_time).total_seconds() / 3600
        if holding_hours > 120:  # 5 days
            return True, "MAX_HOLDING_PERIOD"

        # Build context
        lot_size = get_lot_size(position.underlying)
        current_pnl = (current_candle.close - position.entry_price) * position.quantity * lot_size

        context = {
            "SPOT": float(current_candle.close),
            "VIX": 15.0,
            "TIME": current_candle.timestamp.strftime("%H:%M"),
            "REGIME": regime.regime.value,
            "PNL": float(current_pnl)
        }

        # Evaluate exit conditions
        for condition in exit_conditions:
            is_met = await self.condition_engine.evaluate_condition_historical(
                condition, context
            )

            if is_met:
                return True, f"CONDITION_MET: {condition.get('description', 'unknown')}"

        return False, None

    def _calculate_metrics(
        self,
        strategy_name: str,
        underlying: str,
        start_date: date,
        end_date: date,
        trades: List[BacktestTrade],
        initial_capital: Decimal
    ) -> BacktestResult:
        """Calculate comprehensive performance metrics from trade history"""

        if not trades:
            return BacktestResult(
                backtest_id=f"BT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                strategy_name=strategy_name,
                underlying=underlying,
                start_date=start_date,
                end_date=end_date,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=Decimal("0"),
                avg_pnl_per_trade=Decimal("0"),
                max_win=Decimal("0"),
                max_loss=Decimal("0"),
                max_drawdown=Decimal("0"),
                sharpe_ratio=None,
                sortino_ratio=None,
                profit_factor=0.0,
                avg_holding_period_hours=0.0,
                regime_performance={},
                trades=[]
            )

        # Basic metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0

        # P&L metrics
        total_pnl = sum(t.pnl for t in trades if t.pnl)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else Decimal("0")
        max_win = max((t.pnl for t in trades if t.pnl), default=Decimal("0"))
        max_loss = min((t.pnl for t in trades if t.pnl), default=Decimal("0"))

        # Calculate max drawdown
        equity_curve = [initial_capital]
        for trade in trades:
            equity_curve.append(equity_curve[-1] + trade.pnl)

        max_drawdown = Decimal("0")
        peak = equity_curve[0]
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Risk metrics
        gross_profit = sum(t.pnl for t in trades if t.pnl and t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl and t.pnl < 0))
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else 0.0

        # Sharpe ratio (simplified - assumes daily returns)
        returns = [float(t.pnl) for t in trades if t.pnl]
        if len(returns) > 1:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5
            sharpe_ratio = (mean_return / std_dev) if std_dev > 0 else None
        else:
            sharpe_ratio = None

        # Sortino ratio (downside deviation only)
        downside_returns = [r for r in returns if r < 0]
        if downside_returns and len(downside_returns) > 1:
            mean_downside = sum(downside_returns) / len(downside_returns)
            downside_variance = sum((r - mean_downside) ** 2 for r in downside_returns) / (len(downside_returns) - 1)
            downside_std = downside_variance ** 0.5
            sortino_ratio = (sum(returns) / len(returns)) / downside_std if downside_std > 0 else None
        else:
            sortino_ratio = None

        # Holding period
        holding_periods = [
            (t.exit_time - t.entry_time).total_seconds() / 3600
            for t in trades
            if t.exit_time
        ]
        avg_holding_period = sum(holding_periods) / len(holding_periods) if holding_periods else 0.0

        # Performance by regime
        regime_performance = {}
        for trade in trades:
            regime = trade.regime_at_entry
            if regime not in regime_performance:
                regime_performance[regime] = {
                    "trades": 0,
                    "wins": 0,
                    "total_pnl": Decimal("0")
                }

            regime_performance[regime]["trades"] += 1
            if trade.pnl and trade.pnl > 0:
                regime_performance[regime]["wins"] += 1
            regime_performance[regime]["total_pnl"] += trade.pnl or Decimal("0")

        # Calculate win rates per regime
        for regime, perf in regime_performance.items():
            perf["win_rate"] = perf["wins"] / perf["trades"] if perf["trades"] > 0 else 0.0

        return BacktestResult(
            backtest_id=f"BT_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            strategy_name=strategy_name,
            underlying=underlying,
            start_date=start_date,
            end_date=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_pnl_per_trade=avg_pnl,
            max_win=max_win,
            max_loss=max_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            avg_holding_period_hours=avg_holding_period,
            regime_performance=regime_performance,
            trades=trades
        )


__all__ = ["Backtester", "BacktestResult", "BacktestTrade", "BacktestStatus"]
