"""
Trailing Stop Service Tests

Tests for TrailingStopService including:
- Status retrieval
- Trailing stop activation
- Stop level updates
- Stop trigger detection
- Reset functionality
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.autopilot.trailing_stop import TrailingStopService, get_trailing_stop_service
from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotUserSettings,
    AutoPilotLog,
    LogSeverity
)
from app.models.users import User
from app.schemas.autopilot import TrailingStopStatus


# =============================================================================
# Trailing Stop Service Status Tests
# =============================================================================

class TestTrailingStopServiceStatus:
    """Test TrailingStopService status methods."""

    @pytest.mark.asyncio
    async def test_get_status_disabled(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test getting status when trailing stop is disabled."""
        # Disable trailing stop
        test_strategy_active.trailing_stop_config = {"enabled": False}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        status = await service.get_status(test_strategy_active, Decimal("2000"))

        assert status.enabled is False
        assert status.active is False

    @pytest.mark.asyncio
    async def test_get_status_enabled_not_active(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test getting status when enabled but not yet activated."""
        # Set runtime state to inactive
        test_strategy_with_trailing_stop.runtime_state = {
            "trailing_stop": {"active": False}
        }
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        status = await service.get_status(test_strategy_with_trailing_stop, Decimal("2000"))

        assert status.enabled is True
        assert status.active is False

    @pytest.mark.asyncio
    async def test_get_status_active(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test getting status when trailing stop is active."""
        service = TrailingStopService(db_session, test_user.id)

        status = await service.get_status(test_strategy_with_trailing_stop, Decimal("3500"))

        assert status.enabled is True
        assert status.active is True
        assert status.high_water_mark is not None


# =============================================================================
# Trailing Stop Service Activation Tests
# =============================================================================

class TestTrailingStopServiceActivation:
    """Test TrailingStopService activation functionality."""

    @pytest.mark.asyncio
    async def test_update_activates_trailing_stop(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy,
        test_trailing_stop_config
    ):
        """Test that trailing stop activates when profit threshold is reached."""
        test_strategy_active.trailing_stop_config = test_trailing_stop_config
        test_strategy_active.runtime_state = {}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        # P&L = 3500, activation_profit = 3000, should activate
        should_exit, reason = await service.update_trailing_stop(
            test_strategy_active,
            Decimal("3500")
        )

        assert should_exit is False
        assert test_strategy_active.runtime_state["trailing_stop"]["active"] is True
        assert test_strategy_active.runtime_state["trailing_stop"]["high_water_mark"] == 3500.0

    @pytest.mark.asyncio
    async def test_update_does_not_activate_below_threshold(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy,
        test_trailing_stop_config
    ):
        """Test that trailing stop does not activate below profit threshold."""
        test_strategy_active.trailing_stop_config = test_trailing_stop_config
        test_strategy_active.runtime_state = {}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        # P&L = 2000, activation_profit = 3000, should NOT activate
        should_exit, reason = await service.update_trailing_stop(
            test_strategy_active,
            Decimal("2000")
        )

        assert should_exit is False
        trailing_state = test_strategy_active.runtime_state.get("trailing_stop", {})
        assert trailing_state.get("active", False) is False


# =============================================================================
# Trailing Stop Service Update Tests
# =============================================================================

class TestTrailingStopServiceUpdate:
    """Test TrailingStopService stop level update functionality."""

    @pytest.mark.asyncio
    async def test_update_raises_high_water_mark(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test that high water mark increases when profit increases."""
        service = TrailingStopService(db_session, test_user.id)

        # Start with HWM = 4000, P&L = 5000
        should_exit, reason = await service.update_trailing_stop(
            test_strategy_with_trailing_stop,
            Decimal("5000")
        )

        assert should_exit is False
        assert test_strategy_with_trailing_stop.runtime_state["trailing_stop"]["high_water_mark"] == 5000.0

    @pytest.mark.asyncio
    async def test_update_does_not_lower_high_water_mark(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test that high water mark does not decrease when profit decreases."""
        service = TrailingStopService(db_session, test_user.id)

        original_hwm = test_strategy_with_trailing_stop.runtime_state["trailing_stop"]["high_water_mark"]

        # P&L drops to 3500 but HWM should stay at 4000
        should_exit, reason = await service.update_trailing_stop(
            test_strategy_with_trailing_stop,
            Decimal("3500")
        )

        assert should_exit is False
        assert test_strategy_with_trailing_stop.runtime_state["trailing_stop"]["high_water_mark"] == original_hwm

    @pytest.mark.asyncio
    async def test_update_calculates_fixed_stop_level(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy,
        test_trailing_stop_config
    ):
        """Test fixed trail distance calculation."""
        test_strategy_active.trailing_stop_config = test_trailing_stop_config  # trail_distance = 1000
        test_strategy_active.runtime_state = {}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        # P&L = 5000, HWM = 5000, trail_distance = 1000
        # Stop level should be 5000 - 1000 = 4000
        await service.update_trailing_stop(test_strategy_active, Decimal("5000"))

        assert test_strategy_active.runtime_state["trailing_stop"]["stop_level"] == 4000.0

    @pytest.mark.asyncio
    async def test_update_calculates_percentage_stop_level(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy,
        test_trailing_stop_config_percentage
    ):
        """Test percentage trail distance calculation."""
        test_strategy_active.trailing_stop_config = test_trailing_stop_config_percentage  # trail_distance = 20%
        test_strategy_active.runtime_state = {}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        # P&L = 10000, HWM = 10000, trail_distance = 20%
        # Stop level should be 10000 - (10000 * 0.20) = 8000
        await service.update_trailing_stop(test_strategy_active, Decimal("10000"))

        assert test_strategy_active.runtime_state["trailing_stop"]["stop_level"] == 8000.0

    @pytest.mark.asyncio
    async def test_update_respects_min_profit_lock(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy,
        test_trailing_stop_config
    ):
        """Test that min_profit_lock is respected."""
        test_strategy_active.trailing_stop_config = test_trailing_stop_config  # min_profit_lock = 500
        test_strategy_active.runtime_state = {}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        # P&L = 3500, HWM = 3500, trail_distance = 1000
        # Without min_profit_lock, stop would be 2500
        # But min_profit_lock = 500, so stop should be max(2500, 500) = 2500
        await service.update_trailing_stop(test_strategy_active, Decimal("3500"))

        stop_level = test_strategy_active.runtime_state["trailing_stop"]["stop_level"]
        assert stop_level >= 500  # Should be at least min_profit_lock


# =============================================================================
# Trailing Stop Service Trigger Tests
# =============================================================================

class TestTrailingStopServiceTrigger:
    """Test TrailingStopService trigger functionality."""

    @pytest.mark.asyncio
    async def test_update_triggers_stop(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test that stop triggers when P&L drops below stop level."""
        service = TrailingStopService(db_session, test_user.id)

        # Stop level is 3000, P&L drops to 2500
        should_exit, reason = await service.update_trailing_stop(
            test_strategy_with_trailing_stop,
            Decimal("2500")
        )

        assert should_exit is True
        assert "triggered" in reason.lower()

    @pytest.mark.asyncio
    async def test_check_stop_triggered_true(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test check_stop_triggered returns True when triggered."""
        service = TrailingStopService(db_session, test_user.id)

        # Stop level is 3000, P&L = 2500
        is_triggered = await service.check_stop_triggered(
            test_strategy_with_trailing_stop,
            Decimal("2500")
        )

        assert is_triggered is True

    @pytest.mark.asyncio
    async def test_check_stop_triggered_false(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test check_stop_triggered returns False when not triggered."""
        service = TrailingStopService(db_session, test_user.id)

        # Stop level is 3000, P&L = 3500
        is_triggered = await service.check_stop_triggered(
            test_strategy_with_trailing_stop,
            Decimal("3500")
        )

        assert is_triggered is False

    @pytest.mark.asyncio
    async def test_check_stop_disabled_returns_false(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test check_stop_triggered returns False when disabled."""
        test_strategy_active.trailing_stop_config = {"enabled": False}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)

        is_triggered = await service.check_stop_triggered(
            test_strategy_active,
            Decimal("0")  # Even with zero P&L
        )

        assert is_triggered is False


# =============================================================================
# Trailing Stop Service Reset Tests
# =============================================================================

class TestTrailingStopServiceReset:
    """Test TrailingStopService reset functionality."""

    @pytest.mark.asyncio
    async def test_reset_trailing_stop(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy
    ):
        """Test resetting trailing stop state."""
        service = TrailingStopService(db_session, test_user.id)

        await service.reset_trailing_stop(test_strategy_with_trailing_stop)

        trailing_state = test_strategy_with_trailing_stop.runtime_state.get("trailing_stop", {})
        assert trailing_state.get("active") is False
        assert trailing_state.get("high_water_mark") == 0
        assert trailing_state.get("stop_level") == 0


# =============================================================================
# Trailing Stop Service WebSocket Tests
# =============================================================================

class TestTrailingStopServiceWebSocket:
    """Test TrailingStopService WebSocket notifications."""

    @pytest.mark.asyncio
    async def test_activation_sends_websocket(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy,
        test_trailing_stop_config,
        mock_ws_manager
    ):
        """Test that activation sends WebSocket notification."""
        test_strategy_active.trailing_stop_config = test_trailing_stop_config
        test_strategy_active.runtime_state = {}
        await db_session.commit()

        service = TrailingStopService(db_session, test_user.id)
        service.set_websocket_manager(mock_ws_manager)

        await service.update_trailing_stop(test_strategy_active, Decimal("5000"))

        mock_ws_manager.broadcast_to_user.assert_called()

    @pytest.mark.asyncio
    async def test_update_sends_websocket(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_trailing_stop: AutoPilotStrategy,
        mock_ws_manager
    ):
        """Test that stop level updates send WebSocket notification."""
        service = TrailingStopService(db_session, test_user.id)
        service.set_websocket_manager(mock_ws_manager)

        # Increase profit to update stop level
        await service.update_trailing_stop(
            test_strategy_with_trailing_stop,
            Decimal("6000")
        )

        mock_ws_manager.broadcast_to_user.assert_called()


# =============================================================================
# Trailing Stop Service Factory Tests
# =============================================================================

class TestTrailingStopServiceFactory:
    """Test TrailingStopService factory function."""

    @pytest.mark.asyncio
    async def test_get_trailing_stop_service(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test factory function creates service instance."""
        service = await get_trailing_stop_service(db_session, test_user.id)

        assert isinstance(service, TrailingStopService)
        assert service.user_id == test_user.id
