"""Tests for TickerAdapter error reporting — Layer 1.1.

Tests that adapter_base.py supports:
- Error callback registration
- Error reporting to callback
- Auth error reporting with last_error tracking
- Graceful behavior when no callback is set
"""

import asyncio
import pytest
from decimal import Decimal
from typing import List, Any
from unittest.mock import MagicMock

from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter
from app.services.brokers.market_data.ticker.models import NormalizedTick


# ─── Concrete stub for testing abstract class ─────────────────────────────────

class StubAdapter(TickerAdapter):
    """Minimal concrete adapter for testing base class behavior."""

    async def _connect_ws(self, credentials: dict) -> None:
        pass

    async def _disconnect_ws(self) -> None:
        pass

    async def _subscribe_ws(self, broker_tokens: list, mode: str) -> None:
        pass

    async def _unsubscribe_ws(self, broker_tokens: list) -> None:
        pass

    def _translate_to_broker_tokens(self, canonical_tokens: List[int]) -> list:
        return canonical_tokens

    def _get_canonical_token(self, broker_token: Any) -> int:
        return broker_token

    def _parse_tick(self, raw_data: Any) -> List[NormalizedTick]:
        return []


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def adapter():
    return StubAdapter("test_broker")


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestErrorCallbackRegistration:
    def test_set_on_error_callback(self, adapter: StubAdapter):
        """Error callback can be registered on the adapter."""
        cb = MagicMock()
        adapter.set_on_error_callback(cb)
        assert adapter._on_error_callback is cb

    def test_no_error_callback_initially(self, adapter: StubAdapter):
        """Error callback is None by default."""
        assert adapter._on_error_callback is None


class TestReportError:
    def test_report_error_calls_callback(self, adapter: StubAdapter):
        """_report_error invokes the registered callback with broker, type, msg."""
        cb = MagicMock()
        adapter.set_on_error_callback(cb)

        adapter._report_error("connection_closed", "WebSocket closed unexpectedly")

        cb.assert_called_once_with("test_broker", "connection_closed", "WebSocket closed unexpectedly")

    def test_report_error_without_callback_no_crash(self, adapter: StubAdapter):
        """_report_error with no callback does not raise."""
        # Should not raise
        adapter._report_error("connection_closed", "WebSocket closed unexpectedly")

    def test_report_error_sets_last_error(self, adapter: StubAdapter):
        """_report_error stores the error details in last_error."""
        adapter._report_error("timeout", "Connection timed out")

        assert adapter.last_error is not None
        assert adapter.last_error["error_type"] == "timeout"
        assert adapter.last_error["error_msg"] == "Connection timed out"


class TestReportAuthError:
    def test_report_auth_error_calls_callback_with_auth_type(self, adapter: StubAdapter):
        """_report_auth_error invokes callback with error_type='auth'."""
        cb = MagicMock()
        adapter.set_on_error_callback(cb)

        adapter._report_auth_error("UDAPI100050", "Invalid token used to access API")

        cb.assert_called_once_with(
            "test_broker", "auth", "UDAPI100050: Invalid token used to access API"
        )

    def test_report_auth_error_sets_last_error_with_code(self, adapter: StubAdapter):
        """_report_auth_error stores error_code in last_error."""
        adapter._report_auth_error("AB1010", "Invalid Token")

        assert adapter.last_error is not None
        assert adapter.last_error["error_type"] == "auth"
        assert adapter.last_error["error_code"] == "AB1010"
        assert adapter.last_error["error_msg"] == "AB1010: Invalid Token"

    def test_report_auth_error_without_callback_no_crash(self, adapter: StubAdapter):
        """_report_auth_error with no callback does not raise."""
        adapter._report_auth_error("TOKEN_EXPIRED", "Session expired")


class TestLastErrorProperty:
    def test_last_error_none_initially(self, adapter: StubAdapter):
        """last_error is None before any errors reported."""
        assert adapter.last_error is None

    def test_last_error_updated_by_report_error(self, adapter: StubAdapter):
        """last_error reflects the most recent _report_error call."""
        adapter._report_error("timeout", "first error")
        adapter._report_error("disconnect", "second error")

        assert adapter.last_error["error_type"] == "disconnect"
        assert adapter.last_error["error_msg"] == "second error"

    def test_last_error_updated_by_report_auth_error(self, adapter: StubAdapter):
        """last_error reflects auth errors too."""
        adapter._report_error("timeout", "normal error")
        adapter._report_auth_error("AB1010", "Invalid Token")

        assert adapter.last_error["error_type"] == "auth"
        assert adapter.last_error["error_code"] == "AB1010"
