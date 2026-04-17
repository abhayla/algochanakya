"""Tests for Phase 4 — EOD snapshot on broker exhaustion (TDD Red).

When ``fetch_option_chain_quotes_with_failover`` returns ``(None, {})`` the
route must try the previous trading day's EOD snapshot before giving up.
If that too is unavailable, return 503 so the frontend can show a clear
"all broker sessions offline" message instead of silent zeros.

Covers the new helper
``app.api.routes.optionchain._apply_exhaustion_eod_fallback``:
- Populates all_quotes from snapshot when quotes empty
- Tags data_freshness = "EOD_SNAPSHOT"
- Raises 503 when no snapshot exists
- No-op when quotes are non-empty (happy-path guard)
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException


def _make_strikes_data():
    return {
        24000: {
            "strike": 24000,
            "ce": {"instrument_token": 100, "tradingsymbol": "NIFTY2642124000CE", "lot_size": 75},
            "pe": {"instrument_token": 101, "tradingsymbol": "NIFTY2642124000PE", "lot_size": 75},
        },
        24100: {
            "strike": 24100,
            "ce": {"instrument_token": 102, "tradingsymbol": "NIFTY2642124100CE", "lot_size": 75},
            "pe": {"instrument_token": 103, "tradingsymbol": "NIFTY2642124100PE", "lot_size": 75},
        },
    }


def _make_eod_snapshot():
    return {
        Decimal("24000"): {
            "ce_oi": 500000, "ce_volume": 12000, "ce_ltp": Decimal("150"), "ce_iv": Decimal("18.5"),
            "pe_oi": 300000, "pe_volume": 8000, "pe_ltp": Decimal("140"), "pe_iv": Decimal("22.1"),
        },
        Decimal("24100"): {
            "ce_oi": 400000, "ce_volume": 10000, "ce_ltp": Decimal("100"), "ce_iv": Decimal("17.8"),
            "pe_oi": 350000, "pe_volume": 9000, "pe_ltp": Decimal("180"), "pe_iv": Decimal("21.5"),
        },
    }


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.unit
class TestApplyExhaustionEODFallback:
    @pytest.mark.asyncio
    async def test_empty_quotes_with_snapshot_fills_from_eod(
        self, mock_db, monkeypatch
    ):
        """all_quotes={} + EOD available → return filled all_quotes + use_eod=True."""
        mock_service = MagicMock()
        mock_service.get_snapshot = AsyncMock(return_value=_make_eod_snapshot())
        monkeypatch.setattr(
            "app.api.routes.optionchain.EODSnapshotService",
            lambda: mock_service,
        )

        from app.api.routes.optionchain import _apply_exhaustion_eod_fallback

        all_quotes, use_eod = await _apply_exhaustion_eod_fallback(
            all_quotes={},
            strikes_data=_make_strikes_data(),
            underlying="NIFTY",
            expiry_date=date(2026, 4, 21),
            db=mock_db,
        )

        assert use_eod is True
        assert len(all_quotes) > 0
        # Snapshot-sourced entries present
        assert all_quotes["NFO:NIFTY2642124000CE"]["oi"] == 500000
        assert all_quotes["NFO:NIFTY2642124100PE"]["oi"] == 350000

    @pytest.mark.asyncio
    async def test_empty_quotes_without_snapshot_raises_503(
        self, mock_db, monkeypatch
    ):
        """No quotes AND no snapshot → 503 with clear message."""
        mock_service = MagicMock()
        mock_service.get_snapshot = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "app.api.routes.optionchain.EODSnapshotService",
            lambda: mock_service,
        )

        from app.api.routes.optionchain import _apply_exhaustion_eod_fallback

        with pytest.raises(HTTPException) as exc_info:
            await _apply_exhaustion_eod_fallback(
                all_quotes={},
                strikes_data=_make_strikes_data(),
                underlying="NIFTY",
                expiry_date=date(2026, 4, 21),
                db=mock_db,
            )

        assert exc_info.value.status_code == 503
        assert "broker" in exc_info.value.detail.lower() or "unavailable" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_nonempty_quotes_noop(self, mock_db, monkeypatch):
        """Happy path: quotes present → helper must NOT touch them and NOT
        query EOD. This prevents accidental override when brokers ARE
        returning data."""
        mock_service = MagicMock()
        mock_service.get_snapshot = AsyncMock(return_value=_make_eod_snapshot())
        monkeypatch.setattr(
            "app.api.routes.optionchain.EODSnapshotService",
            lambda: mock_service,
        )

        from app.api.routes.optionchain import _apply_exhaustion_eod_fallback

        live_quotes = {
            "NFO:NIFTY2642124000CE": {
                "last_price": 42.0, "oi": 999, "volume": 1,
                "ohlc": {"close": 42}, "depth": {"buy": [], "sell": []},
            }
        }

        all_quotes, use_eod = await _apply_exhaustion_eod_fallback(
            all_quotes=live_quotes,
            strikes_data=_make_strikes_data(),
            underlying="NIFTY",
            expiry_date=date(2026, 4, 21),
            db=mock_db,
        )

        assert use_eod is False
        assert all_quotes is live_quotes  # same object, untouched
        mock_service.get_snapshot.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_eod_exception_raises_503(self, mock_db, monkeypatch):
        """If snapshot lookup itself fails (network, db, …), don't let it
        cascade as 500 — convert to 503 same as the no-snapshot case."""
        mock_service = MagicMock()
        mock_service.get_snapshot = AsyncMock(side_effect=RuntimeError("db down"))
        monkeypatch.setattr(
            "app.api.routes.optionchain.EODSnapshotService",
            lambda: mock_service,
        )

        from app.api.routes.optionchain import _apply_exhaustion_eod_fallback

        with pytest.raises(HTTPException) as exc_info:
            await _apply_exhaustion_eod_fallback(
                all_quotes={},
                strikes_data=_make_strikes_data(),
                underlying="NIFTY",
                expiry_date=date(2026, 4, 21),
                db=mock_db,
            )

        assert exc_info.value.status_code == 503
