"""
EOD Option Chain Snapshot Service.

On-demand lazy caching: when market is closed and broker OI is all zeros,
fetch once from NSE v3 API, store in DB, serve as fallback.
Subsequent requests get instant DB reads until next trading session close.
"""
import asyncio
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eod_option_snapshot import EODOptionSnapshot
from app.services.options.nse_fetcher import NSEFetcher, NSEFetchError, NSEValidationError
from app.utils.market_hours import get_last_trading_close, IST, _ist_now

logger = logging.getLogger(__name__)

# Per-(underlying, expiry) locks to prevent duplicate NSE fetches
_fetch_locks: Dict[str, asyncio.Lock] = {}


class EODSnapshotService:
    """Orchestrates EOD snapshot check → fetch → store → serve."""

    def is_snapshot_fresh(self, captured_at: Optional[datetime]) -> bool:
        """Check if captured_at is >= the most recent trading session close."""
        if captured_at is None:
            return False
        last_close = get_last_trading_close()
        # Handle naive datetimes from SQLite test DB
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=IST)
        if last_close.tzinfo is None:
            last_close = last_close.replace(tzinfo=IST)
        return captured_at >= last_close

    async def get_snapshot(
        self,
        underlying: str,
        expiry_date: date,
        db: AsyncSession,
    ) -> Optional[Dict[Decimal, dict]]:
        """
        Main entry point: check DB freshness → return or fetch+store+return.

        Returns: {Decimal(strike): {"ce_oi": int, "pe_oi": int, ...}} or None
        """
        # Check DB for existing snapshot
        db_rows = await self._load_from_db(underlying, expiry_date, db)

        if db_rows:
            # Check freshness using the first row's captured_at
            captured_at = db_rows[0].captured_at
            if self.is_snapshot_fresh(captured_at):
                logger.debug(
                    "[EOD] Fresh snapshot for %s/%s (captured %s)",
                    underlying, expiry_date, captured_at,
                )
                return self._rows_to_dict(db_rows)

        # Stale or missing — fetch from NSE with lock
        lock_key = f"{underlying}:{expiry_date}"
        if lock_key not in _fetch_locks:
            _fetch_locks[lock_key] = asyncio.Lock()

        async with _fetch_locks[lock_key]:
            # Double-check after acquiring lock (another coroutine may have fetched)
            db_rows = await self._load_from_db(underlying, expiry_date, db)
            if db_rows:
                captured_at = db_rows[0].captured_at
                if self.is_snapshot_fresh(captured_at):
                    return self._rows_to_dict(db_rows)

            # Fetch from NSE
            try:
                fetcher = NSEFetcher()
                nse_data = await fetcher.fetch_option_chain(underlying, expiry_date)
                await self._store_snapshot(underlying, expiry_date, nse_data, db)

                # Re-read from DB to return consistent data
                db_rows = await self._load_from_db(underlying, expiry_date, db)
                if db_rows:
                    return self._rows_to_dict(db_rows)
                return None

            except (NSEFetchError, NSEValidationError, Exception) as e:
                logger.warning("[EOD] NSE fetch failed for %s/%s: %s", underlying, expiry_date, e)
                # Return stale data if available (better than nothing)
                if db_rows:
                    logger.info("[EOD] Returning stale snapshot for %s/%s", underlying, expiry_date)
                    return self._rows_to_dict(db_rows)
                return None

    async def _load_from_db(
        self, underlying: str, expiry_date: date, db: AsyncSession
    ) -> list:
        """Load snapshot rows from DB for given underlying + expiry."""
        result = await db.execute(
            select(EODOptionSnapshot)
            .where(
                EODOptionSnapshot.underlying == underlying,
                EODOptionSnapshot.expiry_date == expiry_date,
            )
            .order_by(EODOptionSnapshot.strike)
        )
        return result.scalars().all()

    async def _store_snapshot(
        self,
        underlying: str,
        expiry_date: date,
        nse_data: dict,
        db: AsyncSession,
    ) -> None:
        """DELETE old rows + INSERT new ones (SQLite-compatible upsert)."""
        now = _ist_now()

        # Delete old rows for this (underlying, expiry)
        await db.execute(
            delete(EODOptionSnapshot).where(
                EODOptionSnapshot.underlying == underlying,
                EODOptionSnapshot.expiry_date == expiry_date,
            )
        )

        # Insert new rows
        spot_price = nse_data["spot_price"]
        for strike, data in nse_data["strikes"].items():
            row = EODOptionSnapshot(
                underlying=underlying,
                expiry_date=expiry_date,
                strike=strike,
                ce_ltp=data["ce_ltp"],
                ce_oi=data["ce_oi"],
                ce_volume=data["ce_volume"],
                ce_iv=data["ce_iv"],
                pe_ltp=data["pe_ltp"],
                pe_oi=data["pe_oi"],
                pe_volume=data["pe_volume"],
                pe_iv=data["pe_iv"],
                spot_price=spot_price,
                captured_at=now,
            )
            db.add(row)

        await db.commit()

    @staticmethod
    def _rows_to_dict(rows: list) -> Dict[Decimal, dict]:
        """Convert DB rows to {Decimal(strike): {...}} dict."""
        result = {}
        for row in rows:
            result[row.strike] = {
                "ce_ltp": row.ce_ltp,
                "ce_oi": row.ce_oi,
                "ce_volume": row.ce_volume,
                "ce_iv": row.ce_iv,
                "pe_ltp": row.pe_ltp,
                "pe_oi": row.pe_oi,
                "pe_volume": row.pe_volume,
                "pe_iv": row.pe_iv,
            }
        return result
