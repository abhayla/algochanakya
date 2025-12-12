"""
WebSocket Routes

WebSocket endpoint for AutoPilot real-time updates.
"""
import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import jwt, JWTError

from app.config import settings
from app.websocket.manager import get_ws_manager, WSMessage, MessageType

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(token: str) -> str:
    """Validate JWT token and return user ID."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Invalid token: no subject")
        return str(user_id)
    except JWTError as e:
        raise ValueError(f"Token validation failed: {e}")


@router.websocket("/ws/autopilot")
async def autopilot_websocket(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for AutoPilot real-time updates.

    Connect with: ws://host/ws/autopilot?token=<jwt_token>

    Messages received from client:
    - ping: Respond with pong (keepalive)
    - subscribe: Subscribe to specific strategy updates
      {"type": "subscribe", "data": {"strategy_id": 123}}
    - unsubscribe: Unsubscribe from strategy updates
      {"type": "unsubscribe", "data": {"strategy_id": 123}}

    Messages sent to client:
    - connected: Connection established
    - pong: Response to ping
    - heartbeat: Server-initiated keepalive
    - strategy_update: Strategy data changed
    - strategy_status_changed: Status transition
    - order_placed/filled/rejected: Order events
    - pnl_update: P&L changes
    - condition_evaluated: Condition check results
    - conditions_met: All conditions satisfied
    - risk_alert: Risk limit warnings
    - error: Error messages
    """
    manager = get_ws_manager()

    # Validate token
    try:
        user_id = await get_user_from_token(token)
    except ValueError as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=4001, reason=str(e))
        return

    # Connect
    connected = await manager.connect(websocket, user_id)
    if not connected:
        return

    heartbeat_task = None

    try:
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(
            _heartbeat_loop(websocket, manager)
        )

        # Message handling loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type", "")
                msg_data = message.get("data", {})

                if msg_type == "ping":
                    await manager.send_to_connection(
                        websocket,
                        WSMessage(type=MessageType.PONG, data={})
                    )

                elif msg_type == "subscribe":
                    # Handle subscription to specific strategy
                    strategy_id = msg_data.get("strategy_id")
                    if strategy_id:
                        await manager.subscribe_to_strategy(user_id, int(strategy_id))
                        logger.debug(f"User {user_id} subscribed to strategy {strategy_id}")
                        await manager.send_to_connection(
                            websocket,
                            WSMessage(
                                type=MessageType.STRATEGY_UPDATE,
                                data={
                                    "strategy_id": strategy_id,
                                    "subscribed": True,
                                    "message": f"Subscribed to strategy {strategy_id}"
                                }
                            )
                        )

                elif msg_type == "unsubscribe":
                    # Handle unsubscription
                    strategy_id = msg_data.get("strategy_id")
                    if strategy_id:
                        await manager.unsubscribe_from_strategy(user_id, int(strategy_id))
                        logger.debug(f"User {user_id} unsubscribed from strategy {strategy_id}")

                else:
                    logger.debug(f"Unknown message type: {msg_type}")

            except json.JSONDecodeError:
                await manager.send_to_connection(
                    websocket,
                    WSMessage(
                        type=MessageType.ERROR,
                        data={"message": "Invalid JSON"}
                    )
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        await manager.disconnect(websocket)


async def _heartbeat_loop(websocket: WebSocket, manager):
    """Send periodic heartbeat to keep connection alive."""
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        try:
            await manager.send_to_connection(
                websocket,
                WSMessage(type=MessageType.HEARTBEAT, data={})
            )
        except Exception:
            break


@router.get("/ws/autopilot/status")
async def websocket_status():
    """
    Get WebSocket connection status.

    Returns:
        Connection statistics
    """
    manager = get_ws_manager()
    return {
        "total_connections": manager.get_total_connections(),
        "connected_users": len(manager.get_connected_users()),
        "status": "healthy"
    }
