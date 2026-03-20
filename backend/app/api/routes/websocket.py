"""
WebSocket route for live market data ticks.

Refactored to use the 5-component ticker architecture (Phase 4):
- TickerRouter handles user registration, subscriptions, and tick fan-out
- TickerPool manages adapter lifecycle and ref-counted subscriptions
- Broker-agnostic: adding new brokers requires zero changes here

Before: 494 lines with broker-specific logic
After:  ~120 lines (broker-agnostic, credential loading retained)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, BrokerConnection
from app.models.broker_api_credentials import BrokerAPICredentials
from app.models.broker_instrument_tokens import BrokerInstrumentToken
from app.models.user_preferences import MarketDataSource, UserPreferences
from app.utils.jwt import verify_access_token
from app.utils.smartapi_utils import get_valid_smartapi_credentials
from app.services.brokers.market_data.ticker import TickerPool, TickerRouter
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _exchange_type_for(exchange: str) -> int:
    return {"NSE": 1, "NFO": 2, "BSE": 3, "BFO": 4, "MCX": 5}.get(exchange, 2)


async def _authenticate_user(token: str, db: AsyncSession) -> User:
    """Authenticate user from JWT token. Raises on failure."""
    payload = verify_access_token(token)
    user_id = payload.get("user_id")
    if not user_id:
        raise Exception("Invalid token: missing user_id")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise Exception("User not found")
    return user


async def _get_market_data_source(user_id, db: AsyncSession) -> str:
    """Get user's preferred market data source. Defaults to SmartAPI."""
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    if prefs and prefs.market_data_source:
        src = prefs.market_data_source
        # "platform" means use platform default (SmartAPI is first in chain)
        return MarketDataSource.SMARTAPI if src == MarketDataSource.PLATFORM else src
    return MarketDataSource.SMARTAPI


async def _get_user_broker_creds(
    user_id, broker: str, db: AsyncSession
) -> Optional[BrokerAPICredentials]:
    """Load active user credentials from broker_api_credentials table."""
    result = await db.execute(
        select(BrokerAPICredentials).where(
            BrokerAPICredentials.user_id == user_id,
            BrokerAPICredentials.broker == broker,
            BrokerAPICredentials.is_active == True,
        )
    )
    return result.scalar_one_or_none()


def _creds_not_expired(creds: BrokerAPICredentials) -> bool:
    """Check if credentials have a valid (non-expired) token.

    Returns True if no token_expiry set or token_expiry is in the future.
    """
    if not creds.token_expiry:
        return True
    return datetime.now(timezone.utc) < creds.token_expiry


# Map ORG_ACTIVE_BROKERS DB names to MarketDataSource values
_BROKER_TO_SOURCE = {
    "angelone": MarketDataSource.SMARTAPI,
    "kite": MarketDataSource.KITE,
    "zerodha": MarketDataSource.KITE,
    "upstox": MarketDataSource.UPSTOX,
    "dhan": MarketDataSource.DHAN,
    "fyers": MarketDataSource.FYERS,
    "paytm": MarketDataSource.PAYTM,
}


async def _try_fallback_brokers(
    failed_source: str, user: "User", db: AsyncSession
) -> Optional[str]:
    """Try each ORG_ACTIVE_BROKER as fallback, skipping the one that already failed.

    Returns the MarketDataSource string of the first broker that has credentials,
    or None if all fail.
    """
    from app.constants.brokers import ORG_ACTIVE_BROKERS

    for broker_name in ORG_ACTIVE_BROKERS:
        source = _BROKER_TO_SOURCE.get(broker_name)
        if not source or source == failed_source:
            continue

        if await _ensure_broker_credentials(source, user, db):
            logger.info("Fallback to %s succeeded (was %s)", source, failed_source)
            return source

    logger.warning("All fallback brokers failed after %s", failed_source)
    return None


