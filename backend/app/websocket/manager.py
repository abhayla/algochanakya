"""
WebSocket Manager

Manages WebSocket connections for real-time updates.
Broadcasts strategy updates, P&L changes, and notifications.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    # Connection
    CONNECTED = "connected"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

    # Strategy updates
    STRATEGY_UPDATE = "strategy_update"
    STRATEGY_STATUS_CHANGED = "strategy_status_changed"

    # Order updates
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_REJECTED = "order_rejected"

    # P&L updates
    PNL_UPDATE = "pnl_update"

    # Condition updates
    CONDITION_EVALUATED = "condition_evaluated"
    CONDITIONS_MET = "conditions_met"

    # Risk alerts
    RISK_ALERT = "risk_alert"
    DAILY_LIMIT_WARNING = "daily_limit_warning"

    # System
    MARKET_STATUS = "market_status"
    HEARTBEAT = "heartbeat"
    SYSTEM_ALERT = "system_alert"

    # Phase 3: Kill Switch
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
    KILL_SWITCH_RESET = "kill_switch_reset"

    # Phase 3: Confirmations (Semi-Auto Mode)
    CONFIRMATION_REQUEST = "confirmation_request"
    CONFIRMATION_EXPIRED = "confirmation_expired"
    CONFIRMATION_RESOLVED = "confirmation_resolved"

    # Phase 3: Adjustments
    ADJUSTMENT_TRIGGERED = "adjustment_triggered"
    ADJUSTMENT_EXECUTED = "adjustment_executed"

    # Phase 3: Trailing Stop
    TRAILING_STOP_UPDATE = "trailing_stop_update"
    TRAILING_STOP_TRIGGERED = "trailing_stop_triggered"

    # Phase 3: Greeks
    GREEKS_UPDATE = "greeks_update"


@dataclass
class WSMessage:
    """WebSocket message structure."""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_json(self) -> str:
        return json.dumps({
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "data": self.data,
            "timestamp": self.timestamp
        })


class ConnectionManager:
    """
    Manages WebSocket connections.

    Features:
    - Per-user connection tracking
    - Broadcast to all users
    - Broadcast to specific user
    - Heartbeat mechanism
    - Auto-reconnection handling
    """

    def __init__(self):
        # user_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        # WebSocket -> user_id mapping
        self._ws_to_user: Dict[WebSocket, str] = {}
        # Strategy subscriptions: user_id -> set of strategy_ids
        self._subscriptions: Dict[str, Set[int]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            user_id: User ID

        Returns:
            True if connection successful
        """
        try:
            await websocket.accept()

            async with self._lock:
                if user_id not in self._connections:
                    self._connections[user_id] = set()
                self._connections[user_id].add(websocket)
                self._ws_to_user[websocket] = user_id

            logger.info(f"WebSocket connected for user {user_id}")

            # Send connected message
            await self.send_to_connection(
                websocket,
                WSMessage(
                    type=MessageType.CONNECTED,
                    data={"user_id": user_id, "message": "Connected to AutoPilot"}
                )
            )

            return True

        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            return False

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            user_id = self._ws_to_user.pop(websocket, None)
            if user_id and user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
                    # Also clean up subscriptions
                    self._subscriptions.pop(user_id, None)

        logger.info(f"WebSocket disconnected for user {user_id}")

    async def subscribe_to_strategy(self, user_id: str, strategy_id: int):
        """Subscribe user to strategy updates."""
        async with self._lock:
            if user_id not in self._subscriptions:
                self._subscriptions[user_id] = set()
            self._subscriptions[user_id].add(strategy_id)

    async def unsubscribe_from_strategy(self, user_id: str, strategy_id: int):
        """Unsubscribe user from strategy updates."""
        async with self._lock:
            if user_id in self._subscriptions:
                self._subscriptions[user_id].discard(strategy_id)

    def is_subscribed(self, user_id: str, strategy_id: int) -> bool:
        """Check if user is subscribed to strategy."""
        return strategy_id in self._subscriptions.get(user_id, set())

    async def send_to_user(self, user_id: str, message: WSMessage):
        """Send message to all connections of a specific user."""
        async with self._lock:
            connections = self._connections.get(user_id, set()).copy()

        for websocket in connections:
            await self.send_to_connection(websocket, message)

    async def send_to_connection(self, websocket: WebSocket, message: WSMessage):
        """Send message to a specific WebSocket connection."""
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message.to_json())
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            await self.disconnect(websocket)

    async def broadcast(self, message: WSMessage, user_ids: Optional[List[str]] = None):
        """
        Broadcast message to multiple users.

        Args:
            message: Message to broadcast
            user_ids: List of user IDs. If None, broadcast to all.
        """
        async with self._lock:
            if user_ids is None:
                targets = list(self._connections.keys())
            else:
                targets = user_ids

        for user_id in targets:
            await self.send_to_user(user_id, message)

    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs."""
        return list(self._connections.keys())

    def get_connection_count(self, user_id: str) -> int:
        """Get number of connections for a user."""
        return len(self._connections.get(user_id, set()))

    def get_total_connections(self) -> int:
        """Get total number of WebSocket connections."""
        return sum(len(conns) for conns in self._connections.values())

    # ========================================================================
    # Convenience methods for specific message types
    # ========================================================================

    async def send_strategy_update(
        self,
        user_id: str,
        strategy_id: int,
        update_type: str = None,
        data: Dict[str, Any] = None,
        **updates
    ):
        """
        Send strategy update to user.

        Can be called with either:
        - send_strategy_update(user_id, strategy_id, updates={"key": "value"})
        - send_strategy_update(user_id, strategy_id, update_type="type", data={"key": "value"})
        """
        if data is not None:
            payload = {"strategy_id": strategy_id, **data}
            if update_type:
                payload["update_type"] = update_type
        else:
            payload = {"strategy_id": strategy_id, **updates}

        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.STRATEGY_UPDATE,
                data=payload
            )
        )

    async def send_status_change(
        self,
        user_id: str,
        strategy_id: int,
        old_status: str,
        new_status: str,
        reason: str = ""
    ):
        """Send strategy status change notification."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.STRATEGY_STATUS_CHANGED,
                data={
                    "strategy_id": strategy_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "reason": reason
                }
            )
        )

    async def send_order_update(
        self,
        user_id: str,
        strategy_id: int,
        order_id: int,
        event_type: MessageType,
        order_data: Dict[str, Any]
    ):
        """Send order event notification."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=event_type,
                data={
                    "strategy_id": strategy_id,
                    "order_id": order_id,
                    **order_data
                }
            )
        )

    async def send_pnl_update(
        self,
        user_id: str,
        strategy_id: int,
        realized_pnl: float,
        unrealized_pnl: float,
        total_pnl: float
    ):
        """Send P&L update to user."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.PNL_UPDATE,
                data={
                    "strategy_id": strategy_id,
                    "realized_pnl": realized_pnl,
                    "unrealized_pnl": unrealized_pnl,
                    "total_pnl": total_pnl
                }
            )
        )

    async def send_condition_update(
        self,
        user_id: str,
        strategy_id: int,
        conditions_met: bool,
        condition_states: List[Dict[str, Any]]
    ):
        """Send condition evaluation update."""
        msg_type = MessageType.CONDITIONS_MET if conditions_met else MessageType.CONDITION_EVALUATED
        await self.send_to_user(
            user_id,
            WSMessage(
                type=msg_type,
                data={
                    "strategy_id": strategy_id,
                    "conditions_met": conditions_met,
                    "condition_states": condition_states
                }
            )
        )

    async def send_risk_alert(
        self,
        user_id: str,
        alert_type: str,
        message: str,
        data: Dict[str, Any]
    ):
        """Send risk alert to user."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.RISK_ALERT,
                data={
                    "alert_type": alert_type,
                    "message": message,
                    **data
                }
            )
        )

    async def send_market_status(self, is_open: bool, message: str = ""):
        """Broadcast market status to all connected users."""
        await self.broadcast(
            WSMessage(
                type=MessageType.MARKET_STATUS,
                data={
                    "is_open": is_open,
                    "message": message
                }
            )
        )

    # ========================================================================
    # Phase 3: Additional convenience methods
    # ========================================================================

    async def send_system_alert(
        self,
        alert_type: str,
        message: str,
        data: Dict[str, Any] = None
    ):
        """Broadcast system alert to all connected users."""
        await self.broadcast(
            WSMessage(
                type=MessageType.SYSTEM_ALERT,
                data={
                    "alert_type": alert_type,
                    "message": message,
                    **(data or {})
                }
            )
        )

    async def send_confirmation_request(
        self,
        user_id: str,
        strategy_id: int,
        confirmation_id: int,
        action_type: str,
        description: str,
        expires_at: datetime
    ):
        """Send confirmation request for semi-auto execution mode."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.CONFIRMATION_REQUEST,
                data={
                    "strategy_id": strategy_id,
                    "confirmation_id": confirmation_id,
                    "action_type": action_type,
                    "description": description,
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
            )
        )

    async def send_kill_switch_update(
        self,
        is_enabled: bool,
        reason: str = "",
        triggered_by: str = None
    ):
        """Broadcast kill switch status change to all users."""
        msg_type = MessageType.KILL_SWITCH_TRIGGERED if is_enabled else MessageType.KILL_SWITCH_RESET
        await self.broadcast(
            WSMessage(
                type=msg_type,
                data={
                    "is_enabled": is_enabled,
                    "reason": reason,
                    "triggered_by": triggered_by
                }
            )
        )

    async def send_trailing_stop_update(
        self,
        user_id: str,
        strategy_id: int,
        peak_pnl: float,
        current_stop_level: float,
        distance_to_stop: float,
        is_active: bool
    ):
        """Send trailing stop update to user."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.TRAILING_STOP_UPDATE,
                data={
                    "strategy_id": strategy_id,
                    "peak_pnl": peak_pnl,
                    "current_stop_level": current_stop_level,
                    "distance_to_stop": distance_to_stop,
                    "is_active": is_active
                }
            )
        )

    async def send_greeks_update(
        self,
        user_id: str,
        strategy_id: int,
        greeks: Dict[str, Any]
    ):
        """Send Greeks update to user."""
        await self.send_to_user(
            user_id,
            WSMessage(
                type=MessageType.GREEKS_UPDATE,
                data={
                    "strategy_id": strategy_id,
                    **greeks
                }
            )
        )

    async def send_adjustment_update(
        self,
        user_id: str,
        strategy_id: int,
        event_type: str,  # "triggered" or "executed"
        adjustment_data: Dict[str, Any]
    ):
        """Send adjustment event to user."""
        msg_type = (MessageType.ADJUSTMENT_TRIGGERED
                    if event_type == "triggered"
                    else MessageType.ADJUSTMENT_EXECUTED)
        await self.send_to_user(
            user_id,
            WSMessage(
                type=msg_type,
                data={
                    "strategy_id": strategy_id,
                    **adjustment_data
                }
            )
        )


# Singleton instance
ws_manager = ConnectionManager()


def get_ws_manager() -> ConnectionManager:
    """Get WebSocket manager instance."""
    return ws_manager
