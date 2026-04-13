"""
Tests for EODSnapshotService — orchestration layer for EOD option chain snapshots.

TDD: Written FIRST, before the implementation.
"""
import asyncio
import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.eod_option_snapshot import EODOptionSnapshot
from app.utils.market_hours import IST


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_nse_parsed(spot=24500, num_strikes=60):
    """Build a parsed NSE response dict (output of NSEFetcher.parse_nse_response)."""
    strikes = {}
    for i in range(num_strikes):
        strike = Decimal(str(24000 + i * 100))
        strikes[strike] = {
            "ce_ltp": Decimal("150.50"),
            "ce_oi": 500000 - i * 5000,
            "ce_volume": 12000,
            "ce_iv": Decimal("18.5"),
            "pe_ltp": Decimal("140.25"),
            "pe_oi": 300000 + i * 3000,
            "pe_volume": 8000,
            "pe_iv": Decimal("22.1"),
        }
    return {
        "spot_price": Decimal(str(spot)),
        "total_ce_oi": sum(s["ce_oi"] for s in strikes.values()),
        "total_pe_oi": sum(s["pe_oi"] for s in strikes.values()),
        "strikes": strikes,
    }


async def _insert_snapshot_rows(db, underlying, expiry, spot, captured_at, num_strikes=5):
    """Insert EODOptionSnapshot rows into the test DB."""
    for i in range(num_strikes):
        strike = Decimal(str(24000 + i * 100))
        row = EODOptionSnapshot(
            underlying=underlying,
            expiry_date=expiry,
            strike=strike,
            ce_ltp=Decimal("150.50"),
            ce_oi=500000 - i * 5000,
            ce_volume=12000,
            ce_iv=Decimal("18.5"),
            pe_ltp=Decimal("140.25"),
            pe_oi=300000 + i * 3000,
            pe_volume=8000,
            pe_iv=Decimal("22.1"),
            spot_price=Decimal(str(spot)),
            captured_at=captured_at,
        )
        db.add(row)
    await db.commit()


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestIsSnapshotFresh:

    def test_fresh_after_close(self):
        """captured Friday 16:00, now Saturday → True (Friday's data is fresh)."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        svc = EODSnapshotService()
        captured = datetime(2026, 4, 10, 16, 0, tzinfo=IST)  # Friday 16:00
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)  # Friday 15:35

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close", return_value=last_close):
            assert svc.is_snapshot_fresh(captured) is True

    def test_stale_old_capture(self):
        """captured Thursday, now Friday evening → False (Thursday data is stale)."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        svc = EODSnapshotService()
        captured = datetime(2026, 4, 9, 16, 0, tzinfo=IST)  # Thursday 16:00
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)  # Friday 15:35

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close", return_value=last_close):
            assert svc.is_snapshot_fresh(captured) is False

    def test_no_captured_at_is_stale(self):
        """None captured_at → always stale."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        svc = EODSnapshotService()
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close", return_value=last_close):
            assert svc.is_snapshot_fresh(None) is False


class TestGetSnapshot:

    @pytest.mark.asyncio
    async def test_returns_none_empty_db_nse_fails(self, db_session):
        """Cold start + NSE fails → returns None."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        svc = EODSnapshotService()
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_option_chain = AsyncMock(side_effect=Exception("NSE down"))

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=datetime(2026, 4, 10, 15, 35, tzinfo=IST)), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            result = await svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_fresh_data_from_db(self, db_session):
        """DB has recent data → returns it without fetching NSE."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        fresh_time = datetime(2026, 4, 10, 16, 0, tzinfo=IST)
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        await _insert_snapshot_rows(db_session, "NIFTY", date(2026, 4, 16), 24500, fresh_time, 5)

        svc = EODSnapshotService()
        mock_fetcher = AsyncMock()

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            result = await svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session)

        assert result is not None
        assert len(result) == 5
        # NSE should NOT have been called
        mock_fetcher.fetch_option_chain.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetches_when_stale(self, db_session):
        """Old captured_at → calls NSE, stores new data, returns it."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        stale_time = datetime(2026, 4, 9, 16, 0, tzinfo=IST)  # Thursday
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)  # Friday

        await _insert_snapshot_rows(db_session, "NIFTY", date(2026, 4, 16), 24500, stale_time, 3)

        svc = EODSnapshotService()
        nse_data = _make_nse_parsed(num_strikes=60)
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_option_chain = AsyncMock(return_value=nse_data)

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            result = await svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session)

        assert result is not None
        assert len(result) == 60
        mock_fetcher.fetch_option_chain.assert_called_once()

    @pytest.mark.asyncio
    async def test_nse_failure_returns_stale_data(self, db_session):
        """NSE raises, stale DB exists → returns stale data (better than nothing)."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        stale_time = datetime(2026, 4, 9, 16, 0, tzinfo=IST)
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        await _insert_snapshot_rows(db_session, "NIFTY", date(2026, 4, 16), 24500, stale_time, 5)

        svc = EODSnapshotService()
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_option_chain = AsyncMock(side_effect=Exception("NSE blocked"))

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            result = await svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session)

        # Should return stale data rather than None
        assert result is not None
        assert len(result) == 5


class TestFetchAndStore:

    @pytest.mark.asyncio
    async def test_creates_rows_in_db(self, db_session):
        """Mock NSE → verify DB rows are created."""
        from app.services.options.eod_snapshot_service import EODSnapshotService
        from sqlalchemy import select, func

        svc = EODSnapshotService()
        nse_data = _make_nse_parsed(num_strikes=5)
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_option_chain = AsyncMock(return_value=nse_data)

        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            result = await svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session)

        # Check DB rows
        count = await db_session.execute(
            select(func.count()).select_from(EODOptionSnapshot).where(
                EODOptionSnapshot.underlying == "NIFTY",
                EODOptionSnapshot.expiry_date == date(2026, 4, 16),
            )
        )
        assert count.scalar() == 5
        assert result is not None
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_replaces_old_rows_on_refetch(self, db_session):
        """Re-fetch should DELETE old rows and INSERT new ones."""
        from app.services.options.eod_snapshot_service import EODSnapshotService
        from sqlalchemy import select, func

        stale_time = datetime(2026, 4, 9, 16, 0, tzinfo=IST)
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        # Insert 3 old rows
        await _insert_snapshot_rows(db_session, "NIFTY", date(2026, 4, 16), 24500, stale_time, 3)

        svc = EODSnapshotService()
        nse_data = _make_nse_parsed(num_strikes=5)
        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_option_chain = AsyncMock(return_value=nse_data)

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            await svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session)

        # Should have 5 rows (not 3+5=8)
        count = await db_session.execute(
            select(func.count()).select_from(EODOptionSnapshot).where(
                EODOptionSnapshot.underlying == "NIFTY",
                EODOptionSnapshot.expiry_date == date(2026, 4, 16),
            )
        )
        assert count.scalar() == 5


class TestRaceCondition:

    @pytest.mark.asyncio
    async def test_concurrent_calls_single_fetch(self, db_session):
        """3 concurrent calls → NSE called once (lock prevents duplicate fetches)."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        svc = EODSnapshotService()
        nse_data = _make_nse_parsed(num_strikes=5)
        call_count = 0

        async def slow_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)  # Simulate network delay
            return nse_data

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_option_chain = AsyncMock(side_effect=slow_fetch)

        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            results = await asyncio.gather(
                svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session),
                svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session),
                svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session),
            )

        # All 3 calls should return data
        for r in results:
            assert r is not None

        # NSE should only be called ONCE (others waited on lock then read DB)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_underlying_independent(self, db_session):
        """NIFTY and BANKNIFTY fetch independently (different locks)."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        svc = EODSnapshotService()
        nse_data = _make_nse_parsed(num_strikes=5)
        call_count = 0

        async def counting_fetch(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return nse_data

        mock_fetcher = AsyncMock()
        mock_fetcher.fetch_option_chain = AsyncMock(side_effect=counting_fetch)

        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher", return_value=mock_fetcher):
            await asyncio.gather(
                svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session),
                svc.get_snapshot("BANKNIFTY", date(2026, 4, 16), db_session),
            )

        # Both should fetch independently
        assert call_count == 2


class TestReturnFormat:

    @pytest.mark.asyncio
    async def test_returns_dict_keyed_by_decimal_strike(self, db_session):
        """Return value should be {Decimal(strike): {ce_oi, pe_oi, ...}}."""
        from app.services.options.eod_snapshot_service import EODSnapshotService

        fresh_time = datetime(2026, 4, 10, 16, 0, tzinfo=IST)
        last_close = datetime(2026, 4, 10, 15, 35, tzinfo=IST)

        await _insert_snapshot_rows(db_session, "NIFTY", date(2026, 4, 16), 24500, fresh_time, 3)

        svc = EODSnapshotService()

        with patch("app.services.options.eod_snapshot_service.get_last_trading_close",
                    return_value=last_close), \
             patch("app.services.options.eod_snapshot_service.NSEFetcher"):
            result = await svc.get_snapshot("NIFTY", date(2026, 4, 16), db_session)

        assert isinstance(result, dict)
        first_key = next(iter(result))
        assert isinstance(first_key, Decimal)

        entry = result[first_key]
        assert "ce_oi" in entry
        assert "pe_oi" in entry
        assert "ce_volume" in entry
        assert "pe_volume" in entry
        assert "ce_ltp" in entry
        assert "pe_ltp" in entry
        assert "ce_iv" in entry
        assert "pe_iv" in entry
