"""
Wire #2: AIMonitor ↔ StrategyMonitor Integration Tests

Tests that StrategyMonitor can invoke AIMonitor for AI-managed strategies
and that AIMonitor errors don't crash the main monitoring loop.
TDD RED phase — these tests should FAIL until strategy_monitor.py is wired.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


def _create_strategy_monitor():
    """Create StrategyMonitor with heavy dependencies mocked out."""
    mock_adapter = MagicMock()
    mock_adapter.ltp = MagicMock(return_value={})
    mock_market_data = MagicMock()

    with patch("app.services.autopilot.strategy_monitor.KillSwitchService"), \
         patch("app.services.autopilot.strategy_monitor.AdjustmentEngine"), \
         patch("app.services.autopilot.strategy_monitor.ConfirmationService"), \
         patch("app.services.autopilot.strategy_monitor.TrailingStopService"), \
         patch("app.services.autopilot.strategy_monitor.GreeksCalculatorService"), \
         patch("app.services.autopilot.strategy_monitor.get_order_executor"), \
         patch("app.services.autopilot.strategy_monitor.get_ws_manager"), \
         patch("app.services.autopilot.strategy_monitor.ConditionEngine") as MockCE:

        from app.services.autopilot.strategy_monitor import StrategyMonitor
        monitor = StrategyMonitor(
            broker_adapter=mock_adapter,
            market_data=mock_market_data,
            condition_engine=MockCE()
        )
    return monitor


class TestStrategyMonitorAIIntegration:
    """Verify StrategyMonitor calls AIMonitor for AI strategies."""

    @pytest.mark.asyncio
    async def test_strategy_monitor_accepts_ai_monitor(self):
        """StrategyMonitor must accept an optional ai_monitor parameter."""
        monitor = _create_strategy_monitor()

        # Must be able to set ai_monitor
        mock_ai_monitor = AsyncMock()
        monitor.ai_monitor = mock_ai_monitor
        assert monitor.ai_monitor is mock_ai_monitor

    @pytest.mark.asyncio
    async def test_ai_monitor_called_for_ai_strategies(self):
        """When processing AI-managed strategies, StrategyMonitor must call ai_monitor."""
        monitor = _create_strategy_monitor()

        mock_ai_monitor = AsyncMock()
        mock_ai_monitor.process_ai_strategies = AsyncMock(return_value=[])
        monitor.ai_monitor = mock_ai_monitor

        # Create a mock AI-managed strategy (has ai_managed=True)
        mock_strategy = MagicMock()
        mock_strategy.id = uuid4()
        mock_strategy.status = "active"
        mock_strategy.ai_managed = True
        mock_strategy.user_id = uuid4()

        # Call the AI processing method
        mock_db = AsyncMock()
        mock_ai_config = MagicMock()
        mock_ai_config.ai_enabled = True

        await monitor._process_ai_strategies(
            db=mock_db,
            strategies=[mock_strategy],
            ai_config=mock_ai_config
        )

        mock_ai_monitor.process_ai_strategies.assert_called_once()

    @pytest.mark.asyncio
    async def test_ai_monitor_error_does_not_crash_loop(self):
        """If AIMonitor raises, StrategyMonitor must continue processing."""
        monitor = _create_strategy_monitor()

        mock_ai_monitor = AsyncMock()
        mock_ai_monitor.process_ai_strategies = AsyncMock(
            side_effect=Exception("AIMonitor crashed")
        )
        monitor.ai_monitor = mock_ai_monitor

        mock_db = AsyncMock()
        mock_ai_config = MagicMock()
        mock_ai_config.ai_enabled = True

        mock_strategy = MagicMock()
        mock_strategy.id = uuid4()
        mock_strategy.ai_managed = True
        mock_strategy.user_id = uuid4()

        # Must NOT raise — error is caught and logged
        await monitor._process_ai_strategies(
            db=mock_db,
            strategies=[mock_strategy],
            ai_config=mock_ai_config
        )
        # If we get here, the test passes (no crash)

    @pytest.mark.asyncio
    async def test_non_ai_strategies_skip_ai_monitor(self):
        """Non-AI strategies must NOT invoke AIMonitor."""
        monitor = _create_strategy_monitor()

        mock_ai_monitor = AsyncMock()
        mock_ai_monitor.process_ai_strategies = AsyncMock(return_value=[])
        monitor.ai_monitor = mock_ai_monitor

        mock_strategy = MagicMock()
        mock_strategy.id = uuid4()
        mock_strategy.ai_managed = False  # NOT AI managed

        mock_db = AsyncMock()

        await monitor._process_ai_strategies(
            db=mock_db,
            strategies=[mock_strategy],
            ai_config=None
        )

        # AI monitor should NOT be called for non-AI strategies
        mock_ai_monitor.process_ai_strategies.assert_not_called()
