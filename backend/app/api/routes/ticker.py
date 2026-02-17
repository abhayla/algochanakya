"""
Ticker system API endpoints.

Provides health status and failover diagnostics.
"""

from fastapi import APIRouter, Depends, Request
from typing import Dict, Any

from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/ticker", tags=["Ticker"])


@router.get("/health")
async def get_ticker_health(
    request: Request,
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get health status of all ticker adapters.

    Returns health scores, tick rates, error counts, and latency metrics
    for each registered broker adapter.
    """
    health_monitor = getattr(request.app.state, "ticker_health_monitor", None)
    if not health_monitor:
        return {"error": "Health monitor not initialized"}

    all_health = health_monitor.get_all_health()

    return {
        broker: {
            "broker_type": health.broker_type,
            "health_score": health.health_score,
            "is_connected": health.is_connected,
            "tick_count_1min": health.tick_count_1min,
            "error_count_5min": health.error_count_5min,
            "avg_latency_ms": round(health.avg_latency_ms, 2),
            "last_tick_time": (
                health.last_tick_time.isoformat()
                if health.last_tick_time
                else None
            ),
        }
        for broker, health in all_health.items()
    }


@router.get("/failover/status")
async def get_failover_status(
    request: Request,
    current_user=Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get failover controller status.

    Returns active broker, failover state, and broker configuration.
    """
    failover = getattr(request.app.state, "failover_controller", None)
    if not failover:
        return {"error": "Failover controller not initialized"}

    return failover.status()