async def _ensure_broker_credentials(
    broker_type: str, user: User, db: AsyncSession
) -> bool:
    """
    Load broker credentials and set on TickerPool if not already set.

    Returns True if credentials are available, False otherwise.
    For platform-level brokers, loads from .env or user credentials.
    Falls back to alternative broker if credentials unavailable.

    For SmartAPI: also loads canonical→broker token map from broker_instrument_tokens
    table. Without this, SmartAPITickerAdapter cannot translate canonical tokens to
    SmartAPI tokens and subscribes to nothing. Hardcoded index fallback ensures
    NIFTY/BANKNIFTY/FINNIFTY/SENSEX work even if the DB table is empty.
    """
    pool = TickerPool.get_instance()

    # Skip if valid (non-expired) credentials already cached
    if pool.credentials_valid(broker_type):
        return True

    # Clear any expired credentials so we re-fetch below
    pool.clear_expired_credentials()

    if broker_type == MarketDataSource.SMARTAPI:
        # Try user-level SmartAPI credentials first
        credentials = await get_valid_smartapi_credentials(user.id, db, auto_refresh=True)
        if credentials and credentials.access_token and credentials.feed_token:
            # Build token map: canonical int token → (smartapi_str_token, exchange_type)
            # The broker_instrument_tokens table maps canonical_symbol (kite format) to
            # broker-specific tokens. For kite broker rows, broker_token IS the canonical
            # int token. Cross-reference with smartapi rows to build the full map.
            token_map = {}
            try:
                # Get kite rows: canonical_symbol → canonical int token (broker_token)
                kite_result = await db.execute(
                    select(BrokerInstrumentToken).where(
                        BrokerInstrumentToken.broker == "kite"
                    )
                )
                kite_rows = kite_result.scalars().all()
                kite_symbol_to_token = {row.canonical_symbol: row.broker_token for row in kite_rows}

                # Get smartapi rows: canonical_symbol → (smartapi token str, exchange)
                sa_result = await db.execute(
                    select(BrokerInstrumentToken).where(
                        BrokerInstrumentToken.broker == "smartapi"
                    )
                )
                sa_rows = sa_result.scalars().all()

                for row in sa_rows:
                    canonical_int = kite_symbol_to_token.get(row.canonical_symbol)
                    if canonical_int is not None:
                        exchange_type = _exchange_type_for(row.exchange)
                        token_map[int(canonical_int)] = (str(row.broker_token), exchange_type)

                logger.info("[SmartAPI] Loaded %d token mappings from DB", len(token_map))
            except Exception as e:
                logger.warning("[SmartAPI] Failed to load token map from DB: %s", e)

            # Fallback: hardcoded index tokens — ensures header prices always work
            if not token_map:
                token_map = {
                    256265: ("99926000", 1),   # NIFTY 50 (NSE)
                    260105: ("99926009", 1),   # NIFTY BANK (NSE)
                    257801: ("99926037", 1),   # FINNIFTY (NSE)
                    265: ("99919000", 3),      # SENSEX (BSE)
                }
                logger.info("[SmartAPI] Using hardcoded index token fallback (DB table empty)")

            pool.set_credentials("smartapi", {
                "jwt_token": credentials.access_token,
                "api_key": settings.ANGEL_API_KEY,
                "client_id": credentials.client_id,
                "feed_token": credentials.feed_token,
                "token_map": token_map,
                "token_expiry": credentials.token_expiry,
            })
            return True
        return False

    elif broker_type == MarketDataSource.KITE:
        # 1. User's own API credentials from Settings (skip if expired)
        user_creds = await _get_user_broker_creds(user.id, "zerodha", db)
        if user_creds and user_creds.access_token and _creds_not_expired(user_creds):
            pool.set_credentials("kite", {
                "api_key": user_creds.api_key or settings.KITE_API_KEY,
                "access_token": user_creds.access_token,
                "token_expiry": user_creds.token_expiry,
            })
            return True

        # 2. Platform .env credentials
        kite_env_token = getattr(settings, "KITE_ACCESS_TOKEN", "")
        if settings.KITE_API_KEY and kite_env_token:
            pool.set_credentials("kite", {
                "api_key": settings.KITE_API_KEY,
                "access_token": kite_env_token,
            })
            return True

        return False

    elif broker_type == MarketDataSource.DHAN:
        # 1. User's own API credentials from Settings (skip if expired)
        user_creds = await _get_user_broker_creds(user.id, "dhan", db)
        if user_creds and user_creds.access_token and _creds_not_expired(user_creds):
            pool.set_credentials("dhan", {
                "client_id": user_creds.client_id or settings.DHAN_CLIENT_ID,
                "access_token": user_creds.access_token,
                "token_expiry": user_creds.token_expiry,
            })
            return True

        # 2. Platform .env credentials
        if settings.DHAN_CLIENT_ID and settings.DHAN_ACCESS_TOKEN:
            pool.set_credentials("dhan", {
                "client_id": settings.DHAN_CLIENT_ID,
                "access_token": settings.DHAN_ACCESS_TOKEN,
            })
            return True

        return False

    elif broker_type == MarketDataSource.FYERS:
        # 1. User's own API credentials from Settings (skip if expired)
        user_creds = await _get_user_broker_creds(user.id, "fyers", db)
        if user_creds and user_creds.access_token and _creds_not_expired(user_creds):
            pool.set_credentials("fyers", {
                "app_id": user_creds.client_id or settings.FYERS_APP_ID,
                "access_token": user_creds.access_token,
                "token_expiry": user_creds.token_expiry,
            })
            return True

        # 2. Platform .env credentials
        if settings.FYERS_APP_ID and settings.FYERS_ACCESS_TOKEN:
            pool.set_credentials("fyers", {
                "app_id": settings.FYERS_APP_ID,
                "access_token": settings.FYERS_ACCESS_TOKEN,
            })
            return True

        return False

    elif broker_type == MarketDataSource.UPSTOX:
        import time, base64, json as _json
        def _jwt_expired(token: str) -> bool:
            try:
                payload = _json.loads(base64.b64decode(token.split(".")[1] + "=="))
                return int(time.time()) >= payload.get("exp", 0)
            except Exception:
                return True

        # 1. User's own API credentials from Settings
        user_creds = await _get_user_broker_creds(user.id, "upstox", db)
        if user_creds and user_creds.access_token and not _jwt_expired(user_creds.access_token):
            pool.set_credentials("upstox", {
                "api_key": user_creds.api_key or settings.UPSTOX_API_KEY,
                "access_token": user_creds.access_token,
            })
            return True

        # 2. Platform .env token (skip if expired)
        access_token = getattr(settings, "UPSTOX_ACCESS_TOKEN", "")
        api_key = settings.UPSTOX_API_KEY
        if access_token and _jwt_expired(access_token):
            logger.info("[Upstox] Platform token expired")
            access_token = None
            pool._credentials.pop("upstox", None)

        if api_key and access_token:
            pool.set_credentials("upstox", {
                "api_key": api_key,
                "access_token": access_token,
            })
            return True

        return False

    elif broker_type == MarketDataSource.PAYTM:
        # 1. User's own API credentials from Settings (skip if expired)
        # Paytm WebSocket uses public_access_token (stored as feed_token in broker_api_credentials)
        user_creds = await _get_user_broker_creds(user.id, "paytm", db)
        if user_creds and user_creds.feed_token and _creds_not_expired(user_creds):
            pool.set_credentials("paytm", {
                "api_key": user_creds.api_key or settings.PAYTM_API_KEY,
                "public_access_token": user_creds.feed_token,
                "token_expiry": user_creds.token_expiry,
            })
            return True

        # 2. Platform .env credentials
        if settings.PAYTM_API_KEY and settings.PAYTM_PUBLIC_ACCESS_TOKEN:
            pool.set_credentials("paytm", {
                "api_key": settings.PAYTM_API_KEY,
                "public_access_token": settings.PAYTM_PUBLIC_ACCESS_TOKEN,
            })
            return True

        return False

    return False


