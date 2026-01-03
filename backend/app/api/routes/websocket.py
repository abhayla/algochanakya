"""
WebSocket API Routes

Real-time data streaming endpoint for frontend clients.
Supports routing between SmartAPI and Kite based on user preference.
"""
import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, BrokerConnection, UserPreferences
from app.models.smartapi_credentials import SmartAPICredentials
from app.models.user_preferences import MarketDataSource
from app.utils.jwt import verify_access_token
from app.utils.encryption import decrypt
from app.services.kite_ticker import kite_ticker_service
from app.services.smartapi_ticker import smartapi_ticker_service
from app.config import settings

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


async def get_user_market_data_source(user_id, db: AsyncSession) -> str:
    """
    Get user's preferred market data source.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Market data source ('smartapi' or 'kite')
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()

    if preferences and preferences.market_data_source:
        return preferences.market_data_source

    return MarketDataSource.SMARTAPI  # Default to SmartAPI


async def get_smartapi_credentials(user_id, db: AsyncSession):
    """
    Get user's SmartAPI credentials if configured.

    Args:
        user_id: User ID
        db: Database session

    Returns:
        Tuple of (credentials, decrypted_pin, decrypted_totp_secret) or (None, None, None)
    """
    result = await db.execute(
        select(SmartAPICredentials).where(
            SmartAPICredentials.user_id == user_id,
            SmartAPICredentials.is_active == True
        )
    )
    credentials = result.scalar_one_or_none()

    if not credentials:
        return None, None, None

    try:
        pin = decrypt(credentials.encrypted_pin)
        totp_secret = decrypt(credentials.encrypted_totp_secret)
        return credentials, pin, totp_secret
    except Exception as e:
        logger.error(f"Failed to decrypt SmartAPI credentials: {e}")
        return None, None, None


@router.websocket("/ws/ticks")
async def websocket_ticks(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token")
):
    """
    WebSocket endpoint for live price streaming.

    Routes to SmartAPI or Kite based on user preference.
    Client connects with JWT token in query param.
    Client sends: {"action": "subscribe", "tokens": [256265, 260105]}
    Server sends: {"type": "ticks", "data": [...]}

    Args:
        websocket: WebSocket connection
        token: JWT access token
    """
    user = None
    user_id = None
    ticker_service = None  # Will be set to either kite or smartapi ticker
    market_data_source = None

    try:
        # Accept connection
        await websocket.accept()
        print(f"[WS] WebSocket connection accepted", flush=True)
        logger.info("WebSocket connection accepted")

        # Authenticate user and determine market data source
        async for db in get_db():
            try:
                user = await get_user_from_token(token, db)
                user_id = str(user.id)
                print(f"[WS] User authenticated: {user_id}", flush=True)

                # Get user's preferred market data source
                market_data_source = await get_user_market_data_source(user.id, db)
                print(f"[WS] Market data source: {market_data_source}", flush=True)

                # Try SmartAPI first if preferred
                if market_data_source == MarketDataSource.SMARTAPI:
                    credentials, pin, totp_secret = await get_smartapi_credentials(user.id, db)
                    if credentials and credentials.jwt_token and credentials.feed_token:
                        ticker_service = smartapi_ticker_service
                        print(f"[WS] Using SmartAPI ticker", flush=True)
                    else:
                        print(f"[WS] SmartAPI not configured, falling back to Kite", flush=True)
                        market_data_source = MarketDataSource.KITE

                # Use Kite if SmartAPI not available or not preferred
                if market_data_source == MarketDataSource.KITE or ticker_service is None:
                    broker_connection = await get_user_broker_connection(user.id, db)
                    kite_access_token = broker_connection.access_token
                    ticker_service = kite_ticker_service
                    market_data_source = MarketDataSource.KITE
                    print(f"[WS] Using Kite ticker", flush=True)

                    if kite_access_token:
                        print(f"[WS] Kite token found: ...{kite_access_token[-10:]}", flush=True)

                logger.info(f"WebSocket authenticated for user {user_id}, source: {market_data_source}")

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                await websocket.close()
                return
            break  # Exit the async for after first iteration

        # Connect to the selected ticker service
        if market_data_source == MarketDataSource.SMARTAPI:
            # Connect SmartAPI if not connected
            if not smartapi_ticker_service.is_connected:
                print(f"[WS] Connecting to SmartAPI WebSocket...", flush=True)
                logger.info("Connecting to SmartAPI WebSocket...")
                try:
                    async for db in get_db():
                        credentials, pin, totp_secret = await get_smartapi_credentials(user.id, db)
                        break

                    if credentials and credentials.jwt_token:
                        await smartapi_ticker_service.connect(
                            jwt_token=credentials.jwt_token,
                            api_key=settings.ANGEL_API_KEY,
                            client_id=credentials.client_id,
                            feed_token=credentials.feed_token
                        )

                        # Wait for connection
                        for i in range(20):
                            await asyncio.sleep(0.5)
                            if smartapi_ticker_service.is_connected:
                                print(f"[WS] SmartAPI WebSocket connected!", flush=True)
                                logger.info("SmartAPI WebSocket connected!")
                                break
                        else:
                            print(f"[WS] SmartAPI connection timeout, falling back to Kite", flush=True)
                            ticker_service = kite_ticker_service
                            market_data_source = MarketDataSource.KITE

                except Exception as e:
                    print(f"[WS] SmartAPI connection failed: {e}, falling back to Kite", flush=True)
                    logger.error(f"SmartAPI connection failed: {e}")
                    ticker_service = kite_ticker_service
                    market_data_source = MarketDataSource.KITE

        # Connect Kite if needed (either as primary or fallback)
        if market_data_source == MarketDataSource.KITE:
            if not kite_ticker_service.is_connected:
                print(f"[WS] Connecting to Kite WebSocket...", flush=True)
                logger.info("Connecting to Kite WebSocket...")
                try:
                    async for db in get_db():
                        broker_connection = await get_user_broker_connection(user.id, db)
                        kite_access_token = broker_connection.access_token
                        break

                    await kite_ticker_service.connect(kite_access_token)

                    # Wait for connection
                    for i in range(20):
                        await asyncio.sleep(0.5)
                        if kite_ticker_service.is_connected:
                            print(f"[WS] Kite WebSocket connected!", flush=True)
                            logger.info("Kite WebSocket connected!")
                            break
                    else:
                        print(f"[WS] Kite WebSocket connection timeout, but continuing...", flush=True)
                        logger.warning("Kite WebSocket connection timeout, but continuing...")

                except Exception as e:
                    print(f"[WS] Kite connection failed: {e}", flush=True)
                    logger.error(f"Kite connection failed: {e}")

        # Check connection status
        is_connected = ticker_service.is_connected if ticker_service else False
        if not is_connected:
            await websocket.send_json({
                "type": "warning",
                "message": f"{market_data_source.upper()} connection failed. Please check your credentials."
            })

        # Register this client with the ticker service
        await ticker_service.register_client(user_id, websocket)

        # Send connection success
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "source": market_data_source,
            "connected": is_connected
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
                    exchange = data.get("exchange", "NFO")  # For SmartAPI

                    if tokens:
                        if market_data_source == MarketDataSource.SMARTAPI:
                            # SmartAPI uses string tokens
                            tokens = [str(t) for t in tokens]
                            await ticker_service.subscribe(tokens, user_id, exchange, mode)
                        else:
                            # Kite uses integer tokens
                            tokens = [int(t) for t in tokens]
                            await ticker_service.subscribe(tokens, user_id, mode)

                        await websocket.send_json({
                            "type": "subscribed",
                            "tokens": tokens,
                            "mode": mode,
                            "source": market_data_source
                        })
                        logger.info(f"User {user_id} subscribed to {len(tokens)} tokens via {market_data_source}")

                elif action == "unsubscribe":
                    tokens = data.get("tokens", [])
                    exchange = data.get("exchange", "NFO")

                    if tokens:
                        if market_data_source == MarketDataSource.SMARTAPI:
                            tokens = [str(t) for t in tokens]
                            await ticker_service.unsubscribe(tokens, user_id, exchange)
                        else:
                            tokens = [int(t) for t in tokens]
                            await ticker_service.unsubscribe(tokens, user_id)

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
        # Unregister client from the appropriate ticker service
        if user_id and ticker_service:
            await ticker_service.unregister_client(user_id)
            logger.info(f"User {user_id} cleaned up from {market_data_source}")
