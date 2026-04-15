"""
Pytest fixtures for AI service integration tests.

Provides fixtures for:
- Mock KiteConnect client
- Mock AsyncSession (db)
- Mock MarketDataService
- AIMonitor with mocked dependencies
- DailyScheduler with mocked jobs
- LearningPipeline with mocked scorer
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# MOCK BROKER FIXTURES
# =============================================================================

@pytest.fixture
def mock_kite():
    """Create a mock KiteConnect client."""
    kite = MagicMock()
    kite.ltp = MagicMock(return_value={"NSE:NIFTY 50": {"last_price": 22000.0}})
    kite.quote = MagicMock(return_value={})
    kite.positions = MagicMock(return_value={"net": []})
    kite.orders = MagicMock(return_value=[])
    kite.place_order = MagicMock(return_value="ORDER123")
    return kite


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def mock_market_data():
    """Create a mock MarketDataService."""
    md = MagicMock()
    spot = MagicMock()
    spot.ltp = 22000.0
    md.get_spot_price = AsyncMock(return_value=spot)
    md.get_vix = AsyncMock(return_value=14.5)
    md.get_live_quote = AsyncMock(return_value=MagicMock(last_price=22000.0))
    return md


# =============================================================================
# AI CONFIG FIXTURES
# =============================================================================

@pytest.fixture
def sample_user_id():
    """Return a consistent test user UUID."""
    return uuid4()


@pytest.fixture
def mock_ai_user_config(sample_user_id):
    """Create a mock AIUserConfig."""
    config = MagicMock()
    config.user_id = sample_user_id
    config.ai_enabled = True
    config.trading_mode = "paper"
    config.autonomy_level = "SANDBOX"
    config.max_daily_trades = 5
    config.max_concurrent_strategies = 2
    config.min_confidence_threshold = 60
    config.max_vix_threshold = 25.0
    config.weekly_loss_limit = 10000
    return config


# =============================================================================
# KILL SWITCH FIXTURES
# =============================================================================

@pytest.fixture
def mock_kill_switch():
    """Create a mock KillSwitchService."""
    ks = AsyncMock()
    ks.is_enabled = AsyncMock(return_value=False)
    ks.trigger = AsyncMock(return_value=MagicMock(
        strategies_affected=2,
        positions_exited=4,
        orders_placed=4
    ))
    ks.get_status = AsyncMock(return_value=MagicMock(
        enabled=False,
        triggered_at=None,
        can_reset=True
    ))
    return ks


# =============================================================================
# ADJUSTMENT ENGINE FIXTURES
# =============================================================================

@pytest.fixture
def mock_adjustment_engine():
    """Create a mock AdjustmentEngine."""
    ae = AsyncMock()
    ae.evaluate_rules = AsyncMock(return_value=[])
    ae.execute_adjustment = AsyncMock(return_value={
        "executed": True,
        "action": "add_hedge",
        "order_id": "ADJ123"
    })
    return ae
