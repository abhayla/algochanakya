"""
Confirmation Service - Phase 3

Semi-auto execution mode - require user confirmation before executing orders.

Confirmation Flow:
1. Condition/adjustment triggers
2. Create pending_confirmation record
3. Send WebSocket message with confirmation request
4. Show modal in frontend with action details
5. User confirms or rejects within timeout (default 30s)
6. If confirmed: execute action
7. If rejected: skip action, log rejection
8. If expired: skip action, log expiration
"""
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from app.models.autopilot import (
    AutoPilotPendingConfirmation,
    AutoPilotStrategy,
    AutoPilotLog,
    ConfirmationStatus,
    LogSeverity
)
from app.schemas.autopilot import (
    PendingConfirmationResponse,
    ConfirmationActionResponse
)

logger = logging.getLogger(__name__)


class ConfirmationService:
    """
    Service for managing semi-auto confirmation requests.

    In semi-auto mode, actions require explicit user confirmation
    before execution. This provides a safety layer while still
    automating the detection of conditions.
    """

    def __init__(self, db: AsyncSession, user_id: UUID):
        self.db = db
        self.user_id = user_id
        self.websocket_manager = None
        self.default_timeout_seconds = 30

    def set_websocket_manager(self, manager):
        """Inject WebSocket manager for sending alerts"""
        self.websocket_manager = manager

    def set_default_timeout(self, timeout_seconds: int):
        """Set default timeout for confirmations"""
        self.default_timeout_seconds = timeout_seconds

    async def create_confirmation(
        self,
        strategy_id: int,
        action_type: str,
        action_description: str,
        action_data: Dict[str, Any],
        rule_id: Optional[str] = None,
        rule_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> AutoPilotPendingConfirmation:
        """
        Create a new pending confirmation request.

        Args:
            strategy_id: The strategy this confirmation is for
            action_type: Type of action (entry, adjustment, exit, hedge)
            action_description: Human-readable description
            action_data: Full action data to execute if confirmed
            rule_id: Optional rule ID if this is an adjustment
            rule_name: Optional rule name
            timeout_seconds: Seconds until expiration

        Returns:
            The created confirmation record
        """
        timeout = timeout_seconds or self.default_timeout_seconds
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout)

        confirmation = AutoPilotPendingConfirmation(
            user_id=self.user_id,
            strategy_id=strategy_id,
            action_type=action_type,
            action_description=action_description,
            action_data=action_data,
            rule_id=rule_id,
            rule_name=rule_name,
            status=ConfirmationStatus.PENDING,
            timeout_seconds=timeout,
            expires_at=expires_at
        )

        self.db.add(confirmation)
        await self.db.flush()

        # Log the confirmation request
        await self._log_confirmation_requested(confirmation)

        # Send WebSocket notification
        await self._send_confirmation_request(confirmation)

        await self.db.commit()

        logger.info(f"Created confirmation {confirmation.id} for strategy {strategy_id}")
        return confirmation

    async def get_pending_confirmations(
        self,
        strategy_id: Optional[int] = None
    ) -> List[PendingConfirmationResponse]:
        """
        Get all pending confirmations for user.

        Args:
            strategy_id: Optional filter by strategy

        Returns:
            List of pending confirmation responses
        """
        query = (
            select(AutoPilotPendingConfirmation)
            .options(selectinload(AutoPilotPendingConfirmation.strategy))
            .where(
                and_(
                    AutoPilotPendingConfirmation.user_id == self.user_id,
                    AutoPilotPendingConfirmation.status == ConfirmationStatus.PENDING
                )
            )
        )

        if strategy_id:
            query = query.where(AutoPilotPendingConfirmation.strategy_id == strategy_id)

        result = await self.db.execute(query)
        confirmations = result.scalars().all()

        now = datetime.now(timezone.utc)
        responses = []

        for conf in confirmations:
            time_remaining = max(0, int((conf.expires_at - now).total_seconds()))
            responses.append(PendingConfirmationResponse(
                id=conf.id,
                strategy_id=conf.strategy_id,
                strategy_name=conf.strategy.name if conf.strategy else "Unknown",
                action_type=conf.action_type,
                action_description=conf.action_description,
                action_data=conf.action_data,
                rule_id=conf.rule_id,
                rule_name=conf.rule_name,
                status=conf.status,
                timeout_seconds=conf.timeout_seconds,
                expires_at=conf.expires_at,
                time_remaining_seconds=time_remaining,
                created_at=conf.created_at
            ))

        return responses

    async def confirm(
        self,
        confirmation_id: int
    ) -> ConfirmationActionResponse:
        """
        Confirm a pending action.

        Args:
            confirmation_id: The confirmation to confirm

        Returns:
            Response with execution result
        """
        confirmation = await self._get_confirmation(confirmation_id)

        if not confirmation:
            raise ValueError(f"Confirmation {confirmation_id} not found")

        if confirmation.status != ConfirmationStatus.PENDING:
            raise ValueError(f"Confirmation {confirmation_id} is not pending (status: {confirmation.status})")

        if confirmation.expires_at < datetime.now(timezone.utc):
            # Already expired
            await self._expire_confirmation(confirmation)
            raise ValueError(f"Confirmation {confirmation_id} has expired")

        try:
            # Update status
            confirmation.status = ConfirmationStatus.CONFIRMED
            confirmation.responded_at = datetime.now(timezone.utc)
            confirmation.response_source = 'user'

            # Execute the action
            execution_result = await self._execute_confirmed_action(confirmation)

            confirmation.execution_result = execution_result
            await self.db.commit()

            # Log the confirmation
            await self._log_confirmation_received(confirmation, 'confirmed')

            # Send WebSocket notification
            await self._send_confirmation_result(confirmation, 'confirmed')

            logger.info(f"Confirmation {confirmation_id} confirmed and executed")

            return ConfirmationActionResponse(
                success=True,
                confirmation_id=confirmation_id,
                action_taken='confirmed',
                execution_result=execution_result,
                orders_placed=execution_result.get('orders_placed', []),
                message=f"Action confirmed and executed successfully"
            )

        except Exception as e:
            logger.error(f"Error executing confirmed action: {e}")
            confirmation.status = ConfirmationStatus.REJECTED
            confirmation.execution_result = {'error': str(e)}
            await self.db.commit()
            raise

    async def reject(
        self,
        confirmation_id: int,
        reason: Optional[str] = None
    ) -> ConfirmationActionResponse:
        """
        Reject a pending action.

        Args:
            confirmation_id: The confirmation to reject
            reason: Optional rejection reason

        Returns:
            Response with rejection details
        """
        confirmation = await self._get_confirmation(confirmation_id)

        if not confirmation:
            raise ValueError(f"Confirmation {confirmation_id} not found")

        if confirmation.status != ConfirmationStatus.PENDING:
            raise ValueError(f"Confirmation {confirmation_id} is not pending")

        # Update status
        confirmation.status = ConfirmationStatus.REJECTED
        confirmation.responded_at = datetime.now(timezone.utc)
        confirmation.response_source = 'user'
        confirmation.execution_result = {'rejected': True, 'reason': reason}

        await self.db.commit()

        # Log the rejection
        await self._log_confirmation_received(confirmation, 'rejected')

        # Send WebSocket notification
        await self._send_confirmation_result(confirmation, 'rejected')

        logger.info(f"Confirmation {confirmation_id} rejected")

        return ConfirmationActionResponse(
            success=True,
            confirmation_id=confirmation_id,
            action_taken='rejected',
            execution_result=None,
            orders_placed=[],
            message=f"Action rejected: {reason or 'User rejected'}"
        )

    async def expire_old_confirmations(self) -> int:
        """
        Expire all confirmations that have passed their timeout.
        This should be called periodically by a background task.

        Returns:
            Number of confirmations expired
        """
        now = datetime.now(timezone.utc)

        # Find expired pending confirmations
        result = await self.db.execute(
            select(AutoPilotPendingConfirmation)
            .where(
                and_(
                    AutoPilotPendingConfirmation.status == ConfirmationStatus.PENDING,
                    AutoPilotPendingConfirmation.expires_at < now
                )
            )
        )
        expired = result.scalars().all()

        count = 0
        for confirmation in expired:
            await self._expire_confirmation(confirmation)
            count += 1

        if count > 0:
            await self.db.commit()
            logger.info(f"Expired {count} pending confirmations")

        return count

    async def cancel_confirmation(
        self,
        confirmation_id: int
    ) -> bool:
        """
        Cancel a pending confirmation (e.g., when strategy is paused).

        Args:
            confirmation_id: The confirmation to cancel

        Returns:
            True if cancelled successfully
        """
        confirmation = await self._get_confirmation(confirmation_id)

        if not confirmation:
            return False

        if confirmation.status != ConfirmationStatus.PENDING:
            return False

        confirmation.status = ConfirmationStatus.CANCELLED
        confirmation.responded_at = datetime.now(timezone.utc)
        confirmation.response_source = 'system'

        await self.db.commit()
        logger.info(f"Confirmation {confirmation_id} cancelled")
        return True

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    async def _get_confirmation(
        self,
        confirmation_id: int
    ) -> Optional[AutoPilotPendingConfirmation]:
        """Get a confirmation by ID"""
        result = await self.db.execute(
            select(AutoPilotPendingConfirmation)
            .options(selectinload(AutoPilotPendingConfirmation.strategy))
            .where(
                and_(
                    AutoPilotPendingConfirmation.id == confirmation_id,
                    AutoPilotPendingConfirmation.user_id == self.user_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def _expire_confirmation(
        self,
        confirmation: AutoPilotPendingConfirmation
    ):
        """Mark a confirmation as expired"""
        confirmation.status = ConfirmationStatus.EXPIRED
        confirmation.responded_at = datetime.now(timezone.utc)
        confirmation.response_source = 'timeout'
        confirmation.execution_result = {'expired': True}

        # Log the expiration
        await self._log_confirmation_timeout(confirmation)

        # Send WebSocket notification
        await self._send_confirmation_expired(confirmation)

        logger.info(f"Confirmation {confirmation.id} expired")

    async def _execute_confirmed_action(
        self,
        confirmation: AutoPilotPendingConfirmation
    ) -> Dict[str, Any]:
        """
        Execute the confirmed action.

        This would typically delegate to the appropriate service
        (order executor, adjustment engine, etc.) based on action_type.
        """
        action_data = confirmation.action_data
        action_type = confirmation.action_type

        # Placeholder - actual implementation would call appropriate services
        logger.info(f"Executing confirmed action: {action_type}")

        # Return execution result
        return {
            'executed': True,
            'action_type': action_type,
            'executed_at': datetime.now(timezone.utc).isoformat()
        }

    async def _log_confirmation_requested(
        self,
        confirmation: AutoPilotPendingConfirmation
    ):
        """Log confirmation requested event"""
        log = AutoPilotLog(
            user_id=self.user_id,
            strategy_id=confirmation.strategy_id,
            event_type='confirmation_requested',
            severity=LogSeverity.INFO,
            rule_name=confirmation.rule_name,
            message=f"Confirmation requested for {confirmation.action_type}: {confirmation.action_description}",
            event_data={
                'confirmation_id': confirmation.id,
                'action_type': confirmation.action_type,
                'timeout_seconds': confirmation.timeout_seconds
            }
        )
        self.db.add(log)

    async def _log_confirmation_received(
        self,
        confirmation: AutoPilotPendingConfirmation,
        action: str
    ):
        """Log confirmation received event"""
        log = AutoPilotLog(
            user_id=self.user_id,
            strategy_id=confirmation.strategy_id,
            event_type='confirmation_received',
            severity=LogSeverity.INFO,
            rule_name=confirmation.rule_name,
            message=f"Confirmation {action} for {confirmation.action_type}",
            event_data={
                'confirmation_id': confirmation.id,
                'action': action
            }
        )
        self.db.add(log)

    async def _log_confirmation_timeout(
        self,
        confirmation: AutoPilotPendingConfirmation
    ):
        """Log confirmation timeout event"""
        log = AutoPilotLog(
            user_id=self.user_id,
            strategy_id=confirmation.strategy_id,
            event_type='confirmation_timeout',
            severity=LogSeverity.WARNING,
            rule_name=confirmation.rule_name,
            message=f"Confirmation timed out for {confirmation.action_type}",
            event_data={
                'confirmation_id': confirmation.id,
                'action_type': confirmation.action_type
            }
        )
        self.db.add(log)

    async def _send_confirmation_request(
        self,
        confirmation: AutoPilotPendingConfirmation
    ):
        """Send WebSocket notification for confirmation request"""
        if self.websocket_manager:
            strategy_name = confirmation.strategy.name if confirmation.strategy else "Unknown"
            await self.websocket_manager.broadcast_to_user(
                user_id=str(self.user_id),
                message={
                    'type': 'confirmation_required',
                    'confirmation_id': confirmation.id,
                    'strategy_id': confirmation.strategy_id,
                    'strategy_name': strategy_name,
                    'action_type': confirmation.action_type,
                    'action_description': confirmation.action_description,
                    'rule_name': confirmation.rule_name,
                    'expires_at': confirmation.expires_at.isoformat(),
                    'timeout_seconds': confirmation.timeout_seconds
                }
            )

    async def _send_confirmation_result(
        self,
        confirmation: AutoPilotPendingConfirmation,
        result: str
    ):
        """Send WebSocket notification for confirmation result"""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_user(
                user_id=str(self.user_id),
                message={
                    'type': f'confirmation_{result}',
                    'confirmation_id': confirmation.id,
                    'strategy_id': confirmation.strategy_id,
                    'action_type': confirmation.action_type,
                    'execution_result': confirmation.execution_result
                }
            )

    async def _send_confirmation_expired(
        self,
        confirmation: AutoPilotPendingConfirmation
    ):
        """Send WebSocket notification for confirmation expired"""
        if self.websocket_manager:
            await self.websocket_manager.broadcast_to_user(
                user_id=str(self.user_id),
                message={
                    'type': 'confirmation_expired',
                    'confirmation_id': confirmation.id,
                    'strategy_id': confirmation.strategy_id,
                    'action_type': confirmation.action_type
                }
            )


# Factory function for dependency injection
async def get_confirmation_service(
    db: AsyncSession,
    user_id: UUID
) -> ConfirmationService:
    """Create a ConfirmationService instance"""
    return ConfirmationService(db, user_id)
