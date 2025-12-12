"""
AutoPilot Analytics Service

Phase 4: Performance analytics, metrics, and insights.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from collections import defaultdict
from sqlalchemy import select, func, and_, extract, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autopilot import AutoPilotTradeJournal


class AnalyticsService:
    """Service for calculating performance analytics."""

    @staticmethod
    def _get_date_range(period: str) -> tuple[date, date]:
        """Get date range from period string."""
        today = date.today()

        if period == "7d":
            start = today - timedelta(days=7)
        elif period == "30d":
            start = today - timedelta(days=30)
        elif period == "90d":
            start = today - timedelta(days=90)
        elif period == "ytd":
            start = date(today.year, 1, 1)
        else:  # all
            start = date(2020, 1, 1)  # Far back date

        return start, today

    @staticmethod
    async def get_performance(
        db: AsyncSession,
        user_id: UUID,
        period: str = "30d",
        underlying: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comprehensive performance analytics."""
        start_date, end_date = AnalyticsService._get_date_range(period)

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.entry_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.entry_time <= datetime.combine(end_date, datetime.max.time())
        ]

        if underlying:
            conditions.append(AutoPilotTradeJournal.underlying == underlying)

        # Total trades
        total_query = select(func.count(AutoPilotTradeJournal.id)).where(and_(*conditions))
        total_result = await db.execute(total_query)
        total_trades = total_result.scalar() or 0

        if total_trades == 0:
            return {
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                "performance": {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0,
                    "gross_pnl": Decimal("0"),
                    "net_pnl": Decimal("0"),
                    "total_brokerage": Decimal("0"),
                    "avg_win": None,
                    "avg_loss": None,
                    "profit_factor": None,
                    "max_drawdown": None,
                    "max_drawdown_pct": None,
                    "sharpe_ratio": None,
                    "expectancy": None
                },
                "best_trade": None,
                "worst_trade": None,
                "avg_trade_pnl": None,
                "avg_holding_minutes": None,
                "most_traded_underlying": None,
                "most_profitable_strategy": None
            }

        # Winning trades
        win_query = select(func.count(AutoPilotTradeJournal.id)).where(
            and_(*conditions, AutoPilotTradeJournal.net_pnl > 0)
        )
        win_result = await db.execute(win_query)
        winning_trades = win_result.scalar() or 0

        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Total P&L and brokerage
        pnl_query = select(
            func.sum(AutoPilotTradeJournal.gross_pnl),
            func.sum(AutoPilotTradeJournal.net_pnl),
            func.sum(AutoPilotTradeJournal.brokerage)
        ).where(and_(*conditions))
        pnl_result = await db.execute(pnl_query)
        pnl_row = pnl_result.one()
        gross_pnl = pnl_row[0] or Decimal("0")
        net_pnl = pnl_row[1] or Decimal("0")
        total_brokerage = pnl_row[2] or Decimal("0")

        # Average win
        avg_win_query = select(func.avg(AutoPilotTradeJournal.net_pnl)).where(
            and_(*conditions, AutoPilotTradeJournal.net_pnl > 0)
        )
        avg_win_result = await db.execute(avg_win_query)
        avg_win = avg_win_result.scalar()

        # Average loss
        avg_loss_query = select(func.avg(AutoPilotTradeJournal.net_pnl)).where(
            and_(*conditions, AutoPilotTradeJournal.net_pnl < 0)
        )
        avg_loss_result = await db.execute(avg_loss_query)
        avg_loss = avg_loss_result.scalar()

        # Profit factor = Gross wins / Gross losses
        total_wins_query = select(func.sum(AutoPilotTradeJournal.net_pnl)).where(
            and_(*conditions, AutoPilotTradeJournal.net_pnl > 0)
        )
        total_wins_result = await db.execute(total_wins_query)
        total_wins = total_wins_result.scalar() or Decimal("0")

        total_losses_query = select(func.sum(AutoPilotTradeJournal.net_pnl)).where(
            and_(*conditions, AutoPilotTradeJournal.net_pnl < 0)
        )
        total_losses_result = await db.execute(total_losses_query)
        total_losses = abs(total_losses_result.scalar() or Decimal("0"))

        profit_factor = float(total_wins / total_losses) if total_losses > 0 else None

        # Best and worst trade
        best_query = select(func.max(AutoPilotTradeJournal.net_pnl)).where(and_(*conditions))
        best_result = await db.execute(best_query)
        best_trade = best_result.scalar()

        worst_query = select(func.min(AutoPilotTradeJournal.net_pnl)).where(and_(*conditions))
        worst_result = await db.execute(worst_query)
        worst_trade = worst_result.scalar()

        # Average trade P&L
        avg_pnl = net_pnl / total_trades if total_trades > 0 else None

        # Average holding duration
        avg_holding_query = select(func.avg(AutoPilotTradeJournal.holding_duration_minutes)).where(and_(*conditions))
        avg_holding_result = await db.execute(avg_holding_query)
        avg_holding = avg_holding_result.scalar()
        avg_holding_minutes = int(avg_holding) if avg_holding else None

        # Expectancy = (Win% * Avg Win) - (Loss% * Avg Loss)
        expectancy = None
        if avg_win is not None and avg_loss is not None:
            win_pct = winning_trades / total_trades if total_trades > 0 else 0
            loss_pct = losing_trades / total_trades if total_trades > 0 else 0
            expectancy = Decimal(str(win_pct * float(avg_win) - loss_pct * abs(float(avg_loss))))

        # Most traded underlying
        most_traded_query = select(
            AutoPilotTradeJournal.underlying,
            func.count(AutoPilotTradeJournal.id).label('count')
        ).where(and_(*conditions)).group_by(
            AutoPilotTradeJournal.underlying
        ).order_by(desc('count')).limit(1)
        most_traded_result = await db.execute(most_traded_query)
        most_traded_row = most_traded_result.first()
        most_traded_underlying = most_traded_row[0] if most_traded_row else None

        # Most profitable strategy
        most_profitable_query = select(
            AutoPilotTradeJournal.strategy_name,
            func.sum(AutoPilotTradeJournal.net_pnl).label('total_pnl')
        ).where(and_(*conditions)).group_by(
            AutoPilotTradeJournal.strategy_name
        ).order_by(desc('total_pnl')).limit(1)
        most_profitable_result = await db.execute(most_profitable_query)
        most_profitable_row = most_profitable_result.first()
        most_profitable_strategy = most_profitable_row[0] if most_profitable_row else None

        # Calculate max drawdown (simplified - from cumulative P&L)
        trades_query = select(AutoPilotTradeJournal).where(and_(*conditions)).order_by(AutoPilotTradeJournal.exit_time)
        trades_result = await db.execute(trades_query)
        trades = trades_result.scalars().all()

        max_drawdown = Decimal("0")
        max_drawdown_pct = 0.0
        peak = Decimal("0")
        cumulative = Decimal("0")

        for trade in trades:
            if trade.net_pnl:
                cumulative += trade.net_pnl
                if cumulative > peak:
                    peak = cumulative
                drawdown = peak - cumulative
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    if peak > 0:
                        max_drawdown_pct = float(drawdown / peak * 100)

        return {
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "performance": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "total_brokerage": total_brokerage,
                "avg_win": Decimal(str(round(avg_win, 2))) if avg_win else None,
                "avg_loss": Decimal(str(round(avg_loss, 2))) if avg_loss else None,
                "profit_factor": round(profit_factor, 2) if profit_factor else None,
                "max_drawdown": max_drawdown,
                "max_drawdown_pct": round(max_drawdown_pct, 2) if max_drawdown_pct else None,
                "sharpe_ratio": None,  # Would need daily returns to calculate
                "expectancy": expectancy
            },
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "avg_trade_pnl": avg_pnl,
            "avg_holding_minutes": avg_holding_minutes,
            "most_traded_underlying": most_traded_underlying,
            "most_profitable_strategy": most_profitable_strategy
        }

    @staticmethod
    async def get_daily_pnl(
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get daily P&L breakdown."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.exit_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.exit_time <= datetime.combine(end_date, datetime.max.time())
        ]

        # Get all trades in period
        query = select(AutoPilotTradeJournal).where(and_(*conditions)).order_by(AutoPilotTradeJournal.exit_time)
        result = await db.execute(query)
        trades = result.scalars().all()

        # Group by date
        daily_data = defaultdict(lambda: {"pnl": Decimal("0"), "trades": 0})

        for trade in trades:
            if trade.exit_time and trade.net_pnl:
                trade_date = trade.exit_time.date()
                daily_data[trade_date]["pnl"] += trade.net_pnl
                daily_data[trade_date]["trades"] += 1

        # Build result with cumulative P&L
        result_list = []
        cumulative = Decimal("0")

        current_date = start_date
        while current_date <= end_date:
            day_data = daily_data.get(current_date, {"pnl": Decimal("0"), "trades": 0})
            cumulative += day_data["pnl"]

            result_list.append({
                "date": current_date,
                "pnl": day_data["pnl"],
                "trades": day_data["trades"],
                "cumulative_pnl": cumulative
            })
            current_date += timedelta(days=1)

        return result_list

    @staticmethod
    async def get_by_strategy(
        db: AsyncSession,
        user_id: UUID,
        period: str = "30d"
    ) -> List[Dict[str, Any]]:
        """Get performance breakdown by strategy."""
        start_date, end_date = AnalyticsService._get_date_range(period)

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.entry_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.entry_time <= datetime.combine(end_date, datetime.max.time())
        ]

        query = select(
            AutoPilotTradeJournal.strategy_name,
            AutoPilotTradeJournal.underlying,
            func.count(AutoPilotTradeJournal.id).label('trades'),
            func.sum(AutoPilotTradeJournal.net_pnl).label('pnl'),
            func.avg(AutoPilotTradeJournal.holding_duration_minutes).label('avg_holding')
        ).where(and_(*conditions)).group_by(
            AutoPilotTradeJournal.strategy_name,
            AutoPilotTradeJournal.underlying
        ).order_by(desc('pnl'))

        result = await db.execute(query)
        rows = result.all()

        strategies = []
        for row in rows:
            # Calculate win rate per strategy
            win_query = select(func.count(AutoPilotTradeJournal.id)).where(
                and_(
                    *conditions,
                    AutoPilotTradeJournal.strategy_name == row.strategy_name,
                    AutoPilotTradeJournal.net_pnl > 0
                )
            )
            win_result = await db.execute(win_query)
            wins = win_result.scalar() or 0
            win_rate = (wins / row.trades * 100) if row.trades > 0 else 0

            strategies.append({
                "strategy_name": row.strategy_name,
                "underlying": row.underlying,
                "trades": row.trades,
                "win_rate": round(win_rate, 2),
                "pnl": row.pnl or Decimal("0"),
                "avg_holding_minutes": int(row.avg_holding) if row.avg_holding else None
            })

        return strategies

    @staticmethod
    async def get_by_weekday(
        db: AsyncSession,
        user_id: UUID,
        period: str = "30d"
    ) -> List[Dict[str, Any]]:
        """Get performance breakdown by weekday."""
        start_date, end_date = AnalyticsService._get_date_range(period)

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.entry_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.entry_time <= datetime.combine(end_date, datetime.max.time())
        ]

        # Get all trades
        query = select(AutoPilotTradeJournal).where(and_(*conditions))
        result = await db.execute(query)
        trades = result.scalars().all()

        # Group by weekday
        weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        weekday_data = defaultdict(lambda: {"pnl": Decimal("0"), "trades": 0, "wins": 0})

        for trade in trades:
            if trade.entry_time:
                weekday = trade.entry_time.weekday()
                weekday_data[weekday]["trades"] += 1
                if trade.net_pnl:
                    weekday_data[weekday]["pnl"] += trade.net_pnl
                    if trade.net_pnl > 0:
                        weekday_data[weekday]["wins"] += 1

        weekdays = []
        for i, name in enumerate(weekday_names):
            data = weekday_data.get(i, {"pnl": Decimal("0"), "trades": 0, "wins": 0})
            win_rate = (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0

            weekdays.append({
                "weekday": name,
                "trades": data["trades"],
                "pnl": data["pnl"],
                "win_rate": round(win_rate, 2)
            })

        return weekdays

    @staticmethod
    async def get_drawdown(
        db: AsyncSession,
        user_id: UUID,
        period: str = "30d"
    ) -> Dict[str, Any]:
        """Get drawdown analysis."""
        start_date, end_date = AnalyticsService._get_date_range(period)

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.exit_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.exit_time <= datetime.combine(end_date, datetime.max.time())
        ]

        query = select(AutoPilotTradeJournal).where(and_(*conditions)).order_by(AutoPilotTradeJournal.exit_time)
        result = await db.execute(query)
        trades = result.scalars().all()

        if not trades:
            return {
                "max_drawdown": Decimal("0"),
                "max_drawdown_pct": 0.0,
                "max_drawdown_date": None,
                "recovery_date": None,
                "drawdown_periods": [],
                "current_drawdown": Decimal("0"),
                "current_drawdown_pct": 0.0
            }

        # Calculate drawdown series
        cumulative = Decimal("0")
        peak = Decimal("0")
        max_drawdown = Decimal("0")
        max_drawdown_date = None
        current_drawdown = Decimal("0")
        drawdown_periods = []
        in_drawdown = False
        drawdown_start = None

        for trade in trades:
            if trade.net_pnl:
                cumulative += trade.net_pnl

                if cumulative > peak:
                    # New peak - if we were in drawdown, record recovery
                    if in_drawdown:
                        drawdown_periods.append({
                            "start_date": drawdown_start,
                            "end_date": trade.exit_time.date() if trade.exit_time else None,
                            "depth": max_drawdown
                        })
                        in_drawdown = False

                    peak = cumulative

                drawdown = peak - cumulative
                if drawdown > 0 and not in_drawdown:
                    in_drawdown = True
                    drawdown_start = trade.exit_time.date() if trade.exit_time else None

                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_date = trade.exit_time.date() if trade.exit_time else None

                current_drawdown = drawdown

        max_drawdown_pct = float(max_drawdown / peak * 100) if peak > 0 else 0.0
        current_drawdown_pct = float(current_drawdown / peak * 100) if peak > 0 else 0.0

        return {
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "max_drawdown_date": max_drawdown_date,
            "recovery_date": None,  # Would need more logic
            "drawdown_periods": drawdown_periods[-5:],  # Last 5 periods
            "current_drawdown": current_drawdown,
            "current_drawdown_pct": round(current_drawdown_pct, 2)
        }

    @staticmethod
    async def get_by_underlying(
        db: AsyncSession,
        user_id: UUID,
        period: str = "30d"
    ) -> List[Dict[str, Any]]:
        """Get performance breakdown by underlying."""
        start_date, end_date = AnalyticsService._get_date_range(period)

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False,
            AutoPilotTradeJournal.entry_time >= datetime.combine(start_date, datetime.min.time()),
            AutoPilotTradeJournal.entry_time <= datetime.combine(end_date, datetime.max.time())
        ]

        query = select(
            AutoPilotTradeJournal.underlying,
            func.count(AutoPilotTradeJournal.id).label('trades'),
            func.sum(AutoPilotTradeJournal.net_pnl).label('pnl')
        ).where(and_(*conditions)).group_by(
            AutoPilotTradeJournal.underlying
        ).order_by(desc('pnl'))

        result = await db.execute(query)
        rows = result.all()

        underlyings = []
        for row in rows:
            underlyings.append({
                "underlying": row.underlying,
                "trades": row.trades,
                "pnl": row.pnl or Decimal("0")
            })

        return underlyings
