"""
WebSocket Event Constants

Centralized WebSocket message types and actions.
This is the SINGLE SOURCE OF TRUTH for WebSocket-related constants.

Updated: 2025-12-21
"""

# =============================================================================
# CLIENT -> SERVER ACTIONS
# =============================================================================


class WSAction:
    """Client actions sent to the server."""

    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"


# =============================================================================
# SERVER -> CLIENT MESSAGE TYPES
# =============================================================================


class WSMessageType:
    """Server message types sent to the client."""

    CONNECTED = "connected"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    TICKS = "ticks"
    PONG = "pong"
    ERROR = "error"


# =============================================================================
# AUTOPILOT WEBSOCKET MESSAGE TYPES
# =============================================================================


class AutoPilotWSMessageType:
    """AutoPilot-specific WebSocket message types."""

    STRATEGY_UPDATE = "strategy_update"
    STRATEGY_STATUS_CHANGED = "strategy_status_changed"
    PNL_UPDATE = "pnl_update"
    CONDITION_EVALUATED = "condition_evaluated"
    CONDITIONS_MET = "conditions_met"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"
    RISK_ALERT = "risk_alert"
    DAILY_LIMIT_WARNING = "daily_limit_warning"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
    KILL_SWITCH_RESET = "kill_switch_reset"
    NOTIFICATION = "notification"
    CONFIRMATION_REQUEST = "confirmation_request"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    ADJUSTMENT_TRIGGERED = "adjustment_triggered"
    ADJUSTMENT_EXECUTED = "adjustment_executed"
    TRAILING_STOP_UPDATE = "trailing_stop_update"
    GREEKS_UPDATE = "greeks_update"
