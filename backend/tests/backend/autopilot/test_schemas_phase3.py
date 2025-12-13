"""
Phase 3 Schema Tests

Tests for Pydantic schemas related to Kill Switch, Adjustments, Confirmations,
Trailing Stop, Position Sizing, and Greeks.
"""
import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any
from pydantic import ValidationError

from app.schemas.autopilot import (
    # Enums
    ConfirmationStatus,
    TrailType,
    AdjustmentTriggerType,
    AdjustmentActionType,
    ExecutionMode,
    # Kill Switch
    KillSwitchStatus,
    KillSwitchTriggerRequest,
    KillSwitchTriggerResponse,
    KillSwitchResetRequest,
    # Adjustments
    AdjustmentTrigger,
    AdjustmentAction,
    AdjustmentRule,
    # Confirmations
    PendingConfirmationResponse,
    ConfirmationActionRequest,
    ConfirmationActionResponse,
    # Trailing Stop
    TrailingStopConfig,
    TrailingStopStatus,
    # Position Sizing
    PositionSizingRequest,
    PositionSizingResponse,
    # Greeks
    GreeksSnapshot,
    PositionGreeksResponse,
    # WebSocket Messages
    ConfirmationRequiredMessage,
    KillSwitchMessage,
    TrailingStopMessage,
    # Dashboard
    DashboardSummaryWithKillSwitch,
    Underlying
)


# =============================================================================
# Kill Switch Schema Tests
# =============================================================================

class TestKillSwitchSchemas:
    """Test Kill Switch related schemas."""

    def test_kill_switch_status_enabled(self):
        """Test KillSwitchStatus with enabled state."""
        status = KillSwitchStatus(
            enabled=True,
            triggered_at=datetime.now(timezone.utc),
            affected_strategies=3,
            can_reset=True
        )
        assert status.enabled is True
        assert status.affected_strategies == 3
        assert status.can_reset is True

    def test_kill_switch_status_disabled(self):
        """Test KillSwitchStatus with disabled state."""
        status = KillSwitchStatus(
            enabled=False,
            triggered_at=None,
            affected_strategies=0,
            can_reset=True
        )
        assert status.enabled is False
        assert status.triggered_at is None
        assert status.affected_strategies == 0

    def test_kill_switch_trigger_request_minimal(self):
        """Test KillSwitchTriggerRequest with minimal data."""
        request = KillSwitchTriggerRequest()
        assert request.reason is None
        assert request.force is False

    def test_kill_switch_trigger_request_with_reason(self):
        """Test KillSwitchTriggerRequest with reason."""
        request = KillSwitchTriggerRequest(
            reason="Market volatility too high",
            force=True
        )
        assert request.reason == "Market volatility too high"
        assert request.force is True

    def test_kill_switch_trigger_response(self):
        """Test KillSwitchTriggerResponse."""
        response = KillSwitchTriggerResponse(
            success=True,
            strategies_affected=2,
            positions_exited=8,
            orders_placed=[1001, 1002, 1003, 1004],
            triggered_at=datetime.now(timezone.utc),
            message="Kill switch activated successfully"
        )
        assert response.success is True
        assert response.strategies_affected == 2
        assert response.positions_exited == 8
        assert len(response.orders_placed) == 4

    def test_kill_switch_reset_request(self):
        """Test KillSwitchResetRequest."""
        request = KillSwitchResetRequest(confirm=True)
        assert request.confirm is True


# =============================================================================
# Adjustment Schema Tests
# =============================================================================

