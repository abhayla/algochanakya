"""
WebSocket Fallback Chain Tests (Gap F)

Tests that the WebSocket falls back through ORG_ACTIVE_BROKERS when
credentials are unavailable, not just SmartAPI↔Kite swap.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.user_preferences import MarketDataSource


@pytest.fixture
def test_user_id():
    return uuid4()


@pytest.fixture
def mock_user(test_user_id):
    user = MagicMock()
    user.id = test_user_id
    return user


class TestWebSocketFallbackChain:

    @pytest.mark.asyncio
    async def test_fallback_tries_org_active_brokers_in_order(self):
        """When preferred broker fails, should try each ORG_ACTIVE_BROKER in order."""
        from app.api.routes.websocket import _try_fallback_brokers

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        # Simulate: first fallback (angelone/smartapi) fails, second (upstox) succeeds
        call_count = [0]
        async def mock_ensure(broker_type, user, db):
            call_count[0] += 1
            if broker_type == "upstox":
                return True
            return False

        with patch("app.api.routes.websocket._ensure_broker_credentials", side_effect=mock_ensure):
            result_broker = await _try_fallback_brokers("fyers", mock_user, mock_db)

        assert result_broker is not None
        assert call_count[0] >= 2  # Tried at least angelone + upstox

    @pytest.mark.asyncio
    async def test_fallback_skips_original_broker(self):
        """Fallback should not retry the broker that already failed."""
        from app.api.routes.websocket import _try_fallback_brokers

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        tried_brokers = []
        async def mock_ensure(broker_type, user, db):
            tried_brokers.append(broker_type)
            return False

        with patch("app.api.routes.websocket._ensure_broker_credentials", side_effect=mock_ensure):
            result = await _try_fallback_brokers("smartapi", mock_user, mock_db)

        assert result is None
        assert "smartapi" not in tried_brokers

    @pytest.mark.asyncio
    async def test_fallback_returns_none_when_all_fail(self):
        """Returns None when no broker has credentials."""
        from app.api.routes.websocket import _try_fallback_brokers

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        async def mock_ensure(broker_type, user, db):
            return False

        with patch("app.api.routes.websocket._ensure_broker_credentials", side_effect=mock_ensure):
            result = await _try_fallback_brokers("smartapi", mock_user, mock_db)

        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_maps_broker_names_to_market_data_sources(self):
        """ORG_ACTIVE_BROKERS uses DB names (angelone), but _ensure_broker_credentials uses MarketDataSource (smartapi)."""
        from app.api.routes.websocket import _try_fallback_brokers

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = uuid4()

        tried_brokers = []
        async def mock_ensure(broker_type, user, db):
            tried_brokers.append(broker_type)
            return broker_type == "smartapi"

        with patch("app.api.routes.websocket._ensure_broker_credentials", side_effect=mock_ensure):
            result = await _try_fallback_brokers("kite", mock_user, mock_db)

        # "angelone" in ORG_ACTIVE_BROKERS should map to "smartapi" MarketDataSource
        assert "smartapi" in tried_brokers
        assert result == "smartapi"
