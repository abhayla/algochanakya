"""
Tests for proactive data source warmup on login.

REQ-M002: Login callback triggers data source warmup.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.unit
class TestWarmDataSources:
    """REQ-M002: warm_data_sources() verifies and refreshes platform brokers."""

    @pytest.mark.asyncio
    async def test_healthy_broker_skipped(self):
        """Healthy broker returns 'healthy' status — no refresh needed."""
        from app.services.brokers.data_source_warmup import warm_data_sources

        mock_adapter = AsyncMock()
        mock_adapter.get_best_price = AsyncMock(
            return_value={"NIFTY": Decimal("24500")}
        )

        with patch(
            "app.services.brokers.data_source_warmup._create_platform_adapter",
            return_value=mock_adapter,
        ), patch(
            "app.services.brokers.data_source_warmup.ORG_ACTIVE_BROKERS",
            ["angelone"],
        ), patch(
            "app.services.brokers.data_source_warmup._ensure_instrument_mappings_fresh",
            new_callable=AsyncMock,
        ):
            results = await warm_data_sources()

        assert results["angelone"] == "healthy"

    @pytest.mark.asyncio
    async def test_expired_broker_refreshed(self):
        """Expired broker gets refreshed successfully."""
        from app.services.brokers.data_source_warmup import warm_data_sources
        from app.services.brokers.market_data.exceptions import AuthenticationError

        mock_adapter = AsyncMock()
        mock_adapter.get_best_price = AsyncMock(
            side_effect=AuthenticationError("upstox", "Token expired")
        )

        with patch(
            "app.services.brokers.data_source_warmup._create_platform_adapter",
            return_value=mock_adapter,
        ), patch(
            "app.services.brokers.data_source_warmup.ORG_ACTIVE_BROKERS",
            ["upstox"],
        ), patch(
            "app.services.brokers.data_source_warmup._refresh_platform_broker",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_refresh, patch(
            "app.services.brokers.data_source_warmup._ensure_instrument_mappings_fresh",
            new_callable=AsyncMock,
        ):
            results = await warm_data_sources()

        assert results["upstox"] == "refreshed"
        mock_refresh.assert_called_once_with("upstox")

    @pytest.mark.asyncio
    async def test_refresh_failure_reported(self):
        """Broker refresh failure returns 'failed' status."""
        from app.services.brokers.data_source_warmup import warm_data_sources
        from app.services.brokers.market_data.exceptions import AuthenticationError

        mock_adapter = AsyncMock()
        mock_adapter.get_best_price = AsyncMock(
            side_effect=AuthenticationError("upstox", "Token expired")
        )

        with patch(
            "app.services.brokers.data_source_warmup._create_platform_adapter",
            return_value=mock_adapter,
        ), patch(
            "app.services.brokers.data_source_warmup.ORG_ACTIVE_BROKERS",
            ["upstox"],
        ), patch(
            "app.services.brokers.data_source_warmup._refresh_platform_broker",
            new_callable=AsyncMock,
            return_value=False,
        ), patch(
            "app.services.brokers.data_source_warmup._ensure_instrument_mappings_fresh",
            new_callable=AsyncMock,
        ):
            results = await warm_data_sources()

        assert results["upstox"] == "failed"

    @pytest.mark.asyncio
    async def test_generic_error_captured(self):
        """Non-auth error returns error status without crashing."""
        from app.services.brokers.data_source_warmup import warm_data_sources

        mock_adapter = AsyncMock()
        mock_adapter.get_best_price = AsyncMock(
            side_effect=ConnectionError("Network down")
        )

        with patch(
            "app.services.brokers.data_source_warmup._create_platform_adapter",
            return_value=mock_adapter,
        ), patch(
            "app.services.brokers.data_source_warmup.ORG_ACTIVE_BROKERS",
            ["angelone"],
        ), patch(
            "app.services.brokers.data_source_warmup._ensure_instrument_mappings_fresh",
            new_callable=AsyncMock,
        ):
            results = await warm_data_sources()

        assert "error" in results["angelone"]

    @pytest.mark.asyncio
    async def test_adapter_creation_failure_handled(self):
        """If adapter can't be created, report error gracefully."""
        from app.services.brokers.data_source_warmup import warm_data_sources

        with patch(
            "app.services.brokers.data_source_warmup._create_platform_adapter",
            side_effect=Exception("No credentials"),
        ), patch(
            "app.services.brokers.data_source_warmup.ORG_ACTIVE_BROKERS",
            ["upstox"],
        ), patch(
            "app.services.brokers.data_source_warmup._ensure_instrument_mappings_fresh",
            new_callable=AsyncMock,
        ):
            results = await warm_data_sources()

        assert "error" in results["upstox"]

    @pytest.mark.asyncio
    async def test_instrument_freshness_called(self):
        """warm_data_sources checks instrument mapping freshness."""
        from app.services.brokers.data_source_warmup import warm_data_sources

        mock_adapter = AsyncMock()
        mock_adapter.get_best_price = AsyncMock(
            return_value={"NIFTY": Decimal("24500")}
        )

        with patch(
            "app.services.brokers.data_source_warmup._create_platform_adapter",
            return_value=mock_adapter,
        ), patch(
            "app.services.brokers.data_source_warmup.ORG_ACTIVE_BROKERS",
            ["angelone"],
        ), patch(
            "app.services.brokers.data_source_warmup._ensure_instrument_mappings_fresh",
            new_callable=AsyncMock,
        ) as mock_freshness:
            await warm_data_sources()

        mock_freshness.assert_called_once()
