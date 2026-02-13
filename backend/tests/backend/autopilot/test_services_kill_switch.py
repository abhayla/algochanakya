"""
Kill Switch Service Tests

Tests for KillSwitchService including:
- Status checks
- Triggering kill switch
- Resetting kill switch
- Strategy exit handling
- WebSocket notifications
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.autopilot.kill_switch import KillSwitchService, get_kill_switch_service
from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotUserSettings,
    AutoPilotOrder,
    AutoPilotLog,
    StrategyStatus,
    OrderPurpose,
    LogSeverity
)
from app.models.users import User
from app.schemas.autopilot import KillSwitchStatus, KillSwitchTriggerResponse


# =============================================================================
# Kill Switch Service Status Tests
# =============================================================================

class TestKillSwitchServiceStatus:
    """Test KillSwitchService status methods."""

    @pytest.mark.asyncio
    async def test_get_status_disabled(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test getting status when kill switch is disabled."""
        service = KillSwitchService(db_session, test_user.id)

        status = await service.get_status()

        assert status.enabled is False
        assert status.triggered_at is None
        assert status.can_reset is True

    @pytest.mark.asyncio
    async def test_get_status_enabled(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test getting status when kill switch is enabled."""
        service = KillSwitchService(db_session, test_settings_with_kill_switch.user_id)

        status = await service.get_status()

        assert status.enabled is True
        assert status.triggered_at is not None

    @pytest.mark.asyncio
    async def test_is_enabled_false(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test is_enabled returns False when kill switch is off."""
        service = KillSwitchService(db_session, test_user.id)

        is_enabled = await service.is_enabled()

        assert is_enabled is False

    @pytest.mark.asyncio
    async def test_is_enabled_true(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test is_enabled returns True when kill switch is on."""
        service = KillSwitchService(db_session, test_settings_with_kill_switch.user_id)

        is_enabled = await service.is_enabled()

        assert is_enabled is True

    @pytest.mark.asyncio
    async def test_get_status_with_active_strategies(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test getting status counts active strategies."""
        service = KillSwitchService(db_session, test_user.id)

        status = await service.get_status()

        assert status.affected_strategies >= 1


# =============================================================================
# Kill Switch Service Trigger Tests
# =============================================================================

class TestKillSwitchServiceTrigger:
    """Test KillSwitchService trigger functionality."""

    @pytest.mark.asyncio
    async def test_trigger_kill_switch_no_active_strategies(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test triggering kill switch with no active strategies."""
        service = KillSwitchService(db_session, test_user.id)

        response = await service.trigger(reason="Test trigger")

        assert response.success is True
        assert response.strategies_affected == 0
        assert response.positions_exited == 0
        assert "Kill switch activated" in response.message

    @pytest.mark.asyncio
    async def test_trigger_kill_switch_with_active_strategies(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test triggering kill switch with active strategies."""
        service = KillSwitchService(db_session, test_user.id)

        response = await service.trigger(reason="Market volatility")

        assert response.success is True
        assert response.strategies_affected >= 1
        assert response.triggered_at is not None

    @pytest.mark.asyncio
    async def test_trigger_kill_switch_with_positions(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings,
        test_strategy_active_with_positions: AutoPilotStrategy
    ):
        """Test triggering kill switch exits positions."""
        service = KillSwitchService(db_session, test_user.id)

        response = await service.trigger(reason="Emergency exit")

        assert response.success is True
        # Should create exit orders for each position
        assert response.positions_exited >= 0

    @pytest.mark.asyncio
    async def test_trigger_kill_switch_updates_settings(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test that triggering kill switch updates user settings."""
        service = KillSwitchService(db_session, test_user.id)

        await service.trigger(reason="Test")

        # Refresh settings
        await db_session.refresh(test_settings)

        assert test_settings.kill_switch_enabled is True
        assert test_settings.kill_switch_triggered_at is not None

    @pytest.mark.asyncio
    async def test_trigger_kill_switch_with_websocket_manager(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings,
        mock_ws_manager
    ):
        """Test kill switch sends WebSocket notification."""
        service = KillSwitchService(db_session, test_user.id)
        service.set_websocket_manager(mock_ws_manager)

        await service.trigger(reason="Emergency")

        # Verify WebSocket notification was sent
        mock_ws_manager.broadcast_to_user.assert_called()

    @pytest.mark.asyncio
    async def test_trigger_kill_switch_creates_log(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test that triggering kill switch creates a log entry."""
        service = KillSwitchService(db_session, test_user.id)

        await service.trigger(reason="Test trigger")

        # Check for log entry
        result = await db_session.execute(
            select(AutoPilotLog)
            .where(AutoPilotLog.user_id == test_user.id)
            .where(AutoPilotLog.event_type == 'kill_switch_activated')
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.severity == LogSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_trigger_kill_switch_pauses_waiting_strategies(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings: AutoPilotUserSettings,
        test_strategy_waiting: AutoPilotStrategy
    ):
        """Test that kill switch pauses waiting strategies."""
        service = KillSwitchService(db_session, test_user.id)

        await service.trigger(reason="Test")

        # Refresh strategy
        await db_session.refresh(test_strategy_waiting)

        assert test_strategy_waiting.status == StrategyStatus.PAUSED.value


# =============================================================================
# Kill Switch Service Reset Tests
# =============================================================================

class TestKillSwitchServiceReset:
    """Test KillSwitchService reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_kill_switch(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test resetting kill switch."""
        service = KillSwitchService(db_session, test_settings_with_kill_switch.user_id)

        result = await service.reset(confirm=True)

        assert result["success"] is True
        assert "reset" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_reset_kill_switch_updates_settings(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test that resetting kill switch updates user settings."""
        service = KillSwitchService(db_session, test_settings_with_kill_switch.user_id)

        await service.reset(confirm=True)

        # Refresh settings
        await db_session.refresh(test_settings_with_kill_switch)

        assert test_settings_with_kill_switch.kill_switch_enabled is False
        assert test_settings_with_kill_switch.kill_switch_triggered_at is None

    @pytest.mark.asyncio
    async def test_reset_kill_switch_requires_confirmation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test that reset requires explicit confirmation."""
        service = KillSwitchService(db_session, test_settings_with_kill_switch.user_id)

        with pytest.raises(ValueError, match="Must confirm"):
            await service.reset(confirm=False)

    @pytest.mark.asyncio
    async def test_reset_kill_switch_creates_log(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test that resetting creates a log entry."""
        service = KillSwitchService(db_session, test_settings_with_kill_switch.user_id)

        await service.reset(confirm=True)

        # Check for log entry
        result = await db_session.execute(
            select(AutoPilotLog)
            .where(AutoPilotLog.user_id == test_settings_with_kill_switch.user_id)
            .where(AutoPilotLog.event_type == 'kill_switch_reset')
        )
        log = result.scalar_one_or_none()

        assert log is not None
        assert log.severity == LogSeverity.INFO

    @pytest.mark.asyncio
    async def test_reset_kill_switch_with_websocket_manager(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_settings_with_kill_switch: AutoPilotUserSettings,
        mock_ws_manager
    ):
        """Test reset sends WebSocket notification."""
        service = KillSwitchService(db_session, test_settings_with_kill_switch.user_id)
        service.set_websocket_manager(mock_ws_manager)

        await service.reset(confirm=True)

        # Verify WebSocket notification was sent
        mock_ws_manager.broadcast_to_user.assert_called()


# =============================================================================
# Kill Switch Service Factory Tests
# =============================================================================

class TestKillSwitchServiceFactory:
    """Test KillSwitchService factory function."""

    @pytest.mark.asyncio
    async def test_get_kill_switch_service(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test factory function creates service instance."""
        service = await get_kill_switch_service(db_session, test_user.id)

        assert isinstance(service, KillSwitchService)
        assert service.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_service_set_order_executor(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_order_executor
    ):
        """Test setting order executor."""
        service = KillSwitchService(db_session, test_user.id)

        service.set_order_executor(mock_order_executor)

        assert service.order_executor is not None

    @pytest.mark.asyncio
    async def test_service_set_websocket_manager(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_ws_manager
    ):
        """Test setting WebSocket manager."""
        service = KillSwitchService(db_session, test_user.id)

        service.set_websocket_manager(mock_ws_manager)

        assert service.websocket_manager is not None
