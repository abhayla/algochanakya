"""
WebSocket Health API Endpoints - Priority 4.1

Provides endpoints for monitoring WebSocket connection health,
circuit breaker status, and manual controls.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel

from app.models import User
from app.utils.dependencies import get_current_user
from app.services.ai.websocket_health_monitor import (
    get_health_monitor,
    CircuitBreakerState,
    HealthLevel
)

router = APIRouter(prefix="/websocket-health", tags=["AI WebSocket Health"])


class HealthStatusResponse(BaseModel):
    """Response model for health status."""
    health_score: float
    health_level: str
    circuit_state: str
    trading_allowed: bool
    is_connected: bool
    is_data_stale: bool
    sync_lag_seconds: float
    avg_latency_ms: float
    messages_per_second: float
    error_count_last_minute: int
    reconnect_count_last_hour: int
    circuit_state_changed_at: str | None
    calculated_at: str


class HealthEventResponse(BaseModel):
    """Response model for health events."""
    event_type: str
    old_state: str
    new_state: str
    reason: str
    metrics: Dict[str, Any]
    timestamp: str


class CircuitControlRequest(BaseModel):
    """Request model for circuit breaker control."""
    reason: str = "Manual control"


class CircuitControlResponse(BaseModel):
    """Response model for circuit breaker control."""
    success: bool
    circuit_state: str
    message: str


@router.get("/status", response_model=HealthStatusResponse)
async def get_health_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current WebSocket health status.

    Returns health score, circuit breaker state, connection status,
    and various metrics.

    Health Levels:
    - EXCELLENT (80-100): Optimal performance
    - GOOD (60-79): Normal operation
    - DEGRADED (40-59): Some issues detected
    - POOR (20-39): Significant problems
    - CRITICAL (0-19): Trading paused

    Circuit States:
    - CLOSED: Normal operation, AI trading allowed
    - OPEN: Circuit tripped, AI trading paused
    - HALF_OPEN: Testing recovery
    """
    monitor = get_health_monitor()
    return monitor.get_health_summary()


@router.get("/events", response_model=List[HealthEventResponse])
async def get_health_events(
    limit: int = 20,
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get recent health state change events.

    Events include circuit breaker trips, recoveries, and health
    level changes.
    """
    if limit < 1 or limit > 100:
        limit = 20

    monitor = get_health_monitor()
    return monitor.get_recent_events(limit)


@router.get("/trading-allowed")
async def check_trading_allowed(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Quick check if AI trading is currently allowed.

    Returns:
        allowed: True if trading is permitted
        circuit_state: Current circuit breaker state
        reason: Reason if trading is not allowed
    """
    monitor = get_health_monitor()
    allowed = monitor.is_trading_allowed()
    state = monitor.get_circuit_state()

    reason = ""
    if not allowed:
        if state == CircuitBreakerState.OPEN:
            reason = "Circuit breaker tripped due to poor WebSocket health"
        elif state == CircuitBreakerState.HALF_OPEN:
            reason = "Circuit breaker in recovery testing mode"

    return {
        "allowed": allowed,
        "circuit_state": state.value,
        "reason": reason
    }


@router.post("/circuit/open", response_model=CircuitControlResponse)
async def trip_circuit_breaker(
    request: CircuitControlRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually trip the circuit breaker to pause AI trading.

    Use this in emergencies to immediately stop all AI trading
    regardless of current health metrics.
    """
    monitor = get_health_monitor()

    if monitor.get_circuit_state() == CircuitBreakerState.OPEN:
        return {
            "success": False,
            "circuit_state": CircuitBreakerState.OPEN.value,
            "message": "Circuit breaker is already open"
        }

    await monitor.force_circuit_open(reason=request.reason)

    return {
        "success": True,
        "circuit_state": CircuitBreakerState.OPEN.value,
        "message": f"Circuit breaker tripped: {request.reason}"
    }


@router.post("/circuit/close", response_model=CircuitControlResponse)
async def reset_circuit_breaker(
    request: CircuitControlRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually reset the circuit breaker to allow AI trading.

    Use with caution - only reset when you've verified the
    underlying issues have been resolved.
    """
    monitor = get_health_monitor()

    if monitor.get_circuit_state() == CircuitBreakerState.CLOSED:
        return {
            "success": False,
            "circuit_state": CircuitBreakerState.CLOSED.value,
            "message": "Circuit breaker is already closed"
        }

    await monitor.force_circuit_close(reason=request.reason)

    return {
        "success": True,
        "circuit_state": CircuitBreakerState.CLOSED.value,
        "message": f"Circuit breaker reset: {request.reason}"
    }


@router.get("/thresholds")
async def get_health_thresholds(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current health monitoring thresholds.

    Returns the configuration values used for health scoring
    and circuit breaker decisions.
    """
    from app.services.ai.websocket_health_monitor import WebSocketHealthMonitor

    return {
        "stale_data_threshold_seconds": WebSocketHealthMonitor.STALE_DATA_THRESHOLD_SECONDS,
        "critical_lag_threshold_seconds": WebSocketHealthMonitor.CRITICAL_LAG_THRESHOLD_SECONDS,
        "circuit_open_threshold": WebSocketHealthMonitor.CIRCUIT_OPEN_THRESHOLD,
        "circuit_half_open_threshold": WebSocketHealthMonitor.CIRCUIT_HALF_OPEN_THRESHOLD,
        "circuit_close_threshold": WebSocketHealthMonitor.CIRCUIT_CLOSE_THRESHOLD,
        "circuit_recovery_seconds": WebSocketHealthMonitor.CIRCUIT_RECOVERY_SECONDS,
        "latency_thresholds_ms": {
            "excellent": WebSocketHealthMonitor.EXCELLENT_LATENCY_MS,
            "good": WebSocketHealthMonitor.GOOD_LATENCY_MS,
            "degraded": WebSocketHealthMonitor.DEGRADED_LATENCY_MS,
            "poor": WebSocketHealthMonitor.POOR_LATENCY_MS
        },
        "scoring_weights": {
            "latency": WebSocketHealthMonitor.LATENCY_WEIGHT,
            "message_rate": WebSocketHealthMonitor.MESSAGE_RATE_WEIGHT,
            "error": WebSocketHealthMonitor.ERROR_WEIGHT,
            "sync_lag": WebSocketHealthMonitor.SYNC_LAG_WEIGHT
        }
    }
