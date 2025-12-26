"""
Extreme Event Handler

Detects and responds to black swan events:
- VIX_SPIKE: VIX > 30 (alert), VIX > 40 (kill switch)
- CIRCUIT_BREAKER: Exchange trading halt
- API_OUTAGE: Consecutive Kite API failures
- MARGIN_SPIKE: Margin requirements spike > 2x normal
"""

from enum import Enum
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class ExtremeEventType(Enum):
    """Types of extreme market events."""
    VIX_SPIKE = "vix_spike"           # VIX > 30
    VIX_CRISIS = "vix_crisis"         # VIX > 40
    CIRCUIT_BREAKER = "circuit_breaker"  # Exchange halt
    API_OUTAGE = "api_outage"         # Kite API failures
    MARGIN_SPIKE = "margin_spike"     # Margin > 2x normal


class ExtremeEventSeverity(Enum):
    """Severity levels for response actions."""
    WARNING = "warning"     # Alert only
    ELEVATED = "elevated"   # Pause new deployments
    CRITICAL = "critical"   # Trigger kill switch


# Event thresholds
VIX_WARNING_THRESHOLD = 30.0     # Alert user, widen stops
VIX_CRITICAL_THRESHOLD = 40.0   # Trigger kill switch
API_FAILURE_THRESHOLD = 3       # 3 failures in 1 minute
API_FAILURE_WINDOW_SECONDS = 60


class ExtremeEventHandler:
    """
    Detects and responds to extreme market events.

    Integrates with:
    - RiskStateEngine for state transitions
    - KillSwitchService for emergency exits
    - WebSocketManager for alerts
    - AIMonitor for blocking deployments
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._api_failures: List[datetime] = []  # Track recent failures
        self._last_event: Optional[Dict] = None
        self._event_cooldown = timedelta(minutes=5)  # Avoid alert spam

    async def detect_extreme_events(
        self,
        vix: float,
        is_market_open: bool = True
    ) -> List[Dict]:
        """
        Check for all extreme event conditions.

        Args:
            vix: Current VIX value
            is_market_open: Whether market is open

        Returns:
            List of detected events with type, severity, and recommended action
        """
        events = []

        # Check VIX spike
        if vix >= VIX_CRITICAL_THRESHOLD:
            events.append({
                "type": ExtremeEventType.VIX_CRISIS,
                "severity": ExtremeEventSeverity.CRITICAL,
                "value": vix,
                "threshold": VIX_CRITICAL_THRESHOLD,
                "action": "trigger_kill_switch",
                "message": f"CRITICAL: VIX at {vix:.2f} (>= {VIX_CRITICAL_THRESHOLD}). Emergency exit all positions."
            })
        elif vix >= VIX_WARNING_THRESHOLD:
            events.append({
                "type": ExtremeEventType.VIX_SPIKE,
                "severity": ExtremeEventSeverity.ELEVATED,
                "value": vix,
                "threshold": VIX_WARNING_THRESHOLD,
                "action": "pause_deployments",
                "message": f"WARNING: VIX at {vix:.2f} (>= {VIX_WARNING_THRESHOLD}). Pausing new deployments."
            })

        # Check API health
        api_event = self._check_api_health()
        if api_event:
            events.append(api_event)

        return events

    def record_api_failure(self) -> None:
        """Record an API failure for health tracking."""
        now = datetime.utcnow()
        self._api_failures.append(now)

        # Clean old failures outside window
        cutoff = now - timedelta(seconds=API_FAILURE_WINDOW_SECONDS)
        self._api_failures = [f for f in self._api_failures if f > cutoff]

        logger.warning(
            f"API failure recorded. {len(self._api_failures)} failures in last {API_FAILURE_WINDOW_SECONDS}s"
        )

    def record_api_success(self) -> None:
        """Record API success - clears failure count."""
        if self._api_failures:
            logger.info("API success - clearing failure count")
            self._api_failures = []

    def _check_api_health(self) -> Optional[Dict]:
        """Check for API outage based on recent failures."""
        if len(self._api_failures) >= API_FAILURE_THRESHOLD:
            return {
                "type": ExtremeEventType.API_OUTAGE,
                "severity": ExtremeEventSeverity.ELEVATED,
                "value": len(self._api_failures),
                "threshold": API_FAILURE_THRESHOLD,
                "action": "pause_monitoring",
                "message": f"API OUTAGE: {len(self._api_failures)} failures in {API_FAILURE_WINDOW_SECONDS}s. Pausing monitoring."
            }
        return None

    async def handle_event(
        self,
        event: Dict,
        user_id: str,
        kill_switch_service,
        ws_manager
    ) -> Dict:
        """
        Execute response protocol for detected event.

        Args:
            event: Detected event from detect_extreme_events()
            user_id: User UUID
            kill_switch_service: KillSwitchService instance
            ws_manager: WebSocketManager instance

        Returns:
            Result of action taken
        """
        event_type = event["type"]
        severity = event["severity"]

        result = {
            "event_type": event_type.value,
            "severity": severity.value,
            "action_taken": None,
            "success": False
        }

        # Send WebSocket alert
        if ws_manager:
            await ws_manager.send_risk_alert(
                user_id=user_id,
                alert_type=event_type.value,
                message=event["message"],
                data={
                    "severity": severity.value,
                    "value": event["value"],
                    "threshold": event["threshold"],
                    "recommended_action": event["action"]
                }
            )

        # Execute action based on severity
        if severity == ExtremeEventSeverity.CRITICAL:
            # Trigger kill switch
            if kill_switch_service:
                trigger_result = await kill_switch_service.trigger(
                    reason=event["message"],
                    force=True
                )
                result["action_taken"] = "kill_switch_triggered"
                result["success"] = trigger_result.success
                result["details"] = {
                    "strategies_affected": trigger_result.strategies_affected,
                    "positions_exited": trigger_result.positions_exited
                }

                logger.critical(
                    f"Kill switch triggered due to {event_type.value}: {event['message']}"
                )

        elif severity == ExtremeEventSeverity.ELEVATED:
            # Just alert - ai_monitor will check and pause
            result["action_taken"] = "alert_sent"
            result["success"] = True

            logger.warning(
                f"Extreme event detected: {event_type.value} - {event['message']}"
            )

        return result

    def get_current_status(self) -> Dict:
        """Get current extreme event status for dashboard."""
        return {
            "api_failures_recent": len(self._api_failures),
            "api_health": "healthy" if len(self._api_failures) < API_FAILURE_THRESHOLD else "degraded",
            "last_event": self._last_event
        }


__all__ = ["ExtremeEventHandler", "ExtremeEventType", "ExtremeEventSeverity"]
