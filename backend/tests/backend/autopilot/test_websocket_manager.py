"""
WebSocket Manager Tests

Tests for app/websocket/manager.py:
- Connection management (connect, disconnect)
- Subscription handling
- Message broadcasting
- Convenience methods for specific message types
"""

import pytest
import pytest_asyncio
import asyncio
import json
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from starlette.websockets import WebSocketState

from app.websocket.manager import (
    ConnectionManager, WSMessage, MessageType, get_ws_manager
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def manager():
    """Create fresh ConnectionManager instance."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket."""
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_websocket_disconnected():
    """Create mock WebSocket in disconnected state."""
    ws = AsyncMock()
    ws.client_state = WebSocketState.DISCONNECTED
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


# =============================================================================
# WSMESSAGE TESTS
# =============================================================================

class TestWSMessage:
    """Tests for WSMessage dataclass."""

    def test_message_creation(self):
        """Test basic message creation."""
        msg = WSMessage(
            type=MessageType.CONNECTED,
            data={"user_id": "123", "message": "Hello"}
        )

        assert msg.type == MessageType.CONNECTED
        assert msg.data["user_id"] == "123"
        assert msg.timestamp  # Auto-generated

    def test_message_to_json(self):
        """Test message serialization to JSON."""
        msg = WSMessage(
            type=MessageType.STRATEGY_UPDATE,
            data={"strategy_id": 1, "status": "active"}
        )

        json_str = msg.to_json()
        parsed = json.loads(json_str)

        assert parsed["type"] == "strategy_update"
        assert parsed["data"]["strategy_id"] == 1
        assert "timestamp" in parsed

    def test_message_custom_timestamp(self):
        """Test message with custom timestamp."""
        custom_time = "2024-12-26T10:30:00Z"
        msg = WSMessage(
            type=MessageType.PING,
            data={},
            timestamp=custom_time
        )

        assert msg.timestamp == custom_time


# =============================================================================
# MESSAGE TYPE TESTS
# =============================================================================

class TestMessageType:
    """Tests for MessageType enum."""

    def test_connection_types(self):
        """Test connection-related message types."""
        assert MessageType.CONNECTED.value == "connected"
        assert MessageType.PING.value == "ping"
        assert MessageType.PONG.value == "pong"
        assert MessageType.ERROR.value == "error"

    def test_strategy_types(self):
        """Test strategy-related message types."""
        assert MessageType.STRATEGY_UPDATE.value == "strategy_update"
        assert MessageType.STRATEGY_STATUS_CHANGED.value == "strategy_status_changed"

    def test_order_types(self):
        """Test order-related message types."""
        assert MessageType.ORDER_PLACED.value == "order_placed"
        assert MessageType.ORDER_FILLED.value == "order_filled"
        assert MessageType.ORDER_REJECTED.value == "order_rejected"

    def test_pnl_types(self):
        """Test P&L-related message types."""
        assert MessageType.PNL_UPDATE.value == "pnl_update"

    def test_condition_types(self):
        """Test condition-related message types."""
        assert MessageType.CONDITION_EVALUATED.value == "condition_evaluated"
        assert MessageType.CONDITIONS_MET.value == "conditions_met"

    def test_risk_types(self):
        """Test risk-related message types."""
        assert MessageType.RISK_ALERT.value == "risk_alert"
        assert MessageType.DAILY_LIMIT_WARNING.value == "daily_limit_warning"

    def test_system_types(self):
        """Test system-related message types."""
        assert MessageType.MARKET_STATUS.value == "market_status"
        assert MessageType.HEARTBEAT.value == "heartbeat"


# =============================================================================
# CONNECTION TESTS
# =============================================================================

class TestConnect:
    """Tests for connect method."""

    @pytest.mark.asyncio
    async def test_connect_success(self, manager, mock_websocket):
        """Test successful WebSocket connection."""
        result = await manager.connect(mock_websocket, "user_123")

        assert result is True
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_sends_welcome_message(self, manager, mock_websocket):
        """Test connected message is sent after connection."""
        await manager.connect(mock_websocket, "user_123")

        mock_websocket.send_text.assert_called_once()
        call_args = mock_websocket.send_text.call_args[0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "connected"
        assert parsed["data"]["user_id"] == "user_123"

    @pytest.mark.asyncio
    async def test_connect_registers_user(self, manager, mock_websocket):
        """Test connection is registered for user."""
        await manager.connect(mock_websocket, "user_123")

        assert "user_123" in manager.get_connected_users()
        assert manager.get_connection_count("user_123") == 1

    @pytest.mark.asyncio
    async def test_connect_multiple_from_same_user(self, manager, mock_websocket):
        """Test multiple connections from same user."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_123")
        await manager.connect(ws2, "user_123")

        assert manager.get_connection_count("user_123") == 2
        assert manager.get_total_connections() == 2

    @pytest.mark.asyncio
    async def test_connect_failure(self, manager, mock_websocket):
        """Test connection failure handling."""
        mock_websocket.accept.side_effect = Exception("Connection refused")

        result = await manager.connect(mock_websocket, "user_123")

        assert result is False


# =============================================================================
# DISCONNECT TESTS
# =============================================================================

class TestDisconnect:
    """Tests for disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager, mock_websocket):
        """Test disconnect removes the connection."""
        await manager.connect(mock_websocket, "user_123")
        await manager.disconnect(mock_websocket)

        assert manager.get_connection_count("user_123") == 0

    @pytest.mark.asyncio
    async def test_disconnect_removes_user_when_last(self, manager, mock_websocket):
        """Test user is removed when last connection disconnects."""
        await manager.connect(mock_websocket, "user_123")
        await manager.disconnect(mock_websocket)

        assert "user_123" not in manager.get_connected_users()

    @pytest.mark.asyncio
    async def test_disconnect_keeps_user_with_other_connections(self, manager):
        """Test user kept when other connections remain."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_123")
        await manager.connect(ws2, "user_123")
        await manager.disconnect(ws1)

        assert "user_123" in manager.get_connected_users()
        assert manager.get_connection_count("user_123") == 1

    @pytest.mark.asyncio
    async def test_disconnect_cleans_subscriptions(self, manager, mock_websocket):
        """Test disconnect cleans up subscriptions when last connection."""
        await manager.connect(mock_websocket, "user_123")
        await manager.subscribe_to_strategy("user_123", 1)
        await manager.disconnect(mock_websocket)

        assert not manager.is_subscribed("user_123", 1)

    @pytest.mark.asyncio
    async def test_disconnect_unknown_websocket(self, manager, mock_websocket):
        """Test disconnecting unknown WebSocket doesn't crash."""
        await manager.disconnect(mock_websocket)  # Should not raise


# =============================================================================
# SUBSCRIPTION TESTS
# =============================================================================

class TestSubscriptions:
    """Tests for subscription management."""

    @pytest.mark.asyncio
    async def test_subscribe_to_strategy(self, manager):
        """Test subscribing to a strategy."""
        await manager.subscribe_to_strategy("user_123", 1)

        assert manager.is_subscribed("user_123", 1)

    @pytest.mark.asyncio
    async def test_subscribe_multiple_strategies(self, manager):
        """Test subscribing to multiple strategies."""
        await manager.subscribe_to_strategy("user_123", 1)
        await manager.subscribe_to_strategy("user_123", 2)

        assert manager.is_subscribed("user_123", 1)
        assert manager.is_subscribed("user_123", 2)

    @pytest.mark.asyncio
    async def test_unsubscribe_from_strategy(self, manager):
        """Test unsubscribing from a strategy."""
        await manager.subscribe_to_strategy("user_123", 1)
        await manager.unsubscribe_from_strategy("user_123", 1)

        assert not manager.is_subscribed("user_123", 1)

    @pytest.mark.asyncio
    async def test_unsubscribe_keeps_others(self, manager):
        """Test unsubscribe keeps other subscriptions."""
        await manager.subscribe_to_strategy("user_123", 1)
        await manager.subscribe_to_strategy("user_123", 2)
        await manager.unsubscribe_from_strategy("user_123", 1)

        assert not manager.is_subscribed("user_123", 1)
        assert manager.is_subscribed("user_123", 2)

    def test_is_subscribed_not_subscribed(self, manager):
        """Test is_subscribed returns False for non-subscribed."""
        assert manager.is_subscribed("user_123", 999) is False


# =============================================================================
# SEND MESSAGE TESTS
# =============================================================================

class TestSendToUser:
    """Tests for send_to_user method."""

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager, mock_websocket):
        """Test sending message to specific user."""
        await manager.connect(mock_websocket, "user_123")

        message = WSMessage(
            type=MessageType.STRATEGY_UPDATE,
            data={"strategy_id": 1}
        )
        await manager.send_to_user("user_123", message)

        # First call is connect message, second is our message
        assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_send_to_user_multiple_connections(self, manager):
        """Test message sent to all user's connections."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_123")
        await manager.connect(ws2, "user_123")

        message = WSMessage(type=MessageType.PING, data={})
        await manager.send_to_user("user_123", message)

        # Each gets connect + our message
        assert ws1.send_text.call_count == 2
        assert ws2.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_user(self, manager):
        """Test sending to non-existent user doesn't crash."""
        message = WSMessage(type=MessageType.PING, data={})
        await manager.send_to_user("nonexistent", message)  # Should not raise


