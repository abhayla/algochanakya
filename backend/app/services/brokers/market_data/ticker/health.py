"""
HealthMonitor: Active health monitoring for ticker adapters.

Runs a 5-second heartbeat loop to track:
- Tick latency
- Tick rate (ticks per minute)
- Error rate
- Connection staleness

Triggers failover when health degrades below threshold.
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from app.services.brokers.market_data.ticker.token_policy import (
    RetryCategory,
    classify_auth_error,
)

logger = logging.getLogger(__name__)


@dataclass
class AdapterHealth:
    """Health metrics for a single adapter."""

    broker_type: str
    is_connected: bool = False
    health_score: float = 100.0  # 0-100

    # Metrics
    tick_count_1min: int = 0
    error_count_5min: int = 0
    avg_latency_ms: float = 0.0
    last_tick_time: Optional[datetime] = None

    # Consecutive low scores (for failover trigger)
    consecutive_low_count: int = 0

    # Historical tracking
    tick_timestamps: list = field(default_factory=list)
    error_timestamps: list = field(default_factory=list)
    latency_samples: list = field(default_factory=list)


class HealthMonitor:
    """
    Active health monitoring for all ticker adapters.

    Runs a 5-second heartbeat loop to calculate health scores and
    trigger failover when degradation detected.
    """

    # Health thresholds
    FAILOVER_THRESHOLD = 30  # Trigger failover if health < 30
    FAILBACK_THRESHOLD = 70  # Trigger failback if primary > 70
    CONSECUTIVE_LOW_COUNT = 3  # Require 3 consecutive low scores (15s total)

    def __init__(self) -> None:
        self._adapter_health: Dict[str, AdapterHealth] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._on_health_change_callback: Optional[
            Callable[[str, float], Awaitable[None]]
        ] = None
        self._is_running = False

    # ========== Registration ==========

    def register_adapter(self, broker_type: str) -> None:
        """Register adapter for health monitoring."""
        if broker_type not in self._adapter_health:
            self._adapter_health[broker_type] = AdapterHealth(broker_type=broker_type)
            logger.info("[HealthMonitor] Registered adapter: %s", broker_type)

    def unregister_adapter(self, broker_type: str) -> None:
        """Unregister adapter from health monitoring."""
        if broker_type in self._adapter_health:
            del self._adapter_health[broker_type]
            logger.info("[HealthMonitor] Unregistered adapter: %s", broker_type)

    # ========== Recording (called by pool/adapters) ==========

    def record_ticks(self, broker_type: str, count: int) -> None:
        """Record tick arrival."""
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        now = datetime.now()

        health.last_tick_time = now
        health.tick_timestamps.extend([now] * count)

        # Cleanup old timestamps (keep only last 1 minute)
        cutoff = now - timedelta(minutes=1)
        health.tick_timestamps = [
            ts for ts in health.tick_timestamps if ts > cutoff
        ]
        health.tick_count_1min = len(health.tick_timestamps)

    def record_error(self, broker_type: str, error: str) -> None:
        """Record error occurrence."""
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        now = datetime.now()

        health.error_timestamps.append(now)

        # Cleanup old timestamps (keep only last 5 minutes)
        cutoff = now - timedelta(minutes=5)
        health.error_timestamps = [
            ts for ts in health.error_timestamps if ts > cutoff
        ]
        health.error_count_5min = len(health.error_timestamps)

        logger.warning("[HealthMonitor] %s error: %s", broker_type, error)

    def record_disconnect(self, broker_type: str) -> None:
        """Record adapter disconnection."""
        if broker_type not in self._adapter_health:
            return

        self._adapter_health[broker_type].is_connected = False
        logger.warning("[HealthMonitor] %s disconnected", broker_type)

    def record_connect(self, broker_type: str) -> None:
        """Record adapter connection."""
        if broker_type not in self._adapter_health:
            return

        self._adapter_health[broker_type].is_connected = True
        logger.info("[HealthMonitor] %s connected", broker_type)

    def record_latency(self, broker_type: str, latency_ms: float) -> None:
        """Record tick latency sample."""
        if broker_type not in self._adapter_health:
            return

        health = self._adapter_health[broker_type]
        health.latency_samples.append(latency_ms)

        # Keep only last 20 samples
        if len(health.latency_samples) > 20:
            health.latency_samples.pop(0)

        health.avg_latency_ms = (
            sum(health.latency_samples) / len(health.latency_samples)
        )

    async def record_auth_failure(
        self, broker_type: str, error_code: str, error_msg: str
    ) -> None:
        """Record auth failure with classification-aware handling.

        NOT_RETRYABLE / NOT_REFRESHABLE → instant failover (health=0, callback)
        RETRYABLE / RETRYABLE_ONCE → gradual decay via record_error()
        """
        if broker_type not in self._adapter_health:
            return

        category = classify_auth_error(broker_type, error_code, error_msg)

        if category in (RetryCategory.NOT_RETRYABLE, RetryCategory.NOT_REFRESHABLE):
            # Instant failover: zero health, trigger callback immediately
            health = self._adapter_health[broker_type]
            health.health_score = 0.0
            health.consecutive_low_count = self.CONSECUTIVE_LOW_COUNT  # Skip gradual check

            logger.warning(
                "[HealthMonitor] %s auth failure (%s): %s %s — instant failover",
                broker_type, category.value, error_code, error_msg,
            )

            if self._on_health_change_callback:
                await self._on_health_change_callback(broker_type, 0.0)
        else:
            # Retryable — use gradual decay path
            self.record_error(broker_type, f"auth:{error_code}: {error_msg}")

    # ========== Health Queries ==========

    def get_health(self, broker_type: str) -> Optional[AdapterHealth]:
        """Get health metrics for specific broker."""
        return self._adapter_health.get(broker_type)

    def get_all_health(self) -> Dict[str, AdapterHealth]:
        """Get health metrics for all brokers."""
        return self._adapter_health.copy()

    # ========== Lifecycle ==========

    async def start(self) -> None:
        """Start health monitoring heartbeat loop."""
        if self._is_running:
            logger.warning("[HealthMonitor] Already running")
            return

        self._is_running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("[HealthMonitor] Started (5s heartbeat)")

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._is_running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        logger.info("[HealthMonitor] Stopped")

    # ========== Callback ==========

    def set_on_health_change(
        self, callback: Callable[[str, float], Awaitable[None]]
    ) -> None:
        """
        Set callback for health change events.

        Callback signature: async def callback(broker_type: str, health_score: float)
        """
        self._on_health_change_callback = callback
        logger.debug("[HealthMonitor] Health change callback set")

    # ========== Private: Heartbeat Loop ==========

    async def _heartbeat_loop(self) -> None:
        """5-second heartbeat loop to calculate health scores."""
        while self._is_running:
            try:
                await asyncio.sleep(5)

                for broker_type, health in self._adapter_health.items():
                    old_score = health.health_score
                    new_score = self._calculate_health_score(health)
                    health.health_score = new_score

                    # Log significant changes
                    if abs(new_score - old_score) > 10:
                        logger.info(
                            "[HealthMonitor] %s health: %.1f -> %.1f",
                            broker_type, old_score, new_score,
                        )

                    # Check for failover trigger
                    if new_score < self.FAILOVER_THRESHOLD:
                        health.consecutive_low_count += 1

                        if health.consecutive_low_count >= self.CONSECUTIVE_LOW_COUNT:
                            logger.warning(
                                "[HealthMonitor] %s health degraded: %.1f "
                                "(%d consecutive low)",
                                broker_type, new_score,
                                health.consecutive_low_count,
                            )

                            if self._on_health_change_callback:
                                await self._on_health_change_callback(
                                    broker_type, new_score
                                )
                    else:
                        health.consecutive_low_count = 0

            except asyncio.CancelledError:
                logger.info("[HealthMonitor] Heartbeat loop cancelled")
                break
            except Exception as e:
                logger.error("[HealthMonitor] Heartbeat loop error: %s", e)

    def _calculate_health_score(self, health: AdapterHealth) -> float:
        """
        Calculate health score (0-100) for adapter.

        Formula (from TICKER-DESIGN-SPEC):
        health_score = (
            latency_score      * 0.30 +    # 30%: Average tick latency
            tick_rate_score    * 0.30 +    # 30%: Ticks per minute
            error_score        * 0.20 +    # 20%: Error rate in last 5 min
            staleness_score    * 0.20      # 20%: Time since last tick
        )
        """
        latency_score = self._score_latency(health.avg_latency_ms)
        tick_rate_score = self._score_tick_rate(health.tick_count_1min)
        error_score = self._score_errors(health.error_count_5min)
        staleness_score = self._score_staleness(health.last_tick_time)

        health_score = (
            latency_score * 0.30
            + tick_rate_score * 0.30
            + error_score * 0.20
            + staleness_score * 0.20
        )

        return round(health_score, 1)

    def _score_latency(self, avg_latency_ms: float) -> float:
        """Score latency: 100 if <100ms, 50 if 100-500ms, 0 if >1000ms."""
        if avg_latency_ms < 100:
            return 100.0
        elif avg_latency_ms < 500:
            return 100 - ((avg_latency_ms - 100) / 400) * 50
        elif avg_latency_ms < 1000:
            return 50 - ((avg_latency_ms - 500) / 500) * 50
        else:
            return 0.0

    def _score_tick_rate(self, tick_count_1min: int) -> float:
        """Score tick rate: min(100, tick_count * 2). Expected ~50 ticks/min."""
        return min(100.0, tick_count_1min * 2)

    def _score_errors(self, error_count_5min: int) -> float:
        """Score errors: max(0, 100 - error_count * 20)."""
        return max(0.0, 100 - error_count_5min * 20)

    def _score_staleness(self, last_tick_time: Optional[datetime]) -> float:
        """Score staleness: 100 if <10s, decay after."""
        if last_tick_time is None:
            return 0.0

        seconds_since_last_tick = (datetime.now() - last_tick_time).total_seconds()

        if seconds_since_last_tick < 10:
            return 100.0
        else:
            return max(0.0, 100 - (seconds_since_last_tick - 10) * 2)
