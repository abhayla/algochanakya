"""
Phase 3 Model Tests

Tests for AutoPilotAdjustmentLog and AutoPilotPendingConfirmation models.
Covers CRUD operations, constraints, relationships, and JSONB fields.
"""
import pytest
import pytest_asyncio
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotAdjustmentLog,
    AutoPilotPendingConfirmation,
    AutoPilotUserSettings,
    AdjustmentTriggerType,
    AdjustmentActionType,
    ExecutionMode,
    ConfirmationStatus,
    StrategyStatus,
    LogSeverity
)
from app.models.users import User


# =============================================================================
# Phase 3 Enum Tests
# =============================================================================

class TestPhase3Enums:
    """Test Phase 3 enum definitions."""

    def test_execution_mode_values(self):
        """Test ExecutionMode enum values."""
        assert ExecutionMode.AUTO.value == "auto"
        assert ExecutionMode.SEMI_AUTO.value == "semi_auto"
        assert ExecutionMode.MANUAL.value == "manual"

    def test_adjustment_trigger_type_values(self):
        """Test AdjustmentTriggerType enum values."""
        assert AdjustmentTriggerType.PNL_BASED.value == "pnl_based"
        assert AdjustmentTriggerType.DELTA_BASED.value == "delta_based"
        assert AdjustmentTriggerType.TIME_BASED.value == "time_based"
        assert AdjustmentTriggerType.PREMIUM_BASED.value == "premium_based"
        assert AdjustmentTriggerType.VIX_BASED.value == "vix_based"
        assert AdjustmentTriggerType.SPOT_BASED.value == "spot_based"

    def test_adjustment_action_type_values(self):
        """Test AdjustmentActionType enum values."""
        assert AdjustmentActionType.ADD_HEDGE.value == "add_hedge"
        assert AdjustmentActionType.CLOSE_LEG.value == "close_leg"
        assert AdjustmentActionType.ROLL_STRIKE.value == "roll_strike"
        assert AdjustmentActionType.ROLL_EXPIRY.value == "roll_expiry"
        assert AdjustmentActionType.EXIT_ALL.value == "exit_all"
        assert AdjustmentActionType.SCALE_DOWN.value == "scale_down"
        assert AdjustmentActionType.SCALE_UP.value == "scale_up"

    def test_confirmation_status_values(self):
        """Test ConfirmationStatus enum values."""
        assert ConfirmationStatus.PENDING.value == "pending"
        assert ConfirmationStatus.CONFIRMED.value == "confirmed"
        assert ConfirmationStatus.REJECTED.value == "rejected"
        assert ConfirmationStatus.EXPIRED.value == "expired"
        assert ConfirmationStatus.CANCELLED.value == "cancelled"


# =============================================================================
# AutoPilotAdjustmentLog Model Tests
# =============================================================================

