"""Startup Option Chain Warm-up — root-cause fix for 15s cold-fetch latency.

Problem
-------
On a cold backend, the first /api/optionchain/chain request during market hours
takes ~15s because:

  1. OptionChainLiveEngine has no fresh snapshot (no ticks yet).
  2. Falls through to SmartAPIMarketDataAdapter.get_option_chain_snap, which
     opens a *fresh* WebSocketV2 connection per request and waits up to 7s
     for all subscribed strikes to tick — many strikes are illiquid, so it
     hits the 7s timeout.
  3. Falls back to REST fetch of ~100 strikes — another few seconds.

Root cause: no persistent broker subscription keeps ticks flowing into the
OCL engine before the first user request arrives.

Fix
---
At backend startup during market hours (and only then), authenticate to
SmartAPI via the platform adapter, register the current NIFTY expiry with the
OCL engine, and subscribe to the option-chain tokens on TickerPool. Ticks
start streaming immediately, `last_tick_at` becomes fresh within seconds, and
subsequent /api/optionchain/chain requests hit the LIVE_ENGINE fast path
(<100ms) instead of the SmartAPI cold path (~15s).

Fire-and-forget. Any failure is logged and swallowed — never blocks startup.
Runs once per backend lifetime.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from sqlalchemy import select, distinct, and_

from app.database import AsyncSessionLocal
from app.models.instruments import Instrument
from app.models.broker_instrument_tokens import BrokerInstrumentToken
from app.utils.market_hours import is_market_open

logger = logging.getLogger(__name__)

# Underlyings to keep warm. NIFTY is the flagship — 90%+ of user traffic.
# Adding BANKNIFTY roughly doubles the tick load; kept for now but can be
# pared back if tick volume becomes a concern.
_WARMUP_UNDERLYINGS = ("NIFTY", "BANKNIFTY")

# Wait this many seconds after ticker init before starting warmup, so the rest
# of the startup sequence (token refresh, health monitor) finishes first.
_STARTUP_DELAY_SECONDS = 15


def _exchange_type_for(exchange: str) -> int:
    """Map instruments.exchange → SmartAPI exchangeType. Matches websocket.py."""
    ex = (exchange or "").upper()
    if ex == "NSE":
        return 1
    if ex == "NFO":
        return 2
    if ex in ("BSE", "BFO"):
        return 3
    return 2  # sane default for options


async def _current_nearest_expiry(underlying: str, db) -> date | None:
    """Return the nearest upcoming expiry for the underlying, or None."""
    q = (
        select(distinct(Instrument.expiry))
        .where(
            and_(
                Instrument.name == underlying,
                Instrument.exchange.in_(("NFO", "BFO")),
                Instrument.instrument_type.in_(("CE", "PE")),
                Instrument.expiry >= date.today(),
                Instrument.source_broker == "kite",  # canonical rows
            )
        )
        .order_by(Instrument.expiry)
        .limit(1)
    )
    row = await db.execute(q)
    result = row.scalar_one_or_none()
    return result


async def _get_platform_smartapi_credentials(db):
    """Return SmartAPI credentials from any active user, or None.

    Mirrors get_platform_market_data_adapter's SmartAPI branch.
    """
    from app.models.broker_api_credentials import BrokerAPICredentials
    from app.utils.smartapi_utils import get_valid_smartapi_credentials

    result = await db.execute(
        select(BrokerAPICredentials).where(
            BrokerAPICredentials.broker == "angelone",
            BrokerAPICredentials.access_token.isnot(None),
        ).limit(1)
    )
    cred_row = result.scalar_one_or_none()
    if not cred_row:
        return None
    return await get_valid_smartapi_credentials(cred_row.user_id, db, auto_refresh=True)


async def _load_smartapi_token_map(db) -> dict[int, tuple[str, int]]:
    """Build canonical int-token → (smartapi str-token, exchangeType) map.

    Same joining strategy as _ensure_broker_credentials in websocket.py, kept
    duplicated so this warmup module has no circular route dependency.
    """
    token_map: dict[int, tuple[str, int]] = {}

    kite_rows = (await db.execute(
        select(BrokerInstrumentToken).where(BrokerInstrumentToken.broker == "kite")
    )).scalars().all()
    kite_symbol_to_token = {r.canonical_symbol: r.broker_token for r in kite_rows}

    sa_rows = (await db.execute(
        select(BrokerInstrumentToken).where(BrokerInstrumentToken.broker == "smartapi")
    )).scalars().all()

    for row in sa_rows:
        canonical_int = kite_symbol_to_token.get(row.canonical_symbol)
        if canonical_int is not None:
            token_map[int(canonical_int)] = (str(row.broker_token), _exchange_type_for(row.exchange))

    # Fallback: ensure the four indices always work
    token_map.setdefault(256265, ("99926000", 1))
    token_map.setdefault(260105, ("99926009", 1))
    token_map.setdefault(257801, ("99926037", 1))
    token_map.setdefault(265, ("99919000", 3))

    return token_map


async def _resolve_underlying(underlying: str, db) -> tuple[str, list] | None:
    """Return (expiry_str, filtered_instruments) for the given underlying's nearest expiry."""
    expiry = await _current_nearest_expiry(underlying, db)
    if not expiry:
        logger.info("[ChainWarmup] %s: no upcoming expiry found — skipping", underlying)
        return None
    expiry_str = expiry.strftime("%Y-%m-%d")

    from app.services.brokers.market_data.instrument_query import get_nfo_instruments

    all_instruments = await get_nfo_instruments(db, underlying, expiry, broker_type="smartapi")
    if not all_instruments:
        logger.info("[ChainWarmup] %s %s: no instruments in DB — skipping", underlying, expiry_str)
        return None

    # Narrow to ATM ± 25 strikes so we don't blow up TickerPool with 200+ tokens
    # for illiquid strikes that will rarely tick.
    all_strikes = sorted({float(i.strike) for i in all_instruments if i.strike})
    if not all_strikes:
        return None
    mid = all_strikes[len(all_strikes) // 2]
    idx = all_strikes.index(mid)
    lo, hi = max(0, idx - 25), min(len(all_strikes), idx + 26)
    window = set(all_strikes[lo:hi])
    filtered = [i for i in all_instruments if float(i.strike) in window and i.instrument_token]
    return (expiry_str, filtered)


def _extend_smartapi_token_map(pool, underlying: str, instruments: list) -> None:
    """Add identity mappings to TickerPool's smartapi token_map for option tokens.

    broker_instrument_tokens does not have per-option rows (only the four indices),
    so the SmartAPI ticker adapter cannot map canonical → SmartAPI for options via
    its DB-loaded map. We pass SmartAPI tokens directly by extending the map with
    identity entries (smartapi_tok → (smartapi_tok, exchangeType)) BEFORE first
    subscribe (adapter reads map only during connect).
    """
    ex_type = 3 if underlying.upper() == "SENSEX" else 2  # BFO for SENSEX, else NFO
    existing_creds = pool._credentials.get("smartapi", {})  # noqa: SLF001 — safe read
    if not existing_creds:
        return
    token_map = existing_creds.get("token_map", {})
    for inst in instruments:
        tok = int(inst.instrument_token)
        token_map[tok] = (str(tok), ex_type)
    existing_creds["token_map"] = token_map
    pool.set_credentials("smartapi", existing_creds)


async def warmup_option_chains() -> None:
    """Fire-and-forget: pre-warm NIFTY + BANKNIFTY current-expiry chains at startup.

    Safe to call unconditionally — internally gates on is_market_open() and
    swallows all exceptions.
    """
    try:
        await asyncio.sleep(_STARTUP_DELAY_SECONDS)
        if not is_market_open():
            logger.info("[ChainWarmup] Market closed — skipping option chain warmup")
            return

        # Set SmartAPI credentials on TickerPool if not already set
        from app.services.brokers.market_data.ticker import TickerPool
        from app.config import settings

        pool = TickerPool.get_instance()

        async with AsyncSessionLocal() as db:
            if not pool.credentials_valid("smartapi"):
                creds = await _get_platform_smartapi_credentials(db)
                if not creds:
                    logger.info("[ChainWarmup] No SmartAPI credentials available — skipping")
                    return
                token_map = await _load_smartapi_token_map(db)
                pool.set_credentials("smartapi", {
                    "jwt_token": creds.access_token,
                    "api_key": settings.ANGEL_API_KEY,
                    "client_id": creds.client_id,
                    "feed_token": creds.feed_token,
                    "token_map": token_map,
                    "token_expiry": creds.token_expiry,
                })
                logger.info("[ChainWarmup] SmartAPI credentials set on TickerPool")

            # Phase 1: resolve every underlying's chain (expiry + instruments) BEFORE
            # any subscription. Phase 2: extend the token_map for all of them together.
            # Phase 3: register + subscribe. This ordering is REQUIRED because the
            # SmartAPI ticker adapter reads the token_map only once during connect().
            resolved: list[tuple[str, str, list]] = []
            for ul in _WARMUP_UNDERLYINGS:
                try:
                    r = await _resolve_underlying(ul, db)
                    if r:
                        expiry_str, instruments = r
                        resolved.append((ul, expiry_str, instruments))
                except Exception as e:
                    logger.warning("[ChainWarmup] %s resolve failed: %s", ul, e)

            for ul, _expiry, instruments in resolved:
                _extend_smartapi_token_map(pool, ul, instruments)

            total_subscribed = 0
            from app.services.options.option_chain_live_engine import OptionChainLiveEngine
            engine = OptionChainLiveEngine.get_instance()
            for ul, expiry_str, instruments in resolved:
                try:
                    engine_tokens = [
                        {
                            "token": int(i.instrument_token),
                            "strike": float(i.strike),
                            "side": i.instrument_type,
                            "tradingsymbol": i.tradingsymbol,
                        }
                        for i in instruments
                    ]
                    engine.register_chain(ul, expiry_str, engine_tokens)
                    tokens = [int(i.instrument_token) for i in instruments]
                    await pool.subscribe("smartapi", tokens, mode="quote")
                    total_subscribed += len(tokens)
                    logger.info(
                        "[ChainWarmup] %s %s: registered + subscribed %d option tokens",
                        ul, expiry_str, len(tokens),
                    )
                except Exception as e:
                    logger.warning("[ChainWarmup] %s subscribe failed: %s", ul, e)

        logger.info(
            "[ChainWarmup] Complete — %d tokens subscribed. Option chain fast-path is now live.",
            total_subscribed,
        )
    except Exception as e:
        logger.warning("[ChainWarmup] Failed (non-fatal): %s", e, exc_info=True)
