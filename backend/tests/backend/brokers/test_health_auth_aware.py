"""Tests for HealthMonitor auth-aware error recording — Layer 2.2.

Tests that HealthMonitor:
- Classifies auth errors via token_policy
- NOT_RETRYABLE / NOT_REFRESHABLE → instant failover callback (bypass gradual decay)
- RETRYABLE → normal record_error path (gradual decay)
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from app.services.brokers.market_data.ticker.health import HealthMonitor
from app.services.brokers.market_data.ticker.token_policy import RetryCategory


@pytest.fixture
def health_monitor():
    m = HealthMonitor()
    m.register_adapter("smartapi")
    m.register_adapter("kite")
    return m


class TestAuthFailureNotRetryableTriggersInstantFailover:
    @pytest.mark.asyncio
    async def test_not_retryable_triggers_callback_immediately(self, health_monitor):
        """NOT_RETRYABLE auth error should invoke health change callback
        immediately — no need to wait for 3 consecutive low heartbeats."""
        callback = AsyncMock()
        health_monitor.set_on_health_change(callback)

        # AB1004 = Invalid API Key → NOT_RETRYABLE
        await health_monitor.record_auth_failure("smartapi", "AB1004", "Invalid API Key")

        callback.assert_called_once()
        broker, score = callback.call_args[0]
        assert broker == "smartapi"
        assert score == 0.0  # Instant zero score for non-retryable

    @pytest.mark.asyncio
    async def test_not_retryable_sets_health_score_zero(self, health_monitor):
        """NOT_RETRYABLE should drop health score to 0 immediately."""
        await health_monitor.record_auth_failure("smartapi", "AB1004", "Invalid API Key")

        health = health_monitor.get_health("smartapi")
        assert health.health_score == 0.0


class TestAuthFailureNotRefreshableTriggersInstantFailover:
    @pytest.mark.asyncio
    async def test_not_refreshable_triggers_callback_immediately(self, health_monitor):
        """NOT_REFRESHABLE auth error should invoke health change callback
        immediately — same as NOT_RETRYABLE."""
        callback = AsyncMock()
        health_monitor.set_on_health_change(callback)

        # TokenException on Kite → NOT_REFRESHABLE
        await health_monitor.record_auth_failure("kite", "TokenException", "Token expired")

        callback.assert_called_once()
        broker, score = callback.call_args[0]
        assert broker == "kite"
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_not_refreshable_sets_health_score_zero(self, health_monitor):
        """NOT_REFRESHABLE should drop health score to 0 immediately."""
        await health_monitor.record_auth_failure("kite", "TokenException", "Token expired")

        health = health_monitor.get_health("kite")
        assert health.health_score == 0.0


class TestAuthFailureRetryableUsesGradualDecay:
    @pytest.mark.asyncio
    async def test_retryable_does_not_trigger_instant_callback(self, health_monitor):
        """RETRYABLE auth error should use normal record_error path,
        not trigger instant failover."""
        callback = AsyncMock()
        health_monitor.set_on_health_change(callback)

        # AB1010 = Invalid Token → RETRYABLE (can refresh via TOTP)
        await health_monitor.record_auth_failure("smartapi", "AB1010", "Invalid Token")

        # Should NOT trigger instant callback — gradual decay via heartbeat
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_retryable_increments_error_count(self, health_monitor):
        """RETRYABLE auth error should record in error_count (gradual decay)."""
        await health_monitor.record_auth_failure("smartapi", "AB1010", "Invalid Token")

        health = health_monitor.get_health("smartapi")
        assert health.error_count_5min >= 1

    @pytest.mark.asyncio
    async def test_retryable_does_not_zero_health(self, health_monitor):
        """RETRYABLE should NOT immediately zero the health score."""
        await health_monitor.record_auth_failure("smartapi", "AB1010", "Invalid Token")

        health = health_monitor.get_health("smartapi")
        # Health should still be > 0 (not instantly zeroed)
        assert health.health_score > 0.0


class TestAuthFailureWithNoCallback:
    @pytest.mark.asyncio
    async def test_no_callback_no_crash(self, health_monitor):
        """Auth failure with no callback set should not crash."""
        # No callback set — should not raise
        await health_monitor.record_auth_failure("smartapi", "AB1004", "Invalid API Key")

        health = health_monitor.get_health("smartapi")
        assert health.health_score == 0.0


class TestAuthFailureUnregisteredBroker:
    @pytest.mark.asyncio
    async def test_unregistered_broker_no_crash(self, health_monitor):
        """Auth failure for unregistered broker should be a no-op."""
        await health_monitor.record_auth_failure("unknown", "ERR", "Something")
        # No crash, no health entry
        assert health_monitor.get_health("unknown") is None
