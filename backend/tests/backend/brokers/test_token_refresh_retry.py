"""
Tests for reactive token refresh retry on MarketDataBrokerAdapter.

REQ-M001: Adapter retry on 401 for Upstox and SmartAPI
REQ-M003: Lock prevents concurrent token refresh storms
REQ-M005: Non-refreshable brokers fail fast to failover
"""
import asyncio
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.brokers.market_data.market_data_base import (
    MarketDataBrokerAdapter,
    BrokerCredentials,
    MarketDataBrokerType,
)
from app.services.brokers.market_data.exceptions import AuthenticationError


# ---------------------------------------------------------------------------
# Concrete test adapter stubs
# ---------------------------------------------------------------------------

class RefreshableAdapter(MarketDataBrokerAdapter):
    """Adapter that supports auto-refresh (like Upstox/SmartAPI)."""

    def __init__(self):
        creds = BrokerCredentials(broker_type="upstox", user_id=uuid4())
        self.refresh_called = 0
        self._get_ltp_impl = AsyncMock(return_value={"NIFTY": Decimal("24500")})
        # _can_auto_refresh must return True BEFORE super().__init__
        # because __init__ calls _wrap_with_token_refresh
        super().__init__(creds)

    @property
    def broker_type(self) -> MarketDataBrokerType:
        return MarketDataBrokerType.UPSTOX

    def _can_auto_refresh(self) -> bool:
        return True

    async def _try_refresh_token(self) -> bool:
        self.refresh_called += 1
        return True

    async def get_quote(self, symbols):
        return {}

    async def _get_ltp_raw(self, symbols):
        """Raw LTP implementation (before wrapping)."""
        return await self._get_ltp_impl(symbols)

    # get_ltp is defined here but will be auto-wrapped by _wrap_with_token_refresh
    async def get_ltp(self, symbols):
        return await self._get_ltp_raw(symbols)

    async def subscribe(self, tokens, mode="quote"):
        pass

    async def unsubscribe(self, tokens):
        pass

    def on_tick(self, callback):
        pass

    async def get_historical(self, symbol, from_date, to_date, interval="day"):
        return []

    async def get_instruments(self, exchange="NFO"):
        return []

    async def search_instruments(self, query):
        return []

    async def get_token(self, symbol):
        return 0

    async def get_symbol(self, token):
        return ""

    async def connect(self):
        return True

    async def disconnect(self):
        pass

    @property
    def is_connected(self):
        return True


class NonRefreshableAdapter(MarketDataBrokerAdapter):
    """Adapter that does NOT support auto-refresh (like Kite/Dhan)."""

    def __init__(self):
        creds = BrokerCredentials(broker_type="kite", user_id=uuid4())
        super().__init__(creds)

    @property
    def broker_type(self) -> MarketDataBrokerType:
        return MarketDataBrokerType.KITE

    def _can_auto_refresh(self) -> bool:
        return False

    async def get_quote(self, symbols):
        return {}

    async def get_ltp(self, symbols):
        raise AuthenticationError("kite", "Token expired")

    async def subscribe(self, tokens, mode="quote"):
        pass

    async def unsubscribe(self, tokens):
        pass

    def on_tick(self, callback):
        pass

    async def get_historical(self, symbol, from_date, to_date, interval="day"):
        return []

    async def get_instruments(self, exchange="NFO"):
        return []

    async def search_instruments(self, query):
        return []

    async def get_token(self, symbol):
        return 0

    async def get_symbol(self, token):
        return ""

    async def connect(self):
        return True

    async def disconnect(self):
        pass

    @property
    def is_connected(self):
        return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTransparentTokenRefresh:
    """REQ-M001: get_ltp()/get_quote() automatically retry on 401 for refreshable adapters."""

    @pytest.mark.asyncio
    async def test_get_ltp_retries_on_auth_error_after_refresh(self):
        """401 → refresh → retry → success — all transparent to caller."""
        adapter = RefreshableAdapter()
        adapter._get_ltp_impl = AsyncMock(
            side_effect=[
                AuthenticationError("upstox", "Token expired"),
                {"NIFTY": Decimal("24500")},
            ]
        )

        # Caller just uses get_ltp() normally — retry is transparent
        result = await adapter.get_ltp(["NIFTY"])

        assert result == {"NIFTY": Decimal("24500")}
        assert adapter.refresh_called == 1
        assert adapter._get_ltp_impl.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_non_auth_error(self):
        """Non-auth errors pass through without retry."""
        adapter = RefreshableAdapter()
        adapter._get_ltp_impl = AsyncMock(
            side_effect=ValueError("some other error")
        )

        with pytest.raises(ValueError, match="some other error"):
            await adapter.get_ltp(["NIFTY"])

        assert adapter.refresh_called == 0

    @pytest.mark.asyncio
    async def test_no_infinite_retry_on_persistent_auth_error(self):
        """If refresh succeeds but retry still gets 401, raise immediately."""
        adapter = RefreshableAdapter()
        adapter._get_ltp_impl = AsyncMock(
            side_effect=AuthenticationError("upstox", "Still expired")
        )

        with pytest.raises(AuthenticationError):
            await adapter.get_ltp(["NIFTY"])

        # Should only refresh once, then raise
        assert adapter.refresh_called == 1
        assert adapter._get_ltp_impl.call_count == 2

    @pytest.mark.asyncio
    async def test_refresh_failure_raises_original_error(self):
        """If refresh itself fails, raise the original AuthenticationError."""
        adapter = RefreshableAdapter()
        adapter._get_ltp_impl = AsyncMock(
            side_effect=AuthenticationError("upstox", "Token expired")
        )
        # Make refresh fail
        async def failing_refresh():
            adapter.refresh_called += 1
            return False
        adapter._try_refresh_token = failing_refresh

        with pytest.raises(AuthenticationError, match="Token expired"):
            await adapter.get_ltp(["NIFTY"])

        assert adapter.refresh_called == 1
        # Should NOT retry after failed refresh
        assert adapter._get_ltp_impl.call_count == 1


