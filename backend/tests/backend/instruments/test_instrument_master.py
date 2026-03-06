"""
Tests for InstrumentMasterService — broker-agnostic instrument population.
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.instrument_master import InstrumentMasterService
from app.services.brokers.market_data.market_data_base import (
    Instrument as AdapterInstrument,
)


def _make_adapter_instrument(
    symbol="NIFTY25MAR25000CE",
    name="NIFTY",
    exchange="NFO",
    token=12345,
    option_type="CE",
    strike=Decimal("25000"),
    expiry=None,
    lot_size=25,
    underlying="NIFTY",
):
    """Helper to create an AdapterInstrument dataclass."""
    if expiry is None:
        expiry = date.today() + timedelta(days=7)
    return AdapterInstrument(
        canonical_symbol=symbol,
        exchange=exchange,
        broker_symbol=symbol,
        instrument_token=token,
        tradingsymbol=symbol,
        name=name,
        instrument_type="CE" if option_type == "CE" else "PE",
        lot_size=lot_size,
        option_type=option_type,
        strike=strike,
        expiry=expiry,
        underlying=underlying,
    )


@pytest.fixture
def mock_adapter():
    adapter = AsyncMock()
    adapter.broker_type = "smartapi"
    return adapter


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


class TestRefreshFromAdapter:
    @pytest.mark.asyncio
    async def test_refresh_from_adapter_smartapi(self, mock_adapter, mock_db):
        """SmartAPI instruments are stored with correct fields."""
        instruments = [
            _make_adapter_instrument(
                symbol="NIFTY25MAR25000CE", token=100, option_type="CE",
                strike=Decimal("25000"), name="NIFTY",
            ),
            _make_adapter_instrument(
                symbol="NIFTY25MAR25000PE", token=101, option_type="PE",
                strike=Decimal("25000"), name="NIFTY",
            ),
        ]
        mock_adapter.get_instruments = AsyncMock(return_value=instruments)

        with patch("app.services.instrument_master.get_redis") as mock_redis:
            mock_redis.return_value = AsyncMock()
            count = await InstrumentMasterService.refresh_from_adapter(
                mock_adapter, "smartapi", mock_db, exchanges=["NFO"]
            )

        assert count == 2
        mock_db.commit.assert_called_once()
        # Verify execute was called (delete + insert)
        assert mock_db.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_refresh_from_adapter_kite(self, mock_adapter, mock_db):
        """Kite instruments are stored the same way."""
        instruments = [
            _make_adapter_instrument(
                symbol="NIFTY25MAR25000CE", token=200, option_type="CE",
                strike=Decimal("25000"),
            ),
        ]
        mock_adapter.get_instruments = AsyncMock(return_value=instruments)
        mock_adapter.broker_type = "kite"

        with patch("app.services.instrument_master.get_redis") as mock_redis:
            mock_redis.return_value = AsyncMock()
            count = await InstrumentMasterService.refresh_from_adapter(
                mock_adapter, "kite", mock_db, exchanges=["NFO"]
            )

        assert count == 1

    @pytest.mark.asyncio
    async def test_refresh_filters_non_options(self, mock_adapter, mock_db):
        """Futures and equity instruments are skipped."""
        instruments = [
            # Option — should be kept
            _make_adapter_instrument(option_type="CE", token=1),
            # Future — no option_type
            AdapterInstrument(
                canonical_symbol="NIFTY25MARFUT", exchange="NFO",
                broker_symbol="NIFTY25MARFUT", instrument_token=2,
                tradingsymbol="NIFTY25MARFUT", name="NIFTY",
                instrument_type="FUT", lot_size=25,
                option_type=None, strike=None,
                expiry=date.today() + timedelta(days=7),
            ),
        ]
        mock_adapter.get_instruments = AsyncMock(return_value=instruments)

        with patch("app.services.instrument_master.get_redis") as mock_redis:
            mock_redis.return_value = AsyncMock()
            count = await InstrumentMasterService.refresh_from_adapter(
                mock_adapter, "smartapi", mock_db
            )

        assert count == 1

    @pytest.mark.asyncio
    async def test_refresh_filters_expired(self, mock_adapter, mock_db):
        """Expired instruments are not stored."""
        instruments = [
            _make_adapter_instrument(
                expiry=date.today() - timedelta(days=1), token=1
            ),
        ]
        mock_adapter.get_instruments = AsyncMock(return_value=instruments)

        with patch("app.services.instrument_master.get_redis") as mock_redis:
            mock_redis.return_value = AsyncMock()
            count = await InstrumentMasterService.refresh_from_adapter(
                mock_adapter, "smartapi", mock_db
            )

        assert count == 0


class TestShouldRefresh:
    @pytest.mark.asyncio
    async def test_should_refresh_empty_table(self, mock_db):
        """Returns True when table is empty."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await InstrumentMasterService.should_refresh(mock_db)
        assert result is True

    @pytest.mark.asyncio
    async def test_should_refresh_stale(self, mock_db):
        """Returns True when >24h since last refresh."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_db.execute = AsyncMock(return_value=mock_result)

        stale_time = (datetime.utcnow() - timedelta(hours=25)).isoformat()

        with patch("app.services.instrument_master.get_redis") as mock_redis:
            redis_mock = AsyncMock()
            redis_mock.get = AsyncMock(return_value=stale_time)
            mock_redis.return_value = redis_mock

            result = await InstrumentMasterService.should_refresh(mock_db)

        assert result is True


class TestExtractUnderlying:
    def test_nifty(self):
        assert InstrumentMasterService._extract_underlying("NIFTY25MAR25000CE") == "NIFTY"

    def test_banknifty(self):
        assert InstrumentMasterService._extract_underlying("BANKNIFTY25MAR45000PE") == "BANKNIFTY"

    def test_none(self):
        assert InstrumentMasterService._extract_underlying("") is None
        assert InstrumentMasterService._extract_underlying(None) is None
