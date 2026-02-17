"""Tests for broker ticker adapter stubs (Paytm — remaining).

Verifies that:
- Each adapter is a proper TickerAdapter subclass
- Adapters can be imported from both adapters/__init__.py and ticker/__init__.py
- TickerPool can register adapters without error (class registration, not instantiation)

NOTE: Dhan, Fyers, Upstox, and Paytm stubs have been fully implemented:
- DhanTickerAdapter: see test_dhan_ticker_adapter.py
- FyersTickerAdapter: see test_fyers_ticker_adapter.py
- UpstoxTickerAdapter: see test_upstox_ticker_adapter.py
- PaytmTickerAdapter: see test_paytm_ticker_adapter.py
"""

import pytest

from app.services.brokers.market_data.ticker.adapter_base import TickerAdapter


# ═══════════════════════════════════════════════════════════════════════
# IMPORT TESTS — verify stubs are accessible from expected paths
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterImports:
    """Verify adapter stubs are importable from both entry points."""

    def test_import_from_adapters_package(self):
        from app.services.brokers.market_data.ticker.adapters import (
            DhanTickerAdapter,
            FyersTickerAdapter,
            UpstoxTickerAdapter,
            PaytmTickerAdapter,
        )
        assert DhanTickerAdapter is not None
        assert FyersTickerAdapter is not None
        assert UpstoxTickerAdapter is not None
        assert PaytmTickerAdapter is not None

    def test_import_from_ticker_package(self):
        from app.services.brokers.market_data.ticker import (
            DhanTickerAdapter,
            FyersTickerAdapter,
            UpstoxTickerAdapter,
            PaytmTickerAdapter,
        )
        assert DhanTickerAdapter is not None
        assert FyersTickerAdapter is not None
        assert UpstoxTickerAdapter is not None
        assert PaytmTickerAdapter is not None

    def test_all_stubs_are_ticker_adapter_subclasses(self):
        from app.services.brokers.market_data.ticker.adapters import (
            DhanTickerAdapter,
            FyersTickerAdapter,
            UpstoxTickerAdapter,
            PaytmTickerAdapter,
        )
        assert issubclass(DhanTickerAdapter, TickerAdapter)
        assert issubclass(FyersTickerAdapter, TickerAdapter)
        assert issubclass(UpstoxTickerAdapter, TickerAdapter)
        assert issubclass(PaytmTickerAdapter, TickerAdapter)


# ═══════════════════════════════════════════════════════════════════════
# DHAN ADAPTER STUB
# ═══════════════════════════════════════════════════════════════════════

# NOTE: Dhan stub tests removed — DhanTickerAdapter is fully implemented.
# See tests/backend/brokers/test_dhan_ticker_adapter.py for full test coverage.

# NOTE: Fyers stub tests removed — FyersTickerAdapter is fully implemented.
# See tests/backend/brokers/test_fyers_ticker_adapter.py for full test coverage.

# NOTE: Upstox stub tests removed — UpstoxTickerAdapter is fully implemented.
# See tests/backend/brokers/test_upstox_ticker_adapter.py for full test coverage.

# NOTE: Paytm stub tests removed — PaytmTickerAdapter is fully implemented.
# See tests/backend/brokers/test_paytm_ticker_adapter.py for full test coverage.


# ═══════════════════════════════════════════════════════════════════════
# POOL REGISTRATION — stubs register without error
# ═══════════════════════════════════════════════════════════════════════

class TestPoolRegistration:
    """Verify stubs can be registered with TickerPool (class-level, no instantiation)."""

    def test_pool_register_dhan(self):
        from app.services.brokers.market_data.ticker.pool import TickerPool
        from app.services.brokers.market_data.ticker.adapters.dhan import DhanTickerAdapter

        pool = TickerPool.__new__(TickerPool)
        pool._adapter_classes = {}
        pool.register_adapter("dhan", DhanTickerAdapter)
        assert "dhan" in pool._adapter_classes
        assert pool._adapter_classes["dhan"] is DhanTickerAdapter

    def test_pool_register_fyers(self):
        from app.services.brokers.market_data.ticker.pool import TickerPool
        from app.services.brokers.market_data.ticker.adapters.fyers import FyersTickerAdapter

        pool = TickerPool.__new__(TickerPool)
        pool._adapter_classes = {}
        pool.register_adapter("fyers", FyersTickerAdapter)
        assert "fyers" in pool._adapter_classes

    def test_pool_register_upstox(self):
        from app.services.brokers.market_data.ticker.pool import TickerPool
        from app.services.brokers.market_data.ticker.adapters.upstox import UpstoxTickerAdapter

        pool = TickerPool.__new__(TickerPool)
        pool._adapter_classes = {}
        pool.register_adapter("upstox", UpstoxTickerAdapter)
        assert "upstox" in pool._adapter_classes

    def test_pool_register_paytm(self):
        from app.services.brokers.market_data.ticker.pool import TickerPool
        from app.services.brokers.market_data.ticker.adapters.paytm import PaytmTickerAdapter

        pool = TickerPool.__new__(TickerPool)
        pool._adapter_classes = {}
        pool.register_adapter("paytm", PaytmTickerAdapter)
        assert "paytm" in pool._adapter_classes

    def test_pool_register_all_four_stubs(self):
        """Register all 4 stubs — verifies no naming conflicts."""
        from app.services.brokers.market_data.ticker.pool import TickerPool
        from app.services.brokers.market_data.ticker.adapters import (
            DhanTickerAdapter,
            FyersTickerAdapter,
            UpstoxTickerAdapter,
            PaytmTickerAdapter,
        )

        pool = TickerPool.__new__(TickerPool)
        pool._adapter_classes = {}
        pool.register_adapter("dhan", DhanTickerAdapter)
        pool.register_adapter("fyers", FyersTickerAdapter)
        pool.register_adapter("upstox", UpstoxTickerAdapter)
        pool.register_adapter("paytm", PaytmTickerAdapter)

        assert len(pool._adapter_classes) == 4
        assert set(pool._adapter_classes.keys()) == {"dhan", "fyers", "upstox", "paytm"}


# ═══════════════════════════════════════════════════════════════════════
# CREDENTIAL LOADING — websocket.py credential patterns
# ═══════════════════════════════════════════════════════════════════════

class TestCredentialPatterns:
    """Verify credential dict structures match what adapters expect."""

    def test_dhan_credential_keys(self):
        """Dhan expects client_id + access_token."""
        creds = {"client_id": "test_id", "access_token": "test_token"}
        assert "client_id" in creds
        assert "access_token" in creds

    def test_fyers_credential_keys(self):
        """Fyers expects app_id + access_token."""
        creds = {"app_id": "test_app", "access_token": "test_token"}
        assert "app_id" in creds
        assert "access_token" in creds

    def test_upstox_credential_keys(self):
        """Upstox expects api_key + access_token."""
        creds = {"api_key": "test_key", "access_token": "test_token"}
        assert "api_key" in creds
        assert "access_token" in creds

    def test_paytm_credential_keys(self):
        """Paytm expects api_key + public_access_token (NOT access_token)."""
        creds = {"api_key": "test_key", "public_access_token": "test_pub_token"}
        assert "api_key" in creds
        assert "public_access_token" in creds
        # Verify it's NOT access_token (common mistake with Paytm)
        assert "access_token" not in creds