class TestAdjustmentSchemas:
    """Test Adjustment related schemas."""

    def test_adjustment_trigger_pnl_based(self):
        """Test AdjustmentTrigger with PNL-based trigger."""
        trigger = AdjustmentTrigger(
            type=AdjustmentTriggerType.pnl_based,
            condition="loss_exceeds",
            value=5000
        )
        assert trigger.type == AdjustmentTriggerType.pnl_based
        assert trigger.condition == "loss_exceeds"
        assert trigger.value == 5000

    def test_adjustment_trigger_delta_based(self):
        """Test AdjustmentTrigger with delta-based trigger."""
        trigger = AdjustmentTrigger(
            type=AdjustmentTriggerType.delta_based,
            condition="exceeds",
            value=0.3
        )
        assert trigger.type == AdjustmentTriggerType.delta_based
        assert trigger.value == 0.3

    def test_adjustment_trigger_time_based(self):
        """Test AdjustmentTrigger with time-based trigger."""
        trigger = AdjustmentTrigger(
            type=AdjustmentTriggerType.time_based,
            condition="after",
            value="15:15"
        )
        assert trigger.type == AdjustmentTriggerType.time_based
        assert trigger.value == "15:15"

    def test_adjustment_action_exit_all(self):
        """Test AdjustmentAction for exit all."""
        action = AdjustmentAction(
            type=AdjustmentActionType.exit_all,
            params={"order_type": "MARKET"}
        )
        assert action.type == AdjustmentActionType.exit_all
        assert action.params["order_type"] == "MARKET"

    def test_adjustment_action_add_hedge(self):
        """Test AdjustmentAction for add hedge."""
        action = AdjustmentAction(
            type=AdjustmentActionType.add_hedge,
            params={"hedge_type": "both", "hedge_delta": 0.5}
        )
        assert action.type == AdjustmentActionType.add_hedge
        assert action.params["hedge_type"] == "both"

    def test_adjustment_rule_complete(self):
        """Test complete AdjustmentRule."""
        rule = AdjustmentRule(
            id="adj_1",
            enabled=True,
            name="Stop Loss Rule",
            trigger=AdjustmentTrigger(
                type=AdjustmentTriggerType.pnl_based,
                condition="loss_exceeds",
                value=5000
            ),
            action=AdjustmentAction(
                type=AdjustmentActionType.exit_all,
                params={"order_type": "MARKET"}
            ),
            execution_mode=ExecutionMode.auto,
            max_executions=1,
            cooldown_seconds=0
        )
        assert rule.id == "adj_1"
        assert rule.enabled is True
        assert rule.trigger.type == AdjustmentTriggerType.pnl_based
        assert rule.action.type == AdjustmentActionType.exit_all

    def test_adjustment_rule_semi_auto(self):
        """Test AdjustmentRule with semi-auto execution."""
        rule = AdjustmentRule(
            id="adj_2",
            enabled=True,
            name="Profit Target",
            trigger=AdjustmentTrigger(
                type=AdjustmentTriggerType.pnl_based,
                condition="profit_exceeds",
                value=10000
            ),
            action=AdjustmentAction(
                type=AdjustmentActionType.exit_all,
                params={"order_type": "LIMIT"}
            ),
            execution_mode=ExecutionMode.semi_auto,
            max_executions=1,
            cooldown_seconds=0
        )
        assert rule.execution_mode == ExecutionMode.semi_auto


# =============================================================================
# Confirmation Schema Tests
# =============================================================================

class TestConfirmationSchemas:
    """Test Confirmation related schemas."""

    def test_pending_confirmation_response(self):
        """Test PendingConfirmationResponse."""
        response = PendingConfirmationResponse(
            id=1,
            strategy_id=10,
            strategy_name="Test Strategy",
            action_type="adjustment_exit_all",
            action_description="Exit all positions due to stop loss",
            action_data={"rule_id": "adj_1"},
            rule_id="adj_1",
            rule_name="Stop Loss Rule",
            status=ConfirmationStatus.pending,
            timeout_seconds=30,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
            time_remaining_seconds=25,
            created_at=datetime.now(timezone.utc)
        )
        assert response.id == 1
        assert response.status == ConfirmationStatus.pending
        assert response.time_remaining_seconds == 25

    def test_confirmation_action_request_confirm(self):
        """Test ConfirmationActionRequest for confirm."""
        request = ConfirmationActionRequest(action="confirm")
        assert request.action == "confirm"

    def test_confirmation_action_request_reject(self):
        """Test ConfirmationActionRequest for reject."""
        request = ConfirmationActionRequest(action="reject")
        assert request.action == "reject"

    def test_confirmation_action_request_invalid(self):
        """Test ConfirmationActionRequest with invalid action."""
        with pytest.raises(ValidationError):
            ConfirmationActionRequest(action="invalid")

    def test_confirmation_action_response_confirmed(self):
        """Test ConfirmationActionResponse for confirmed action."""
        response = ConfirmationActionResponse(
            success=True,
            confirmation_id=1,
            action_taken="confirmed",
            execution_result={"executed": True, "orders_placed": [1001, 1002]},
            orders_placed=[1001, 1002],
            message="Action confirmed and executed successfully"
        )
        assert response.success is True
        assert response.action_taken == "confirmed"
        assert len(response.orders_placed) == 2

    def test_confirmation_action_response_rejected(self):
        """Test ConfirmationActionResponse for rejected action."""
        response = ConfirmationActionResponse(
            success=True,
            confirmation_id=1,
            action_taken="rejected",
            execution_result=None,
            orders_placed=[],
            message="Action rejected by user"
        )
        assert response.action_taken == "rejected"
        assert len(response.orders_placed) == 0


# =============================================================================
# Trailing Stop Schema Tests
# =============================================================================

