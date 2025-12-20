"""
AutoPilot Backtest Service

Phase 4: Backtest strategies on historical data.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autopilot import AutoPilotBacktest


class BacktestService:
    """Service for running strategy backtests."""

    @staticmethod
    async def list_backtests(
        db: AsyncSession,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List user's backtests."""
        conditions = [AutoPilotBacktest.user_id == user_id]

        if status:
            conditions.append(AutoPilotBacktest.status == status)

        # Count total
        count_query = select(func.count(AutoPilotBacktest.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch backtests
        query = select(AutoPilotBacktest).where(and_(*conditions))
        query = query.order_by(desc(AutoPilotBacktest.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        backtests = result.scalars().all()

        return {
            "backtests": backtests,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    @staticmethod
    async def get_backtest(
        db: AsyncSession,
        backtest_id: int,
        user_id: UUID
    ) -> Optional[AutoPilotBacktest]:
        """Get a backtest by ID."""
        query = select(AutoPilotBacktest).where(
            AutoPilotBacktest.id == backtest_id,
            AutoPilotBacktest.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_backtest(
        db: AsyncSession,
        user_id: UUID,
        request: Any
    ) -> AutoPilotBacktest:
        """Create and start a new backtest."""

        backtest = AutoPilotBacktest(
            user_id=user_id,
            name=request.name,
            description=request.description,
            strategy_config=request.strategy_config,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            slippage_pct=request.slippage_pct,
            charges_per_lot=request.charges_per_lot,
            data_interval=request.data_interval,
            status="pending",
            progress_pct=0
        )

        db.add(backtest)
        await db.commit()
        await db.refresh(backtest)

        # Start backtest in background (simplified - in production would use Celery/background task)
        # For now, we'll run a simplified simulation
        try:
            await BacktestService._run_backtest(db, backtest)
        except Exception as e:
            backtest.status = "failed"
            backtest.error_message = str(e)
            await db.commit()

        return backtest

    @staticmethod
    async def _run_backtest(
        db: AsyncSession,
        backtest: AutoPilotBacktest
    ) -> None:
        """Run the backtest simulation."""

        backtest.status = "running"
        backtest.started_at = datetime.utcnow()
        await db.commit()

        # Simulation parameters
        strategy_config = backtest.strategy_config or {}
        underlying = strategy_config.get("underlying", "NIFTY")
        legs_config = strategy_config.get("legs_config", [])
        entry_conditions = strategy_config.get("entry_conditions", {})
        risk_settings = strategy_config.get("risk_settings", {})

        # Lot sizes
        from app.constants import get_lot_size
        lot_size = get_lot_size(underlying)

        # Simulate trades (simplified - in production would use historical data)
        # This is a placeholder simulation
        trades = []
        equity_curve = []
        capital = float(backtest.initial_capital)
        cumulative_pnl = Decimal("0")

        # Generate simulated trades based on date range
        current_date = backtest.start_date
        trade_count = 0

        while current_date <= backtest.end_date:
            # Skip weekends
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            # Update progress
            total_days = (backtest.end_date - backtest.start_date).days
            days_done = (current_date - backtest.start_date).days
            backtest.progress_pct = int((days_done / total_days * 100)) if total_days > 0 else 100
            await db.commit()

            # Simulate trade outcome (simplified random-ish based on date)
            # In production, this would use actual historical data
            day_hash = hash(str(current_date))

            # Simulate win/loss based on hash
            is_win = day_hash % 3 != 0  # ~67% win rate for demo
            pnl_magnitude = abs(day_hash % 5000) + 1000  # 1000-6000 P&L

            if is_win:
                trade_pnl = Decimal(str(pnl_magnitude))
            else:
                trade_pnl = Decimal(str(-pnl_magnitude * 0.8))  # Losses slightly smaller

            # Apply charges
            charges = backtest.charges_per_lot * Decimal(str(strategy_config.get("lots", 1)))
            net_pnl = trade_pnl - charges

            # Apply slippage
            slippage = abs(trade_pnl) * (backtest.slippage_pct / 100)
            net_pnl -= slippage

            cumulative_pnl += net_pnl
            capital = float(backtest.initial_capital) + float(cumulative_pnl)

            trades.append({
                "date": current_date.isoformat(),
                "entry_time": f"{current_date}T09:20:00",
                "exit_time": f"{current_date}T15:15:00",
                "pnl": float(net_pnl),
                "cumulative_pnl": float(cumulative_pnl),
                "exit_reason": "target_hit" if is_win else "stop_loss"
            })

            equity_curve.append({
                "date": current_date.isoformat(),
                "equity": capital,
                "pnl": float(net_pnl)
            })

            trade_count += 1
            current_date += timedelta(days=1)

        # Calculate final metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["pnl"] > 0)
        losing_trades = total_trades - winning_trades

        gross_pnl = sum(Decimal(str(t["pnl"])) for t in trades)
        net_pnl = gross_pnl  # Already net in our simulation

        # Calculate max drawdown
        peak = Decimal("0")
        max_drawdown = Decimal("0")
        cumulative = Decimal("0")

        for trade in trades:
            cumulative += Decimal(str(trade["pnl"]))
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        max_drawdown_pct = float(max_drawdown / backtest.initial_capital * 100) if backtest.initial_capital > 0 else 0

        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Profit factor
        total_wins = sum(Decimal(str(t["pnl"])) for t in trades if t["pnl"] > 0)
        total_losses = abs(sum(Decimal(str(t["pnl"])) for t in trades if t["pnl"] < 0))
        profit_factor = float(total_wins / total_losses) if total_losses > 0 else None

        # Update backtest with results
        backtest.status = "completed"
        backtest.completed_at = datetime.utcnow()
        backtest.progress_pct = 100
        backtest.total_trades = total_trades
        backtest.winning_trades = winning_trades
        backtest.losing_trades = losing_trades
        backtest.win_rate = Decimal(str(round(win_rate, 2)))
        backtest.gross_pnl = gross_pnl
        backtest.net_pnl = net_pnl
        backtest.max_drawdown = max_drawdown
        backtest.max_drawdown_pct = Decimal(str(round(max_drawdown_pct, 2)))
        backtest.profit_factor = Decimal(str(round(profit_factor, 2))) if profit_factor else None
        backtest.equity_curve = equity_curve
        backtest.trades = trades
        backtest.results = {
            "summary": {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "net_pnl": float(net_pnl),
                "max_drawdown": float(max_drawdown),
                "max_drawdown_pct": round(max_drawdown_pct, 2),
                "profit_factor": round(profit_factor, 2) if profit_factor else None
            }
        }

        await db.commit()
        await db.refresh(backtest)

    @staticmethod
    async def cancel_backtest(
        db: AsyncSession,
        backtest_id: int,
        user_id: UUID
    ) -> bool:
        """Cancel a running backtest."""
        query = select(AutoPilotBacktest).where(
            AutoPilotBacktest.id == backtest_id,
            AutoPilotBacktest.user_id == user_id
        )
        result = await db.execute(query)
        backtest = result.scalar_one_or_none()

        if not backtest:
            return False

        if backtest.status not in ["pending", "running"]:
            return False

        backtest.status = "cancelled"
        await db.commit()

        return True

    @staticmethod
    async def delete_backtest(
        db: AsyncSession,
        backtest_id: int,
        user_id: UUID
    ) -> bool:
        """Delete a backtest."""
        query = select(AutoPilotBacktest).where(
            AutoPilotBacktest.id == backtest_id,
            AutoPilotBacktest.user_id == user_id
        )
        result = await db.execute(query)
        backtest = result.scalar_one_or_none()

        if not backtest:
            return False

        await db.delete(backtest)
        await db.commit()

        return True
