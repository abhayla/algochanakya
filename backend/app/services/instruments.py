"""
Instrument Master Service

Downloads and manages Kite Connect instrument master data.
"""
import csv
import io
import logging
from datetime import datetime, date
from typing import List, Optional
from decimal import Decimal

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.dialects.postgresql import insert

from app.models import Instrument
from app.database import get_redis

logger = logging.getLogger(__name__)

KITE_INSTRUMENTS_URL = "https://api.kite.trade/instruments"
INSTRUMENTS_CACHE_KEY = "instruments:last_updated"


class InstrumentService:
    """Service for managing instruments."""

    @staticmethod
    async def download_instruments() -> List[dict]:
        """
        Download instruments CSV from Kite API.

        Returns:
            List of instrument dictionaries
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(KITE_INSTRUMENTS_URL, timeout=60.0)
                response.raise_for_status()

                # Parse CSV
                csv_content = response.text
                reader = csv.DictReader(io.StringIO(csv_content))

                instruments = []
                for row in reader:
                    try:
                        # Parse instrument data
                        instrument = {
                            "instrument_token": int(row["instrument_token"]),
                            "exchange_token": int(row["exchange_token"]) if row.get("exchange_token") else None,
                            "tradingsymbol": row["tradingsymbol"],
                            "name": row.get("name", ""),
                            "exchange": row["exchange"],
                            "segment": row.get("segment", ""),
                            "instrument_type": row.get("instrument_type", ""),
                            "strike": Decimal(row["strike"]) if row.get("strike") and row["strike"] != "0" else None,
                            "expiry": datetime.strptime(row["expiry"], "%Y-%m-%d").date() if row.get("expiry") else None,
                            "lot_size": int(row.get("lot_size", 1)),
                            "tick_size": Decimal(row.get("tick_size", "0.05")),
                        }
                        instruments.append(instrument)
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Skipping invalid instrument row: {e}")
                        continue

                logger.info(f"Downloaded {len(instruments)} instruments from Kite")
                return instruments

        except Exception as e:
            logger.error(f"Failed to download instruments: {e}")
            raise

    @staticmethod
    async def parse_and_store_instruments(db: AsyncSession, instruments: List[dict]) -> int:
        """
        Parse and store instruments in database using upsert.

        Args:
            db: Database session
            instruments: List of instrument dictionaries

        Returns:
            Number of instruments stored
        """
        try:
            # Batch insert/update using PostgreSQL upsert
            if not instruments:
                return 0

            # Create insert statement with on conflict update
            stmt = insert(Instrument).values(instruments)
            stmt = stmt.on_conflict_do_update(
                index_elements=['instrument_token'],
                set_={
                    'exchange_token': stmt.excluded.exchange_token,
                    'tradingsymbol': stmt.excluded.tradingsymbol,
                    'name': stmt.excluded.name,
                    'exchange': stmt.excluded.exchange,
                    'segment': stmt.excluded.segment,
                    'instrument_type': stmt.excluded.instrument_type,
                    'strike': stmt.excluded.strike,
                    'expiry': stmt.excluded.expiry,
                    'lot_size': stmt.excluded.lot_size,
                    'tick_size': stmt.excluded.tick_size,
                    'last_updated': datetime.utcnow(),
                }
            )

            await db.execute(stmt)
            await db.commit()

            # Update cache timestamp
            redis = await get_redis()
            await redis.set(INSTRUMENTS_CACHE_KEY, datetime.utcnow().isoformat())

            logger.info(f"Stored {len(instruments)} instruments in database")
            return len(instruments)

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to store instruments: {e}")
            raise

    @staticmethod
    async def search_instruments(
        db: AsyncSession,
        query: str,
        exchange: Optional[str] = None,
        segment: Optional[str] = None,
        limit: int = 20
    ) -> List[Instrument]:
        """
        Search instruments by trading symbol or name.

        Args:
            db: Database session
            query: Search query
            exchange: Filter by exchange (NSE, BSE, NFO, etc.)
            segment: Filter by segment
            limit: Maximum results to return

        Returns:
            List of matching instruments
        """
        try:
            # Build query
            stmt = select(Instrument).where(
                or_(
                    Instrument.tradingsymbol.ilike(f"%{query}%"),
                    Instrument.name.ilike(f"%{query}%")
                )
            )

            # Add filters
            if exchange:
                stmt = stmt.where(Instrument.exchange == exchange)
            if segment:
                stmt = stmt.where(Instrument.segment == segment)

            # Order by relevance (exact match first, then prefix match)
            stmt = stmt.order_by(
                Instrument.tradingsymbol.ilike(f"{query}%").desc(),
                Instrument.tradingsymbol
            ).limit(limit)

            result = await db.execute(stmt)
            instruments = result.scalars().all()

            return instruments

        except Exception as e:
            logger.error(f"Failed to search instruments: {e}")
            raise

    @staticmethod
    async def get_instrument_by_token(db: AsyncSession, token: int) -> Optional[Instrument]:
        """
        Get instrument by token.

        Args:
            db: Database session
            token: Instrument token

        Returns:
            Instrument or None
        """
        try:
            stmt = select(Instrument).where(Instrument.instrument_token == token)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get instrument by token: {e}")
            raise

    @staticmethod
    async def get_indices() -> List[dict]:
        """
        Get NIFTY 50 and NIFTY BANK instrument tokens.

        Returns:
            List of index instruments
        """
        # Fixed tokens for major indices
        # These tokens are stable and don't change
        return [
            {"token": 256265, "symbol": "NIFTY 50", "exchange": "NSE"},
            {"token": 260105, "symbol": "NIFTY BANK", "exchange": "NSE"}
        ]

    @staticmethod
    async def should_refresh_instruments() -> bool:
        """
        Check if instruments should be refreshed.

        Returns:
            True if refresh needed, False otherwise
        """
        try:
            redis = await get_redis()
            last_updated = await redis.get(INSTRUMENTS_CACHE_KEY)

            if not last_updated:
                return True

            # Check if last update was more than 1 day ago
            last_updated_dt = datetime.fromisoformat(last_updated)
            hours_since_update = (datetime.utcnow() - last_updated_dt).total_seconds() / 3600

            return hours_since_update > 24

        except Exception as e:
            logger.warning(f"Failed to check refresh status: {e}")
            return True


async def refresh_instrument_master(db: AsyncSession):
    """
    Download and refresh instrument master data.

    Args:
        db: Database session
    """
    try:
        logger.info("Starting instrument master refresh...")

        # Download instruments
        instruments = await InstrumentService.download_instruments()

        # Store in database
        count = await InstrumentService.parse_and_store_instruments(db, instruments)

        logger.info(f"Instrument master refresh complete. Stored {count} instruments.")

    except Exception as e:
        logger.error(f"Instrument master refresh failed: {e}")
        raise
