"""
AI Position Synchronization Service

Real-time synchronization of positions from broker with AI analysis.

Features:
- Fetch positions from Kite Connect
- Track position changes (entry/exit)
- Calculate real-time P&L
- Detect strategy mismatches
- Log position events
- Provide position analytics
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

logger = logging.getLogger(__name__)


class PositionChange:
    """Represents a detected change in positions."""

    def __init__(
        self,
        change_type: str,  # "entry", "exit", "adjustment"
        instrument: str,
        quantity_change: int,
        timestamp: datetime
    ):
        self.change_type = change_type
        self.instrument = instrument
        self.quantity_change = quantity_change
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        return {
            "change_type": self.change_type,
            "instrument": self.instrument,
            "quantity_change": self.quantity_change,
            "timestamp": self.timestamp.isoformat()
        }


class PositionAnalysis:
    """Analysis of current position portfolio."""

    def __init__(
        self,
        total_positions: int,
        total_pnl: float,
        total_margin_used: float,
        max_loss_position: Optional[Dict] = None,
        max_profit_position: Optional[Dict] = None,
        strategy_breakdown: Optional[Dict] = None
    ):
        self.total_positions = total_positions
        self.total_pnl = total_pnl
        self.total_margin_used = total_margin_used
        self.max_loss_position = max_loss_position
        self.max_profit_position = max_profit_position
        self.strategy_breakdown = strategy_breakdown or {}

    def to_dict(self) -> Dict:
        return {
            "total_positions": self.total_positions,
            "total_pnl": self.total_pnl,
            "total_margin_used": self.total_margin_used,
            "max_loss_position": self.max_loss_position,
            "max_profit_position": self.max_profit_position,
            "strategy_breakdown": self.strategy_breakdown
        }


class PositionSyncService:
    """
    Real-time position synchronization and analysis.

    Workflow:
    1. Fetch positions from broker
    2. Compare with last known state
    3. Detect changes (entries/exits)
    4. Update database
    5. Analyze portfolio health
    6. Log sync events
    """

    def __init__(self, kite: KiteConnect, db: AsyncSession):
        self.kite = kite
        self.db = db
        self._last_positions: Dict[str, Dict] = {}

    async def sync_positions(self, user_id: str) -> PositionAnalysis:
        """
        Sync positions from broker and analyze.

        Args:
            user_id: User ID for position tracking

        Returns:
            PositionAnalysis with current portfolio state
        """
        try:
            logger.info(f"Syncing positions for user {user_id}")

            # Step 1: Fetch positions from broker
            positions = await self._fetch_broker_positions()

            # Step 2: Detect changes
            changes = self._detect_changes(positions)

            if changes:
                logger.info(f"Detected {len(changes)} position changes")
                for change in changes:
                    logger.info(f"  {change.change_type.upper()}: {change.instrument} ({change.quantity_change:+d})")
                    # await self._log_position_event(user_id, change)

            # Step 3: Update cached state
            self._last_positions = {p["instrument"]: p for p in positions}

            # Step 4: Analyze portfolio
            analysis = self._analyze_positions(positions)

            logger.info(f"Sync complete: {analysis.total_positions} positions, P&L: {analysis.total_pnl:+.2f}")
            return analysis

        except Exception as e:
            logger.error(f"Position sync failed: {e}")
            # Return empty analysis on error
            return PositionAnalysis(
                total_positions=0,
                total_pnl=0.0,
                total_margin_used=0.0
            )

    async def _fetch_broker_positions(self) -> List[Dict]:
        """
        Fetch positions from Kite Connect.

        Returns:
            List of position dictionaries
        """
        try:
            positions = self.kite.positions()
            # Kite returns {"net": [...], "day": [...]}
            net_positions = positions.get("net", [])

            # Filter F&O positions only
            fo_positions = [
                p for p in net_positions
                if p.get("exchange") == "NFO" and p.get("quantity", 0) != 0
            ]

            return [
                {
                    "instrument": p.get("tradingsymbol", ""),
                    "quantity": p.get("quantity", 0),
                    "pnl": p.get("pnl", 0.0),
                    "average_price": p.get("average_price", 0.0),
                    "ltp": p.get("last_price", 0.0),
                    "product": p.get("product", ""),
                    "exchange": p.get("exchange", "NFO")
                }
                for p in fo_positions
            ]

        except Exception as e:
            logger.error(f"Failed to fetch broker positions: {e}")
            return []

    def _detect_changes(self, current_positions: List[Dict]) -> List[PositionChange]:
        """
        Detect changes between current and last known positions.

        Args:
            current_positions: Current positions from broker

        Returns:
            List of detected changes
        """
        changes = []
        current_map = {p["instrument"]: p for p in current_positions}

        # Detect new entries and quantity increases
        for instrument, current in current_map.items():
            if instrument not in self._last_positions:
                # New position
                changes.append(PositionChange(
                    change_type="entry",
                    instrument=instrument,
                    quantity_change=current["quantity"],
                    timestamp=datetime.utcnow()
                ))
            else:
                last = self._last_positions[instrument]
                qty_diff = current["quantity"] - last["quantity"]

                if qty_diff != 0:
                    # Position adjusted
                    changes.append(PositionChange(
                        change_type="adjustment",
                        instrument=instrument,
                        quantity_change=qty_diff,
                        timestamp=datetime.utcnow()
                    ))

        # Detect exits
        for instrument, last in self._last_positions.items():
            if instrument not in current_map:
                # Position closed
                changes.append(PositionChange(
                    change_type="exit",
                    instrument=instrument,
                    quantity_change=-last["quantity"],
                    timestamp=datetime.utcnow()
                ))

        return changes

    def _analyze_positions(self, positions: List[Dict]) -> PositionAnalysis:
        """
        Analyze current position portfolio.

        Args:
            positions: List of positions

        Returns:
            PositionAnalysis with portfolio metrics
        """
        if not positions:
            return PositionAnalysis(
                total_positions=0,
                total_pnl=0.0,
                total_margin_used=0.0
            )

        total_pnl = sum(p["pnl"] for p in positions)
        total_positions = len(positions)

        # Find max profit/loss positions
        sorted_by_pnl = sorted(positions, key=lambda p: p["pnl"])
        max_loss = sorted_by_pnl[0] if sorted_by_pnl else None
        max_profit = sorted_by_pnl[-1] if sorted_by_pnl else None

        # Strategy breakdown (simplified)
        # In real implementation, would group by underlying/expiry
        strategy_breakdown = {
            "long_positions": len([p for p in positions if p["quantity"] > 0]),
            "short_positions": len([p for p in positions if p["quantity"] < 0]),
            "total_qty": sum(abs(p["quantity"]) for p in positions)
        }

        return PositionAnalysis(
            total_positions=total_positions,
            total_pnl=total_pnl,
            total_margin_used=0.0,  # Would need margin API call
            max_loss_position=max_loss,
            max_profit_position=max_profit,
            strategy_breakdown=strategy_breakdown
        )

    async def _log_position_event(self, user_id: str, change: PositionChange):
        """
        Log position change event to database.

        Args:
            user_id: User ID
            change: Position change details
        """
        # Placeholder for database logging
        # In real implementation, would insert into ai_position_sync_events table
        logger.debug(f"Logging position event for user {user_id}: {change.to_dict()}")

    async def get_position_health_score(self, analysis: PositionAnalysis) -> float:
        """
        Calculate a health score for the current portfolio (0-100).

        Args:
            analysis: Current position analysis

        Returns:
            Health score (0-100, higher is better)
        """
        score = 100.0

        # Penalize if in loss
        if analysis.total_pnl < 0:
            loss_ratio = abs(analysis.total_pnl) / max(analysis.total_margin_used, 1000)
            score -= min(50, loss_ratio * 100)

        # Penalize for concentration risk (too many positions)
        if analysis.total_positions > 10:
            score -= min(20, (analysis.total_positions - 10) * 2)

        # Ensure score is in range
        return max(0.0, min(100.0, score))


__all__ = [
    "PositionSyncService",
    "PositionAnalysis",
    "PositionChange"
]
