"""
TickerPool Credential Cache Expiry Tests (Gap Q)

Tests that TickerPool checks token_expiry before reusing cached credentials.
Expired credentials should be cleared so they get re-fetched.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from app.services.brokers.market_data.ticker.pool import TickerPool


@pytest.fixture(autouse=True)
def reset_pool():
    """Reset singleton before each test."""
    TickerPool.reset_instance()
    yield
    TickerPool.reset_instance()


class TestCredentialExpiry:

    def test_set_credentials_stores_expiry(self):
        """set_credentials should store token_expiry if provided."""
        pool = TickerPool.get_instance()
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        pool.set_credentials("smartapi", {
            "jwt_token": "test",
            "token_expiry": future,
        })
        assert pool._credentials["smartapi"]["jwt_token"] == "test"
        assert pool._credentials["smartapi"]["token_expiry"] == future

    def test_credentials_valid_returns_true_for_unexpired(self):
        """credentials_valid() returns True when token_expiry is in the future."""
        pool = TickerPool.get_instance()
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        pool.set_credentials("smartapi", {
            "jwt_token": "test",
            "token_expiry": future,
        })
        assert pool.credentials_valid("smartapi") is True

    def test_credentials_valid_returns_false_for_expired(self):
        """credentials_valid() returns False when token_expiry is in the past."""
        pool = TickerPool.get_instance()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        pool.set_credentials("smartapi", {
            "jwt_token": "test",
            "token_expiry": past,
        })
        assert pool.credentials_valid("smartapi") is False

    def test_credentials_valid_returns_true_when_no_expiry(self):
        """credentials_valid() returns True when no token_expiry is set (e.g., static tokens)."""
        pool = TickerPool.get_instance()
        pool.set_credentials("dhan", {
            "client_id": "D123",
            "access_token": "static_token",
        })
        assert pool.credentials_valid("dhan") is True

    def test_credentials_valid_returns_false_when_not_set(self):
        """credentials_valid() returns False when broker has no credentials at all."""
        pool = TickerPool.get_instance()
        assert pool.credentials_valid("nonexistent") is False

    def test_clear_expired_credentials_removes_expired(self):
        """clear_expired_credentials() removes brokers with expired tokens."""
        pool = TickerPool.get_instance()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=12)

        pool.set_credentials("smartapi", {"jwt_token": "expired", "token_expiry": past})
        pool.set_credentials("kite", {"access_token": "valid", "token_expiry": future})
        pool.set_credentials("dhan", {"access_token": "no_expiry"})

        cleared = pool.clear_expired_credentials()

        assert "smartapi" in cleared
        assert "smartapi" not in pool._credentials
        assert "kite" in pool._credentials
        assert "dhan" in pool._credentials

    def test_clear_expired_returns_empty_when_none_expired(self):
        """clear_expired_credentials() returns empty list when nothing is expired."""
        pool = TickerPool.get_instance()
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        pool.set_credentials("kite", {"access_token": "valid", "token_expiry": future})

        cleared = pool.clear_expired_credentials()
        assert cleared == []
