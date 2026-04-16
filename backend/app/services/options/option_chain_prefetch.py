"""
Option Chain Background Prefetch Service.

On the first after-hours request for ANY underlying, fires a background task
that fetches ALL underlyings x ALL expiries and warms the Redis cache.

Design decisions (from spec):
- No cron job — lazy fan-out triggered by first after-hours request
- Deduplication via _prefetch_session_key — one prefetch per market close session
- Throttled at ~1 request per 2 seconds to respect NSE rate limits
- Uses AsyncSessionLocal for own DB session (runs outside request lifecycle)
- Uses platform adapter singleton (no user context needed)
"""
import asyncio
import logging
from datetime import date

from sqlalchemy import select, distinct, and_

from app.database import AsyncSessionLocal
from app.models.instruments import Instrument
from app.utils.market_hours import is_market_open, get_last_trading_close
from app.services.options.option_chain_cache import (
    get_or_compute,
    get_cached_platform_adapter,
)

logger = logging.getLogger(__name__)

# Deduplication: tracks which market-close session we've already prefetched for.
# Reset when a new trading session closes (i.e., get_last_trading_close() changes).
_prefetch_session_key: str | None = None
_prefetch_lock = asyncio.Lock()

# Underlyings to prefetch
_PREFETCH_UNDERLYINGS = ["NIFTY", "BANKNIFTY", "FINNIFTY"]

# Throttle delay between NSE API calls (seconds)
_THROTTLE_SECONDS = 2.0


async def _get_expiries_for_underlying(underlying: str) -> list[date]:
    """Query DB for available expiry dates for an underlying."""
    async with AsyncSessionLocal() as db:
        query = (
            select(distinct(Instrument.expiry))
            .where(
                and_(
                    Instrument.name == underlying,
                    Instrument.exchange == "NFO",
                    Instrument.instrument_type.in_(["CE", "PE"]),
                    Instrument.expiry >= date.today(),
                    Instrument.source_broker == "kite",
                )
            )
            .order_by(Instrument.expiry)
        )
        result = await db.execute(query)
        return [row[0] for row in result.fetchall() if row[0] is not None]


async def _prefetch_all() -> None:
    """Fan-out: fetch all underlyings x all expiries, warming the Redis cache."""
    total = 0
    errors = 0

    for underlying in _PREFETCH_UNDERLYINGS:
        try:
            expiry_dates = await _get_expiries_for_underlying(underlying)
        except Exception as e:
            logger.warning("[Prefetch] Failed to get expiries for %s: %s", underlying, e)
            continue

        if not expiry_dates:
            logger.info("[Prefetch] No expiries found for %s, skipping", underlying)
            continue

        logger.info(
            "[Prefetch] %s: %d expiries to warm", underlying, len(expiry_dates)
        )

        for expiry_date in expiry_dates:
            expiry_str = expiry_date.strftime("%Y-%m-%d")
            try:
                async def make_compute(ul=underlying, exp=expiry_str, exp_d=expiry_date):
                    """Closure to capture loop variables for the compute function."""
                    # Import here to avoid circular import at module level
                    from app.api.routes.optionchain import _compute_option_chain

                    async with AsyncSessionLocal() as db:
                        return await _compute_option_chain(
                            underlying=ul,
                            expiry=exp,
                            expiry_date=exp_d,
                            user=None,
                            db=db,
                        )

                await get_or_compute(underlying, expiry_str, make_compute)
                total += 1
                logger.debug("[Prefetch] Warmed %s:%s", underlying, expiry_str)
            except Exception as e:
                errors += 1
                logger.warning(
                    "[Prefetch] Failed %s:%s — %s", underlying, expiry_str, e
                )

            # Throttle to avoid NSE rate-limiting
            await asyncio.sleep(_THROTTLE_SECONDS)

    logger.info(
        "[Prefetch] Complete — %d cached, %d errors", total, errors
    )


async def trigger_prefetch_if_needed() -> None:
    """
    Trigger a background prefetch if we haven't already for this market-close session.

    Called from the /chain route handler after any after-hours request.
    Uses get_last_trading_close() as the session key — if the market closed
    today at 15:35, all after-hours requests until next open share the same key.
    """
    if is_market_open():
        return

    session_key = get_last_trading_close().isoformat()

    global _prefetch_session_key

    # Fast path: already prefetched for this session
    if _prefetch_session_key == session_key:
        return

    async with _prefetch_lock:
        # Double-check after acquiring lock
        if _prefetch_session_key == session_key:
            return

        _prefetch_session_key = session_key
        logger.info("[Prefetch] Starting fan-out for session %s", session_key)

    # Run outside the lock — the lock only guards the dedup check
    try:
        await _prefetch_all()
    except Exception as e:
        logger.error("[Prefetch] Fan-out failed: %s", e)
        # Reset so next request retries
        _prefetch_session_key = None
