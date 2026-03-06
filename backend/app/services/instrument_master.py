"""
Broker-Agnostic Instrument Master Service

Downloads instruments from any MarketDataBrokerAdapter and populates the DB.
Replaces the Kite-only instrument download with a broker-agnostic approach.
"""
import logging
import re
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.instruments import Instrument as InstrumentModel
from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    Instrument as AdapterInstrument,
)
from app.database import get_redis

logger = logging.getLogger(__name__)

INSTRUMENTS_CACHE_KEY = "instruments:last_updated"


class InstrumentMasterService:
    """Broker-agnostic service for populating the instruments DB table."""

    @staticmethod
    async def refresh_from_adapter(
        adapter: MarketDataBrokerAdapter,
        broker_name: str,
        db: AsyncSession,
        exchanges: List[str] = None,
    ) -> int:
        """Download instruments from adapter and upsert into DB.

        Args:
            adapter: Any MarketDataBrokerAdapter instance.
            broker_name: Broker identifier (e.g. "smartapi", "kite").
            db: Async database session.
            exchanges: Exchanges to download (default: ["NFO"]).

        Returns:
            Number of option instruments stored.
        """
        if exchanges is None:
            exchanges = ["NFO"]

        today = date.today()

        # Clean up expired instruments for this broker
        await db.execute(
            delete(InstrumentModel).where(
                and_(
                    InstrumentModel.source_broker == broker_name,
                    InstrumentModel.expiry < today,
                )
            )
        )

        all_options: List[dict] = []

        for exchange in exchanges:
            try:
                raw_instruments = await adapter.get_instruments(exchange)
                logger.info(
                    f"[InstrumentMaster] Downloaded {len(raw_instruments)} instruments "
                    f"from {broker_name}/{exchange}"
                )
            except Exception as e:
                logger.error(
                    f"[InstrumentMaster] Failed to get instruments from "
                    f"{broker_name}/{exchange}: {e}"
                )
                continue

            for inst in raw_instruments:
                opt_type = inst.option_type
                if opt_type not in ("CE", "PE"):
                    continue
                if inst.expiry is None or inst.expiry < today:
                    continue
                if inst.strike is None or inst.strike <= 0:
                    continue

                # Extract underlying: prefer adapter field, fallback to name, then parse from symbol
                underlying = (
                    inst.underlying
                    or inst.name
                    or InstrumentMasterService._extract_underlying(inst.canonical_symbol)
                    or ""
                )

                all_options.append({
                    "instrument_token": inst.instrument_token,
                    "tradingsymbol": inst.canonical_symbol,
                    "name": underlying,
                    "exchange": exchange,
                    "instrument_type": opt_type,  # Store CE/PE so existing queries work
                    "option_type": opt_type,
                    "strike": inst.strike,
                    "expiry": inst.expiry,
                    "lot_size": inst.lot_size,
                    "source_broker": broker_name,
                })

        if not all_options:
            logger.warning(
                f"[InstrumentMaster] No option instruments found from {broker_name}"
            )
            return 0

        # Batch upsert
        BATCH_SIZE = 2000
        total_stored = 0

        for i in range(0, len(all_options), BATCH_SIZE):
            batch = all_options[i : i + BATCH_SIZE]
            stmt = insert(InstrumentModel).values(batch)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_instrument_token_source_broker",
                set_={
                    "tradingsymbol": stmt.excluded.tradingsymbol,
                    "name": stmt.excluded.name,
                    "exchange": stmt.excluded.exchange,
                    "instrument_type": stmt.excluded.instrument_type,
                    "option_type": stmt.excluded.option_type,
                    "strike": stmt.excluded.strike,
                    "expiry": stmt.excluded.expiry,
                    "lot_size": stmt.excluded.lot_size,
                    "last_updated": datetime.utcnow(),
                },
            )
            await db.execute(stmt)
            total_stored += len(batch)

        await db.commit()

        # Update cache timestamp
        try:
            redis = await get_redis()
            await redis.set(INSTRUMENTS_CACHE_KEY, datetime.utcnow().isoformat())
        except Exception:
            pass

        logger.info(
            f"[InstrumentMaster] Stored {total_stored} option instruments "
            f"from {broker_name}"
        )
        return total_stored

    @staticmethod
    async def should_refresh(db: AsyncSession) -> bool:
        """Check if instruments should be refreshed (empty or >24h stale)."""
        try:
            # Check if table has any NFO options
            result = await db.execute(
                select(func.count(InstrumentModel.id)).where(
                    and_(
                        InstrumentModel.exchange == "NFO",
                        InstrumentModel.instrument_type.in_(["CE", "PE"]),
                        InstrumentModel.expiry >= date.today(),
                    )
                )
            )
            count = result.scalar()

            if not count or count == 0:
                return True

            # Check staleness via Redis
            redis = await get_redis()
            last_updated = await redis.get(INSTRUMENTS_CACHE_KEY)

            if not last_updated:
                return True

            last_dt = datetime.fromisoformat(last_updated)
            hours_since = (datetime.utcnow() - last_dt).total_seconds() / 3600
            return hours_since > 24

        except Exception as e:
            logger.warning(f"[InstrumentMaster] Could not check refresh status: {e}")
            return True

    @staticmethod
    def _extract_underlying(symbol: str) -> Optional[str]:
        """Extract underlying name from a canonical symbol like NIFTY25APR25000CE."""
        if not symbol:
            return None
        m = re.match(r"^([A-Z]+?)(?:\d{2}[A-Z]{3}|\d{2}[A-Z]\d{2})", symbol)
        return m.group(1) if m else None
