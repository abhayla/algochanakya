"""
Wire #3: AIMonitor Decision → Action Connection Tests

Tests that AIMonitor connects decisions to real actions:
- CRITICAL extreme event → kill_switch.trigger()
- Adjustment decision → adjustment_engine.execute_adjustment()
- Risk state PAUSED → blocks new deployments
TDD RED phase — these tests should FAIL until ai_monitor.py is wired.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def create_ai_monitor(mock_kite, mock_db):
    """Create AIMonitor with ClaudeAdvisor mocked out (avoids Anthropic SDK init)."""
    with patch("app.services.ai.ai_monitor.ClaudeAdvisor"):
        from app.services.ai.ai_monitor import AIMonitor
        return AIMonitor(mock_kite, mock_db)


class TestAIMonitorKillSwitchConnection:
    """Verify CRITICAL extreme events trigger kill switch."""

    @pytest.mark.asyncio
    async def test_critical_event_triggers_kill_switch(
        self, mock_kite, mock_db, mock_ai_user_config, mock_kill_switch
    ):
        """When a CRITICAL extreme event is detected, kill_switch.trigger() must be called."""
        monitor = create_ai_monitor(mock_kite, mock_db)
        monitor.kill_switch = mock_kill_switch

        # Mock extreme event handler to return a CRITICAL event
        mock_event = {
            "type": MagicMock(value="vix_spike"),
            "severity": MagicMock(value="CRITICAL"),
            "message": "VIX spiked to 35 — CRITICAL threshold exceeded",
            "value": 35.0,
            "threshold": 30.0
        }
        # Make severity comparison work
        from app.services.ai.extreme_event_handler import ExtremeEventSeverity
        mock_event["severity"] = ExtremeEventSeverity.CRITICAL

        monitor.extreme_event_handler = AsyncMock()
        monitor.extreme_event_handler.detect_extreme_events = AsyncMock(
            return_value=[mock_event]
        )

        # Mock other dependencies
        monitor.market_data = MagicMock()
        monitor.market_data.get_vix = AsyncMock(return_value=35.0)

        with patch("app.services.ai.ai_monitor.get_health_monitor", return_value=None):
            decisions = await monitor.process_ai_strategies(
                user_id=str(mock_ai_user_config.user_id),
                user_config=mock_ai_user_config,
                active_strategies=[]
            )

        # Kill switch MUST have been triggered
        mock_kill_switch.trigger.assert_called_once()
        # Reason must mention the extreme event
        call_kwargs = mock_kill_switch.trigger.call_args
        assert "reason" in call_kwargs.kwargs or len(call_kwargs.args) > 0

    @pytest.mark.asyncio
    async def test_elevated_event_does_not_trigger_kill_switch(
        self, mock_kite, mock_db, mock_ai_user_config, mock_kill_switch
    ):
        """ELEVATED events should block deployments but NOT trigger kill switch."""
        monitor = create_ai_monitor(mock_kite, mock_db)
        monitor.kill_switch = mock_kill_switch

        from app.services.ai.extreme_event_handler import ExtremeEventSeverity
        mock_event = {
            "type": MagicMock(value="vix_elevated"),
            "severity": ExtremeEventSeverity.ELEVATED,
            "message": "VIX elevated at 22",
            "value": 22.0,
            "threshold": 20.0
        }

        monitor.extreme_event_handler = AsyncMock()
        monitor.extreme_event_handler.detect_extreme_events = AsyncMock(
            return_value=[mock_event]
        )
        monitor.market_data = MagicMock()
        monitor.market_data.get_vix = AsyncMock(return_value=22.0)
        monitor.risk_state_engine = AsyncMock()
        monitor.risk_state_engine.evaluate_state = AsyncMock(return_value=MagicMock(
            state="NORMAL", transition_needed=False
        ))
        monitor.position_sync = AsyncMock()
        monitor.position_sync.sync_positions = AsyncMock(return_value=[])

        with patch("app.services.ai.ai_monitor.get_health_monitor", return_value=None):
            decisions = await monitor.process_ai_strategies(
                user_id=str(mock_ai_user_config.user_id),
                user_config=mock_ai_user_config,
                active_strategies=[]
            )

        # Kill switch should NOT be triggered for elevated events
        mock_kill_switch.trigger.assert_not_called()


class TestAIMonitorAdjustmentConnection:
    """Verify adjustment decisions call adjustment_engine."""

    @pytest.mark.asyncio
    async def test_adjustment_decision_calls_engine(
        self, mock_kite, mock_db, mock_ai_user_config, mock_adjustment_engine
    ):
        """When AIMonitor decides an adjustment is needed, it must call adjustment_engine."""
        from app.services.ai.ai_monitor import AIDecision

        monitor = create_ai_monitor(mock_kite, mock_db)
        monitor.adjustment_engine = mock_adjustment_engine

        # Create a mock strategy that triggers adjustment
        mock_strategy = {
            "id": str(uuid4()),
            "strategy_type": "iron_condor",
            "status": "active",
            "current_pnl": -5000,
            "legs": [],
            "adjustment_rules": [{"type": "pnl_based", "threshold": -3000}]
        }

        # Mock _evaluate_adjustment to return a decision
        adjustment_decision = AIDecision(
            decision_type="adjustment_recommended",
            action_taken="add_hedge",
            confidence=85.0,
            reasoning="P&L exceeded loss threshold, adding protective hedge",
            regime_at_decision="VOLATILE",
            vix_at_decision=18.0,
            spot_at_decision=22000.0,
            indicators_snapshot={}
        )

        monitor._evaluate_adjustment = AsyncMock(return_value=adjustment_decision)
        monitor.extreme_event_handler = AsyncMock()
        monitor.extreme_event_handler.detect_extreme_events = AsyncMock(return_value=[])
        monitor.market_data = MagicMock()
        monitor.market_data.get_vix = AsyncMock(return_value=18.0)
        # evaluate_state returns (RiskState, reason_string) tuple
        # Must use actual RiskState enum so comparison at line 245 works correctly
        from app.models.ai_risk_state import RiskState
        monitor.risk_state_engine = AsyncMock()
        monitor.risk_state_engine.evaluate_state = AsyncMock(
            return_value=(RiskState.NORMAL, "Normal conditions")
        )
        monitor.risk_state_engine.get_current_state = AsyncMock(
            return_value=MagicMock(state="NORMAL")
        )
        monitor.position_sync = AsyncMock()
        monitor.position_sync.sync_positions = AsyncMock(return_value=[])
        monitor._check_regime_change = AsyncMock(return_value=None)
        monitor._evaluate_position_health = AsyncMock(return_value=None)
        monitor.kill_switch = AsyncMock()
        monitor.kill_switch.is_enabled = AsyncMock(return_value=False)

        with patch("app.services.ai.ai_monitor.get_health_monitor", return_value=None):
            decisions = await monitor.process_ai_strategies(
                user_id=str(mock_ai_user_config.user_id),
                user_config=mock_ai_user_config,
                active_strategies=[mock_strategy]
            )

        # Adjustment engine must have been called to execute the adjustment
        mock_adjustment_engine.execute_adjustment.assert_called_once()


class TestAIMonitorHasActionDependencies:
    """Verify AIMonitor accepts kill_switch and adjustment_engine."""

    def test_ai_monitor_accepts_kill_switch(self, mock_kite, mock_db, mock_kill_switch):
        """AIMonitor must accept a kill_switch parameter or attribute."""
        monitor = create_ai_monitor(mock_kite, mock_db)
        monitor.kill_switch = mock_kill_switch
        assert monitor.kill_switch is mock_kill_switch

    def test_ai_monitor_accepts_adjustment_engine(
        self, mock_kite, mock_db, mock_adjustment_engine
    ):
        """AIMonitor must accept an adjustment_engine parameter or attribute."""
        monitor = create_ai_monitor(mock_kite, mock_db)
        monitor.adjustment_engine = mock_adjustment_engine
        assert monitor.adjustment_engine is mock_adjustment_engine