class TestTrailingStopSchemas:
    """Test Trailing Stop related schemas."""

    def test_trailing_stop_config_disabled(self):
        """Test TrailingStopConfig when disabled."""
        config = TrailingStopConfig(enabled=False)
        assert config.enabled is False
        assert config.activation_profit is None

    def test_trailing_stop_config_fixed(self):
        """Test TrailingStopConfig with fixed trail."""
        config = TrailingStopConfig(
            enabled=True,
            activation_profit=Decimal("5000"),
            trail_distance=Decimal("2000"),
            trail_type=TrailType.fixed,
            min_profit_lock=Decimal("1000")
        )
        assert config.enabled is True
        assert config.trail_type == TrailType.fixed
        assert config.activation_profit == Decimal("5000")
        assert config.trail_distance == Decimal("2000")

    def test_trailing_stop_config_percentage(self):
        """Test TrailingStopConfig with percentage trail."""
        config = TrailingStopConfig(
            enabled=True,
            activation_profit=Decimal("5000"),
            trail_distance=Decimal("20"),  # 20%
            trail_type=TrailType.percentage,
            min_profit_lock=Decimal("1000")
        )
        assert config.trail_type == TrailType.percentage

    def test_trailing_stop_status_inactive(self):
        """Test TrailingStopStatus when inactive."""
        status = TrailingStopStatus(
            enabled=True,
            active=False
        )
        assert status.enabled is True
        assert status.active is False
        assert status.high_water_mark is None

    def test_trailing_stop_status_active(self):
        """Test TrailingStopStatus when active."""
        status = TrailingStopStatus(
            enabled=True,
            active=True,
            high_water_mark=Decimal("6000"),
            current_stop_level=Decimal("4000"),
            current_pnl=Decimal("5500"),
            distance_to_stop=Decimal("1500")
        )
        assert status.active is True
        assert status.high_water_mark == Decimal("6000")
        assert status.distance_to_stop == Decimal("1500")


# =============================================================================
# Position Sizing Schema Tests
# =============================================================================

class TestPositionSizingSchemas:
    """Test Position Sizing related schemas."""

    def test_position_sizing_request(self):
        """Test PositionSizingRequest."""
        request = PositionSizingRequest(
            underlying=Underlying.NIFTY,
            strategy_type="iron_condor",
            legs_config=[
                {"strike": 24800, "option_type": "PE", "action": "BUY"},
                {"strike": 24900, "option_type": "PE", "action": "SELL"}
            ],
            max_loss_per_lot=Decimal("2500")
        )
        assert request.underlying == Underlying.NIFTY
        assert request.strategy_type == "iron_condor"
        assert len(request.legs_config) == 2

    def test_position_sizing_request_minimal(self):
        """Test PositionSizingRequest with minimal data."""
        request = PositionSizingRequest(
            underlying=Underlying.BANKNIFTY
        )
        assert request.underlying == Underlying.BANKNIFTY
        assert request.strategy_type is None

    def test_position_sizing_response(self):
        """Test PositionSizingResponse."""
        response = PositionSizingResponse(
            recommended_lots=2,
            max_loss_amount=Decimal("5000"),
            risk_per_trade=Decimal("10000"),
            account_capital=Decimal("500000"),
            vix_adjusted=True,
            calculation_details={
                "base_lots": 4,
                "vix_multiplier": 0.5,
                "vix_regime": "high"
            }
        )
        assert response.recommended_lots == 2
        assert response.vix_adjusted is True
        assert response.calculation_details["vix_regime"] == "high"


# =============================================================================
# Greeks Schema Tests
# =============================================================================

class TestGreeksSchemas:
    """Test Greeks related schemas."""

    def test_greeks_snapshot(self):
        """Test GreeksSnapshot."""
        snapshot = GreeksSnapshot(
            delta=-0.15,
            gamma=0.002,
            theta=-50.0,
            vega=25.0,
            calculated_at=datetime.now(timezone.utc)
        )
        assert snapshot.delta == -0.15
        assert snapshot.gamma == 0.002
        assert snapshot.theta == -50.0
        assert snapshot.vega == 25.0

    def test_position_greeks_response(self):
        """Test PositionGreeksResponse."""
        response = PositionGreeksResponse(
            strategy_id=1,
            net_delta=-0.15,
            net_gamma=0.002,
            net_theta=-50.0,
            net_vega=25.0,
            legs=[
                {"leg_index": 0, "delta": 0.35, "gamma": 0.001, "theta": -15.0, "vega": 10.0},
                {"leg_index": 1, "delta": -0.50, "gamma": -0.001, "theta": 20.0, "vega": -12.0}
            ],
            calculated_at=datetime.now(timezone.utc)
        )
        assert response.net_delta == -0.15
        assert len(response.legs) == 2


# =============================================================================
# WebSocket Message Schema Tests
# =============================================================================

