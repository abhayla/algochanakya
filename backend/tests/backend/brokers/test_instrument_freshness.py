"""
Tests for instrument mapping freshness check.

REQ-M004: populate_broker_token_mappings re-runs when current expiry missing.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, timedelta


@pytest.mark.unit
class TestEnsureMappingsFresh:
    """REQ-M004: ensure_mappings_fresh triggers repopulate when expiry missing."""

    @pytest.fixture(autouse=True)
    def reset_freshness_cache(self):
        """Reset the in-memory freshness timestamp between tests."""
        from app.services.instrument_master import InstrumentMasterService
        InstrumentMasterService._last_freshness_check = 0.0
        yield
        InstrumentMasterService._last_freshness_check = 0.0

    @pytest.mark.asyncio
    async def test_repopulates_when_current_expiry_missing(self):
        """Missing current week's expiry → re-runs populate_broker_token_mappings."""
        from app.services.instrument_master import InstrumentMasterService

        mock_db = AsyncMock()
        # Simulate count query returning 0 (no mappings for current expiry)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            InstrumentMasterService,
            "populate_broker_token_mappings",
            new_callable=AsyncMock,
            return_value=500,
        ) as mock_populate, patch(
            "app.services.instrument_master.get_redis",
            new_callable=AsyncMock,
            return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock()),
        ):
            result = await InstrumentMasterService.ensure_mappings_fresh(mock_db)

        assert result is True
        mock_populate.assert_called_once_with(mock_db)

    @pytest.mark.asyncio
    async def test_skips_when_mappings_exist(self):
        """Current expiry has mappings → no repopulate needed."""
        from app.services.instrument_master import InstrumentMasterService

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 150  # Mappings exist
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            InstrumentMasterService,
            "populate_broker_token_mappings",
            new_callable=AsyncMock,
        ) as mock_populate, patch(
            "app.services.instrument_master.get_redis",
            new_callable=AsyncMock,
            return_value=AsyncMock(get=AsyncMock(return_value=None), setex=AsyncMock()),
        ):
            result = await InstrumentMasterService.ensure_mappings_fresh(mock_db)

        assert result is True
        mock_populate.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_redis_cache(self):
        """Cached freshness check skips DB query entirely."""
        from app.services.instrument_master import InstrumentMasterService

        mock_db = AsyncMock()

        with patch(
            "app.services.instrument_master.get_redis",
            new_callable=AsyncMock,
            return_value=AsyncMock(get=AsyncMock(return_value="1")),
        ):
            result = await InstrumentMasterService.ensure_mappings_fresh(mock_db)

        assert result is True
        # DB should not be queried when Redis cache says fresh
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self):
        """Errors return False but don't crash."""
        from app.services.instrument_master import InstrumentMasterService

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB down"))

        with patch(
            "app.services.instrument_master.get_redis",
            new_callable=AsyncMock,
            return_value=AsyncMock(get=AsyncMock(return_value=None)),
        ):
            result = await InstrumentMasterService.ensure_mappings_fresh(mock_db)

        assert result is False
