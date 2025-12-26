"""
WebSocket Health Monitor Service - Priority 4.1

Monitors WebSocket connection health and implements circuit breaker pattern
to pause AI trading when data quality is poor.

Key Features:
- Health scoring (0-100) based on latency, message rate, error rate
- Sync lag detection (stale data warning)
- Circuit breaker states: CLOSED (normal), OPEN (tripped), HALF_OPEN (testing)
- Integration with AI trading pause mechanism
- Real-time health status broadcasting

Circuit Breaker Thresholds:
- Health score < 30: OPEN (stop trading)
- Health score 30-60 for 30s: HALF_OPEN (test recovery)
- Health score > 60 for 60s: CLOSED (resume trading)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, Enum):
    """Circuit breaker states for WebSocket health."""
    CLOSED = "closed"       # Normal operation, trading allowed
    OPEN = "open"           # Tripped, trading paused
    HALF_OPEN = "half_open" # Testing recovery, limited trading


class HealthLevel(str, Enum):
    """Health level categories."""
    EXCELLENT = "excellent"   # 80-100
    GOOD = "good"             # 60-79
    DEGRADED = "degraded"     # 40-59
    POOR = "poor"             # 20-39
    CRITICAL = "critical"     # 0-19


@dataclass
class HealthMetrics:
    """Current health metrics snapshot."""
    # Core metrics
    health_score: float = 100.0
    health_level: HealthLevel = HealthLevel.EXCELLENT

    # Latency metrics (in milliseconds)
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    latency_score: float = 100.0

    # Message rate metrics
    messages_per_second: float = 0.0
    expected_messages_per_second: float = 1.0  # Minimum expected
    message_rate_score: float = 100.0

    # Error metrics
    error_count_last_minute: int = 0
    error_rate_per_minute: float = 0.0
    error_score: float = 100.0

    # Sync lag metrics
    last_tick_timestamp: Optional[datetime] = None
    sync_lag_seconds: float = 0.0
    sync_lag_score: float = 100.0
    is_data_stale: bool = False

    # Connection status
    is_connected: bool = False
    last_reconnect_at: Optional[datetime] = None
    reconnect_count_last_hour: int = 0

    # Circuit breaker
    circuit_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    circuit_state_changed_at: Optional[datetime] = None
    trading_allowed: bool = True

    # Timestamps
    calculated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HealthEvent:
    """Health state change event."""
    event_type: str  # "health_changed", "circuit_tripped", "circuit_recovered"
    old_state: str
    new_state: str
    reason: str
    metrics: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class WebSocketHealthMonitor:
    """
    Monitors WebSocket connection health and implements circuit breaker.

    Usage:
        monitor = WebSocketHealthMonitor()

        # Record metrics from kite_ticker
        monitor.record_tick_received(latency_ms=15)
        monitor.record_error("connection_lost")

        # Check if trading is allowed
        if monitor.is_trading_allowed():
            # Execute AI trading
            pass

        # Get current health status
        metrics = monitor.get_health_metrics()
    """

    # Thresholds
    STALE_DATA_THRESHOLD_SECONDS = 5.0  # Data older than 5s is stale
    CRITICAL_LAG_THRESHOLD_SECONDS = 30.0  # >30s = critical

    # Circuit breaker thresholds
    CIRCUIT_OPEN_THRESHOLD = 30  # Open circuit if health < 30
    CIRCUIT_HALF_OPEN_THRESHOLD = 50  # Test recovery if health 30-60
    CIRCUIT_CLOSE_THRESHOLD = 60  # Close circuit if health > 60
    CIRCUIT_RECOVERY_SECONDS = 30  # Time in HALF_OPEN before CLOSED
    CIRCUIT_TRIP_SECONDS = 10  # Time in degraded before OPEN

    # Scoring weights
    LATENCY_WEIGHT = 0.25
    MESSAGE_RATE_WEIGHT = 0.25
    ERROR_WEIGHT = 0.25
    SYNC_LAG_WEIGHT = 0.25

    # Latency thresholds (ms)
    EXCELLENT_LATENCY_MS = 50
    GOOD_LATENCY_MS = 100
    DEGRADED_LATENCY_MS = 500
    POOR_LATENCY_MS = 1000

    def __init__(
        self,
        window_size: int = 60,  # Rolling window in seconds
        on_circuit_change: Optional[Callable[[HealthEvent], None]] = None
    ):
        """
        Initialize health monitor.

        Args:
            window_size: Rolling window size for metrics (seconds)
            on_circuit_change: Callback when circuit breaker state changes
        """
        self.window_size = window_size
        self.on_circuit_change = on_circuit_change

        # Rolling windows for metrics
        self._latencies: deque = deque(maxlen=1000)  # (timestamp, latency_ms)
        self._errors: deque = deque(maxlen=100)  # (timestamp, error_type)
        self._ticks: deque = deque(maxlen=1000)  # (timestamp,)
        self._reconnects: deque = deque(maxlen=50)  # (timestamp,)

        # Current state
        self._is_connected = False
        self._last_tick_at: Optional[datetime] = None
        self._circuit_state = CircuitBreakerState.CLOSED
        self._circuit_state_changed_at = datetime.utcnow()
        self._degraded_since: Optional[datetime] = None
        self._recovering_since: Optional[datetime] = None

        # Event history
        self._events: deque = deque(maxlen=100)

        # Background task
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info("WebSocketHealthMonitor initialized")

    async def start(self):
        """Start the background health monitoring task."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("WebSocket health monitoring started")

    async def stop(self):
        """Stop the background monitoring task."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket health monitoring stopped")

    async def _monitoring_loop(self):
        """Background loop that evaluates health every second."""
        while self._running:
            try:
                await self._evaluate_health()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)

    # =========================================================================
    # Metric Recording Methods
    # =========================================================================

    def record_tick_received(self, latency_ms: float = 0):
        """
        Record that a tick was received.

        Args:
            latency_ms: Latency from expected time (optional)
        """
        now = datetime.utcnow()
        self._last_tick_at = now
        self._ticks.append((now,))

        if latency_ms > 0:
            self._latencies.append((now, latency_ms))

    def record_connection_status(self, is_connected: bool):
        """Record connection status change."""
        old_status = self._is_connected
        self._is_connected = is_connected

        if is_connected and not old_status:
            # Just reconnected
            self._reconnects.append((datetime.utcnow(),))
            logger.info("WebSocket reconnected")
        elif not is_connected and old_status:
            logger.warning("WebSocket disconnected")

    def record_error(self, error_type: str, message: str = ""):
        """
        Record a WebSocket error.

        Args:
            error_type: Type of error (connection_lost, parse_error, timeout, etc.)
            message: Optional error message
        """
        now = datetime.utcnow()
        self._errors.append((now, error_type))
        logger.warning(f"WebSocket error recorded: {error_type} - {message}")

    def record_latency(self, latency_ms: float):
        """Record a latency measurement."""
        self._latencies.append((datetime.utcnow(), latency_ms))

    # =========================================================================
    # Health Calculation
    # =========================================================================

    async def _evaluate_health(self):
        """Evaluate current health and update circuit breaker state."""
        metrics = self._calculate_metrics()

        # Update circuit breaker based on health score
        await self._update_circuit_breaker(metrics)

    def _calculate_metrics(self) -> HealthMetrics:
        """Calculate current health metrics."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_size)

        # Calculate latency score
        latency_score, avg_latency, max_latency = self._calculate_latency_score(window_start)

        # Calculate message rate score
        msg_rate_score, messages_per_second = self._calculate_message_rate_score(window_start)

        # Calculate error score
        error_score, error_count, error_rate = self._calculate_error_score(window_start)

        # Calculate sync lag score
        sync_lag_score, sync_lag_seconds, is_stale = self._calculate_sync_lag_score()

        # Calculate overall health score
        health_score = (
            latency_score * self.LATENCY_WEIGHT +
            msg_rate_score * self.MESSAGE_RATE_WEIGHT +
            error_score * self.ERROR_WEIGHT +
            sync_lag_score * self.SYNC_LAG_WEIGHT
        )

        # If disconnected, health is 0
        if not self._is_connected:
            health_score = 0

        # Determine health level
        health_level = self._score_to_level(health_score)

        # Get reconnect count
        hour_ago = now - timedelta(hours=1)
        reconnect_count = sum(1 for ts, in self._reconnects if ts > hour_ago)

        return HealthMetrics(
            health_score=round(health_score, 1),
            health_level=health_level,
            avg_latency_ms=round(avg_latency, 1),
            max_latency_ms=round(max_latency, 1),
            latency_score=round(latency_score, 1),
            messages_per_second=round(messages_per_second, 2),
            message_rate_score=round(msg_rate_score, 1),
            error_count_last_minute=error_count,
            error_rate_per_minute=round(error_rate, 2),
            error_score=round(error_score, 1),
            last_tick_timestamp=self._last_tick_at,
            sync_lag_seconds=round(sync_lag_seconds, 1),
            sync_lag_score=round(sync_lag_score, 1),
            is_data_stale=is_stale,
            is_connected=self._is_connected,
            last_reconnect_at=self._reconnects[-1][0] if self._reconnects else None,
            reconnect_count_last_hour=reconnect_count,
            circuit_state=self._circuit_state,
            circuit_state_changed_at=self._circuit_state_changed_at,
            trading_allowed=self._circuit_state == CircuitBreakerState.CLOSED,
            calculated_at=now
        )

    def _calculate_latency_score(self, window_start: datetime) -> tuple:
        """Calculate latency score (0-100)."""
        recent_latencies = [lat for ts, lat in self._latencies if ts > window_start]

        if not recent_latencies:
            return 100.0, 0.0, 0.0

        avg_latency = statistics.mean(recent_latencies)
        max_latency = max(recent_latencies)

        # Score based on average latency
        if avg_latency <= self.EXCELLENT_LATENCY_MS:
            score = 100
        elif avg_latency <= self.GOOD_LATENCY_MS:
            score = 80 + (self.GOOD_LATENCY_MS - avg_latency) / (self.GOOD_LATENCY_MS - self.EXCELLENT_LATENCY_MS) * 20
        elif avg_latency <= self.DEGRADED_LATENCY_MS:
            score = 50 + (self.DEGRADED_LATENCY_MS - avg_latency) / (self.DEGRADED_LATENCY_MS - self.GOOD_LATENCY_MS) * 30
        elif avg_latency <= self.POOR_LATENCY_MS:
            score = 20 + (self.POOR_LATENCY_MS - avg_latency) / (self.POOR_LATENCY_MS - self.DEGRADED_LATENCY_MS) * 30
        else:
            score = max(0, 20 - (avg_latency - self.POOR_LATENCY_MS) / 100)

        return score, avg_latency, max_latency

    def _calculate_message_rate_score(self, window_start: datetime) -> tuple:
        """Calculate message rate score (0-100)."""
        recent_ticks = sum(1 for ts, in self._ticks if ts > window_start)
        messages_per_second = recent_ticks / self.window_size if self.window_size > 0 else 0

        # During market hours, expect at least 1 tick/second
        # Score based on rate relative to expected
        if messages_per_second >= 1.0:
            score = 100
        elif messages_per_second >= 0.5:
            score = 70 + messages_per_second * 30
        elif messages_per_second >= 0.1:
            score = 30 + messages_per_second * 80
        else:
            score = messages_per_second * 300

        return min(100, score), messages_per_second

    def _calculate_error_score(self, window_start: datetime) -> tuple:
        """Calculate error score (0-100)."""
        minute_ago = datetime.utcnow() - timedelta(minutes=1)
        recent_errors = sum(1 for ts, _ in self._errors if ts > minute_ago)
        error_rate = recent_errors  # per minute

        # Score: 0 errors = 100, each error reduces score
        if recent_errors == 0:
            score = 100
        elif recent_errors <= 2:
            score = 80
        elif recent_errors <= 5:
            score = 50
        elif recent_errors <= 10:
            score = 20
        else:
            score = 0

        return score, recent_errors, error_rate

    def _calculate_sync_lag_score(self) -> tuple:
        """Calculate sync lag score (0-100)."""
        if self._last_tick_at is None:
            return 0, float('inf'), True

        now = datetime.utcnow()
        lag_seconds = (now - self._last_tick_at).total_seconds()
        is_stale = lag_seconds > self.STALE_DATA_THRESHOLD_SECONDS

        # Score based on lag
        if lag_seconds <= 1:
            score = 100
        elif lag_seconds <= self.STALE_DATA_THRESHOLD_SECONDS:
            score = 80 - (lag_seconds - 1) / (self.STALE_DATA_THRESHOLD_SECONDS - 1) * 30
        elif lag_seconds <= self.CRITICAL_LAG_THRESHOLD_SECONDS:
            score = 50 - (lag_seconds - self.STALE_DATA_THRESHOLD_SECONDS) / (
                self.CRITICAL_LAG_THRESHOLD_SECONDS - self.STALE_DATA_THRESHOLD_SECONDS) * 50
        else:
            score = 0

        return max(0, score), lag_seconds, is_stale

    def _score_to_level(self, score: float) -> HealthLevel:
        """Convert score to health level."""
        if score >= 80:
            return HealthLevel.EXCELLENT
        elif score >= 60:
            return HealthLevel.GOOD
        elif score >= 40:
            return HealthLevel.DEGRADED
        elif score >= 20:
            return HealthLevel.POOR
        else:
            return HealthLevel.CRITICAL

    # =========================================================================
    # Circuit Breaker Logic
    # =========================================================================

    async def _update_circuit_breaker(self, metrics: HealthMetrics):
        """Update circuit breaker state based on health metrics."""
        now = datetime.utcnow()
        old_state = self._circuit_state
        new_state = old_state
        reason = ""

        health_score = metrics.health_score

        if old_state == CircuitBreakerState.CLOSED:
            # Check if we need to trip the circuit
            if health_score < self.CIRCUIT_OPEN_THRESHOLD:
                if self._degraded_since is None:
                    self._degraded_since = now
                elif (now - self._degraded_since).total_seconds() >= self.CIRCUIT_TRIP_SECONDS:
                    new_state = CircuitBreakerState.OPEN
                    reason = f"Health score {health_score:.1f} below threshold for {self.CIRCUIT_TRIP_SECONDS}s"
                    self._degraded_since = None
            else:
                self._degraded_since = None

        elif old_state == CircuitBreakerState.OPEN:
            # Check if we can start recovery
            if health_score >= self.CIRCUIT_HALF_OPEN_THRESHOLD:
                new_state = CircuitBreakerState.HALF_OPEN
                reason = f"Health score {health_score:.1f} recovered above {self.CIRCUIT_HALF_OPEN_THRESHOLD}"
                self._recovering_since = now

        elif old_state == CircuitBreakerState.HALF_OPEN:
            if health_score < self.CIRCUIT_OPEN_THRESHOLD:
                # Failed recovery test
                new_state = CircuitBreakerState.OPEN
                reason = f"Recovery failed - health dropped to {health_score:.1f}"
                self._recovering_since = None
            elif health_score >= self.CIRCUIT_CLOSE_THRESHOLD:
                if self._recovering_since is None:
                    self._recovering_since = now
                elif (now - self._recovering_since).total_seconds() >= self.CIRCUIT_RECOVERY_SECONDS:
                    new_state = CircuitBreakerState.CLOSED
                    reason = f"Health stable at {health_score:.1f} for {self.CIRCUIT_RECOVERY_SECONDS}s"
                    self._recovering_since = None

        # Apply state change
        if new_state != old_state:
            await self._change_circuit_state(old_state, new_state, reason, metrics)

    async def _change_circuit_state(
        self,
        old_state: CircuitBreakerState,
        new_state: CircuitBreakerState,
        reason: str,
        metrics: HealthMetrics
    ):
        """Change circuit breaker state and notify."""
        self._circuit_state = new_state
        self._circuit_state_changed_at = datetime.utcnow()

        # Determine event type
        if new_state == CircuitBreakerState.OPEN:
            event_type = "circuit_tripped"
        elif new_state == CircuitBreakerState.CLOSED:
            event_type = "circuit_recovered"
        else:
            event_type = "circuit_testing"

        event = HealthEvent(
            event_type=event_type,
            old_state=old_state.value,
            new_state=new_state.value,
            reason=reason,
            metrics={
                "health_score": metrics.health_score,
                "latency_ms": metrics.avg_latency_ms,
                "sync_lag_s": metrics.sync_lag_seconds,
                "is_connected": metrics.is_connected
            }
        )

        self._events.append(event)

        # Log the change
        log_level = logging.WARNING if new_state == CircuitBreakerState.OPEN else logging.INFO
        logger.log(log_level, f"Circuit breaker: {old_state.value} -> {new_state.value}. {reason}")

        # Notify callback
        if self.on_circuit_change:
            try:
                if asyncio.iscoroutinefunction(self.on_circuit_change):
                    await self.on_circuit_change(event)
                else:
                    self.on_circuit_change(event)
            except Exception as e:
                logger.error(f"Error in circuit change callback: {e}")

    # =========================================================================
    # Public API
    # =========================================================================

    def is_trading_allowed(self) -> bool:
        """Check if AI trading is allowed based on circuit breaker state."""
        return self._circuit_state == CircuitBreakerState.CLOSED

    def get_circuit_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._circuit_state

    def get_health_metrics(self) -> HealthMetrics:
        """Get current health metrics snapshot."""
        return self._calculate_metrics()

    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for API response."""
        metrics = self._calculate_metrics()
        return {
            "health_score": metrics.health_score,
            "health_level": metrics.health_level.value,
            "circuit_state": metrics.circuit_state.value,
            "trading_allowed": metrics.trading_allowed,
            "is_connected": metrics.is_connected,
            "is_data_stale": metrics.is_data_stale,
            "sync_lag_seconds": metrics.sync_lag_seconds,
            "avg_latency_ms": metrics.avg_latency_ms,
            "messages_per_second": metrics.messages_per_second,
            "error_count_last_minute": metrics.error_count_last_minute,
            "reconnect_count_last_hour": metrics.reconnect_count_last_hour,
            "circuit_state_changed_at": metrics.circuit_state_changed_at.isoformat() if metrics.circuit_state_changed_at else None,
            "calculated_at": metrics.calculated_at.isoformat()
        }

    def get_recent_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent health events."""
        events = list(self._events)[-limit:]
        return [
            {
                "event_type": e.event_type,
                "old_state": e.old_state,
                "new_state": e.new_state,
                "reason": e.reason,
                "metrics": e.metrics,
                "timestamp": e.timestamp.isoformat()
            }
            for e in events
        ]

    async def force_circuit_open(self, reason: str = "Manual trigger"):
        """Manually trip the circuit breaker."""
        if self._circuit_state != CircuitBreakerState.OPEN:
            metrics = self._calculate_metrics()
            await self._change_circuit_state(
                self._circuit_state,
                CircuitBreakerState.OPEN,
                f"Manual: {reason}",
                metrics
            )

    async def force_circuit_close(self, reason: str = "Manual reset"):
        """Manually reset the circuit breaker."""
        if self._circuit_state != CircuitBreakerState.CLOSED:
            metrics = self._calculate_metrics()
            await self._change_circuit_state(
                self._circuit_state,
                CircuitBreakerState.CLOSED,
                f"Manual: {reason}",
                metrics
            )


# Singleton instance
_health_monitor: Optional[WebSocketHealthMonitor] = None


def get_health_monitor() -> WebSocketHealthMonitor:
    """Get or create the singleton health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = WebSocketHealthMonitor()
    return _health_monitor


async def initialize_health_monitor(
    on_circuit_change: Optional[Callable] = None
) -> WebSocketHealthMonitor:
    """Initialize and start the health monitor."""
    global _health_monitor
    _health_monitor = WebSocketHealthMonitor(on_circuit_change=on_circuit_change)
    await _health_monitor.start()
    return _health_monitor
