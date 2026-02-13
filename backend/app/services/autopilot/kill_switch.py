"""
Kill Switch Service - Phase 3

Emergency stop all active strategies instantly.
When triggered:
- Exit all active positions immediately (market orders)
- Pause all waiting strategies
- Set kill_switch_enabled = true in user settings
- Record kill_switch_triggered_at timestamp
- Send WebSocket alert to all user connections
- Log the event with all affected strategies
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from app.models.autopilot import (
    AutoPilotUserSettings,
    AutoPilotStrategy,
    AutoPilotOrder,
    AutoPilotLog,
    StrategyStatus,
    OrderPurpose,
    LogSeverity
)
from app.schemas.autopilot import (
    KillSwitchStatus,
    KillSwitchTriggerResponse
)

logger = logging.getLogger(__name__)


class KillSwitchService:
    """
    Service for managing the emergency kill switch functionality.

    The kill switch is a critical safety feature that:
    1. Immediately exits all active positions
    2. Pauses all waiting strategies
    3. Prevents new strategy activations until reset
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.order_executor = None  # Injected when needed
        self.websocket_manager = None  # Injected when needed

    def set_order_executor(self, executor):
        """Inject order executor for placing exit orders"""
        self.order_executor = executor

    def set_websocket_manager(self, manager):
        """Inject WebSocket manager for sending alerts"""
        self.websocket_manager = manager

    async def get_status(self) -> KillSwitchStatus:
        """
        Get current kill switch status for user.

        Returns:
            KillSwitchStatus with enabled state and affected strategies count
        """
        # Get user settings
        settings = await self._get_user_settings()

        # Count active strategies
        active_count = await self._count_active_strategies()

        return KillSwitchStatus(
            enabled=settings.kill_switch_enabled if settings else False,
            triggered_at=settings.kill_switch_triggered_at if settings else None,
            affected_strategies=active_count,
            can_reset=True
        )

    async def is_enabled(self) -> bool:
        """
        Quick check if kill switch is currently enabled.
        Used by Strategy Monitor to prevent activations.
        """
        settings = await self._get_user_settings()
        return settings.kill_switch_enabled if settings else False

    async def trigger(
        self,
        reason: Optional[str] = None,
        force: bool = False
    ) -> KillSwitchTriggerResponse:
        """
        Trigger the kill switch - emergency stop all strategies.

        Args:
            reason: Optional reason for triggering
            force: If True, bypass confirmation

        Returns:
            KillSwitchTriggerResponse with affected strategies and orders
        """
        logger.warning(f"Kill switch triggered for user {self.user_id}, reason: {reason}")

        triggered_at = datetime.now(timezone.utc)
        strategies_affected = 0
        positions_exited = 0
        orders_placed = []

        try:
            # 1. Get all active/waiting strategies
            active_strategies = await self._get_active_strategies()
            strategies_affected = len(active_strategies)

            # 2. Exit all active positions (market orders)
            for strategy in active_strategies:
                if strategy.status == StrategyStatus.ACTIVE:
                    exit_orders = await self._exit_strategy_positions(strategy, reason)
                    orders_placed.extend(exit_orders)
                    positions_exited += len(exit_orders)

            # 3. Pause all waiting strategies
            await self._pause_waiting_strategies()

            # 4. Update user settings
            await self._enable_kill_switch(triggered_at)

            # 5. Log the event
            await self._log_kill_switch_triggered(
                strategies_affected=strategies_affected,
                orders_placed=orders_placed,
                reason=reason
            )

            # 6. Send WebSocket alert
            await self._send_kill_switch_alert(
                triggered_at=triggered_at,
                strategies_affected=strategies_affected,
                reason=reason
            )

            await self.db.commit()

            return KillSwitchTriggerResponse(
                success=True,
                strategies_affected=strategies_affected,
                positions_exited=positions_exited,
                orders_placed=orders_placed,
                triggered_at=triggered_at,
                message=f"Kill switch activated. {strategies_affected} strategies affected, {positions_exited} exit orders placed."
            )

        except Exception as e:
            logger.error(f"Error triggering kill switch: {e}")
            await self.db.rollback()
            raise

    async def reset(self, confirm: bool = True) -> Dict[str, Any]:
        """
        Reset the kill switch, allowing new strategy activations.

        Args:
            confirm: Requires explicit confirmation

        Returns:
            Dict with reset status
        """
        if not confirm:
            raise ValueError("Must confirm kill switch reset")

        logger.info(f"Kill switch reset for user {self.user_id}")

        try:
            # 1. Update user settings
            await self._disable_kill_switch()

            # 2. Log the event
            await self._log_kill_switch_reset()

            # 3. Send WebSocket notification
            await self._send_kill_switch_reset_alert()

            await self.db.commit()

            return {
                "success": True,
                "message": "Kill switch has been reset. You can now activate strategies."
            }

        except Exception as e:
            logger.error(f"Error resetting kill switch: {e}")
            await self.db.rollback()
            raise

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    async def _get_user_settings(self) -> Optional[AutoPilotUserSettings]:
        """Get user's AutoPilot settings"""
        result = await self.db.execute(
            select(AutoPilotUserSettings)
            .where(AutoPilotUserSettings.user_id == self.user_id)
        )
        return result.scalar_one_or_none()

    async def _count_active_strategies(self) -> int:
        """Count active/waiting strategies for user"""
        result = await self.db.execute(
            select(AutoPilotStrategy)
            .where(
                and_(
                    AutoPilotStrategy.user_id == self.user_id,
                    AutoPilotStrategy.status.in_(['waiting', 'active', 'pending'])
                )
            )
        )
        return len(result.scalars().all())

    async def _get_active_strategies(self) -> List[AutoPilotStrategy]:
        """Get all active/waiting strategies for user"""
        result = await self.db.execute(
            select(AutoPilotStrategy)
            .where(
                and_(
                    AutoPilotStrategy.user_id == self.user_id,
                    AutoPilotStrategy.status.in_(['waiting', 'active', 'pending'])
                )
            )
            .options(selectinload(AutoPilotStrategy.orders))
        )
        return result.scalars().all()

    async def _exit_strategy_positions(
        self,
        strategy: AutoPilotStrategy,
        reason: Optional[str] = None
    ) -> List[int]:
        """
        Exit all positions for a strategy with market orders.

        Returns:
            List of order IDs placed
        """
        order_ids = []

        # Get the strategy's runtime state to find current positions
        runtime_state = strategy.runtime_state or {}
        current_positions = runtime_state.get('positions', [])

        if not current_positions and self.order_executor:
            # Try to get positions from broker if not in runtime state
            # This is a fallback - normally positions should be tracked
            logger.info(f"No positions in runtime state for strategy {strategy.id}")

        for position in current_positions:
            try:
                # Create exit order (opposite of current position)
                exit_order = AutoPilotOrder(
                    strategy_id=strategy.id,
                    user_id=self.user_id,
                    purpose=OrderPurpose.KILL_SWITCH,
                    rule_name=f"Kill Switch - {reason or 'Emergency Exit'}",
                    leg_index=position.get('leg_index', 0),
                    exchange=position.get('exchange', 'NFO'),
                    tradingsymbol=position['tradingsymbol'],
                    instrument_token=position.get('instrument_token'),
                    underlying=strategy.underlying,
                    contract_type=position['contract_type'],
                    strike=position.get('strike'),
                    expiry=position['expiry'],
                    # Reverse the transaction type
                    transaction_type='SELL' if position['transaction_type'] == 'BUY' else 'BUY',
                    order_type='MARKET',
                    product=position.get('product', 'NRML'),
                    quantity=abs(position['quantity']),
                    status='pending'
                )
                self.db.add(exit_order)
                await self.db.flush()
                order_ids.append(exit_order.id)

                # Place the order if executor is available
                if self.order_executor:
                    await self.order_executor.place_order(exit_order)

            except Exception as e:
                logger.error(f"Error creating exit order for position: {e}")
                continue

        # Update strategy status
        strategy.status = StrategyStatus.PAUSED
        strategy.completed_at = datetime.now(timezone.utc)

        # Update runtime state
        if strategy.runtime_state is None:
            strategy.runtime_state = {}
        strategy.runtime_state['kill_switch_triggered'] = True
        strategy.runtime_state['kill_switch_reason'] = reason
        strategy.runtime_state['kill_switch_at'] = datetime.now(timezone.utc).isoformat()

        return order_ids

    async def _pause_waiting_strategies(self):
        """Pause all waiting strategies"""
        await self.db.execute(
            update(AutoPilotStrategy)
            .where(
                and_(
                    AutoPilotStrategy.user_id == self.user_id,
                    AutoPilotStrategy.status == 'waiting'
                )
            )
            .values(status='paused')
        )

    async def _enable_kill_switch(self, triggered_at: datetime):
        """Enable kill switch in user settings"""
        await self.db.execute(
            update(AutoPilotUserSettings)
            .where(AutoPilotUserSettings.user_id == self.user_id)
            .values(
                kill_switch_enabled=True,
                kill_switch_triggered_at=triggered_at
            )
        )

    async def _disable_kill_switch(self):
        """Disable kill switch in user settings"""
        await self.db.execute(
            update(AutoPilotUserSettings)
            .where(AutoPilotUserSettings.user_id == self.user_id)
            .values(
                kill_switch_enabled=False,
                kill_switch_triggered_at=None
            )
        )

    async def _log_kill_switch_triggered(
        self,
        strategies_affected: int,
        orders_placed: List[int],
        reason: Optional[str]
    ):
        """Log kill switch triggered event"""
        log = AutoPilotLog(
            user_id=self.user_id,
            event_type='kill_switch_activated',
            severity=LogSeverity.CRITICAL,
            message=f"Kill switch triggered: {strategies_affected} strategies affected, {len(orders_placed)} orders placed. Reason: {reason or 'Manual trigger'}",
            event_data={
                'strategies_affected': strategies_affected,
                'orders_placed': orders_placed,
                'reason': reason
            }
        )
        self.db.add(log)

    async def _log_kill_switch_reset(self):
        """Log kill switch reset event"""
        log = AutoPilotLog(
            user_id=self.user_id,
            event_type='kill_switch_reset',
            severity=LogSeverity.INFO,
            message="Kill switch has been reset",
            event_data={}
        )
        self.db.add(log)

    async def _send_kill_switch_alert(
        self,
        triggered_at: datetime,
        strategies_affected: int,
        reason: Optional[str]
    ):
        """Send WebSocket alert for kill switch triggered"""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_user(
                user_id=str(self.user_id),
                message={
                    'type': 'kill_switch_triggered',
                    'triggered_at': triggered_at.isoformat(),
                    'strategies_affected': strategies_affected,
                    'reason': reason
                }
            )

    async def _send_kill_switch_reset_alert(self):
        """Send WebSocket alert for kill switch reset"""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_user(
                user_id=str(self.user_id),
                message={
                    'type': 'kill_switch_reset',
                    'reset_at': datetime.now(timezone.utc).isoformat()
                }
            )


# Factory function for dependency injection
async def get_kill_switch_service(
    db: AsyncSession,
    user_id: UUID
) -> KillSwitchService:
    """Create a KillSwitchService instance"""
    return KillSwitchService(db, user_id)
