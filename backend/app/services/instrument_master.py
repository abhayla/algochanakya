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
from app.models.broker_instrument_tokens import BrokerInstrumentToken
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
    async def populate_broker_token_mappings(db: AsyncSession) -> int:
        """Populate broker_instrument_tokens for SmartAPI using the instrument master.

        Queries all NFO options from the instruments table (preferring source_broker='kite',
        falling back to all sources if none found), resolves each canonical symbol to a
        SmartAPI token via the SmartAPI instrument master, and upserts into
        broker_instrument_tokens.

        Returns:
            Number of SmartAPI token mappings stored.
        Raises:
            RuntimeError: If SmartAPI instrument master download fails and no instruments
                          can be loaded. Callers should catch this and log as a warning.
        """
        try:
            from app.services.legacy.smartapi_instruments import get_smartapi_instruments
            smartapi_instr = get_smartapi_instruments()

            # Ensure SmartAPI instrument master is loaded.
            # If the in-memory singleton is empty (pre-warm didn't run or failed),
            # download it now. Raise a clear error if the download fails so callers
            # can log a meaningful warning instead of silently getting 0 mappings.
            if not smartapi_instr._instruments:
                logger.info("[InstrumentMaster] SmartAPI instruments not in memory, downloading...")
                count = await smartapi_instr.download_master()
                if not count or not smartapi_instr._instruments:
                    raise RuntimeError(
                        "SmartAPI instrument master download returned 0 instruments. "
                        "Check ANGEL_API_KEY and network connectivity."
                    )
                logger.info(f"[InstrumentMaster] Loaded {count} SmartAPI instruments")

            today = date.today()

            # Fetch all non-expired NFO options from DB, preferring kite-sourced instruments.
            # Kite instruments use canonical symbol format that SmartAPI lookup understands.
            result = await db.execute(
                select(InstrumentModel).where(
                    and_(
                        InstrumentModel.exchange == "NFO",
                        InstrumentModel.instrument_type.in_(["CE", "PE"]),
                        InstrumentModel.expiry >= today,
                        InstrumentModel.source_broker == "kite",
                    )
                )
            )
            kite_instruments = result.scalars().all()

            # Fallback: if no kite-sourced instruments found, use all available sources.
            # This handles dev environments where instruments were downloaded via SmartAPI adapter.
            if not kite_instruments:
                logger.warning(
                    "[InstrumentMaster] No kite-sourced NFO instruments found in DB. "
                    "Trying all source brokers as fallback..."
                )
                result = await db.execute(
                    select(InstrumentModel).where(
                        and_(
                            InstrumentModel.exchange == "NFO",
                            InstrumentModel.instrument_type.in_(["CE", "PE"]),
                            InstrumentModel.expiry >= today,
                        )
                    )
                )
                kite_instruments = result.scalars().all()

            if not kite_instruments:
                raise RuntimeError(
                    "No NFO option instruments found in DB for any source broker. "
                    "Run InstrumentMasterService.refresh_from_adapter() first."
                )

            logger.info(
                f"[InstrumentMaster] Resolving SmartAPI tokens for "
                f"{len(kite_instruments)} instruments"
            )

            mappings: List[dict] = []
            missing = 0

            for inst in kite_instruments:
                canonical_symbol = inst.tradingsymbol
                token_str = await smartapi_instr.lookup_token(canonical_symbol, "NFO")
                if not token_str:
                    missing += 1
                    continue

                underlying = (
                    InstrumentMasterService._extract_underlying(canonical_symbol) or ""
                )
                mappings.append({
                    "canonical_symbol": canonical_symbol,
                    "broker": "smartapi",
                    "broker_symbol": canonical_symbol,  # SmartAPI uses same canonical format
                    "broker_token": int(token_str),
                    "exchange": "NFO",
                    "underlying": underlying,
                    "expiry": inst.expiry,
                    "last_updated": datetime.utcnow(),
                })

            if not mappings:
                logger.warning(
                    f"[InstrumentMaster] No SmartAPI token mappings found "
                    f"({missing} symbols unresolved)"
                )
                return 0

            # Batch upsert
            BATCH_SIZE = 2000
            total_stored = 0
            for i in range(0, len(mappings), BATCH_SIZE):
                batch = mappings[i : i + BATCH_SIZE]
                stmt = insert(BrokerInstrumentToken).values(batch)
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_symbol_broker",
                    set_={
                        "broker_token": stmt.excluded.broker_token,
                        "broker_symbol": stmt.excluded.broker_symbol,
                        "expiry": stmt.excluded.expiry,
                        "last_updated": stmt.excluded.last_updated,
                    },
                )
                await db.execute(stmt)
                total_stored += len(batch)

            await db.commit()

            logger.info(
                f"[InstrumentMaster] Stored {total_stored} SmartAPI token mappings "
                f"({missing} unresolved)"
            )
            return total_stored

        except RuntimeError:
            # Re-raise RuntimeError so callers get a descriptive message
            raise
        except Exception as e:
            logger.error(
                f"[InstrumentMaster] populate_broker_token_mappings failed unexpectedly: {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"populate_broker_token_mappings failed: {e}"
            ) from e

    @staticmethod
    async def ensure_mappings_fresh(db: AsyncSession) -> bool:
        """Check if broker_instrument_tokens has mappings for the current week's expiry.

        If the current trading expiry is missing, re-runs populate_broker_token_mappings.
        Caches freshness check result in Redis for 1 hour.

        Returns True if mappings are fresh (or were refreshed), False on failure.
        """
        redis_key = "instrument_mappings:freshness_checked"
        try:
            redis = await get_redis()
            cached = await redis.get(redis_key)
            if cached:
                return True
        except Exception:
            pass

        try:
            today = date.today()
            # Find current week's Thursday (NSE weekly expiry day)
            days_to_thursday = (3 - today.weekday()) % 7
            if days_to_thursday == 0 and today.weekday() == 3:
                current_expiry = today
            else:
                from datetime import timedelta
                current_expiry = today + timedelta(days=days_to_thursday)

            # Check if any mapping exists for the current expiry
            result = await db.execute(
                select(func.count()).select_from(BrokerInstrumentToken).where(
                    and_(
                        BrokerInstrumentToken.broker == "smartapi",
                        BrokerInstrumentToken.expiry == current_expiry,
                    )
                )
            )
            count = result.scalar() or 0

            if count == 0:
                logger.info(
                    "[InstrumentMaster] No mappings for expiry %s — repopulating",
                    current_expiry,
                )
                stored = await InstrumentMasterService.populate_broker_token_mappings(db)
                logger.info("[InstrumentMaster] Repopulated %d mappings", stored)

            # Cache the check for 1 hour
            try:
                redis = await get_redis()
                await redis.setex(redis_key, 3600, "1")
            except Exception:
                pass

            return True
        except Exception as e:
            logger.error("[InstrumentMaster] ensure_mappings_fresh failed: %s", e)
            return False

    @staticmethod
    def _extract_underlying(symbol: str) -> Optional[str]:
        """Extract underlying name from a canonical symbol like NIFTY25APR25000CE."""
        if not symbol:
            return None
        m = re.match(r"^([A-Z]+?)(?:\d{2}[A-Z]{3}|\d{2}[A-Z]\d{2})", symbol)
        return m.group(1) if m else None
