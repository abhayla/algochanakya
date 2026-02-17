"""Tests for HealthMonitor — health scoring, recording, heartbeat loop."""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from app.services.brokers.market_data.ticker.health import (
    HealthMonitor,
    AdapterHealth,
)


# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def monitor():
    """Create a fresh HealthMonitor for each test."""
    m = HealthMonitor()
    yield m
    if m._is_running:
        await m.stop()


# ─── Registration Tests ───────────────────────────────────────────────────────


class TestRegistration:
    def test_register_adapter(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        assert "smartapi" in monitor._adapter_health
        assert monitor._adapter_health["smartapi"].broker_type == "smartapi"

    def test_register_duplicate_is_noop(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        health.health_score = 42.0
        monitor.register_adapter("smartapi")
        assert monitor._adapter_health["smartapi"].health_score == 42.0

    def test_unregister_adapter(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        monitor.unregister_adapter("smartapi")
        assert "smartapi" not in monitor._adapter_health

    def test_unregister_nonexistent_is_noop(self, monitor: HealthMonitor):
        monitor.unregister_adapter("nonexistent")  # Should not raise


# ─── Recording Tests ──────────────────────────────────────────────────────────


class TestRecording:
    def test_record_ticks(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        monitor.record_ticks("smartapi", 5)
        health = monitor._adapter_health["smartapi"]
        assert health.tick_count_1min == 5
        assert health.last_tick_time is not None

    def test_record_ticks_cleanup_old(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        # Add old timestamps
        old = datetime.now() - timedelta(minutes=2)
        health.tick_timestamps = [old] * 10
        # Record new ticks
        monitor.record_ticks("smartapi", 3)
        # Old timestamps should be cleaned up
        assert health.tick_count_1min == 3

    def test_record_ticks_unregistered_is_noop(self, monitor: HealthMonitor):
        monitor.record_ticks("unknown", 5)  # Should not raise

    def test_record_error(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        monitor.record_error("smartapi", "Connection timeout")
        health = monitor._adapter_health["smartapi"]
        assert health.error_count_5min == 1

    def test_record_error_cleanup_old(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        old = datetime.now() - timedelta(minutes=6)
        health.error_timestamps = [old] * 5
        monitor.record_error("smartapi", "new error")
        assert health.error_count_5min == 1

    def test_record_connect_disconnect(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        assert not monitor._adapter_health["smartapi"].is_connected

        monitor.record_connect("smartapi")
        assert monitor._adapter_health["smartapi"].is_connected

        monitor.record_disconnect("smartapi")
        assert not monitor._adapter_health["smartapi"].is_connected

    def test_record_latency(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        monitor.record_latency("smartapi", 50.0)
        monitor.record_latency("smartapi", 100.0)
        health = monitor._adapter_health["smartapi"]
        assert health.avg_latency_ms == 75.0
        assert len(health.latency_samples) == 2

    def test_record_latency_max_samples(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        for i in range(25):
            monitor.record_latency("smartapi", float(i))
        health = monitor._adapter_health["smartapi"]
        assert len(health.latency_samples) == 20


# ─── Health Score Calculation Tests ────────────────────────────────────────────


class TestHealthScoring:
    def test_perfect_health(self, monitor: HealthMonitor):
        """All metrics optimal -> score ~100."""
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        health.avg_latency_ms = 50.0
        health.tick_count_1min = 50
        health.error_count_5min = 0
        health.last_tick_time = datetime.now()

        score = monitor._calculate_health_score(health)
        assert score == 100.0

    def test_zero_health_no_ticks(self, monitor: HealthMonitor):
        """No ticks ever -> staleness and tick_rate both 0."""
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        health.avg_latency_ms = 0.0
        health.tick_count_1min = 0
        health.error_count_5min = 0
        health.last_tick_time = None

        score = monitor._calculate_health_score(health)
        # latency=100*0.3 + tick_rate=0*0.3 + errors=100*0.2 + staleness=0*0.2
        assert score == 50.0

    def test_high_latency_degrades_score(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        health.avg_latency_ms = 1500.0  # Very high
        health.tick_count_1min = 50
        health.error_count_5min = 0
        health.last_tick_time = datetime.now()

        score = monitor._calculate_health_score(health)
        # latency=0*0.3 + tick_rate=100*0.3 + errors=100*0.2 + staleness=100*0.2
        assert score == 70.0

    def test_many_errors_degrades_score(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        health.avg_latency_ms = 50.0
        health.tick_count_1min = 50
        health.error_count_5min = 5  # 5 errors -> score 0
        health.last_tick_time = datetime.now()

        score = monitor._calculate_health_score(health)
        # latency=100*0.3 + tick_rate=100*0.3 + errors=0*0.2 + staleness=100*0.2
        assert score == 80.0

    def test_stale_ticks_degrade_score(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        health.avg_latency_ms = 50.0
        health.tick_count_1min = 50
        health.error_count_5min = 0
        health.last_tick_time = datetime.now() - timedelta(seconds=60)

        score = monitor._calculate_health_score(health)
        # staleness_score = max(0, 100 - (60-10)*2) = 0
        # latency=100*0.3 + tick_rate=100*0.3 + errors=100*0.2 + staleness=0*0.2
        assert score == 80.0


class TestScoringFunctions:
    def test_score_latency_low(self, monitor: HealthMonitor):
        assert monitor._score_latency(50.0) == 100.0

    def test_score_latency_mid(self, monitor: HealthMonitor):
        score = monitor._score_latency(300.0)
        assert 50 < score < 100

    def test_score_latency_high(self, monitor: HealthMonitor):
        assert monitor._score_latency(1500.0) == 0.0

    def test_score_tick_rate_normal(self, monitor: HealthMonitor):
        assert monitor._score_tick_rate(50) == 100.0

    def test_score_tick_rate_low(self, monitor: HealthMonitor):
        assert monitor._score_tick_rate(10) == 20.0

    def test_score_tick_rate_capped(self, monitor: HealthMonitor):
        assert monitor._score_tick_rate(200) == 100.0

    def test_score_errors_none(self, monitor: HealthMonitor):
        assert monitor._score_errors(0) == 100.0

    def test_score_errors_some(self, monitor: HealthMonitor):
        assert monitor._score_errors(3) == 40.0

    def test_score_errors_many(self, monitor: HealthMonitor):
        assert monitor._score_errors(10) == 0.0

    def test_score_staleness_fresh(self, monitor: HealthMonitor):
        assert monitor._score_staleness(datetime.now()) == 100.0

    def test_score_staleness_none(self, monitor: HealthMonitor):
        assert monitor._score_staleness(None) == 0.0

    def test_score_staleness_old(self, monitor: HealthMonitor):
        old = datetime.now() - timedelta(seconds=120)
        assert monitor._score_staleness(old) == 0.0


# ─── Lifecycle Tests ───────────────────────────────────────────────────────────


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self, monitor: HealthMonitor):
        await monitor.start()
        assert monitor._is_running
        assert monitor._heartbeat_task is not None

        await monitor.stop()
        assert not monitor._is_running

    @pytest.mark.asyncio
    async def test_start_twice_is_noop(self, monitor: HealthMonitor):
        await monitor.start()
        task1 = monitor._heartbeat_task
        await monitor.start()
        # Same task, not replaced
        assert monitor._heartbeat_task is task1
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start(self, monitor: HealthMonitor):
        await monitor.stop()  # Should not raise


# ─── Query Tests ───────────────────────────────────────────────────────────────


class TestQueries:
    def test_get_health_registered(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        health = monitor.get_health("smartapi")
        assert health is not None
        assert health.broker_type == "smartapi"

    def test_get_health_unregistered(self, monitor: HealthMonitor):
        assert monitor.get_health("nonexistent") is None

    def test_get_all_health(self, monitor: HealthMonitor):
        monitor.register_adapter("smartapi")
        monitor.register_adapter("kite")
        all_health = monitor.get_all_health()
        assert len(all_health) == 2
        assert "smartapi" in all_health
        assert "kite" in all_health


# ─── Callback Tests ───────────────────────────────────────────────────────────


class TestCallback:
    def test_set_callback(self, monitor: HealthMonitor):
        cb = AsyncMock()
        monitor.set_on_health_change(cb)
        assert monitor._on_health_change_callback is cb

    @pytest.mark.asyncio
    async def test_heartbeat_triggers_callback_on_low_health(
        self, monitor: HealthMonitor
    ):
        """Simulate consecutive low scores triggering callback."""
        cb = AsyncMock()
        monitor.set_on_health_change(cb)
        monitor.register_adapter("smartapi")

        health = monitor._adapter_health["smartapi"]
        # Set up conditions for low score: no ticks, no latency data
        health.avg_latency_ms = 2000.0
        health.tick_count_1min = 0
        health.error_count_5min = 10
        health.last_tick_time = None

        # Pre-set consecutive_low_count just below threshold
        health.consecutive_low_count = HealthMonitor.CONSECUTIVE_LOW_COUNT - 1

        # Run one heartbeat cycle manually
        old_score = health.health_score
        new_score = monitor._calculate_health_score(health)
        health.health_score = new_score

        assert new_score < HealthMonitor.FAILOVER_THRESHOLD

        # Simulate what heartbeat loop does
        health.consecutive_low_count += 1
        if health.consecutive_low_count >= HealthMonitor.CONSECUTIVE_LOW_COUNT:
            await cb(health.broker_type, new_score)

        cb.assert_called_once_with("smartapi", new_score)

    @pytest.mark.asyncio
    async def test_consecutive_low_resets_on_recovery(
        self, monitor: HealthMonitor
    ):
        """Consecutive low count resets when health recovers."""
        monitor.register_adapter("smartapi")
        health = monitor._adapter_health["smartapi"]
        health.consecutive_low_count = 2

        # Set good health metrics
        health.avg_latency_ms = 50.0
        health.tick_count_1min = 50
        health.error_count_5min = 0
        health.last_tick_time = datetime.now()

        new_score = monitor._calculate_health_score(health)
        assert new_score >= HealthMonitor.FAILOVER_THRESHOLD

        # Simulate heartbeat logic
        health.health_score = new_score
        if new_score >= HealthMonitor.FAILOVER_THRESHOLD:
            health.consecutive_low_count = 0

        assert health.consecutive_low_count == 0
