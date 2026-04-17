"""Tests for market_data.auth_tracking helper — Phase 2 (TDD Red).

The helper wraps adapter coroutines so that auth failures are escalated to
HealthMonitor.record_auth_failure() before being re-raised. Broker-agnostic
— works for any of the 6 market-data brokers.

Covers:
- AuthenticationError always escalates
- BrokerAPIError with a known broker-specific auth code escalates
- BrokerAPIError with a non-auth message does NOT escalate
- Generic exceptions do NOT escalate
- Missing health_monitor is tolerated (no crash)
- Exception is always re-raised after recording
"""

import pytest
from unittest.mock import AsyncMock

from app.services.brokers.market_data.exceptions import (
    AuthenticationError,
    BrokerAPIError,
    MarketDataError,
)


@pytest.fixture
def mock_health_monitor():
    m = AsyncMock()
    m.record_auth_failure = AsyncMock()
    return m


@pytest.mark.unit
class TestCallAdapterWithAuthTracking:
    """The helper must exist and escalate auth failures per plan Phase 2."""

    @pytest.mark.asyncio
    async def test_authentication_error_escalates_and_reraises(
        self, mock_health_monitor
    ):
        """AuthenticationError must call record_auth_failure and re-raise."""
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def failing():
            raise AuthenticationError("smartapi", "AB1010 Invalid Token")

        with pytest.raises(AuthenticationError):
            await call_adapter_with_auth_tracking(
                "smartapi", failing(), mock_health_monitor
            )

        mock_health_monitor.record_auth_failure.assert_awaited_once()
        args = mock_health_monitor.record_auth_failure.await_args.args
        assert args[0] == "smartapi"
        # error code should be extracted from message
        assert "AB1010" in args[1] or args[1] == "AB1010"

    @pytest.mark.asyncio
    async def test_broker_api_error_with_smartapi_auth_code_escalates(
        self, mock_health_monitor
    ):
        """AG8001 in BrokerAPIError message → classified as auth → escalate.

        Note: AG8001 is the SmartAPI production error code (distinct from
        AB1010 which is SDK-level). token_policy currently lists AB-prefixed
        codes; the helper should detect either pattern.
        """
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def failing():
            raise BrokerAPIError("smartapi", "AG8001 Invalid Token")

        with pytest.raises(BrokerAPIError):
            await call_adapter_with_auth_tracking(
                "smartapi", failing(), mock_health_monitor
            )

        mock_health_monitor.record_auth_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broker_api_error_with_ab_code_escalates(
        self, mock_health_monitor
    ):
        """AB1010 is SmartAPI's SDK-level invalid token — must escalate."""
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def failing():
            raise BrokerAPIError("smartapi", "AB1010: Invalid Token")

        with pytest.raises(BrokerAPIError):
            await call_adapter_with_auth_tracking(
                "smartapi", failing(), mock_health_monitor
            )

        mock_health_monitor.record_auth_failure.assert_awaited_once()
        args = mock_health_monitor.record_auth_failure.await_args.args
        assert args[0] == "smartapi"
        assert args[1] == "AB1010"

    @pytest.mark.asyncio
    async def test_broker_api_error_with_upstox_auth_code_escalates(
        self, mock_health_monitor
    ):
        """Broker-agnostic: UDAPI100050 on Upstox → escalate.

        Confirms the helper consults token_policy tables by broker name,
        not just hardcoded SmartAPI codes.
        """
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def failing():
            raise BrokerAPIError("upstox", "UDAPI100050: invalid token")

        with pytest.raises(BrokerAPIError):
            await call_adapter_with_auth_tracking(
                "upstox", failing(), mock_health_monitor
            )

        mock_health_monitor.record_auth_failure.assert_awaited_once()
        args = mock_health_monitor.record_auth_failure.await_args.args
        assert args[0] == "upstox"
        assert args[1] == "UDAPI100050"

    @pytest.mark.asyncio
    async def test_broker_api_error_without_auth_code_does_not_escalate(
        self, mock_health_monitor
    ):
        """Non-auth BrokerAPIError (e.g., rate limit, parse error) must NOT
        trigger record_auth_failure — only re-raise."""
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def failing():
            raise BrokerAPIError("smartapi", "Failed to parse response body")

        with pytest.raises(BrokerAPIError):
            await call_adapter_with_auth_tracking(
                "smartapi", failing(), mock_health_monitor
            )

        mock_health_monitor.record_auth_failure.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_generic_exception_does_not_escalate(self, mock_health_monitor):
        """Unrelated exceptions pass through untouched."""
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def failing():
            raise ValueError("something else")

        with pytest.raises(ValueError):
            await call_adapter_with_auth_tracking(
                "smartapi", failing(), mock_health_monitor
            )

        mock_health_monitor.record_auth_failure.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_health_monitor_tolerated(self):
        """If health_monitor=None (e.g., app startup race), don't crash —
        just re-raise the original exception."""
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def failing():
            raise AuthenticationError("kite", "TokenException: token expired")

        with pytest.raises(AuthenticationError):
            await call_adapter_with_auth_tracking("kite", failing(), None)

    @pytest.mark.asyncio
    async def test_success_returns_result(self, mock_health_monitor):
        """Happy path: coroutine succeeds → helper returns its value."""
        from app.services.brokers.market_data.auth_tracking import (
            call_adapter_with_auth_tracking,
        )

        async def succeeds():
            return {"ltp": 123.45}

        result = await call_adapter_with_auth_tracking(
            "smartapi", succeeds(), mock_health_monitor
        )
        assert result == {"ltp": 123.45}
        mock_health_monitor.record_auth_failure.assert_not_awaited()


@pytest.mark.unit
class TestErrorCodeExtraction:
    """The internal _extract_error_code helper must handle the patterns we
    see in real broker responses."""

    def test_extracts_smartapi_ag_code(self):
        from app.services.brokers.market_data.auth_tracking import _extract_error_code
        assert _extract_error_code("[smartapi] AG8001 Invalid Token") == "AG8001"

    def test_extracts_smartapi_ab_code(self):
        from app.services.brokers.market_data.auth_tracking import _extract_error_code
        assert _extract_error_code("AB1010: Invalid Token") == "AB1010"

    def test_extracts_upstox_code(self):
        from app.services.brokers.market_data.auth_tracking import _extract_error_code
        assert _extract_error_code("UDAPI100050: invalid token") == "UDAPI100050"

    def test_extracts_kite_token_exception(self):
        from app.services.brokers.market_data.auth_tracking import _extract_error_code
        assert _extract_error_code("TokenException: access token expired") == "TokenException"

    def test_returns_none_when_no_code(self):
        from app.services.brokers.market_data.auth_tracking import _extract_error_code
        assert _extract_error_code("Connection timed out") is None
