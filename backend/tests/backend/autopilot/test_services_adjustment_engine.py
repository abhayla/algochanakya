"""
Adjustment Engine Service Tests

Tests for AdjustmentEngine including:
- Rule evaluation (all trigger types)
- Condition checking (PNL, numeric, time)
- Action execution (exit_all, add_hedge, roll, scale)
- Cooldown handling
- Max execution limits
- Execution modes (auto, semi-auto, manual)
- WebSocket notifications
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.adjustment_engine import AdjustmentEngine, get_adjustment_engine
from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotAdjustmentLog,
    AutoPilotLog,
    AdjustmentTriggerType,
    AdjustmentActionType,
    ExecutionMode,
    LogSeverity
)
from app.models.users import User


# =============================================================================
# PNL Condition Tests
# =============================================================================

class TestPNLConditions:
    """Test PNL-based condition checking."""

    @pytest.mark.asyncio
    async def test_pnl_loss_exceeds_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test loss_exceeds condition triggers when loss is larger."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_pnl_condition(
            current_pnl=Decimal("-6000"),
            condition="loss_exceeds",
            target_value=5000
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_pnl_loss_exceeds_not_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test loss_exceeds condition does not trigger when loss is smaller."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_pnl_condition(
            current_pnl=Decimal("-3000"),
            condition="loss_exceeds",
            target_value=5000
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_pnl_profit_exceeds_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test profit_exceeds condition triggers when profit is larger."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_pnl_condition(
            current_pnl=Decimal("15000"),
            condition="profit_exceeds",
            target_value=10000
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_pnl_profit_exceeds_not_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test profit_exceeds condition does not trigger when profit is smaller."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_pnl_condition(
            current_pnl=Decimal("5000"),
            condition="profit_exceeds",
            target_value=10000
        )

        assert result is False


# =============================================================================
# Numeric Condition Tests
# =============================================================================

class TestNumericConditions:
    """Test numeric condition checking."""

    @pytest.mark.asyncio
    async def test_greater_than_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test greater_than condition triggers correctly."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=0.45,
            condition="greater_than",
            target_value=0.30
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_less_than_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test less_than condition triggers correctly."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=15.0,
            condition="less_than",
            target_value=18.0
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_exceeds_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test exceeds condition (alias for greater_than)."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=30.0,
            condition="exceeds",
            target_value=25.0
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_below_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test below condition (alias for less_than)."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=10.0,
            condition="below",
            target_value=12.0
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_between_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test between condition triggers when value is in range."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=15.0,
            condition="between",
            target_value=[10.0, 20.0]
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_between_not_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test between condition does not trigger when value is outside range."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=25.0,
            condition="between",
            target_value=[10.0, 20.0]
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_equals_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test equals condition triggers for matching values."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=25.005,
            condition="equals",
            target_value=25.0
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_null_value_returns_false(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test None value returns False."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_numeric_condition(
            current_value=None,
            condition="greater_than",
            target_value=10.0
        )

        assert result is False


# =============================================================================
# Time Condition Tests
# =============================================================================

class TestTimeConditions:
    """Test time-based condition checking."""

    @pytest.mark.asyncio
    async def test_time_equals_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test time equals condition."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_time_condition(
            current_time="15:15",
            condition="equals",
            target_value="15:15"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_time_after_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test time after condition."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_time_condition(
            current_time="15:20",
            condition="after",
            target_value="15:15"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_time_before_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test time before condition."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_time_condition(
            current_time="09:30",
            condition="before",
            target_value="09:45"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_time_before_not_triggered(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test time before condition not triggered when past target."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = engine._check_time_condition(
            current_time="10:00",
            condition="before",
            target_value="09:45"
        )

        assert result is False


# =============================================================================
# Rule Evaluation Tests
# =============================================================================

class TestRuleEvaluation:
    """Test rule evaluation functionality."""

    @pytest.mark.asyncio
    async def test_evaluate_pnl_based_rule(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test evaluating a PNL-based adjustment rule."""
        engine = AdjustmentEngine(db_session, test_user.id)

        market_data = {
            'spot': 25000,
            'vix': 15.0,
            'option_prices': {}
        }

        # Modify strategy to have runtime state with PNL
        test_strategy_with_adjustments.runtime_state = {
            'positions': [],
            'entry_prices': {},
            'total_premium': 5000
        }

        triggered_rules = await engine.evaluate_rules(test_strategy_with_adjustments, market_data)

        # At least check that evaluation runs without error
        assert isinstance(triggered_rules, list)

    @pytest.mark.asyncio
    async def test_evaluate_disabled_rule_skipped(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test that disabled rules are skipped."""
        engine = AdjustmentEngine(db_session, test_user.id)

        # Disable the rule
        if test_strategy_with_adjustments.adjustment_rules:
            test_strategy_with_adjustments.adjustment_rules[0]['enabled'] = False
        await db_session.commit()

        market_data = {'spot': 25000, 'vix': 15.0}

        triggered_rules = await engine.evaluate_rules(test_strategy_with_adjustments, market_data)

        # Disabled rule should not trigger
        for rule, _ in triggered_rules:
            assert rule.get('enabled', True) is True


# =============================================================================
# Cooldown Tests
# =============================================================================

class TestCooldown:
    """Test cooldown functionality."""

    @pytest.mark.asyncio
    async def test_rule_in_cooldown(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test that rule in cooldown is skipped."""
        engine = AdjustmentEngine(db_session, test_user.id)

        # Create a recent execution log
        log = AutoPilotAdjustmentLog(
            strategy_id=test_strategy_with_adjustments.id,
            user_id=test_user.id,
            rule_id="adj_1",
            rule_name="Test Rule",
            trigger_type=AdjustmentTriggerType.PNL_BASED,
            trigger_condition="loss_exceeds",
            trigger_value=5000,
            actual_value=-6000,
            action_type=AdjustmentActionType.EXIT_ALL,
            action_params={},
            execution_mode=ExecutionMode.AUTO,
            executed=True,
            executed_at=datetime.now(timezone.utc)
        )
        db_session.add(log)
        await db_session.commit()

        # Check cooldown
        in_cooldown = await engine._is_in_cooldown(
            strategy_id=test_strategy_with_adjustments.id,
            rule_id="adj_1",
            cooldown_seconds=60
        )

        assert in_cooldown is True

    @pytest.mark.asyncio
    async def test_rule_not_in_cooldown(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test that rule outside cooldown period is not in cooldown."""
        engine = AdjustmentEngine(db_session, test_user.id)

        # Check cooldown for rule that was never executed
        in_cooldown = await engine._is_in_cooldown(
            strategy_id=test_strategy_with_adjustments.id,
            rule_id="never_executed_rule",
            cooldown_seconds=60
        )

        assert in_cooldown is False

    @pytest.mark.asyncio
    async def test_zero_cooldown_never_blocks(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test that zero cooldown never blocks execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        in_cooldown = await engine._is_in_cooldown(
            strategy_id=test_strategy_with_adjustments.id,
            rule_id="any_rule",
            cooldown_seconds=0
        )

        assert in_cooldown is False


# =============================================================================
# Max Executions Tests
# =============================================================================

class TestMaxExecutions:
    """Test max executions limit functionality."""

    @pytest.mark.asyncio
    async def test_max_executions_exceeded(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test that rule is blocked when max executions exceeded."""
        engine = AdjustmentEngine(db_session, test_user.id)

        # Create 3 execution logs
        for i in range(3):
            log = AutoPilotAdjustmentLog(
                strategy_id=test_strategy_with_adjustments.id,
                user_id=test_user.id,
                rule_id="limited_rule",
                rule_name="Limited Rule",
                trigger_type=AdjustmentTriggerType.PNL_BASED,
                trigger_condition="loss_exceeds",
                trigger_value=5000,
                actual_value=-6000,
                action_type=AdjustmentActionType.EXIT_ALL,
                action_params={},
                execution_mode=ExecutionMode.AUTO,
                executed=True,
                executed_at=datetime.now(timezone.utc) - timedelta(hours=i)
            )
            db_session.add(log)
        await db_session.commit()

        exceeded = await engine._exceeded_max_executions(
            strategy_id=test_strategy_with_adjustments.id,
            rule_id="limited_rule",
            max_executions=3
        )

        assert exceeded is True

    @pytest.mark.asyncio
    async def test_max_executions_not_exceeded(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test rule is not blocked when below max executions."""
        engine = AdjustmentEngine(db_session, test_user.id)

        exceeded = await engine._exceeded_max_executions(
            strategy_id=test_strategy_with_adjustments.id,
            rule_id="new_rule",
            max_executions=5
        )

        assert exceeded is False

    @pytest.mark.asyncio
    async def test_no_max_executions_limit(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test that None max_executions allows unlimited."""
        engine = AdjustmentEngine(db_session, test_user.id)

        exceeded = await engine._exceeded_max_executions(
            strategy_id=test_strategy_with_adjustments.id,
            rule_id="any_rule",
            max_executions=None
        )

        assert exceeded is False


# =============================================================================
# Execution Mode Tests
# =============================================================================

class TestExecutionModes:
    """Test different execution modes."""

    @pytest.mark.asyncio
    async def test_manual_mode_does_not_execute(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test that manual mode logs but does not execute."""
        engine = AdjustmentEngine(db_session, test_user.id)

        rule = {
            'id': 'manual_rule',
            'name': 'Manual Rule',
            'trigger': {'type': 'pnl_based', 'condition': 'loss_exceeds', 'value': 5000},
            'action': {'type': 'exit_all', 'params': {}},
            'execution_mode': 'manual'
        }

        evaluation = {
            'triggered': True,
            'current_value': -6000,
            'trigger_type': 'pnl_based'
        }

        result = await engine.execute_adjustment(
            test_strategy_with_adjustments,
            rule,
            evaluation,
            ExecutionMode.MANUAL
        )

        assert result['executed'] is False
        assert result['manual_mode'] is True

    @pytest.mark.asyncio
    async def test_semi_auto_requires_confirmation(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy,
        mock_confirmation_service
    ):
        """Test that semi-auto mode creates confirmation request."""
        engine = AdjustmentEngine(db_session, test_user.id)
        engine.set_confirmation_service(mock_confirmation_service)

        rule = {
            'id': 'semi_auto_rule',
            'name': 'Semi-Auto Rule',
            'trigger': {'type': 'pnl_based', 'condition': 'loss_exceeds', 'value': 5000},
            'action': {'type': 'exit_all', 'params': {}},
            'execution_mode': 'semi_auto'
        }

        evaluation = {
            'triggered': True,
            'current_value': -6000,
            'trigger_type': 'pnl_based'
        }

        result = await engine.execute_adjustment(
            test_strategy_with_adjustments,
            rule,
            evaluation,
            ExecutionMode.SEMI_AUTO
        )

        assert result['executed'] is False
        assert result['confirmation_required'] is True
        mock_confirmation_service.create_confirmation.assert_called()


# =============================================================================
# Action Execution Tests
# =============================================================================

class TestActionExecution:
    """Test action execution methods."""

    @pytest.mark.asyncio
    async def test_execute_exit_all_action(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test exit_all action execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = await engine._action_exit_all(
            test_strategy_with_adjustments,
            {'order_type': 'MARKET'}
        )

        assert result['action'] == 'exit_all'

    @pytest.mark.asyncio
    async def test_execute_add_hedge_action(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test add_hedge action execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = await engine._action_add_hedge(
            test_strategy_with_adjustments,
            {'hedge_type': 'both'}
        )

        assert result['action'] == 'add_hedge'
        assert result['hedge_type'] == 'both'

    @pytest.mark.asyncio
    async def test_execute_roll_strike_action(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test roll_strike action execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = await engine._action_roll_strike(
            test_strategy_with_adjustments,
            {'direction': 'closer', 'offset': 100}
        )

        assert result['action'] == 'roll_strike'
        assert result['direction'] == 'closer'
        assert result['offset'] == 100

    @pytest.mark.asyncio
    async def test_execute_roll_expiry_action(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test roll_expiry action execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = await engine._action_roll_expiry(
            test_strategy_with_adjustments,
            {}
        )

        assert result['action'] == 'roll_expiry'

    @pytest.mark.asyncio
    async def test_execute_scale_down_action(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test scale_down action execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = await engine._action_scale_down(
            test_strategy_with_adjustments,
            {'percentage': 50}
        )

        assert result['action'] == 'scale_down'
        assert result['percentage'] == 50

    @pytest.mark.asyncio
    async def test_execute_scale_up_action(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test scale_up action execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = await engine._action_scale_up(
            test_strategy_with_adjustments,
            {'percentage': 50}
        )

        assert result['action'] == 'scale_up'
        assert result['percentage'] == 50

    @pytest.mark.asyncio
    async def test_execute_close_leg_action(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy
    ):
        """Test close_leg action execution."""
        engine = AdjustmentEngine(db_session, test_user.id)

        result = await engine._action_close_leg(
            test_strategy_with_adjustments,
            {'leg_id': 'leg_1'}
        )

        assert result['action'] == 'close_leg'
        assert result['leg_id'] == 'leg_1'


# =============================================================================
# WebSocket Notification Tests
# =============================================================================

class TestWebSocketNotifications:
    """Test WebSocket notification sending."""

    @pytest.mark.asyncio
    async def test_adjustment_sends_notification(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_with_adjustments: AutoPilotStrategy,
        mock_ws_manager
    ):
        """Test that adjustment execution sends WebSocket notification."""
        engine = AdjustmentEngine(db_session, test_user.id)
        engine.set_websocket_manager(mock_ws_manager)

        rule = {
            'id': 'test_rule',
            'name': 'Test Rule',
            'trigger': {'type': 'pnl_based', 'condition': 'profit_exceeds', 'value': 5000},
            'action': {'type': 'exit_all', 'params': {}}
        }

        result = {'action': 'exit_all', 'orders_placed': []}

        await engine._send_adjustment_notification(
            test_strategy_with_adjustments,
            rule,
            result
        )

        mock_ws_manager.broadcast_to_user.assert_called()


# =============================================================================
# Factory Tests
# =============================================================================

class TestAdjustmentEngineFactory:
    """Test AdjustmentEngine factory function."""

    @pytest.mark.asyncio
    async def test_get_adjustment_engine(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test factory function creates engine instance."""
        engine = await get_adjustment_engine(db_session, test_user.id)

        assert isinstance(engine, AdjustmentEngine)
        assert engine.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_set_market_data_service(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_market_data_service
    ):
        """Test setting market data service."""
        engine = AdjustmentEngine(db_session, test_user.id)

        engine.set_market_data_service(mock_market_data_service)

        assert engine.market_data_service is not None

    @pytest.mark.asyncio
    async def test_set_order_executor(
        self,
        db_session: AsyncSession,
        test_user: User,
        mock_order_executor
    ):
        """Test setting order executor."""
        engine = AdjustmentEngine(db_session, test_user.id)

        engine.set_order_executor(mock_order_executor)

        assert engine.order_executor is not None
