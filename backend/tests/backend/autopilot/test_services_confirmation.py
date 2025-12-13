"""
Confirmation Service Tests

Tests for ConfirmationService including:
- Creating confirmations
- Getting pending confirmations
- Confirming/rejecting actions
- Expiration handling
- Cancellation
- WebSocket notifications
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.confirmation_service import ConfirmationService, get_confirmation_service
from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotPendingConfirmation,
    AutoPilotLog,
    ConfirmationStatus,
    LogSeverity
)
from app.models.users import User


# =============================================================================
# Confirmation Service Creation Tests
# =============================================================================

class TestConfirmationServiceCreation:
    """Test ConfirmationService creation methods."""

    @pytest.mark.asyncio
    async def test_create_confirmation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test creating a pending confirmation."""
        service = ConfirmationService(db_session, test_user.id)

        confirmation = await service.create_confirmation(
            strategy_id=test_strategy_active.id,
            action_type="entry",
            action_description="Enter iron condor position",
            action_data={"legs": 4, "order_type": "MARKET"},
            timeout_seconds=30
        )

        assert confirmation.id is not None
        assert confirmation.status == ConfirmationStatus.PENDING
        assert confirmation.action_type == "entry"
        assert confirmation.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_create_confirmation_with_rule(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test creating confirmation with rule reference."""
        service = ConfirmationService(db_session, test_user.id)

        confirmation = await service.create_confirmation(
            strategy_id=test_strategy_active.id,
            action_type="adjustment",
            action_description="Add protective hedge",
            action_data={"hedge_type": "both"},
            rule_id="adj_1",
            rule_name="Delta Hedge Rule"
        )

        assert confirmation.rule_id == "adj_1"
        assert confirmation.rule_name == "Delta Hedge Rule"

    @pytest.mark.asyncio
    async def test_create_confirmation_default_timeout(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test confirmation uses default timeout when not specified."""
        service = ConfirmationService(db_session, test_user.id)

        confirmation = await service.create_confirmation(
            strategy_id=test_strategy_active.id,
            action_type="exit",
            action_description="Exit all positions",
            action_data={}
        )

        assert confirmation.timeout_seconds == 30  # Default

    @pytest.mark.asyncio
    async def test_create_confirmation_custom_default_timeout(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test setting custom default timeout."""
        service = ConfirmationService(db_session, test_user.id)
        service.set_default_timeout(60)

        confirmation = await service.create_confirmation(
            strategy_id=test_strategy_active.id,
            action_type="exit",
            action_description="Exit all positions",
            action_data={}
        )

        assert confirmation.timeout_seconds == 60

    @pytest.mark.asyncio
    async def test_create_confirmation_creates_log(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test that creating confirmation logs the event."""
        service = ConfirmationService(db_session, test_user.id)

        await service.create_confirmation(
            strategy_id=test_strategy_active.id,
            action_type="entry",
            action_description="Test entry",
            action_data={}
        )

        # Check for log entry
        result = await db_session.execute(
            select(AutoPilotLog)
            .where(AutoPilotLog.user_id == test_user.id)
            .where(AutoPilotLog.event_type == 'confirmation_requested')
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.severity == LogSeverity.INFO


# =============================================================================
# Confirmation Service Get Pending Tests
# =============================================================================

class TestConfirmationServiceGetPending:
    """Test ConfirmationService get pending methods."""

    @pytest.mark.asyncio
    async def test_get_pending_confirmations_empty(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test getting pending confirmations when none exist."""
        service = ConfirmationService(db_session, test_user.id)

        confirmations = await service.get_pending_confirmations()

        assert confirmations == []

    @pytest.mark.asyncio
    async def test_get_pending_confirmations(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test getting pending confirmations."""
        service = ConfirmationService(db_session, test_user.id)

        confirmations = await service.get_pending_confirmations()

        assert len(confirmations) >= 1
        assert confirmations[0].status == ConfirmationStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_pending_confirmations_by_strategy(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test getting pending confirmations filtered by strategy."""
        service = ConfirmationService(db_session, test_user.id)

        confirmations = await service.get_pending_confirmations(
            strategy_id=test_pending_confirmation.strategy_id
        )

        assert len(confirmations) >= 1
        assert all(c.strategy_id == test_pending_confirmation.strategy_id for c in confirmations)

    @pytest.mark.asyncio
    async def test_get_pending_confirmations_includes_time_remaining(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test that time_remaining_seconds is calculated correctly."""
        service = ConfirmationService(db_session, test_user.id)

        confirmations = await service.get_pending_confirmations()

        assert len(confirmations) >= 1
        assert confirmations[0].time_remaining_seconds >= 0


# =============================================================================
# Confirmation Service Confirm Tests
# =============================================================================

class TestConfirmationServiceConfirm:
    """Test ConfirmationService confirm functionality."""

    @pytest.mark.asyncio
    async def test_confirm_pending_confirmation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test confirming a pending confirmation."""
        service = ConfirmationService(db_session, test_user.id)

        response = await service.confirm(test_pending_confirmation.id)

        assert response.success is True
        assert response.action_taken == 'confirmed'

        # Verify status updated
        await db_session.refresh(test_pending_confirmation)
        assert test_pending_confirmation.status == ConfirmationStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_confirm_nonexistent_raises_error(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test confirming non-existent confirmation raises error."""
        service = ConfirmationService(db_session, test_user.id)

        with pytest.raises(ValueError, match="not found"):
            await service.confirm(99999)

    @pytest.mark.asyncio
    async def test_confirm_already_confirmed_raises_error(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test confirming already confirmed raises error."""
        # First confirm it
        test_pending_confirmation.status = ConfirmationStatus.CONFIRMED
        await db_session.commit()

        service = ConfirmationService(db_session, test_user.id)

        with pytest.raises(ValueError, match="not pending"):
            await service.confirm(test_pending_confirmation.id)

    @pytest.mark.asyncio
    async def test_confirm_expired_raises_error(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation_expired: AutoPilotPendingConfirmation
    ):
        """Test confirming expired confirmation raises error."""
        service = ConfirmationService(db_session, test_user.id)

        with pytest.raises(ValueError, match="expired"):
            await service.confirm(test_pending_confirmation_expired.id)

    @pytest.mark.asyncio
    async def test_confirm_sends_websocket_notification(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation,
        mock_ws_manager
    ):
        """Test that confirming sends WebSocket notification."""
        service = ConfirmationService(db_session, test_user.id)
        service.set_websocket_manager(mock_ws_manager)

        await service.confirm(test_pending_confirmation.id)

        mock_ws_manager.broadcast_to_user.assert_called()


# =============================================================================
# Confirmation Service Reject Tests
# =============================================================================

class TestConfirmationServiceReject:
    """Test ConfirmationService reject functionality."""

    @pytest.mark.asyncio
    async def test_reject_pending_confirmation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test rejecting a pending confirmation."""
        service = ConfirmationService(db_session, test_user.id)

        response = await service.reject(
            test_pending_confirmation.id,
            reason="Changed my mind"
        )

        assert response.success is True
        assert response.action_taken == 'rejected'

        # Verify status updated
        await db_session.refresh(test_pending_confirmation)
        assert test_pending_confirmation.status == ConfirmationStatus.REJECTED

    @pytest.mark.asyncio
    async def test_reject_without_reason(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test rejecting without a reason."""
        service = ConfirmationService(db_session, test_user.id)

        response = await service.reject(test_pending_confirmation.id)

        assert response.success is True
        assert "rejected" in response.message.lower()

    @pytest.mark.asyncio
    async def test_reject_nonexistent_raises_error(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test rejecting non-existent confirmation raises error."""
        service = ConfirmationService(db_session, test_user.id)

        with pytest.raises(ValueError, match="not found"):
            await service.reject(99999)

    @pytest.mark.asyncio
    async def test_reject_already_rejected_raises_error(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test rejecting already rejected raises error."""
        # First reject it
        test_pending_confirmation.status = ConfirmationStatus.REJECTED
        await db_session.commit()

        service = ConfirmationService(db_session, test_user.id)

        with pytest.raises(ValueError, match="not pending"):
            await service.reject(test_pending_confirmation.id)


# =============================================================================
# Confirmation Service Expiration Tests
# =============================================================================

class TestConfirmationServiceExpiration:
    """Test ConfirmationService expiration handling."""

    @pytest.mark.asyncio
    async def test_expire_old_confirmations(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation_expired: AutoPilotPendingConfirmation
    ):
        """Test expiring old confirmations."""
        service = ConfirmationService(db_session, test_user.id)

        count = await service.expire_old_confirmations()

        assert count >= 1

        # Verify status updated
        await db_session.refresh(test_pending_confirmation_expired)
        assert test_pending_confirmation_expired.status == ConfirmationStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_expire_does_not_affect_fresh_confirmations(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test that fresh confirmations are not expired."""
        service = ConfirmationService(db_session, test_user.id)

        await service.expire_old_confirmations()

        # Verify still pending
        await db_session.refresh(test_pending_confirmation)
        assert test_pending_confirmation.status == ConfirmationStatus.PENDING

    @pytest.mark.asyncio
    async def test_expire_logs_timeout(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation_expired: AutoPilotPendingConfirmation
    ):
        """Test that expiration creates log entry."""
        service = ConfirmationService(db_session, test_user.id)

        await service.expire_old_confirmations()

        # Check for log entry
        result = await db_session.execute(
            select(AutoPilotLog)
            .where(AutoPilotLog.user_id == test_user.id)
            .where(AutoPilotLog.event_type == 'confirmation_timeout')
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.severity == LogSeverity.WARNING


# =============================================================================
# Confirmation Service Cancellation Tests
# =============================================================================

class TestConfirmationServiceCancellation:
    """Test ConfirmationService cancellation functionality."""

    @pytest.mark.asyncio
    async def test_cancel_confirmation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test cancelling a pending confirmation."""
        service = ConfirmationService(db_session, test_user.id)

        result = await service.cancel_confirmation(test_pending_confirmation.id)

        assert result is True

        # Verify status updated
        await db_session.refresh(test_pending_confirmation)
        assert test_pending_confirmation.status == ConfirmationStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_false(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test cancelling non-existent confirmation returns False."""
        service = ConfirmationService(db_session, test_user.id)

        result = await service.cancel_confirmation(99999)

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_already_confirmed_returns_false(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test cancelling already confirmed returns False."""
        test_pending_confirmation.status = ConfirmationStatus.CONFIRMED
        await db_session.commit()

        service = ConfirmationService(db_session, test_user.id)

        result = await service.cancel_confirmation(test_pending_confirmation.id)

        assert result is False


# =============================================================================
# Confirmation Service Factory Tests
# =============================================================================

class TestConfirmationServiceFactory:
    """Test ConfirmationService factory function."""

    @pytest.mark.asyncio
    async def test_get_confirmation_service(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test factory function creates service instance."""
        service = await get_confirmation_service(db_session, test_user.id)

        assert isinstance(service, ConfirmationService)
        assert service.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_service_set_websocket_manager(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_ws_manager
    ):
        """Test setting WebSocket manager."""
        service = ConfirmationService(db_session, test_user.id)

        service.set_websocket_manager(mock_ws_manager)

        assert service.websocket_manager is not None