class TestWebSocketMessageSchemas:
    """Test WebSocket message schemas."""

    def test_confirmation_required_message(self):
        """Test ConfirmationRequiredMessage."""
        message = ConfirmationRequiredMessage(
            type="confirmation_required",
            confirmation_id=1,
            strategy_id=10,
            strategy_name="Test Strategy",
            action_type="adjustment_exit_all",
            action_description="Exit all positions",
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
            timeout_seconds=30
        )
        assert message.type == "confirmation_required"
        assert message.confirmation_id == 1
        assert message.timeout_seconds == 30

    def test_kill_switch_message_triggered(self):
        """Test KillSwitchMessage for triggered event."""
        message = KillSwitchMessage(
            type="kill_switch_triggered",
            triggered_at=datetime.now(timezone.utc),
            strategies_affected=2,
            reason="User initiated emergency stop"
        )
        assert message.type == "kill_switch_triggered"
        assert message.strategies_affected == 2

    def test_kill_switch_message_reset(self):
        """Test KillSwitchMessage for reset event."""
        message = KillSwitchMessage(
            type="kill_switch_reset",
            strategies_affected=0
        )
        assert message.type == "kill_switch_reset"
        assert message.triggered_at is None

    def test_trailing_stop_message_activated(self):
        """Test TrailingStopMessage for activation."""
        message = TrailingStopMessage(
            type="trailing_stop_activated",
            strategy_id=1,
            high_water_mark=Decimal("5000"),
            current_stop_level=Decimal("3000"),
            current_pnl=Decimal("5000")
        )
        assert message.type == "trailing_stop_activated"
        assert message.high_water_mark == Decimal("5000")

    def test_trailing_stop_message_updated(self):
        """Test TrailingStopMessage for update."""
        message = TrailingStopMessage(
            type="trailing_stop_updated",
            strategy_id=1,
            high_water_mark=Decimal("7000"),
            current_stop_level=Decimal("5000"),
            current_pnl=Decimal("6500")
        )
        assert message.type == "trailing_stop_updated"


# =============================================================================
# Dashboard Schema Tests
# =============================================================================

class TestDashboardSchemas:
    """Test Dashboard related schemas."""

    def test_dashboard_summary_with_kill_switch(self):
        """Test DashboardSummaryWithKillSwitch."""
        from app.schemas.autopilot import RiskMetrics, StrategyListItem

        summary = DashboardSummaryWithKillSwitch(
            active_strategies=2,
            waiting_strategies=1,
            pending_confirmations=1,
            today_realized_pnl=Decimal("5000"),
            today_unrealized_pnl=Decimal("2000"),
            today_total_pnl=Decimal("7000"),
            risk_metrics=RiskMetrics(
                daily_loss_limit=Decimal("20000"),
                daily_loss_used=Decimal("3000"),
                daily_loss_pct=15.0,
                max_capital=Decimal("500000"),
                capital_used=Decimal("100000"),
                capital_pct=20.0,
                max_active_strategies=5,
                active_strategies_count=2,
                status="safe"
            ),
            strategies=[],
            kite_connected=True,
            websocket_connected=True,
            last_update=datetime.now(timezone.utc),
            kill_switch_enabled=False,
            kill_switch_triggered_at=None
        )
        assert summary.active_strategies == 2
        assert summary.pending_confirmations == 1
        assert summary.kill_switch_enabled is False


# =============================================================================
# Enum Schema Tests
# =============================================================================

class TestEnumSchemas:
    """Test enum value access in schemas."""

    def test_confirmation_status_values(self):
        """Test ConfirmationStatus enum values."""
        assert ConfirmationStatus.pending == "pending"
        assert ConfirmationStatus.confirmed == "confirmed"
        assert ConfirmationStatus.rejected == "rejected"
        assert ConfirmationStatus.expired == "expired"
        assert ConfirmationStatus.cancelled == "cancelled"

    def test_trail_type_values(self):
        """Test TrailType enum values."""
        assert TrailType.fixed == "fixed"
        assert TrailType.percentage == "percentage"

    def test_adjustment_trigger_type_values(self):
        """Test AdjustmentTriggerType enum values."""
        assert AdjustmentTriggerType.pnl_based == "pnl_based"
        assert AdjustmentTriggerType.delta_based == "delta_based"
        assert AdjustmentTriggerType.time_based == "time_based"

    def test_adjustment_action_type_values(self):
        """Test AdjustmentActionType enum values."""
        assert AdjustmentActionType.exit_all == "exit_all"
        assert AdjustmentActionType.add_hedge == "add_hedge"
        assert AdjustmentActionType.roll_strike == "roll_strike"

    def test_execution_mode_values(self):
        """Test ExecutionMode enum values."""
        assert ExecutionMode.auto == "auto"
        assert ExecutionMode.semi_auto == "semi_auto"
        assert ExecutionMode.manual == "manual"