class TestSendToConnection:
    """Tests for send_to_connection method."""

    @pytest.mark.asyncio
    async def test_send_to_connected_websocket(self, manager, mock_websocket):
        """Test sending to connected WebSocket."""
        message = WSMessage(type=MessageType.PONG, data={})
        await manager.send_to_connection(mock_websocket, message)

        mock_websocket.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_disconnected_websocket(self, manager, mock_websocket_disconnected):
        """Test sending to disconnected WebSocket is skipped."""
        message = WSMessage(type=MessageType.PONG, data={})
        await manager.send_to_connection(mock_websocket_disconnected, message)

        mock_websocket_disconnected.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_error_disconnects(self, manager, mock_websocket):
        """Test send error triggers disconnect."""
        await manager.connect(mock_websocket, "user_123")
        mock_websocket.send_text.side_effect = [None, Exception("Send failed")]  # Connect succeeds, next fails

        message = WSMessage(type=MessageType.PING, data={})
        await manager.send_to_connection(mock_websocket, message)

        # Should have tried to disconnect
        assert manager.get_connection_count("user_123") == 0


# =============================================================================
# BROADCAST TESTS
# =============================================================================

class TestBroadcast:
    """Tests for broadcast method."""

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, manager):
        """Test broadcasting to all connected users."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_2")

        message = WSMessage(type=MessageType.MARKET_STATUS, data={"is_open": True})
        await manager.broadcast(message)

        # Each user gets connect message + broadcast
        assert ws1.send_text.call_count == 2
        assert ws2.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_specific_users(self, manager):
        """Test broadcasting to specific users only."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED
        ws3 = AsyncMock()
        ws3.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_2")
        await manager.connect(ws3, "user_3")

        message = WSMessage(type=MessageType.HEARTBEAT, data={})
        await manager.broadcast(message, user_ids=["user_1", "user_3"])

        # user_1 and user_3 get connect + broadcast
        assert ws1.send_text.call_count == 2
        assert ws3.send_text.call_count == 2
        # user_2 only gets connect message
        assert ws2.send_text.call_count == 1


