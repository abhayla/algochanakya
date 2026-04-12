"""
Centralized NFO instrument queries with source_broker filtering.

Prevents the duplicate-row problem where the instruments table has rows from
multiple broker sources (kite, smartapi) with different instrument_token values.

Usage:
    from app.services.brokers.market_data.instrument_query import (
        get_nfo_instruments,
        get_single_instrument,
        preferred_source_brokers,
    )

    instruments = await get_nfo_instruments(db, "NIFTY", expiry, broker_type="upstox")
"""

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instruments import Instrument

logger = logging.getLogger(__name__)

# Broker adapter type → source_broker values to query, in preference order.
# SmartAPI and Upstox share NSE exchange tokens (confirmed April 2026).
# Kite uses its own internal instrument_token (different numbering).
_SOURCE_BROKER_PREFERENCE = {
    "smartapi": ["smartapi", "kite"],
    "upstox":   ["smartapi", "kite"],
    "kite":     ["kite", "smartapi"],
    "dhan":     ["smartapi", "kite"],
    "fyers":    ["smartapi", "kite"],
    "paytm":    ["smartapi", "kite"],
}


def preferred_source_brokers(broker_type: str) -> List[str]:
    """Return source_broker values to query, in preference order."""
    return _SOURCE_BROKER_PREFERENCE.get(broker_type.lower(), ["kite", "smartapi"])


async def get_nfo_instruments(
    db: AsyncSession,
    underlying: str,
    expiry: date,
    broker_type: str = "smartapi",
) -> List[Instrument]:
    """Fetch NFO option instruments with broker-aware source filtering.

    Tries preferred source_broker first, falls back if empty.
    Returns only CE/PE instruments with non-null strike.

    Args:
        db: Async database session.
        underlying: Underlying name (e.g., "NIFTY", "BANKNIFTY").
        expiry: Expiry date to filter by.
        broker_type: Active market data broker type (determines source_broker preference).

    Returns:
        List of Instrument rows from a single source_broker (no duplicates).
    """
    sources = preferred_source_brokers(broker_type)

    for source in sources:
        result = await db.execute(
            select(Instrument).where(
                and_(
                    Instrument.name == underlying,
                    Instrument.exchange == "NFO",
                    Instrument.instrument_type.in_(["CE", "PE"]),
                    Instrument.expiry == expiry,
                    Instrument.strike.isnot(None),
                    Instrument.source_broker == source,
                )
            )
        )
        instruments = result.scalars().all()
        if instruments:
            logger.debug(
                f"[InstrumentQuery] {len(instruments)} instruments for "
                f"{underlying} {expiry} from source_broker={source}"
            )
            return instruments

    logger.warning(
        f"[InstrumentQuery] No instruments found for {underlying} {expiry} "
        f"across sources {sources}"
    )
    return []


async def get_single_instrument(
    db: AsyncSession,
    underlying: str,
    expiry: date,
    strike,
    contract_type: str,
    broker_type: str = "smartapi",
) -> Optional[Instrument]:
    """Fetch a single instrument with source_broker filtering.

    Prevents scalar_one_or_none() crash when duplicate rows exist
    from multiple source_brokers.

    Args:
        db: Async database session.
        underlying: Underlying name.
        expiry: Expiry date.
        strike: Strike price.
        contract_type: "CE" or "PE".
        broker_type: Active market data broker type.

    Returns:
        Single Instrument or None.
    """
    sources = preferred_source_brokers(broker_type)

    for source in sources:
        result = await db.execute(
            select(Instrument).where(
                and_(
                    Instrument.name == underlying,
                    Instrument.exchange == "NFO",
                    Instrument.expiry == expiry,
                    Instrument.strike == strike,
                    Instrument.instrument_type == contract_type,
                    Instrument.source_broker == source,
                )
            )
        )
        inst = result.scalar_one_or_none()
        if inst:
            return inst

    return None