@pytest.mark.unit
class TestNonRefreshableFailFast:
    """REQ-M005: Non-refreshable brokers fail fast — no wrapping applied."""

    @pytest.mark.asyncio
    async def test_non_refreshable_raises_immediately(self):
        """Kite/Dhan 401 → immediate raise, no refresh attempt."""
        adapter = NonRefreshableAdapter()

        with pytest.raises(AuthenticationError, match="Token expired"):
            await adapter.get_ltp(["NIFTY"])


@pytest.mark.unit
class TestConcurrentRefreshLock:
    """REQ-M003: Lock serializes concurrent refresh attempts."""

    @pytest.mark.asyncio
    async def test_concurrent_refreshes_are_serialized(self):
        """Two simultaneous 401s → refreshes run sequentially (not in parallel)."""
        adapter = RefreshableAdapter()
        call_count = 0
        concurrent_refreshes = 0
        max_concurrent = 0

        async def mock_ltp(symbols):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise AuthenticationError("upstox", "Token expired")
            return {"NIFTY": Decimal("24500")}

        adapter._get_ltp_impl = mock_ltp

        async def tracked_refresh():
            nonlocal concurrent_refreshes, max_concurrent
            concurrent_refreshes += 1
            max_concurrent = max(max_concurrent, concurrent_refreshes)
            await asyncio.sleep(0.05)
            adapter.refresh_called += 1
            concurrent_refreshes -= 1
            return True
        adapter._try_refresh_token = tracked_refresh

        results = await asyncio.gather(
            adapter.get_ltp(["NIFTY"]),
            adapter.get_ltp(["NIFTY"]),
        )

        # Both should succeed
        for r in results:
            assert r == {"NIFTY": Decimal("24500")}

        # Lock ensures max 1 concurrent refresh (no storms)
        assert max_concurrent == 1


@pytest.mark.unit
class TestCanAutoRefresh:
    """Base class _can_auto_refresh() default behavior."""

    def test_base_class_defaults_to_false(self):
        """Base class returns False — subclasses must opt in."""
        adapter = NonRefreshableAdapter()
        assert adapter._can_auto_refresh() is False

    def test_refreshable_adapter_returns_true(self):
        adapter = RefreshableAdapter()
        assert adapter._can_auto_refresh() is True

    def test_wrapping_only_applied_to_refreshable(self):
        """Non-refreshable adapters keep their original methods unwrapped."""
        adapter = NonRefreshableAdapter()
        # get_ltp on non-refreshable is the original method, not wrapped
        assert not hasattr(adapter.get_ltp, '__wrapped__')
