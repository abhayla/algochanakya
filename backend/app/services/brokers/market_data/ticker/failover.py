"""
FailoverController: Automatic broker failover with make-before-break pattern.

Responsibilities:
- Listen to HealthMonitor for degraded health
- Execute failover (primary -> secondary) with make-before-break
- Execute failback (secondary -> primary) when primary recovers
- Flap prevention (120s cooldown between events)
"""

import asyncio
import logging
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from app.constants.brokers import ORG_ACTIVE_BROKERS

if TYPE_CHECKING:
    from app.services.brokers.market_data.ticker.pool import TickerPool
    from app.services.brokers.market_data.ticker.router import TickerRouter
    from app.services.brokers.market_data.ticker.health import HealthMonitor

logger = logging.getLogger(__name__)


class FailoverController:
    """
    Automatic broker failover controller.

    Pattern: Make-before-break
    1. Connect + subscribe on secondary
    2. Wait 2s overlap (both adapters active)
    3. Switch user routing
    4. Unsubscribe + cleanup primary
    """

    # Configuration
    FAILOVER_THRESHOLD = 30  # Trigger failover if health < 30
    FAILBACK_THRESHOLD = 70  # Trigger failback if primary > 70
    FAILBACK_SUSTAINED_SECONDS = 60  # Primary must be healthy for 60s
    FLAP_PREVENTION_SECONDS = 120  # Min 120s between failover events

    def __init__(
        self,
        primary_broker: str = ORG_ACTIVE_BROKERS[0],
        secondary_broker: str = ORG_ACTIVE_BROKERS[1] if len(ORG_ACTIVE_BROKERS) > 1 else ORG_ACTIVE_BROKERS[0],
    ) -> None:
        self.primary_broker = primary_broker
        self.secondary_broker = secondary_broker
        self.active_broker = primary_broker
        self.is_failed_over = False

        # Dependencies (injected via set_dependencies)
        self._pool: Optional["TickerPool"] = None
        self._router: Optional["TickerRouter"] = None
        self._health_monitor: Optional["HealthMonitor"] = None

        # Failover tracking
        self._last_failover_time: Optional[datetime] = None
        self._primary_healthy_since: Optional[datetime] = None
        self._failback_task: Optional[asyncio.Task] = None

    # ========== Dependency Injection ==========

    def set_dependencies(
        self,
        pool: "TickerPool",
        router: "TickerRouter",
        health_monitor: "HealthMonitor",
    ) -> None:
        """Set dependencies and register health change callback."""
        self._pool = pool
        self._router = router
        self._health_monitor = health_monitor

        health_monitor.set_on_health_change(self._on_health_degraded)

        logger.info(
            "[FailoverController] Initialized: primary=%s, secondary=%s",
            self.primary_broker, self.secondary_broker,
        )

    # ========== Health Callback ==========

    async def _on_health_degraded(
        self, broker_type: str, health_score: float
    ) -> None:
        """Callback when adapter health degrades."""
        # Only act on the active broker
        if broker_type != self.active_broker:
            logger.debug(
                "[FailoverController] Health degraded for %s, "
                "but not active broker (active=%s)",
                broker_type, self.active_broker,
            )
            return

        # Flap prevention
        if self._last_failover_time:
            seconds_since_last = (
                datetime.now() - self._last_failover_time
            ).total_seconds()
            if seconds_since_last < self.FLAP_PREVENTION_SECONDS:
                logger.warning(
                    "[FailoverController] Flap prevention: Only %.0fs "
                    "since last failover (need %ds)",
                    seconds_since_last, self.FLAP_PREVENTION_SECONDS,
                )
                return

        # Execute failover
        if broker_type == self.primary_broker:
            await self._execute_failover(
                self.primary_broker, self.secondary_broker
            )
        elif broker_type == self.secondary_broker and self.is_failed_over:
            logger.error(
                "[FailoverController] Secondary %s also degraded! "
                "No more failover options.",
                self.secondary_broker,
            )

    # ========== Failover Execution ==========

    async def _execute_failover(
        self, from_broker: str, to_broker: str
    ) -> None:
        """Execute failover with make-before-break pattern."""
        logger.warning(
            "[FailoverController] Executing failover: %s -> %s",
            from_broker, to_broker,
        )

        try:
            # Step 1: Migrate subscriptions (make-before-break)
            await self._pool.migrate_subscriptions(from_broker, to_broker)

            # Step 2: Switch user routing
            await self._router.switch_users_broker(from_broker, to_broker)

            # Step 3: Update state
            self.active_broker = to_broker
            self.is_failed_over = True
            self._last_failover_time = datetime.now()

            logger.warning(
                "[FailoverController] Failover complete: %s -> %s",
                from_broker, to_broker,
            )

            # Start monitoring for failback
            if from_broker == self.primary_broker:
                self._failback_task = asyncio.create_task(
                    self._monitor_failback()
                )

        except Exception as e:
            logger.error("[FailoverController] Failover failed: %s", e)

    async def _monitor_failback(self) -> None:
        """
        Monitor primary broker health for failback opportunity.

        Failback when primary health > 70 sustained for 60s.
        """
        logger.info(
            "[FailoverController] Monitoring for failback opportunity..."
        )

        while self.is_failed_over:
            await asyncio.sleep(10)  # Check every 10s

            primary_health = self._health_monitor.get_health(
                self.primary_broker
            )
            if not primary_health:
                continue

            if primary_health.health_score >= self.FAILBACK_THRESHOLD:
                # Track sustained healthy period
                if self._primary_healthy_since is None:
                    self._primary_healthy_since = datetime.now()
                    logger.info(
                        "[FailoverController] Primary %s recovering "
                        "(health=%.1f)",
                        self.primary_broker,
                        primary_health.health_score,
                    )

                healthy_duration = (
                    datetime.now() - self._primary_healthy_since
                ).total_seconds()
                if healthy_duration >= self.FAILBACK_SUSTAINED_SECONDS:
                    logger.info(
                        "[FailoverController] Primary healthy for %.0fs, "
                        "executing failback",
                        healthy_duration,
                    )
                    await self._execute_failback()
                    break
            else:
                self._primary_healthy_since = None

    async def _execute_failback(self) -> None:
        """Execute failback (secondary -> primary)."""
        logger.warning(
            "[FailoverController] Executing failback: %s -> %s",
            self.secondary_broker, self.primary_broker,
        )

        try:
            await self._pool.migrate_subscriptions(
                self.secondary_broker, self.primary_broker
            )
            await self._router.switch_users_broker(
                self.secondary_broker, self.primary_broker
            )

            self.active_broker = self.primary_broker
            self.is_failed_over = False
            self._last_failover_time = datetime.now()
            self._primary_healthy_since = None

            logger.warning(
                "[FailoverController] Failback complete: %s -> %s",
                self.secondary_broker, self.primary_broker,
            )

        except Exception as e:
            logger.error("[FailoverController] Failback failed: %s", e)

    # ========== Lifecycle ==========

    async def stop(self) -> None:
        """Cancel failback monitoring task if running."""
        if self._failback_task and not self._failback_task.done():
            self._failback_task.cancel()
            try:
                await self._failback_task
            except asyncio.CancelledError:
                pass
        logger.info("[FailoverController] Stopped")

    # ========== Status ==========

    def status(self) -> dict:
        """Get failover controller status."""
        return {
            "active_broker": self.active_broker,
            "is_failed_over": self.is_failed_over,
            "primary_broker": self.primary_broker,
            "secondary_broker": self.secondary_broker,
            "last_failover_time": (
                self._last_failover_time.isoformat()
                if self._last_failover_time
                else None
            ),
        }