class TestAutoPilotAdjustmentLogModel:
    """Test AutoPilotAdjustmentLog model CRUD and constraints."""

    @pytest.mark.asyncio
    async def test_create_adjustment_log(
        self,
        db_session: AsyncSession,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test creating an adjustment log entry."""
        log = AutoPilotAdjustmentLog(
            strategy_id=test_strategy_with_adjustments.id,
            user_id=test_strategy_with_adjustments.user_id,
            rule_id="adj_1",
            rule_name="Stop Loss Rule",
            trigger_type=AdjustmentTriggerType.PNL_BASED,
            trigger_condition="loss_exceeds",
            trigger_value=5000,
            actual_value=-5500,
            action_type=AdjustmentActionType.EXIT_ALL,
            action_params={"order_type": "MARKET"},
            execution_mode=ExecutionMode.AUTO,
            executed=False
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.rule_id == "adj_1"
        assert log.trigger_type == AdjustmentTriggerType.PNL_BASED
        assert log.action_type == AdjustmentActionType.EXIT_ALL
        assert log.executed is False

    @pytest.mark.asyncio
    async def test_adjustment_log_with_execution(
        self,
        db_session: AsyncSession,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test adjustment log with executed status.

        Note: This test tests ARRAY column (order_ids) which requires PostgreSQL.
        For SQLite tests, we skip the order_ids field.
        """
        executed_at = datetime.now(timezone.utc)
        log = AutoPilotAdjustmentLog(
            strategy_id=test_strategy_with_adjustments.id,
            user_id=test_strategy_with_adjustments.user_id,
            rule_id="adj_2",
            rule_name="Profit Target",
            trigger_type=AdjustmentTriggerType.PNL_BASED,
            trigger_condition="profit_exceeds",
            trigger_value=10000,
            actual_value=12000,
            action_type=AdjustmentActionType.EXIT_ALL,
            action_params={"order_type": "LIMIT"},
            execution_mode=ExecutionMode.AUTO,
            executed=True,
            executed_at=executed_at,
            execution_result={"orders_placed": [1001, 1002, 1003, 1004]}
            # order_ids skipped - ARRAY type requires PostgreSQL
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.executed is True
        assert log.executed_at is not None
        assert log.execution_result["orders_placed"] == [1001, 1002, 1003, 1004]

    @pytest.mark.asyncio
    async def test_adjustment_log_delta_based_trigger(
        self,
        db_session: AsyncSession,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test adjustment log with delta-based trigger."""
        log = AutoPilotAdjustmentLog(
            strategy_id=test_strategy_with_adjustments.id,
            user_id=test_strategy_with_adjustments.user_id,
            rule_id="adj_delta",
            rule_name="Delta Hedge Rule",
            trigger_type=AdjustmentTriggerType.DELTA_BASED,
            trigger_condition="exceeds",
            trigger_value=0.3,
            actual_value=0.45,
            action_type=AdjustmentActionType.ADD_HEDGE,
            action_params={"hedge_type": "both"},
            execution_mode=ExecutionMode.SEMI_AUTO,
            executed=False
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.trigger_type == AdjustmentTriggerType.DELTA_BASED
        assert log.action_type == AdjustmentActionType.ADD_HEDGE
        assert log.execution_mode == ExecutionMode.SEMI_AUTO

    @pytest.mark.asyncio
    async def test_adjustment_log_time_based_trigger(
        self,
        db_session: AsyncSession,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test adjustment log with time-based trigger."""
        log = AutoPilotAdjustmentLog(
            strategy_id=test_strategy_with_adjustments.id,
            user_id=test_strategy_with_adjustments.user_id,
            rule_id="adj_time",
            rule_name="Auto Exit at Time",
            trigger_type=AdjustmentTriggerType.TIME_BASED,
            trigger_condition="after",
            trigger_value="15:15",
            actual_value="15:16",
            action_type=AdjustmentActionType.EXIT_ALL,
            action_params={"order_type": "MARKET"},
            execution_mode=ExecutionMode.AUTO,
            executed=True,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.trigger_type == AdjustmentTriggerType.TIME_BASED
        assert log.trigger_value == "15:15"

    @pytest.mark.asyncio
    async def test_adjustment_log_with_error(
        self,
        db_session: AsyncSession,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test adjustment log with error message."""
        log = AutoPilotAdjustmentLog(
            strategy_id=test_strategy_with_adjustments.id,
            user_id=test_strategy_with_adjustments.user_id,
            rule_id="adj_error",
            rule_name="Failed Adjustment",
            trigger_type=AdjustmentTriggerType.PNL_BASED,
            trigger_condition="loss_exceeds",
            trigger_value=3000,
            actual_value=-3500,
            action_type=AdjustmentActionType.EXIT_ALL,
            action_params={},
            execution_mode=ExecutionMode.AUTO,
            executed=False,
            error_message="Order placement failed: Insufficient margin"
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.executed is False
        assert "Insufficient margin" in log.error_message

    @pytest.mark.asyncio
    async def test_adjustment_log_strategy_relationship(
        self,
        db_session: AsyncSession,
        test_adjustment_log: AutoPilotAdjustmentLog
    ):
        """Test adjustment log relationship with strategy."""
        await db_session.refresh(test_adjustment_log, ["strategy"])

        assert test_adjustment_log.strategy is not None
        assert test_adjustment_log.strategy.name == "Strategy With Adjustments"


# =============================================================================
# AutoPilotPendingConfirmation Model Tests
# =============================================================================

class TestAutoPilotPendingConfirmationModel:
    """Test AutoPilotPendingConfirmation model CRUD and constraints."""

    @pytest.mark.asyncio
    async def test_create_pending_confirmation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test creating a pending confirmation."""
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
        confirmation = AutoPilotPendingConfirmation(
            user_id=test_user.id,
            strategy_id=test_strategy_active.id,
            action_type="adjustment_exit_all",
            action_description="Exit all positions due to stop loss",
            action_data={"rule_id": "adj_1", "order_type": "MARKET"},
            status=ConfirmationStatus.PENDING,
            timeout_seconds=30,
            expires_at=expires_at
        )
        db_session.add(confirmation)
        await db_session.commit()
        await db_session.refresh(confirmation)

        assert confirmation.id is not None
        assert confirmation.status == ConfirmationStatus.PENDING
        assert confirmation.timeout_seconds == 30

    @pytest.mark.asyncio
    async def test_confirmation_with_rule_reference(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active: AutoPilotStrategy
    ):
        """Test confirmation with rule reference."""
        confirmation = AutoPilotPendingConfirmation(
            user_id=test_user.id,
            strategy_id=test_strategy_active.id,
            action_type="adjustment_add_hedge",
            action_description="Add protective hedge",
            action_data={"hedge_type": "both"},
            rule_id="adj_2",
            rule_name="Delta Hedge Rule",
            status=ConfirmationStatus.PENDING,
            timeout_seconds=60,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=60)
        )
        db_session.add(confirmation)
        await db_session.commit()
        await db_session.refresh(confirmation)

        assert confirmation.rule_id == "adj_2"
        assert confirmation.rule_name == "Delta Hedge Rule"

    @pytest.mark.asyncio
    async def test_confirmation_confirmed_status(
        self,
        db_session: AsyncSession,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test updating confirmation to confirmed status.

        Note: order_ids ARRAY column is skipped for SQLite compatibility.
        """
        test_pending_confirmation.status = ConfirmationStatus.CONFIRMED
        test_pending_confirmation.responded_at = datetime.now(timezone.utc)
        test_pending_confirmation.response_source = "user"
        test_pending_confirmation.execution_result = {"executed": True, "order_ids": [1001, 1002]}
        # order_ids field skipped - ARRAY type requires PostgreSQL

        await db_session.commit()
        await db_session.refresh(test_pending_confirmation)

        assert test_pending_confirmation.status == ConfirmationStatus.CONFIRMED
        assert test_pending_confirmation.response_source == "user"
        assert test_pending_confirmation.execution_result["executed"] is True

    @pytest.mark.asyncio
    async def test_confirmation_rejected_status(
        self,
        db_session: AsyncSession,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test updating confirmation to rejected status."""
        test_pending_confirmation.status = ConfirmationStatus.REJECTED
        test_pending_confirmation.responded_at = datetime.now(timezone.utc)
        test_pending_confirmation.response_source = "user"
        test_pending_confirmation.execution_result = {"rejected": True, "reason": "User declined"}

        await db_session.commit()
        await db_session.refresh(test_pending_confirmation)

        assert test_pending_confirmation.status == ConfirmationStatus.REJECTED
        assert test_pending_confirmation.execution_result["reason"] == "User declined"

    @pytest.mark.asyncio
    async def test_confirmation_expired_status(
        self,
        db_session: AsyncSession,
        test_pending_confirmation_expired: AutoPilotPendingConfirmation
    ):
        """Test expired confirmation."""
        test_pending_confirmation_expired.status = ConfirmationStatus.EXPIRED
        test_pending_confirmation_expired.responded_at = datetime.now(timezone.utc)
        test_pending_confirmation_expired.response_source = "timeout"

        await db_session.commit()
        await db_session.refresh(test_pending_confirmation_expired)

        assert test_pending_confirmation_expired.status == ConfirmationStatus.EXPIRED
        assert test_pending_confirmation_expired.response_source == "timeout"
        # Compare without timezone for SQLite compatibility (SQLite stores naive datetimes)
        expires_at = test_pending_confirmation_expired.expires_at
        if expires_at.tzinfo is None:
            # SQLite returns naive datetime, compare with naive
            assert expires_at < datetime.utcnow()
        else:
            assert expires_at < datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_confirmation_strategy_relationship(
        self,
        db_session: AsyncSession,
        test_pending_confirmation: AutoPilotPendingConfirmation
    ):
        """Test confirmation relationship with strategy."""
        await db_session.refresh(test_pending_confirmation, ["strategy"])

        assert test_pending_confirmation.strategy is not None
        assert test_pending_confirmation.strategy.status == "active"


# =============================================================================
# AutoPilotUserSettings Kill Switch Fields Tests
# =============================================================================

class TestUserSettingsKillSwitchFields:
    """Test kill switch fields in AutoPilotUserSettings."""

    @pytest.mark.asyncio
    async def test_settings_kill_switch_disabled_by_default(
        self,
        db_session: AsyncSession,
        test_settings: AutoPilotUserSettings
    ):
        """Test that kill switch is disabled by default."""
        assert test_settings.kill_switch_enabled is False
        assert test_settings.kill_switch_triggered_at is None

    @pytest.mark.asyncio
    async def test_settings_with_kill_switch_enabled(
        self,
        db_session: AsyncSession,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test settings with kill switch enabled."""
        assert test_settings_with_kill_switch.kill_switch_enabled is True
        assert test_settings_with_kill_switch.kill_switch_triggered_at is not None

    @pytest.mark.asyncio
    async def test_enable_kill_switch(
        self,
        db_session: AsyncSession,
        test_settings: AutoPilotUserSettings
    ):
        """Test enabling kill switch."""
        triggered_at = datetime.now(timezone.utc)
        test_settings.kill_switch_enabled = True
        test_settings.kill_switch_triggered_at = triggered_at

        await db_session.commit()
        await db_session.refresh(test_settings)

        assert test_settings.kill_switch_enabled is True
        assert test_settings.kill_switch_triggered_at is not None

    @pytest.mark.asyncio
    async def test_reset_kill_switch(
        self,
        db_session: AsyncSession,
        test_settings_with_kill_switch: AutoPilotUserSettings
    ):
        """Test resetting kill switch."""
        test_settings_with_kill_switch.kill_switch_enabled = False
        test_settings_with_kill_switch.kill_switch_triggered_at = None

        await db_session.commit()
        await db_session.refresh(test_settings_with_kill_switch)

        assert test_settings_with_kill_switch.kill_switch_enabled is False
        assert test_settings_with_kill_switch.kill_switch_triggered_at is None
