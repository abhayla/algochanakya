"""
WebSocket API Routes

Real-time data streaming endpoint for frontend clients.
Routes to SmartAPI or Kite ticker service based on user preference.

Note: WebSocket uses singleton ticker services (smartapi_ticker_service,
kite_ticker_service) to manage persistent connections for multiple users.
This is different from REST API routes which use get_user_market_data_adapter().
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, BrokerConnection, UserPreferences
from app.models.smartapi_credentials import SmartAPICredentials
from app.models.user_preferences import MarketDataSource
from app.utils.jwt import verify_access_token
from app.utils.encryption import decrypt
from app.utils.smartapi_utils import get_valid_smartapi_credentials
from app.services.legacy.kite_ticker import kite_ticker_service
from app.services.legacy.smartapi_ticker import smartapi_ticker_service
from app.services.legacy.smartapi_market_data import SmartAPIMarketData
from app.config import settings

# Mapping of Kite index tokens to SmartAPI tokens and names (for initial REST quotes)
KITE_TO_SMARTAPI_INDEX = {
    256265: {'smartapi_token': '99926000', 'exchange': 'NSE', 'name': 'NIFTY 50'},      # NIFTY 50
    260105: {'smartapi_token': '99926009', 'exchange': 'NSE', 'name': 'NIFTY BANK'},    # NIFTY BANK
    257801: {'smartapi_token': '99926037', 'exchange': 'NSE', 'name': 'NIFTY FIN'},     # FINNIFTY
    265: {'smartapi_token': '99919000', 'exchange': 'BSE', 'name': 'SENSEX'},           # SENSEX
}

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


async def fetch_initial_index_quotes(
    kite_tokens: List[int],
    jwt_token: str,
    websocket: WebSocket
) -> None:
    """
    Fetch initial index quotes via REST API and send to client.

    This ensures the UI shows last prices even when market is closed
    and no live ticks are being received.

    Args:
        kite_tokens: List of Kite instrument tokens
        jwt_token: SmartAPI JWT token
        websocket: Client WebSocket connection
    """
    try:
        # Filter to only index tokens we can map
        index_tokens_to_fetch = []
        for kite_token in kite_tokens:
            if kite_token in KITE_TO_SMARTAPI_INDEX:
                index_tokens_to_fetch.append(kite_token)

        if not index_tokens_to_fetch:
            return

        # Create market data service
        market_data = SmartAPIMarketData(
            api_key=settings.ANGEL_API_KEY,
            jwt_token=jwt_token
        )

        # Group by exchange and fetch quotes
        by_exchange: Dict[str, List[tuple]] = {}
        for kite_token in index_tokens_to_fetch:
            info = KITE_TO_SMARTAPI_INDEX[kite_token]
            exchange = info['exchange']
            if exchange not in by_exchange:
                by_exchange[exchange] = []
            by_exchange[exchange].append((kite_token, info['smartapi_token'], info['name']))

        ticks = []
        for exchange, token_info_list in by_exchange.items():
            smartapi_tokens = [t[1] for t in token_info_list]

            try:
                quotes = await market_data.get_quote(exchange, smartapi_tokens, mode='FULL')

                for kite_token, smartapi_token, name in token_info_list:
                    quote = quotes.get(smartapi_token)
                    if quote:
                        ltp = float(quote.get('ltp', 0))
                        close = float(quote.get('close', 0))
                        change = ltp - close if ltp and close else 0
                        change_percent = (change / close * 100) if close else 0

                        ticks.append({
                            'token': kite_token,  # Use Kite token for frontend compatibility
                            'ltp': ltp,
                            'change': round(change, 2),
                            'change_percent': round(change_percent, 2),
                            'open': float(quote.get('open', 0)),
                            'high': float(quote.get('high', 0)),
                            'low': float(quote.get('low', 0)),
                            'close': close,
                            'volume': quote.get('volume', 0),
                        })
                        logger.info(f"[WS] Initial quote for {name}: LTP={ltp}, Close={close}")

            except Exception as e:
                logger.warning(f"[WS] Failed to fetch initial quotes for {exchange}: {e}")

        # Send initial ticks to client
        if ticks:
            await websocket.send_json({"type": "ticks", "data": ticks})
            logger.info(f"[WS] Sent {len(ticks)} initial index quotes to client")

    except Exception as e:
        logger.error(f"[WS] Error fetching initial quotes: {e}")


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
    smartapi_jwt_token = None  # Store SmartAPI JWT for REST API calls

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

                # Get user's preferred market data source and select ticker service
                market_data_source = await get_user_market_data_source(user.id, db)
                print(f"[WS] Preferred market data source: {market_data_source}", flush=True)

                # Select appropriate ticker service (singleton services for WebSocket)
                if market_data_source == MarketDataSource.SMARTAPI:
                    # Check if SmartAPI credentials are available
                    credentials, pin, totp_secret = await get_smartapi_credentials(user.id, db)
                    if credentials and credentials.jwt_token and credentials.feed_token:
                        ticker_service = smartapi_ticker_service
                        smartapi_jwt_token = credentials.jwt_token  # Store for REST API calls
                        print(f"[WS] Selected SmartAPI ticker service", flush=True)
                    else:
                        # Fall back to Kite if SmartAPI not configured
                        print(f"[WS] SmartAPI credentials not found, using Kite", flush=True)
                        market_data_source = MarketDataSource.KITE
                        ticker_service = kite_ticker_service
                else:
                    # Use Kite ticker service
                    ticker_service = kite_ticker_service
                    print(f"[WS] Selected Kite ticker service", flush=True)

                logger.info(f"WebSocket authenticated for user {user_id}, using {market_data_source}")

            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                await websocket.close()
                return
            break  # Exit the async for after first iteration

        # Connect to the selected ticker service if not already connected
        connection_failed = False

        if market_data_source == MarketDataSource.SMARTAPI:
            if not smartapi_ticker_service.is_connected:
                print(f"[WS] Connecting to SmartAPI WebSocket...", flush=True)
                logger.info("Connecting to SmartAPI WebSocket...")
                try:
                    async for db in get_db():
                        credentials = await get_valid_smartapi_credentials(user.id, db, auto_refresh=True)
                        break

                    if credentials and credentials.jwt_token:
                        smartapi_jwt_token = credentials.jwt_token  # Update with refreshed token
                        await smartapi_ticker_service.connect(
                            jwt_token=credentials.jwt_token,
                            api_key=settings.ANGEL_API_KEY,
                            client_id=credentials.client_id,
                            feed_token=credentials.feed_token
                        )

                        # Wait for connection (10 seconds max)
                        for _ in range(20):
                            await asyncio.sleep(0.5)
                            if smartapi_ticker_service.is_connected:
                                print(f"[WS] SmartAPI WebSocket connected", flush=True)
                                break
                        else:
                            connection_failed = True
                            print(f"[WS] SmartAPI connection timeout", flush=True)

                except Exception as e:
                    connection_failed = True
                    print(f"[WS] SmartAPI connection failed: {e}", flush=True)
                    logger.error(f"SmartAPI connection failed: {e}")

                # Fall back to Kite if SmartAPI connection failed
                if connection_failed:
                    print(f"[WS] Falling back to Kite", flush=True)
                    ticker_service = kite_ticker_service
                    market_data_source = MarketDataSource.KITE
                    connection_failed = False  # Reset for Kite connection attempt

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

                    # Wait for connection (10 seconds max)
                    for _ in range(20):
                        await asyncio.sleep(0.5)
                        if kite_ticker_service.is_connected:
                            print(f"[WS] Kite WebSocket connected", flush=True)
                            break
                    else:
                        print(f"[WS] Kite connection timeout, but continuing...", flush=True)
                        logger.warning("Kite connection timeout")

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
                    exchange = data.get("exchange", "NFO")  # Used by SmartAPI

                    if tokens:
                        # Store original tokens for initial quote fetch (as integers)
                        original_tokens = [int(t) for t in tokens]

                        # Convert tokens to appropriate type and subscribe
                        if market_data_source == MarketDataSource.SMARTAPI:
                            tokens = [str(t) for t in tokens]  # SmartAPI uses string tokens
                            await ticker_service.subscribe(tokens, user_id, exchange, mode)

                            # Fetch initial quotes via REST API for index tokens
                            # This ensures UI shows last prices even when market is closed
                            if smartapi_jwt_token:
                                await fetch_initial_index_quotes(
                                    original_tokens,
                                    smartapi_jwt_token,
                                    websocket
                                )
                        else:
                            tokens = [int(t) for t in tokens]  # Kite uses integer tokens
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
                    exchange = data.get("exchange", "NFO")  # Used by SmartAPI

                    if tokens:
                        # Convert tokens to appropriate type and unsubscribe
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
