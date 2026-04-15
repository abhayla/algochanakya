"""
Data Source Warmup Service

Proactively verifies and refreshes platform data source broker tokens.
Called as a fire-and-forget background task after every user login.

By the time the frontend loads (~2-3s), data sources should be ready.
"""
import asyncio
import logging
import os
from typing import Dict
from uuid import UUID

from app.constants.brokers import ORG_ACTIVE_BROKERS
from app.services.brokers.market_data.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


def schedule_warmup():
    """Fire-and-forget warmup. Safe to call during shutdown (no-ops gracefully)."""
    try:
        asyncio.create_task(warm_data_sources())
    except RuntimeError:
        logger.debug("[Warmup] Skipped — no running event loop")


async def warm_data_sources() -> Dict[str, str]:
    """Verify and refresh all platform data source brokers.

    Returns dict of {broker: status} where status is one of:
    'healthy', 'refreshed', 'failed', or 'error: <message>'.

    Non-blocking — catches all exceptions so login is never delayed.
    """
    results: Dict[str, str] = {}

    for broker in ORG_ACTIVE_BROKERS:
        try:
            adapter = _create_platform_adapter(broker)
            await adapter.get_best_price(["NIFTY"])
            results[broker] = "healthy"
        except AuthenticationError:
            refreshed = await _refresh_platform_broker(broker)
            results[broker] = "refreshed" if refreshed else "failed"
        except Exception as e:
            results[broker] = f"error: {e}"

    try:
        await _ensure_instrument_mappings_fresh()
    except Exception as e:
        logger.warning("[Warmup] Instrument freshness check failed: %s", e)

    logger.info("[Warmup] Data source status: %s", results)
    return results


def _create_platform_adapter(broker: str):
    """Create a market data adapter using platform-level .env credentials.

    Mirrors the env-based adapter creation in factory.get_platform_market_data_adapter()
    but for a specific broker rather than the failover chain.
    """
    from app.config import settings

    null_user = UUID(int=0)

    if broker in ("angelone", "smartapi"):
        from app.services.brokers.market_data.market_data_base import SmartAPIMarketDataCredentials
        from app.services.brokers.market_data.smartapi_adapter import SmartAPIMarketDataAdapter

        api_key = getattr(settings, "ANGEL_API_KEY", "")
        jwt_token = getattr(settings, "ANGEL_JWT_TOKEN", "") or ""
        feed_token = getattr(settings, "ANGEL_FEED_TOKEN", "") or ""

        if not api_key:
            raise RuntimeError("No ANGEL_API_KEY in .env")

        creds = SmartAPIMarketDataCredentials(
            broker_type="smartapi", user_id=null_user,
            client_id=getattr(settings, "ANGEL_CLIENT_ID", ""),
            jwt_token=jwt_token, feed_token=feed_token,
        )
        return SmartAPIMarketDataAdapter(creds, db=None)

    elif broker == "upstox":
        from app.services.brokers.market_data.market_data_base import UpstoxMarketDataCredentials
        from app.services.brokers.market_data.upstox_adapter import UpstoxMarketDataAdapter

        api_key = os.environ.get("UPSTOX_API_KEY", "")
        access_token = os.environ.get("UPSTOX_ACCESS_TOKEN", "") or getattr(settings, "UPSTOX_ACCESS_TOKEN", "")

        if not access_token:
            raise RuntimeError("No UPSTOX_ACCESS_TOKEN in .env")

        creds = UpstoxMarketDataCredentials(
            broker_type="upstox", user_id=null_user,
            api_key=api_key, access_token=access_token,
        )
        return UpstoxMarketDataAdapter(creds, db=None)

    else:
        raise RuntimeError(f"Unsupported platform broker: {broker}")


async def _refresh_platform_broker(broker: str) -> bool:
    """Refresh a platform broker's token. Returns True on success."""
    from app.services.brokers.platform_token_refresh import refresh_broker_token
    try:
        return await refresh_broker_token(broker)
    except Exception as e:
        logger.error("[Warmup] %s refresh failed: %s", broker, e)
        return False


async def _ensure_instrument_mappings_fresh():
    """Check and refresh broker_instrument_tokens if current expiry is missing."""
    from app.services.instrument_master import InstrumentMasterService
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await InstrumentMasterService.ensure_mappings_fresh(db)
