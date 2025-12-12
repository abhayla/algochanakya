"""
AutoPilot Trade Journal Service

Phase 4: Automatic trade logging and journal management.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
import csv
import io
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autopilot import (
    AutoPilotTradeJournal, AutoPilotStrategy, AutoPilotOrder
)
from app.schemas.autopilot import (
    TradeJournalUpdateRequest, TradeJournalExportRequest
)


class TradeJournalService:
    """Service for managing trade journal entries."""

    @staticmethod
    async def list_trades(
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        underlying: Optional[str] = None,
        exit_reason: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_open: Optional[bool] = None,
        min_pnl: Optional[Decimal] = None,
        max_pnl: Optional[Decimal] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List trade journal entries with filters."""

        conditions = [AutoPilotTradeJournal.user_id == user_id]

        if start_date:
            conditions.append(AutoPilotTradeJournal.entry_time >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            conditions.append(AutoPilotTradeJournal.entry_time <= datetime.combine(end_date, datetime.max.time()))
        if underlying:
            conditions.append(AutoPilotTradeJournal.underlying == underlying)
        if exit_reason:
            conditions.append(AutoPilotTradeJournal.exit_reason == exit_reason)
        if tags:
            conditions.append(AutoPilotTradeJournal.tags.contains(tags))
        if is_open is not None:
            conditions.append(AutoPilotTradeJournal.is_open == is_open)
        if min_pnl is not None:
            conditions.append(AutoPilotTradeJournal.net_pnl >= min_pnl)
        if max_pnl is not None:
            conditions.append(AutoPilotTradeJournal.net_pnl <= max_pnl)

        # Count total
        count_query = select(func.count(AutoPilotTradeJournal.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch trades
        query = select(AutoPilotTradeJournal).where(and_(*conditions))
        query = query.order_by(desc(AutoPilotTradeJournal.entry_time))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        trades = result.scalars().all()

        return {
            "trades": trades,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    @staticmethod
    async def get_trade(
        db: AsyncSession,
        trade_id: int,
        user_id: UUID
    ) -> Optional[AutoPilotTradeJournal]:
        """Get a trade journal entry by ID."""
        query = select(AutoPilotTradeJournal).where(
            AutoPilotTradeJournal.id == trade_id,
            AutoPilotTradeJournal.user_id == user_id
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_trade_entry(
        db: AsyncSession,
        user_id: UUID,
        strategy: AutoPilotStrategy,
        entry_orders: List[AutoPilotOrder],
        entry_premium: Decimal,
        market_conditions: Optional[Dict[str, Any]] = None
    ) -> AutoPilotTradeJournal:
        """Create a trade journal entry when strategy enters position."""

        # Build legs snapshot from orders
        legs = []
        total_quantity = 0
        for order in entry_orders:
            legs.append({
                "leg_id": f"leg_{order.leg_index}",
                "contract_type": order.contract_type,
                "transaction_type": order.transaction_type,
                "strike": float(order.strike) if order.strike else None,
                "expiry": order.expiry.isoformat() if order.expiry else None,
                "entry_price": float(order.executed_price) if order.executed_price else None,
                "quantity": order.quantity,
                "tradingsymbol": order.tradingsymbol
            })
            total_quantity += order.quantity

        # Get lot size
        lot_sizes = {"NIFTY": 25, "BANKNIFTY": 15, "FINNIFTY": 25, "SENSEX": 10}
        lot_size = lot_sizes.get(strategy.underlying, 25)
        lots = total_quantity // lot_size if lot_size else strategy.lots

        trade = AutoPilotTradeJournal(
            user_id=user_id,
            strategy_id=strategy.id,
            strategy_name=strategy.name,
            underlying=strategy.underlying,
            position_type=strategy.position_type,
            entry_time=datetime.utcnow(),
            legs=legs,
            lots=lots,
            total_quantity=total_quantity,
            entry_premium=entry_premium,
            market_conditions=market_conditions or {},
            entry_order_ids=[o.id for o in entry_orders],
            is_open=True
        )

        db.add(trade)
        await db.commit()
        await db.refresh(trade)

        return trade

    @staticmethod
    async def close_trade_entry(
        db: AsyncSession,
        trade_id: int,
        user_id: UUID,
        exit_orders: List[AutoPilotOrder],
        exit_premium: Decimal,
        exit_reason: str,
        gross_pnl: Decimal,
        brokerage: Decimal = Decimal("0"),
        taxes: Decimal = Decimal("0"),
        max_profit_reached: Optional[Decimal] = None,
        max_loss_reached: Optional[Decimal] = None,
        max_drawdown: Optional[Decimal] = None,
        market_conditions_exit: Optional[Dict[str, Any]] = None
    ) -> Optional[AutoPilotTradeJournal]:
        """Close a trade journal entry when strategy exits."""

        trade = await TradeJournalService.get_trade(db, trade_id, user_id)
        if not trade or not trade.is_open:
            return None

        # Calculate P&L
        net_pnl = gross_pnl - brokerage - taxes
        pnl_percentage = None
        if trade.entry_premium and trade.entry_premium > 0:
            pnl_percentage = (net_pnl / trade.entry_premium) * 100

        # Calculate holding duration
        exit_time = datetime.utcnow()
        holding_duration = int((exit_time - trade.entry_time).total_seconds() / 60)

        # Update legs with exit prices
        legs = trade.legs or []
        for order in exit_orders:
            for leg in legs:
                if leg.get("tradingsymbol") == order.tradingsymbol:
                    leg["exit_price"] = float(order.executed_price) if order.executed_price else None

        # Merge market conditions
        market_conditions = trade.market_conditions or {}
        if market_conditions_exit:
            market_conditions.update({
                "vix_at_exit": market_conditions_exit.get("vix"),
                "spot_at_exit": market_conditions_exit.get("spot")
            })

        # Update trade entry
        trade.exit_time = exit_time
        trade.holding_duration_minutes = holding_duration
        trade.exit_premium = exit_premium
        trade.gross_pnl = gross_pnl
        trade.brokerage = brokerage
        trade.taxes = taxes
        trade.net_pnl = net_pnl
        trade.pnl_percentage = pnl_percentage
        trade.max_profit_reached = max_profit_reached
        trade.max_loss_reached = max_loss_reached
        trade.max_drawdown = max_drawdown
        trade.exit_reason = exit_reason
        trade.exit_order_ids = [o.id for o in exit_orders]
        trade.legs = legs
        trade.market_conditions = market_conditions
        trade.is_open = False

        await db.commit()
        await db.refresh(trade)

        return trade

    @staticmethod
    async def update_trade(
        db: AsyncSession,
        trade_id: int,
        user_id: UUID,
        request: TradeJournalUpdateRequest
    ) -> Optional[AutoPilotTradeJournal]:
        """Update trade notes/tags."""

        trade = await TradeJournalService.get_trade(db, trade_id, user_id)
        if not trade:
            return None

        if request.notes is not None:
            trade.notes = request.notes
        if request.tags is not None:
            trade.tags = request.tags

        await db.commit()
        await db.refresh(trade)

        return trade

    @staticmethod
    async def get_journal_stats(
        db: AsyncSession,
        user_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get journal statistics."""

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False
        ]

        if start_date:
            conditions.append(AutoPilotTradeJournal.entry_time >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            conditions.append(AutoPilotTradeJournal.entry_time <= datetime.combine(end_date, datetime.max.time()))

        # Total trades
        total_query = select(func.count(AutoPilotTradeJournal.id)).where(and_(*conditions))
        total_result = await db.execute(total_query)
        total_trades = total_result.scalar() or 0

        if total_trades == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "gross_pnl": Decimal("0"),
                "net_pnl": Decimal("0"),
                "avg_win": None,
                "avg_loss": None,
                "best_trade": None,
                "worst_trade": None
            }

        # Winning trades
        win_query = select(func.count(AutoPilotTradeJournal.id)).where(
            and_(*conditions, AutoPilotTradeJournal.net_pnl > 0)
        )
        win_result = await db.execute(win_query)
        winning_trades = win_result.scalar() or 0

        # Losing trades
        losing_trades = total_trades - winning_trades

        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # Total P&L
        pnl_query = select(
            func.sum(AutoPilotTradeJournal.gross_pnl),
            func.sum(AutoPilotTradeJournal.net_pnl)
        ).where(and_(*conditions))
        pnl_result = await db.execute(pnl_query)
        pnl_row = pnl_result.one()
        gross_pnl = pnl_row[0] or Decimal("0")
        net_pnl = pnl_row[1] or Decimal("0")

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

        # Best and worst trade
        best_query = select(func.max(AutoPilotTradeJournal.net_pnl)).where(and_(*conditions))
        best_result = await db.execute(best_query)
        best_trade = best_result.scalar()

        worst_query = select(func.min(AutoPilotTradeJournal.net_pnl)).where(and_(*conditions))
        worst_result = await db.execute(worst_query)
        worst_trade = worst_result.scalar()

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "avg_win": Decimal(str(round(avg_win, 2))) if avg_win else None,
            "avg_loss": Decimal(str(round(avg_loss, 2))) if avg_loss else None,
            "best_trade": best_trade,
            "worst_trade": worst_trade
        }

    @staticmethod
    async def export_trades(
        db: AsyncSession,
        user_id: UUID,
        request: TradeJournalExportRequest
    ) -> str:
        """Export trades to CSV format."""

        conditions = [
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.is_open == False
        ]

        if request.start_date:
            conditions.append(AutoPilotTradeJournal.entry_time >= datetime.combine(request.start_date, datetime.min.time()))
        if request.end_date:
            conditions.append(AutoPilotTradeJournal.entry_time <= datetime.combine(request.end_date, datetime.max.time()))
        if request.underlying:
            conditions.append(AutoPilotTradeJournal.underlying == request.underlying)
        if request.exit_reason:
            conditions.append(AutoPilotTradeJournal.exit_reason == request.exit_reason)

        query = select(AutoPilotTradeJournal).where(and_(*conditions))
        query = query.order_by(desc(AutoPilotTradeJournal.entry_time))

        result = await db.execute(query)
        trades = result.scalars().all()

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "ID", "Strategy Name", "Underlying", "Position Type",
            "Entry Time", "Exit Time", "Holding Duration (min)",
            "Lots", "Entry Premium", "Exit Premium",
            "Gross P&L", "Brokerage", "Taxes", "Net P&L", "P&L %",
            "Exit Reason", "Tags", "Notes"
        ])

        # Data
        for trade in trades:
            writer.writerow([
                trade.id,
                trade.strategy_name,
                trade.underlying,
                trade.position_type,
                trade.entry_time.isoformat() if trade.entry_time else "",
                trade.exit_time.isoformat() if trade.exit_time else "",
                trade.holding_duration_minutes,
                trade.lots,
                float(trade.entry_premium) if trade.entry_premium else "",
                float(trade.exit_premium) if trade.exit_premium else "",
                float(trade.gross_pnl) if trade.gross_pnl else "",
                float(trade.brokerage) if trade.brokerage else "",
                float(trade.taxes) if trade.taxes else "",
                float(trade.net_pnl) if trade.net_pnl else "",
                float(trade.pnl_percentage) if trade.pnl_percentage else "",
                trade.exit_reason,
                ",".join(trade.tags) if trade.tags else "",
                trade.notes or ""
            ])

        return output.getvalue()

    @staticmethod
    async def find_open_trade_for_strategy(
        db: AsyncSession,
        user_id: UUID,
        strategy_id: int
    ) -> Optional[AutoPilotTradeJournal]:
        """Find open trade entry for a strategy."""
        query = select(AutoPilotTradeJournal).where(
            AutoPilotTradeJournal.user_id == user_id,
            AutoPilotTradeJournal.strategy_id == strategy_id,
            AutoPilotTradeJournal.is_open == True
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_trade_metrics(
        db: AsyncSession,
        trade_id: int,
        user_id: UUID,
        current_pnl: Decimal,
        max_profit: Optional[Decimal] = None,
        max_loss: Optional[Decimal] = None,
        max_drawdown: Optional[Decimal] = None
    ) -> Optional[AutoPilotTradeJournal]:
        """Update live metrics for an open trade."""

        trade = await TradeJournalService.get_trade(db, trade_id, user_id)
        if not trade or not trade.is_open:
            return None

        # Update max profit
        if max_profit is not None:
            if trade.max_profit_reached is None or max_profit > trade.max_profit_reached:
                trade.max_profit_reached = max_profit

        # Update max loss
        if max_loss is not None:
            if trade.max_loss_reached is None or max_loss < trade.max_loss_reached:
                trade.max_loss_reached = max_loss

        # Update max drawdown
        if max_drawdown is not None:
            if trade.max_drawdown is None or max_drawdown > trade.max_drawdown:
                trade.max_drawdown = max_drawdown

        await db.commit()
        await db.refresh(trade)

        return trade
