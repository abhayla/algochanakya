"""
Trailing Stop Service - Phase 3

Dynamic stop loss that trails profit.

Configuration:
- enabled: Enable trailing stop
- activation_profit: Profit threshold to activate trailing stop
- trail_distance: Distance to trail behind highest profit
- trail_type: 'fixed' | 'percentage' | 'atr_based'
- min_profit_lock: Minimum profit to lock

Logic:
1. When unrealized profit >= activation_profit, trailing stop activates
2. Track highest profit reached (high_water_mark)
3. Stop loss = high_water_mark - trail_distance
4. If current P&L drops below stop loss, exit position
5. Ensure minimum profit is locked (min_profit_lock)
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotLog,
    LogSeverity
)
from app.schemas.autopilot import TrailingStopStatus

logger = logging.getLogger(__name__)


class TrailingStopService:
    """
    Service for managing trailing stop loss functionality.

    Trailing stops protect profits by setting a dynamic stop level
    that moves up as profit increases, but never moves down.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.websocket_manager = None

    def set_websocket_manager(self, manager):
        """Inject WebSocket manager for sending alerts"""
        self.websocket_manager = manager

    async def get_status(
        self,
        strategy: AutoPilotStrategy,
        current_pnl: Decimal
    ) -> TrailingStopStatus:
        """
        Get current trailing stop status for a strategy.

        Args:
            strategy: The strategy to check
            current_pnl: Current unrealized P&L

        Returns:
            TrailingStopStatus with current state
        """
        config = strategy.trailing_stop_config or {}

        if not config.get('enabled', False):
            return TrailingStopStatus(
                enabled=False,
                active=False
            )

        runtime_state = strategy.runtime_state or {}
        trailing_state = runtime_state.get('trailing_stop', {})

        return TrailingStopStatus(
            enabled=True,
            active=trailing_state.get('active', False),
            high_water_mark=Decimal(str(trailing_state.get('high_water_mark', 0))) if trailing_state.get('high_water_mark') else None,
            current_stop_level=Decimal(str(trailing_state.get('stop_level', 0))) if trailing_state.get('stop_level') else None,
            current_pnl=current_pnl,
            distance_to_stop=current_pnl - Decimal(str(trailing_state.get('stop_level', 0))) if trailing_state.get('stop_level') else None
        )

    async def update_trailing_stop(
        self,
        strategy: AutoPilotStrategy,
        current_pnl: Decimal
    ) -> Tuple[bool, Optional[str]]:
        """
        Update trailing stop state based on current P&L.

        Args:
            strategy: The strategy to update
            current_pnl: Current unrealized P&L

        Returns:
            Tuple of (should_exit, reason)
        """
        config = strategy.trailing_stop_config or {}

        if not config.get('enabled', False):
            return (False, None)

        runtime_state = strategy.runtime_state or {}
        trailing_state = runtime_state.get('trailing_stop', {})

        activation_profit = Decimal(str(config.get('activation_profit', 0)))
        trail_distance = Decimal(str(config.get('trail_distance', 0)))
        trail_type = config.get('trail_type', 'fixed')
        min_profit_lock = Decimal(str(config.get('min_profit_lock', 0)))

        is_active = trailing_state.get('active', False)
        high_water_mark = Decimal(str(trailing_state.get('high_water_mark', 0)))
        stop_level = Decimal(str(trailing_state.get('stop_level', 0)))

        # Check if trailing stop should activate
        if not is_active and current_pnl >= activation_profit:
            is_active = True
            high_water_mark = current_pnl
            stop_level = self._calculate_stop_level(
                high_water_mark, trail_distance, trail_type, min_profit_lock
            )

            # Log activation
            await self._log_trailing_stop_event(
                strategy,
                'trailing_stop_activated',
                f"Trailing stop activated at profit {current_pnl}"
            )

            # Send WebSocket notification
            await self._send_trailing_stop_notification(
                strategy,
                'trailing_stop_activated',
                high_water_mark,
                stop_level,
                current_pnl
            )

            logger.info(f"Trailing stop activated for strategy {strategy.id}")

        # Update high water mark if profit increased
        elif is_active and current_pnl > high_water_mark:
            high_water_mark = current_pnl
            new_stop_level = self._calculate_stop_level(
                high_water_mark, trail_distance, trail_type, min_profit_lock
            )

            # Only update if new stop is higher
            if new_stop_level > stop_level:
                stop_level = new_stop_level

                # Send WebSocket notification
                await self._send_trailing_stop_notification(
                    strategy,
                    'trailing_stop_updated',
                    high_water_mark,
                    stop_level,
                    current_pnl
                )

                logger.info(f"Trailing stop updated for strategy {strategy.id}: HWM={high_water_mark}, Stop={stop_level}")

        # Update runtime state
        runtime_state['trailing_stop'] = {
            'active': is_active,
            'high_water_mark': float(high_water_mark),
            'stop_level': float(stop_level),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        strategy.runtime_state = runtime_state

        # Check if stop is triggered
        if is_active and current_pnl <= stop_level:
            await self._log_trailing_stop_event(
                strategy,
                'exit_triggered',
                f"Trailing stop triggered: P&L {current_pnl} <= Stop {stop_level}"
            )
            return (True, f"Trailing stop triggered at {stop_level}")

        return (False, None)

    async def check_stop_triggered(
        self,
        strategy: AutoPilotStrategy,
        current_pnl: Decimal
    ) -> bool:
        """
        Quick check if trailing stop is triggered.

        Args:
            strategy: The strategy to check
            current_pnl: Current unrealized P&L

        Returns:
            True if stop is triggered and position should be exited
        """
        config = strategy.trailing_stop_config or {}

        if not config.get('enabled', False):
            return False

        runtime_state = strategy.runtime_state or {}
        trailing_state = runtime_state.get('trailing_stop', {})

        if not trailing_state.get('active', False):
            return False

        stop_level = Decimal(str(trailing_state.get('stop_level', 0)))
        return current_pnl <= stop_level

    def _calculate_stop_level(
        self,
        high_water_mark: Decimal,
        trail_distance: Decimal,
        trail_type: str,
        min_profit_lock: Decimal
    ) -> Decimal:
        """
        Calculate the stop level based on configuration.

        Args:
            high_water_mark: Highest profit reached
            trail_distance: Trail distance configuration
            trail_type: Type of trailing ('fixed', 'percentage', 'atr_based')
            min_profit_lock: Minimum profit to lock

        Returns:
            Calculated stop level
        """
        if trail_type == 'percentage':
            # Trail by percentage of profit
            trail_amount = high_water_mark * (trail_distance / Decimal('100'))
        elif trail_type == 'atr_based':
            # ATR-based trailing would need ATR value
            # For now, fall back to fixed
            trail_amount = trail_distance
        else:  # 'fixed'
            trail_amount = trail_distance

        stop_level = high_water_mark - trail_amount

        # Ensure minimum profit is locked
        if min_profit_lock and stop_level < min_profit_lock:
            stop_level = min_profit_lock

        return stop_level

    async def reset_trailing_stop(
        self,
        strategy: AutoPilotStrategy
    ):
        """
        Reset trailing stop state (e.g., when re-entering position).

        Args:
            strategy: The strategy to reset
        """
        runtime_state = strategy.runtime_state or {}
        runtime_state['trailing_stop'] = {
            'active': False,
            'high_water_mark': 0,
            'stop_level': 0,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        strategy.runtime_state = runtime_state

        logger.info(f"Trailing stop reset for strategy {strategy.id}")

    async def _log_trailing_stop_event(
        self,
        strategy: AutoPilotStrategy,
        event_type: str,
        message: str
    ):
        """Log trailing stop event"""
        log = AutoPilotLog(
            user_id=self.user_id,
            strategy_id=strategy.id,
            event_type=event_type,
            severity=LogSeverity.INFO,
            message=message,
            event_data={
                'trailing_stop': strategy.trailing_stop_config,
                'runtime_state': strategy.runtime_state.get('trailing_stop', {}) if strategy.runtime_state else {}
            }
        )
        self.db.add(log)

    async def _send_trailing_stop_notification(
        self,
        strategy: AutoPilotStrategy,
        event_type: str,
        high_water_mark: Decimal,
        stop_level: Decimal,
        current_pnl: Decimal
    ):
        """Send WebSocket notification for trailing stop events"""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_user(
                user_id=str(self.user_id),
                message={
                    'type': event_type,
                    'strategy_id': strategy.id,
                    'high_water_mark': float(high_water_mark),
                    'current_stop_level': float(stop_level),
                    'current_pnl': float(current_pnl)
                }
            )


# Factory function for dependency injection
async def get_trailing_stop_service(
    db: AsyncSession,
    user_id: UUID
) -> TrailingStopService:
    """Create a TrailingStopService instance"""
    return TrailingStopService(db, user_id)
