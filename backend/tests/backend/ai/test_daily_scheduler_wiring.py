"""
Wire #1: DailyScheduler Lifespan Integration Tests

Tests that DailyScheduler is started during app lifespan and stopped on shutdown.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# Patches needed to isolate lifespan from real services
LIFESPAN_PATCHES = {
    "app.main.init_db": AsyncMock(),
    "app.main.refresh_instrument_master_startup": AsyncMock(),
    "app.main.close_db": AsyncMock(),
    "app.services.autopilot.strategy_monitor.stop_strategy_monitor": AsyncMock(),
}


class TestSchedulerLifespanStartup:
    """Verify DailyScheduler starts and stops with the app."""

    @pytest.mark.asyncio
    async def test_lifespan_starts_scheduler(self):
        """DailyScheduler.start() must be called during app startup."""
        with patch("app.main.start_scheduler", new_callable=AsyncMock) as mock_start, \
             patch("app.main.stop_scheduler", new_callable=AsyncMock), \
             patch("app.main.init_db", new_callable=AsyncMock), \
             patch("app.main.refresh_instrument_master_startup", new_callable=AsyncMock), \
             patch("app.main.close_db", new_callable=AsyncMock), \
             patch("app.services.autopilot.strategy_monitor.stop_strategy_monitor", new_callable=AsyncMock):

            from app.main import lifespan, app

            async with lifespan(app):
                mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_stops_scheduler_on_shutdown(self):
        """DailyScheduler.stop() must be called during app shutdown."""
        with patch("app.main.start_scheduler", new_callable=AsyncMock), \
             patch("app.main.stop_scheduler", new_callable=AsyncMock) as mock_stop, \
             patch("app.main.init_db", new_callable=AsyncMock), \
             patch("app.main.refresh_instrument_master_startup", new_callable=AsyncMock), \
             patch("app.main.close_db", new_callable=AsyncMock), \
             patch("app.services.autopilot.strategy_monitor.stop_strategy_monitor", new_callable=AsyncMock):

            from app.main import lifespan, app

            async with lifespan(app):
                pass

            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_failure_does_not_crash_startup(self):
        """If scheduler fails to start, app startup must continue."""
        with patch("app.main.start_scheduler", new_callable=AsyncMock,
                    side_effect=Exception("Scheduler init failed")), \
             patch("app.main.stop_scheduler", new_callable=AsyncMock), \
             patch("app.main.init_db", new_callable=AsyncMock), \
             patch("app.main.refresh_instrument_master_startup", new_callable=AsyncMock), \
             patch("app.main.close_db", new_callable=AsyncMock), \
             patch("app.services.autopilot.strategy_monitor.stop_strategy_monitor", new_callable=AsyncMock):

            from app.main import lifespan, app

            # Should NOT raise — scheduler failure is non-fatal
            async with lifespan(app):
                pass