# =============================================================================
# STATS TESTS
# =============================================================================

class TestStats:
    """Tests for connection statistics methods."""

    def test_get_connected_users_empty(self, manager):
        """Test get_connected_users with no connections."""
        assert manager.get_connected_users() == []

    @pytest.mark.asyncio
    async def test_get_connected_users(self, manager):
        """Test get_connected_users returns user IDs."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_2")

        users = manager.get_connected_users()
        assert "user_1" in users
        assert "user_2" in users

    def test_get_connection_count_no_user(self, manager):
        """Test get_connection_count for non-connected user."""
        assert manager.get_connection_count("unknown") == 0

    @pytest.mark.asyncio
    async def test_get_connection_count(self, manager):
        """Test get_connection_count for connected user."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_1")

        assert manager.get_connection_count("user_1") == 2

    def test_get_total_connections_empty(self, manager):
        """Test get_total_connections with no connections."""
        assert manager.get_total_connections() == 0

    @pytest.mark.asyncio
    async def test_get_total_connections(self, manager):
        """Test get_total_connections."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED
        ws3 = AsyncMock()
        ws3.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_1")
        await manager.connect(ws3, "user_2")

        assert manager.get_total_connections() == 3


# =============================================================================
# CONVENIENCE METHOD TESTS
# =============================================================================

class TestConvenienceMethods:
    """Tests for convenience message methods."""

    @pytest.mark.asyncio
    async def test_send_strategy_update(self, manager, mock_websocket):
        """Test send_strategy_update."""
        await manager.connect(mock_websocket, "user_123")

        await manager.send_strategy_update(
            user_id="user_123",
            strategy_id=1,
            updates={"status": "active", "pnl": 1000}
        )

        # Get the last call (strategy update)
        call_args = mock_websocket.send_text.call_args_list[-1][0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "strategy_update"
        assert parsed["data"]["strategy_id"] == 1
        assert parsed["data"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_send_status_change(self, manager, mock_websocket):
        """Test send_status_change."""
        await manager.connect(mock_websocket, "user_123")

        await manager.send_status_change(
            user_id="user_123",
            strategy_id=1,
            old_status="waiting",
            new_status="active",
            reason="Conditions met"
        )

        call_args = mock_websocket.send_text.call_args_list[-1][0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "strategy_status_changed"
        assert parsed["data"]["old_status"] == "waiting"
        assert parsed["data"]["new_status"] == "active"
        assert parsed["data"]["reason"] == "Conditions met"

    @pytest.mark.asyncio
    async def test_send_order_update(self, manager, mock_websocket):
        """Test send_order_update."""
        await manager.connect(mock_websocket, "user_123")

        await manager.send_order_update(
            user_id="user_123",
            strategy_id=1,
            order_id=100,
            event_type=MessageType.ORDER_FILLED,
            order_data={"price": 150.50, "quantity": 25}
        )

        call_args = mock_websocket.send_text.call_args_list[-1][0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "order_filled"
        assert parsed["data"]["order_id"] == 100
        assert parsed["data"]["price"] == 150.50

    @pytest.mark.asyncio
    async def test_send_pnl_update(self, manager, mock_websocket):
        """Test send_pnl_update."""
        await manager.connect(mock_websocket, "user_123")

        await manager.send_pnl_update(
            user_id="user_123",
            strategy_id=1,
            realized_pnl=1000.0,
            unrealized_pnl=500.0,
            total_pnl=1500.0
        )

        call_args = mock_websocket.send_text.call_args_list[-1][0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "pnl_update"
        assert parsed["data"]["realized_pnl"] == 1000.0
        assert parsed["data"]["unrealized_pnl"] == 500.0
        assert parsed["data"]["total_pnl"] == 1500.0

    @pytest.mark.asyncio
    async def test_send_condition_update_met(self, manager, mock_websocket):
        """Test send_condition_update when conditions met."""
        await manager.connect(mock_websocket, "user_123")

        await manager.send_condition_update(
            user_id="user_123",
            strategy_id=1,
            conditions_met=True,
            condition_states=[{"id": "c1", "is_met": True}]
        )

        call_args = mock_websocket.send_text.call_args_list[-1][0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "conditions_met"
        assert parsed["data"]["conditions_met"] is True

    @pytest.mark.asyncio
    async def test_send_condition_update_not_met(self, manager, mock_websocket):
        """Test send_condition_update when conditions not met."""
        await manager.connect(mock_websocket, "user_123")

        await manager.send_condition_update(
            user_id="user_123",
            strategy_id=1,
            conditions_met=False,
            condition_states=[{"id": "c1", "is_met": False}]
        )

        call_args = mock_websocket.send_text.call_args_list[-1][0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "condition_evaluated"
        assert parsed["data"]["conditions_met"] is False

    @pytest.mark.asyncio
    async def test_send_risk_alert(self, manager, mock_websocket):
        """Test send_risk_alert."""
        await manager.connect(mock_websocket, "user_123")

        await manager.send_risk_alert(
            user_id="user_123",
            alert_type="daily_limit",
            message="Daily loss limit reached",
            data={"loss": 20000, "limit": 20000}
        )

        call_args = mock_websocket.send_text.call_args_list[-1][0][0]
        parsed = json.loads(call_args)

        assert parsed["type"] == "risk_alert"
        assert parsed["data"]["alert_type"] == "daily_limit"
        assert parsed["data"]["message"] == "Daily loss limit reached"

    @pytest.mark.asyncio
    async def test_send_market_status(self, manager):
        """Test send_market_status broadcasts to all."""
        ws1 = AsyncMock()
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock()
        ws2.client_state = WebSocketState.CONNECTED

        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_2")

        await manager.send_market_status(is_open=True, message="Market is open")

        # Both should receive the broadcast
        for ws in [ws1, ws2]:
            call_args = ws.send_text.call_args_list[-1][0][0]
            parsed = json.loads(call_args)
            assert parsed["type"] == "market_status"
            assert parsed["data"]["is_open"] is True


# =============================================================================
# SINGLETON TESTS
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_ws_manager_returns_same_instance(self):
        """Test get_ws_manager returns same instance."""
        manager1 = get_ws_manager()
        manager2 = get_ws_manager()

        assert manager1 is manager2


# =============================================================================
# CONCURRENCY TESTS
# =============================================================================

class TestConcurrency:
    """Tests for thread-safe operations."""

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, manager):
        """Test handling concurrent connections."""
        websockets = []
        for i in range(10):
            ws = AsyncMock()
            ws.client_state = WebSocketState.CONNECTED
            websockets.append(ws)

        # Connect all concurrently
        await asyncio.gather(*[
            manager.connect(ws, f"user_{i}")
            for i, ws in enumerate(websockets)
        ])

        assert manager.get_total_connections() == 10
        assert len(manager.get_connected_users()) == 10

    @pytest.mark.asyncio
    async def test_concurrent_disconnections(self, manager):
        """Test handling concurrent disconnections."""
        websockets = []
        for i in range(10):
            ws = AsyncMock()
            ws.client_state = WebSocketState.CONNECTED
            websockets.append(ws)
            await manager.connect(ws, f"user_{i}")

        # Disconnect all concurrently
        await asyncio.gather(*[
            manager.disconnect(ws)
            for ws in websockets
        ])

        assert manager.get_total_connections() == 0

    @pytest.mark.asyncio
    async def test_concurrent_subscriptions(self, manager):
        """Test handling concurrent subscriptions."""
        await asyncio.gather(*[
            manager.subscribe_to_strategy("user_1", i)
            for i in range(100)
        ])

        for i in range(100):
            assert manager.is_subscribed("user_1", i)
