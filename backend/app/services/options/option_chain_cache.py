"""
Option Chain Cache Service.

Redis response cache + request coalescing + platform adapter singleton.
Cache key: optionchain:{underlying}:{expiry}
TTL: 3s during market hours (short-lived dedup), seconds until next market open after hours.
"""
import asyncio
import json
import logging
import random
import time
from typing import Any, Callable, Optional

from app.database import get_redis
from app.utils.market_hours import is_market_open, get_next_market_open, _ist_now
from app.services.brokers.market_data.factory import get_platform_market_data_adapter

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "optionchain"

# NSE refreshes OI every ~3 minutes; 3s staleness is safe for display (not order execution).
# Request coalescing handles thundering herd within this window.
LIVE_MARKET_CACHE_TTL = 3


# ---------------------------------------------------------------------------
# TTL
# ---------------------------------------------------------------------------

def get_cache_ttl_seconds() -> int:
    """Cache TTL: 3s during market hours, seconds-until-open after hours."""
    if is_market_open():
        return LIVE_MARKET_CACHE_TTL
    now = _ist_now()
    next_open = get_next_market_open(now)
    ttl = int((next_open - now).total_seconds())
    ttl = max(ttl, 60)  # Floor at 60s to avoid degenerate TTLs near open
    # ±10% jitter to prevent cache stampede at market open
    ttl = int(ttl * (0.9 + 0.2 * random.random()))
    return max(ttl, 60)


def _cache_key(underlying: str, expiry: str) -> str:
    return f"{CACHE_KEY_PREFIX}:{underlying}:{expiry}"


# ---------------------------------------------------------------------------
# Redis read / write (fault-tolerant — never raises on Redis failure)
# ---------------------------------------------------------------------------

async def get_cached_response(underlying: str, expiry: str) -> Optional[dict]:
    """Check Redis for a cached option chain response. Returns None on miss or failure."""
    try:
        redis = await get_redis()
        if redis is None:
            return None
        cached = await redis.get(_cache_key(underlying, expiry))
        if cached:
            logger.debug("[Cache] HIT %s:%s", underlying, expiry)
            return json.loads(cached)
    except Exception as e:
        logger.warning("[Cache] Redis read failed: %s", e)
    return None


async def store_cached_response(underlying: str, expiry: str, result: dict) -> None:
    """Store computed response in Redis with appropriate TTL. No-op if Redis is down."""
    ttl = get_cache_ttl_seconds()
    try:
        redis = await get_redis()
        if redis is None:
            return
        payload = json.dumps(result, default=str)
        await redis.setex(_cache_key(underlying, expiry), ttl, payload)
        logger.info("[Cache] Stored %s:%s TTL=%ds (%dKB)", underlying, expiry, ttl, len(payload) // 1024)
    except Exception as e:
        logger.warning("[Cache] Redis write failed: %s", e)


# ---------------------------------------------------------------------------
# Request coalescing — prevents thundering herd on cache miss
# ---------------------------------------------------------------------------

_inflight: dict[str, asyncio.Future] = {}


async def get_or_compute(
    underlying: str,
    expiry: str,
    compute_fn: Callable[[], Any],
) -> dict:
    """
    Cache-first with request coalescing.

    1. Redis hit → return immediately
    2. Another request already computing this key → await its result
    3. First request → call compute_fn(), cache result, return
    """
    # 1. Redis hit
    cached = await get_cached_response(underlying, expiry)
    if cached is not None:
        return cached

    # 2. Coalesce: if another coroutine is already computing, await it
    key = _cache_key(underlying, expiry)
    if key in _inflight:
        return await _inflight[key]

    # 3. I'm the first — compute, cache, serve
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    _inflight[key] = future
    try:
        result = await compute_fn()
        await store_cached_response(underlying, expiry, result)
        future.set_result(result)
        return result
    except Exception as e:
        future.set_exception(e)
        raise
    finally:
        _inflight.pop(key, None)


# ---------------------------------------------------------------------------
# Platform adapter singleton — avoids per-request adapter creation
# ---------------------------------------------------------------------------

_cached_adapter: Optional[tuple] = None  # (adapter, created_at_timestamp)
_ADAPTER_TTL = 3600  # 1 hour


async def get_cached_platform_adapter(db):
    """Return a cached platform-level market data adapter, refreshing if stale."""
    global _cached_adapter
    now = time.time()
    if _cached_adapter is not None:
        adapter, created_at = _cached_adapter
        if now - created_at < _ADAPTER_TTL and adapter.is_connected:
            return adapter
    adapter = await get_platform_market_data_adapter(db)
    _cached_adapter = (adapter, now)
    return adapter
