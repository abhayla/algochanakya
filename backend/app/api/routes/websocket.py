"""
WebSocket API Routes

Real-time data streaming endpoint for frontend clients.
"""
import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, BrokerConnection
from app.utils.jwt import verify_access_token
from app.services.kite_ticker import kite_ticker_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    """
    Get user from JWT token.

    Args:
        token: JWT token
        db: Database session

    Returns:
        User object

    Raises:
        Exception: If token invalid or user not found
    """
    try:
        payload = verify_access_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise Exception("Invalid token: missing user_id")

        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise Exception("User not found")

        return user

    except Exception as e:
        raise Exception(f"Authentication failed: {str(e)}")


async def get_user_broker_connection(user_id, db: AsyncSession) -> BrokerConnection:
    """
    Get user's active broker connection.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        BrokerConnection object

    Raises:
        Exception: If no active connection found
    """
    result = await db.execute(
        select(BrokerConnection).where(
            BrokerConnection.user_id == user_id,
            BrokerConnection.broker == "zerodha",
            BrokerConnection.is_active == True
        )
    )
    broker_connection = result.scalar_one_or_none()

    if not broker_connection:
        raise Exception("No active Zerodha connection. Please login again.")

    return broker_connection


@router.websocket("/ws/ticks")
async def websocket_ticks(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token")
):
    """
    WebSocket endpoint for live price streaming.

    Client connects with JWT token in query param.
    Client sends: {"action": "subscribe", "tokens": [256265, 260105]}
    Server sends: {"type": "ticks", "data": [...]}

    Args:
        websocket: WebSocket connection
        token: JWT access token
    """
    user = None
    user_id = None

    try:
        # Accept connection
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        # Authenticate user and get broker connection
        async for db in get_db():
            try:
                user = await get_user_from_token(token, db)
                user_id = str(user.id)
                broker_connection = await get_user_broker_connection(user.id, db)
                kite_access_token = broker_connection.access_token

                logger.info(f"WebSocket authenticated for user {user_id}")

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                await websocket.close()
                return
            break  # Exit the async for after first iteration

        # Connect to Kite WebSocket if not already connected
        if not kite_ticker_service.is_connected:
            logger.info("Connecting to Kite WebSocket...")
            await kite_ticker_service.connect(kite_access_token)

            # Wait for connection to establish (up to 10 seconds)
            for i in range(20):
                await asyncio.sleep(0.5)
                if kite_ticker_service.is_connected:
                    logger.info("Kite WebSocket connected!")
                    break
            else:
                logger.warning("Kite WebSocket connection timeout, but continuing...")

        # Register this client with the ticker service
        await kite_ticker_service.register_client(user_id, websocket)

        # Send connection success
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "kite_connected": kite_ticker_service.is_connected
        })

        # Handle client messages
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_text()
                data = json.loads(message)

                action = data.get("action")

                if action == "subscribe":
                    tokens = data.get("tokens", [])
                    mode = data.get("mode", "ltp")  # ltp, quote, or full

                    if tokens:
                        # Ensure tokens are integers
                        tokens = [int(t) for t in tokens]
                        await kite_ticker_service.subscribe(tokens, user_id, mode)
                        await websocket.send_json({
                            "type": "subscribed",
                            "tokens": tokens,
                            "mode": mode
                        })
                        logger.info(f"User {user_id} subscribed to {len(tokens)} tokens")

                elif action == "unsubscribe":
                    tokens = data.get("tokens", [])

                    if tokens:
                        tokens = [int(t) for t in tokens]
                        await kite_ticker_service.unsubscribe(tokens, user_id)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "tokens": tokens
                        })
                        logger.info(f"User {user_id} unsubscribed from {len(tokens)} tokens")

                elif action == "ping":
                    # Keepalive ping
                    await websocket.send_json({"type": "pong"})

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })

            except WebSocketDisconnect:
                logger.info(f"User {user_id} disconnected")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON message"
                })
            except Exception as e:
                logger.error(f"Error handling message from user {user_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")

    finally:
        # Unregister client
        if user_id:
            await kite_ticker_service.unregister_client(user_id)
            logger.info(f"User {user_id} cleaned up")
