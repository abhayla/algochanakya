"""
Factory functions for broker-related test objects (users, connections, credentials).

Replaces duplicated test_user and test_broker_connection fixtures
in individual test files.

Usage:
    from tests.factories.broker import make_user_dict, make_broker_connection_dict
"""

from uuid import uuid4
from datetime import datetime


# Canonical broker name → DB name mapping
# DB stores 'zerodha'/'angelone', BrokerType enum uses 'kite'/'angel'
BROKER_DB_NAMES = {
    "kite":    "zerodha",
    "angel":   "angelone",
    "upstox":  "upstox",
    "dhan":    "dhan",
    "fyers":   "fyers",
    "paytm":   "paytm",
}

BROKER_ENUM_NAMES = {v: k for k, v in BROKER_DB_NAMES.items()}


def make_user_dict(
    email: str = "test@example.com",
    user_id: str = None,
    **overrides,
) -> dict:
    """Create a user dict suitable for test assertions."""
    user = {
        "id": user_id or str(uuid4()),
        "email": email,
        "created_at": datetime.now().isoformat(),
    }
    user.update(overrides)
    return user


def make_broker_connection_dict(
    broker_db_name: str = "zerodha",
    broker_user_id: str = "TEST123",
    access_token: str = "test_access_token",
    is_active: bool = True,
    user_id: str = None,
    **overrides,
) -> dict:
    """
    Create a broker connection dict.

    Args:
        broker_db_name: DB-stored name ('zerodha', 'angelone', etc.)
                        Use BROKER_DB_NAMES[broker_type] to convert from enum value.
    """
    conn = {
        "id": str(uuid4()),
        "user_id": user_id or str(uuid4()),
        "broker": broker_db_name,
        "broker_user_id": broker_user_id,
        "access_token": access_token,
        "is_active": is_active,
        "created_at": datetime.now().isoformat(),
    }
    conn.update(overrides)
    return conn


def make_preferences_dict(
    market_data_source: str = "smartapi",
    order_broker: str = "kite",
    pnl_grid_interval: int = 100,
    **overrides,
) -> dict:
    """Create a user preferences dict."""
    prefs = {
        "market_data_source": market_data_source,
        "order_broker": order_broker,
        "pnl_grid_interval": pnl_grid_interval,
    }
    prefs.update(overrides)
    return prefs