@router.websocket("/ws/ticks")
async def websocket_ticks(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    """
    WebSocket endpoint for live market data ticks.

    Routes to the appropriate broker adapter based on user preference.
    All broker-specific logic is handled by TickerAdapter implementations.

    Client messages:
        {"action": "subscribe", "tokens": [256265, 260105], "mode": "quote"}
        {"action": "unsubscribe", "tokens": [256265]}
        {"action": "ping"}

    Server messages:
        {"type": "ticks", "data": [{...NormalizedTick...}]}
        {"type": "connected", "source": "smartapi", "connected": true}
        {"type": "subscribed", "tokens": [...], "mode": "quote", "source": "..."}
        {"type": "unsubscribed", "tokens": [...]}
        {"type": "failover", "data": {"from_broker": "...", "to_broker": "..."}}
        {"type": "error", "message": "..."}
        {"type": "pong"}
    """
    user: Optional[User] = None
    user_id: Optional[str] = None
    broker_type: Optional[str] = None
    ticker_router = TickerRouter.get_instance()

    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")

        # Authenticate and load preferences
        async for db in get_db():
            try:
                user = await _authenticate_user(token, db)
                user_id = str(user.id)
                broker_type = await _get_market_data_source(user.id, db)
                logger.info("User %s authenticated, preferred broker: %s", user_id, broker_type)

                # Load credentials for preferred broker
                creds_ok = await _ensure_broker_credentials(broker_type, user, db)

                # Fallback: try each ORG_ACTIVE_BROKER in order
                if not creds_ok:
                    logger.info("Credentials unavailable for %s, trying fallback chain", broker_type)
                    fallback_source = await _try_fallback_brokers(broker_type, user, db)
                    if fallback_source:
                        broker_type = fallback_source
                        creds_ok = True

                if not creds_ok:
                    await websocket.send_json({
                        "type": "error",
                        "message": "No broker credentials available. Please configure market data credentials in Settings.",
                    })
                    await websocket.close()
                    return

            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
                await websocket.close()
                return
            break

        # Register user with ticker router
        await ticker_router.register_user(user_id, websocket, broker_type)
        logger.info("User %s registered with ticker router (broker=%s)", user_id, broker_type)

        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully",
            "source": broker_type,
            "connected": True,
        })

        # Message loop
        while True:
            try:
                raw = await websocket.receive_text()
                data = json.loads(raw)
                action = data.get("action")

                if action == "subscribe":
                    tokens = data.get("tokens", [])
                    mode = data.get("mode", "quote")
                    if not tokens:
                        await websocket.send_json({"type": "error", "message": "No tokens provided"})
                        continue

                    # Ensure tokens are ints (canonical Kite format)
                    tokens = [int(t) for t in tokens]
                    await ticker_router.subscribe(user_id, tokens, mode)

                    await websocket.send_json({
                        "type": "subscribed",
                        "tokens": tokens,
                        "mode": mode,
                        "source": broker_type,
                    })
                    logger.info("User %s subscribed to %d tokens", user_id, len(tokens))

                elif action == "unsubscribe":
                    tokens = data.get("tokens", [])
                    if not tokens:
                        await websocket.send_json({"type": "error", "message": "No tokens provided"})
                        continue

                    tokens = [int(t) for t in tokens]
                    await ticker_router.unsubscribe(user_id, tokens)

                    await websocket.send_json({"type": "unsubscribed", "tokens": tokens})
                    logger.info("User %s unsubscribed from %d tokens", user_id, len(tokens))

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

                else:
                    await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})

            except WebSocketDisconnect:
                logger.info("User %s disconnected", user_id)
                break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON message"})
            except Exception as e:
                logger.error("Error handling message from user %s: %s", user_id, e)
                await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for user %s", user_id)
    except Exception as e:
        logger.error("WebSocket error for user %s: %s", user_id, e)

    finally:
        if user_id:
            await ticker_router.unregister_user(user_id)
            logger.info("User %s cleanup complete", user_id)
