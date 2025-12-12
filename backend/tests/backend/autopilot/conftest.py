"""
Pytest fixtures for AutoPilot testing.

Provides fixtures for:
- Async database sessions (SQLite in-memory)
- Test users with UUID
- AutoPilot user settings
- AutoPilot strategies (draft, waiting, active)
- Mock Kite Connect client
- Mock Market Data service
- Mock WebSocket manager
- Async HTTP client with dependency overrides
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime, date, time, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, String, BigInteger, Integer, event
from sqlalchemy.engine import Engine
from httpx import AsyncClient, ASGITransport

# SQLite JSONB compatibility
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)


# SQLite ARRAY compatibility - convert ARRAY to JSON for SQLite
@compiles(ARRAY, 'sqlite')
def compile_array_sqlite(element, compiler, **kw):
    return "JSON"


# SQLite BigInteger compatibility - use INTEGER for autoincrement to work
@compiles(BigInteger, 'sqlite')
def compile_biginteger_sqlite(element, compiler, **kw):
    return "INTEGER"


# SQLite UUID compatibility - store as TEXT
@compiles(PgUUID, 'sqlite')
def compile_uuid_sqlite(element, compiler, **kw):
    return "TEXT"


# SQLite PgEnum compatibility - store as VARCHAR
@compiles(PgEnum, 'sqlite')
def compile_pgenum_sqlite(element, compiler, **kw):
    return "VARCHAR(50)"


# Import app components
from app.database import Base, get_db
from app.main import app
from app.models.users import User
from app.models.autopilot import (
    AutoPilotStrategy, AutoPilotUserSettings, AutoPilotOrder, AutoPilotLog,
    AutoPilotTemplate, AutoPilotConditionEval, AutoPilotDailySummary,
    AutoPilotAdjustmentLog, AutoPilotPendingConfirmation,
    StrategyStatus, Underlying, PositionType, OrderStatus, OrderPurpose, LogSeverity,
    ExecutionMode, AdjustmentTriggerType, AdjustmentActionType, ConfirmationStatus,
    # Phase 4 Models
    AutoPilotTradeJournal, AutoPilotAnalyticsCache, AutoPilotReport,
    AutoPilotBacktest, AutoPilotTemplateRating,
    ExitReason, TemplateCategory, ReportType, ReportFormat, BacktestStatus, ShareMode
)
from app.utils.dependencies import get_current_user


# Test database URL - SQLite in-memory
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# =============================================================================
# EVENT LOOP FIXTURE
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for a test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        # Clean up tables before each test (order matters due to foreign keys)
        tables_to_clean = [
            # Phase 4 tables (clean first due to FK dependencies)
            AutoPilotTemplateRating.__table__,
            AutoPilotBacktest.__table__,
            AutoPilotReport.__table__,
            AutoPilotAnalyticsCache.__table__,
            AutoPilotTradeJournal.__table__,
            # Phase 1-3 tables
            AutoPilotConditionEval.__table__,
            AutoPilotLog.__table__,
            AutoPilotOrder.__table__,
            AutoPilotDailySummary.__table__,
            AutoPilotAdjustmentLog.__table__,
            AutoPilotPendingConfirmation.__table__,
            AutoPilotStrategy.__table__,
            AutoPilotUserSettings.__table__,
            AutoPilotTemplate.__table__,
            User.__table__,
        ]
        for table in tables_to_clean:
            try:
                await session.execute(table.delete())
            except Exception:
                pass
        await session.commit()

        yield session
        await session.rollback()


# =============================================================================
# USER FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user with UUID."""
    user = User(
        id=uuid4(),
        email="autopilot_test@example.com"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def another_user(db_session: AsyncSession) -> User:
    """Create another test user for isolation tests."""
    user = User(
        id=uuid4(),
        email="other_user@example.com"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =============================================================================
# AUTOPILOT SETTINGS FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def test_settings(db_session: AsyncSession, test_user: User) -> AutoPilotUserSettings:
    """Create AutoPilot user settings."""
    settings = AutoPilotUserSettings(
        user_id=test_user.id,
        daily_loss_limit=Decimal("20000.00"),
        per_strategy_loss_limit=Decimal("10000.00"),
        max_capital_deployed=Decimal("500000.00"),
        max_active_strategies=3,
        no_trade_first_minutes=5,
        no_trade_last_minutes=5,
        cooldown_after_loss=False,
        cooldown_minutes=30,
        cooldown_threshold=Decimal("5000.00"),
        default_order_settings={
            "order_type": "MARKET",
            "execution_style": "sequential",
            "delay_between_legs": 2
        },
        notification_prefs={
            "enabled": True,
            "channels": ["in_app"]
        },
        failure_handling={
            "on_network_error": "retry",
            "max_retries": 3
        },
        paper_trading_mode=False,
        show_advanced_features=False
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(settings)
    return settings


# =============================================================================
# AUTOPILOT STRATEGY FIXTURES
# =============================================================================

def get_sample_legs_config() -> List[Dict[str, Any]]:
    """Return sample legs configuration for Iron Condor."""
    return [
        {
            "id": "leg_1",
            "contract_type": "PE",
            "transaction_type": "BUY",
            "strike_selection": {"mode": "atm_offset", "offset": -4},
            "quantity_multiplier": 1,
            "execution_order": 1
        },
        {
            "id": "leg_2",
            "contract_type": "PE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": -2},
            "quantity_multiplier": 1,
            "execution_order": 2
        },
        {
            "id": "leg_3",
            "contract_type": "CE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": 2},
            "quantity_multiplier": 1,
            "execution_order": 3
        },
        {
            "id": "leg_4",
            "contract_type": "CE",
            "transaction_type": "BUY",
            "strike_selection": {"mode": "atm_offset", "offset": 4},
            "quantity_multiplier": 1,
            "execution_order": 4
        }
    ]


def get_sample_entry_conditions() -> Dict[str, Any]:
    """Return sample entry conditions."""
    return {
        "logic": "AND",
        "conditions": [
            {
                "id": "cond_1",
                "enabled": True,
                "variable": "TIME.CURRENT",
                "operator": "greater_than",
                "value": "09:20"
            },
            {
                "id": "cond_2",
                "enabled": True,
                "variable": "VIX.VALUE",
                "operator": "less_than",
                "value": 20
            }
        ]
    }


def get_sample_risk_settings() -> Dict[str, Any]:
    """Return sample risk settings."""
    return {
        "max_loss": 5000,
        "max_loss_pct": 50,
        "trailing_stop": {
            "enabled": True,
            "trigger_profit": 3000,
            "trail_amount": 1000
        },
        "max_margin": 100000,
        "time_stop": "15:15"
    }


def get_sample_order_settings() -> Dict[str, Any]:
    """Return sample order settings."""
    return {
        "order_type": "MARKET",
        "execution_style": "sequential",
        "leg_sequence": ["leg_2", "leg_3", "leg_1", "leg_4"],
        "delay_between_legs": 2,
        "slippage_protection": {
            "enabled": True,
            "max_per_leg_pct": 2.0,
            "max_total_pct": 5.0,
            "on_exceed": "retry",
            "max_retries": 3
        },
        "on_leg_failure": "stop"
    }


def get_sample_schedule_config() -> Dict[str, Any]:
    """Return sample schedule configuration."""
    return {
        "activation_mode": "always",
        "active_days": ["MON", "TUE", "WED", "THU", "FRI"],
        "start_time": "09:15",
        "end_time": "15:30",
        "expiry_days_only": False
    }


@pytest_asyncio.fixture
async def test_strategy(db_session: AsyncSession, test_user: User) -> AutoPilotStrategy:
    """Create a test strategy in draft status."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Test Iron Condor",
        description="A test Iron Condor strategy",
        status="draft",
        underlying="NIFTY",
        expiry_type="current_week",
        expiry_date=None,
        lots=1,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        adjustment_rules=[],
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_strategy_waiting(db_session: AsyncSession, test_user: User) -> AutoPilotStrategy:
    """Create a test strategy in waiting status."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Waiting Strategy",
        description="A strategy waiting for entry conditions",
        status="waiting",
        underlying="NIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100,
        activated_at=datetime.utcnow(),
        runtime_state={
            "paper_trading": False,
            "current_pnl": 0,
            "margin_used": 0,
            "current_positions": []
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_strategy_active(db_session: AsyncSession, test_user: User) -> AutoPilotStrategy:
    """Create a test strategy in active status with positions."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Active Strategy",
        description="An active strategy with positions",
        status="active",
        underlying="NIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100,
        activated_at=datetime.utcnow(),
        runtime_state={
            "paper_trading": False,
            "current_pnl": 1500.0,
            "margin_used": 50000.0,
            "entry_time": datetime.utcnow().isoformat(),
            "current_positions": [
                {
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24D2624800PE",
                    "quantity": 25,
                    "transaction_type": "BUY",
                    "entry_price": 50.0,
                    "current_ltp": 45.0
                },
                {
                    "leg_id": "leg_2",
                    "tradingsymbol": "NIFTY24D2624900PE",
                    "quantity": -25,
                    "transaction_type": "SELL",
                    "entry_price": 80.0,
                    "current_ltp": 70.0
                }
            ]
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_strategy_paused(db_session: AsyncSession, test_user: User) -> AutoPilotStrategy:
    """Create a test strategy in paused status."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Paused Strategy",
        description="A paused strategy",
        status="paused",
        underlying="BANKNIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100,
        activated_at=datetime.utcnow(),
        runtime_state={
            "paper_trading": False,
            "current_pnl": 0,
            "margin_used": 0
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_strategy_completed(db_session: AsyncSession, test_user: User) -> AutoPilotStrategy:
    """Create a test strategy in completed status."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Completed Strategy",
        description="A completed strategy",
        status="completed",
        underlying="NIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100,
        completed_at=datetime.utcnow(),
        runtime_state={
            "realized_pnl": 5000.0,
            "exit_reason": "Target profit reached"
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


# =============================================================================
# AUTOPILOT ORDER FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def test_order(
    db_session: AsyncSession,
    test_user: User,
    test_strategy_active: AutoPilotStrategy
) -> AutoPilotOrder:
    """Create a test order."""
    order = AutoPilotOrder(
        strategy_id=test_strategy_active.id,
        user_id=test_user.id,
        kite_order_id="220101000001",
        purpose="entry",
        leg_index=0,
        exchange="NFO",
        tradingsymbol="NIFTY24D2624900PE",
        underlying="NIFTY",
        contract_type="PE",
        strike=Decimal("24900"),
        expiry=date.today(),
        transaction_type="SELL",
        order_type="MARKET",
        product="MIS",
        quantity=25,
        ltp_at_order=Decimal("80.50"),
        executed_price=Decimal("80.25"),
        executed_quantity=25,
        slippage_amount=Decimal("6.25"),
        slippage_pct=Decimal("0.31"),
        status="complete",
        order_placed_at=datetime.utcnow(),
        order_filled_at=datetime.utcnow()
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    return order


# =============================================================================
# AUTOPILOT LOG FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def test_log(
    db_session: AsyncSession,
    test_user: User,
    test_strategy: AutoPilotStrategy
) -> AutoPilotLog:
    """Create a test log entry."""
    log = AutoPilotLog(
        user_id=test_user.id,
        strategy_id=test_strategy.id,
        event_type="strategy_created",
        severity="info",
        message="Strategy created successfully",
        event_data={"strategy_id": test_strategy.id}
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


# =============================================================================
# AUTOPILOT TEMPLATE FIXTURES
# =============================================================================

@pytest_asyncio.fixture
async def test_template(db_session: AsyncSession) -> AutoPilotTemplate:
    """Create a test AutoPilot template."""
    template = AutoPilotTemplate(
        name="Iron Condor Template",
        description="Standard Iron Condor for weekly expiry",
        is_system=True,
        is_public=True,
        strategy_config={
            "underlying": "NIFTY",
            "legs_config": get_sample_legs_config(),
            "entry_conditions": get_sample_entry_conditions(),
            "risk_settings": get_sample_risk_settings()
        },
        category="neutral",
        tags=["neutral", "income", "defined-risk"],
        risk_level="medium",
        usage_count=100
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


# =============================================================================
# HTTP CLIENT FIXTURE
# =============================================================================

@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession,
    test_user: User
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client without authentication."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    # Don't override get_current_user - will raise 401

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Aliases for API tests compatibility
@pytest_asyncio.fixture
async def async_client(client: AsyncClient) -> AsyncClient:
    """Alias for client fixture used by API tests."""
    return client


@pytest_asyncio.fixture
async def async_client_no_auth(unauthenticated_client: AsyncClient) -> AsyncClient:
    """Alias for unauthenticated_client fixture used by API tests."""
    return unauthenticated_client


@pytest_asyncio.fixture
async def test_strategy_draft(test_strategy: AutoPilotStrategy) -> AutoPilotStrategy:
    """Alias for test_strategy fixture (which is in draft status) used by API tests."""
    return test_strategy


# =============================================================================
# MOCK FIXTURES
# =============================================================================

@pytest.fixture
def mock_kite():
    """Mock KiteConnect client."""
    mock = MagicMock()

    # Mock LTP response
    mock.ltp.return_value = {
        "NSE:NIFTY 50": {"last_price": 25000.0, "instrument_token": 256265},
        "NSE:NIFTY BANK": {"last_price": 52000.0, "instrument_token": 260105},
        "NFO:NIFTY24D2624800PE": {"last_price": 50.0, "instrument_token": 12345},
        "NFO:NIFTY24D2624900PE": {"last_price": 80.0, "instrument_token": 12346},
        "NFO:NIFTY24D2625100CE": {"last_price": 75.0, "instrument_token": 12347},
        "NFO:NIFTY24D2625200CE": {"last_price": 45.0, "instrument_token": 12348},
        "NSE:INDIA VIX": {"last_price": 15.5, "instrument_token": 264969},
    }

    # Mock quote response
    mock.quote.return_value = {
        "NSE:NIFTY 50": {
            "last_price": 25000.0,
            "instrument_token": 256265,
            "ohlc": {"open": 24900, "high": 25100, "low": 24850, "close": 24950}
        },
        "NSE:NIFTY BANK": {
            "last_price": 52000.0,
            "instrument_token": 260105,
            "ohlc": {"open": 51800, "high": 52200, "low": 51700, "close": 51900}
        },
        "NSE:INDIA VIX": {"last_price": 15.5, "instrument_token": 264969}
    }

    # Mock place_order
    mock.place_order.return_value = "220101000001"

    # Mock order_history
    mock.order_history.return_value = [
        {
            "order_id": "220101000001",
            "status": "COMPLETE",
            "filled_quantity": 25,
            "average_price": 80.25
        }
    ]

    return mock


@pytest.fixture
def mock_market_data(mock_kite):
    """Mock MarketDataService."""
    from app.services.market_data import MarketDataService, SpotData, MarketQuote

    mock = AsyncMock(spec=MarketDataService)
    mock.kite = mock_kite

    # Mock get_ltp
    async def mock_get_ltp(instruments):
        result = {}
        for inst in instruments:
            if "NIFTY" in inst:
                result[inst] = Decimal("80.0")
            else:
                result[inst] = Decimal("50.0")
        return result

    mock.get_ltp = mock_get_ltp

    # Mock get_spot_price
    async def mock_get_spot_price(underlying):
        spot_prices = {
            "NIFTY": SpotData(
                symbol="NIFTY",
                ltp=Decimal("25000.0"),
                change=Decimal("50.0"),
                change_pct=0.2,
                timestamp=datetime.now()
            ),
            "BANKNIFTY": SpotData(
                symbol="BANKNIFTY",
                ltp=Decimal("52000.0"),
                change=Decimal("100.0"),
                change_pct=0.19,
                timestamp=datetime.now()
            )
        }
        return spot_prices.get(underlying.upper(), spot_prices["NIFTY"])

    mock.get_spot_price = mock_get_spot_price

    # Mock get_vix
    async def mock_get_vix():
        return Decimal("15.5")

    mock.get_vix = mock_get_vix

    return mock


@pytest.fixture
def mock_ws_manager():
    """Mock WebSocket ConnectionManager."""
    mock = AsyncMock()

    # Track sent messages for assertions
    mock.sent_messages = []

    async def mock_send_to_user(user_id, message):
        mock.sent_messages.append({"user_id": user_id, "message": message})

    async def mock_send_strategy_update(user_id, strategy_id, updates):
        mock.sent_messages.append({
            "type": "strategy_update",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "updates": updates
        })

    async def mock_send_status_change(user_id, strategy_id, old_status, new_status, reason=""):
        mock.sent_messages.append({
            "type": "status_change",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason
        })

    async def mock_send_pnl_update(user_id, strategy_id, realized_pnl, unrealized_pnl, total_pnl):
        mock.sent_messages.append({
            "type": "pnl_update",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl
        })

    async def mock_send_condition_update(user_id, strategy_id, conditions_met, condition_states):
        mock.sent_messages.append({
            "type": "condition_update",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "conditions_met": conditions_met,
            "condition_states": condition_states
        })

    async def mock_send_order_update(user_id, strategy_id, order_id, event_type, order_data):
        mock.sent_messages.append({
            "type": "order_update",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "order_id": order_id,
            "event_type": event_type,
            "order_data": order_data
        })

    async def mock_send_risk_alert(user_id, alert_type, message, data):
        mock.sent_messages.append({
            "type": "risk_alert",
            "user_id": user_id,
            "alert_type": alert_type,
            "message": message,
            "data": data
        })

    async def mock_send_market_status(is_open, message=""):
        mock.sent_messages.append({
            "type": "market_status",
            "is_open": is_open,
            "message": message
        })

    mock.send_to_user = mock_send_to_user
    mock.send_strategy_update = mock_send_strategy_update
    mock.send_status_change = mock_send_status_change
    mock.send_pnl_update = mock_send_pnl_update
    mock.send_condition_update = mock_send_condition_update
    mock.send_order_update = mock_send_order_update
    mock.send_risk_alert = mock_send_risk_alert
    mock.send_market_status = mock_send_market_status

    # Connection tracking
    mock.get_connected_users.return_value = ["user_1", "user_2"]
    mock.get_total_connections.return_value = 2

    return mock


@pytest.fixture
def mock_condition_engine(mock_market_data):
    """Mock ConditionEngine."""
    from app.services.condition_engine import ConditionEngine, EvaluationResult, ConditionResult

    mock = AsyncMock(spec=ConditionEngine)

    async def mock_evaluate(strategy_id, entry_conditions, underlying, legs_config):
        # Default: all conditions met
        conditions = entry_conditions.get("conditions", [])
        results = []
        for cond in conditions:
            results.append(ConditionResult(
                condition_id=cond.get("id", "unknown"),
                variable=cond.get("variable", ""),
                operator=cond.get("operator", ""),
                target_value=cond.get("value"),
                current_value=cond.get("value"),  # Same as target = met
                is_met=True,
                progress_pct=100.0
            ))

        return EvaluationResult(
            strategy_id=strategy_id,
            all_conditions_met=True,
            individual_results=results,
            evaluation_time=datetime.now()
        )

    mock.evaluate = mock_evaluate
    return mock


@pytest.fixture
def mock_order_executor(mock_kite, mock_market_data):
    """Mock OrderExecutor."""
    from app.services.order_executor import OrderExecutor, OrderResult

    mock = AsyncMock(spec=OrderExecutor)

    async def mock_execute_entry(db, strategy, dry_run=False):
        legs = strategy.legs_config or []
        results = []
        for i, leg in enumerate(legs):
            results.append(OrderResult(
                success=True,
                order_id=str(1000 + i),
                kite_order_id=f"DRY_{datetime.now().timestamp()}_{i}" if dry_run else f"220101{i:06d}",
                message="Order placed" + (" (dry run)" if dry_run else ""),
                executed_price=Decimal("80.0"),
                leg_id=leg.get("id", f"leg_{i}")
            ))
        return True, results

    async def mock_execute_exit(db, strategy, exit_type="market", reason="manual", dry_run=False):
        runtime_state = strategy.runtime_state or {}
        positions = runtime_state.get("current_positions", [])
        results = []
        for i, pos in enumerate(positions):
            results.append(OrderResult(
                success=True,
                order_id=str(2000 + i),
                kite_order_id=f"EXIT_{datetime.now().timestamp()}_{i}",
                message=f"Exit order placed: {reason}",
                executed_price=Decimal("75.0"),
                leg_id=pos.get("leg_id", f"leg_{i}")
            ))
        return True, results

    mock.execute_entry = mock_execute_entry
    mock.execute_exit = mock_execute_exit

    return mock


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_strategy_request(
    name: str = "Test Strategy",
    underlying: str = "NIFTY",
    lots: int = 1,
    **kwargs
) -> Dict[str, Any]:
    """Helper to create strategy request payload."""
    return {
        "name": name,
        "description": kwargs.get("description", "Test description"),
        "underlying": underlying,
        "expiry_type": kwargs.get("expiry_type", "current_week"),
        "lots": lots,
        "position_type": kwargs.get("position_type", "intraday"),
        "legs_config": kwargs.get("legs_config", [
            {
                "id": "leg_1",
                "contract_type": "CE",
                "transaction_type": "SELL",
                "strike_selection": {"mode": "atm_offset", "offset": 2},
                "quantity_multiplier": 1,
                "execution_order": 1
            },
            {
                "id": "leg_2",
                "contract_type": "PE",
                "transaction_type": "SELL",
                "strike_selection": {"mode": "atm_offset", "offset": -2},
                "quantity_multiplier": 1,
                "execution_order": 2
            }
        ]),
        "entry_conditions": kwargs.get("entry_conditions", {
            "logic": "AND",
            "conditions": []
        }),
        "adjustment_rules": kwargs.get("adjustment_rules", []),
        "priority": kwargs.get("priority", 100)
    }


# =============================================================================
# ASSERTION HELPERS
# =============================================================================

def assert_strategy_response(response_data: Dict[str, Any], expected_status: str = None):
    """Assert common strategy response structure."""
    assert "id" in response_data
    assert "name" in response_data
    assert "status" in response_data
    assert "underlying" in response_data
    assert "legs_config" in response_data
    assert "entry_conditions" in response_data

    if expected_status:
        assert response_data["status"] == expected_status


def assert_settings_response(response_data: Dict[str, Any]):
    """Assert user settings response structure."""
    assert "daily_loss_limit" in response_data
    assert "per_strategy_loss_limit" in response_data
    assert "max_capital_deployed" in response_data
    assert "max_active_strategies" in response_data
    assert "no_trade_first_minutes" in response_data
    assert "no_trade_last_minutes" in response_data
    assert "paper_trading_mode" in response_data


def assert_dashboard_response(response_data: Dict[str, Any]):
    """Assert dashboard summary response structure."""
    assert "active_strategies" in response_data
    assert "waiting_strategies" in response_data
    assert "today_realized_pnl" in response_data
    assert "today_unrealized_pnl" in response_data
    assert "today_total_pnl" in response_data
    assert "risk_metrics" in response_data
    assert "strategies" in response_data


# =============================================================================
# PHASE 3 FIXTURES - Kill Switch, Adjustments, Confirmations, Trailing Stop
# =============================================================================

@pytest.fixture
def test_adjustment_rule() -> Dict[str, Any]:
    """Sample adjustment rule configuration for PNL-based stop loss."""
    return {
        "id": "adj_1",
        "enabled": True,
        "name": "Stop Loss Rule",
        "trigger": {
            "type": "pnl_based",
            "condition": "loss_exceeds",
            "value": 2000
        },
        "action": {
            "type": "exit_all",
            "params": {"order_type": "MARKET"}
        },
        "execution_mode": "auto",
        "max_executions": 1,
        "cooldown_seconds": 0
    }


@pytest.fixture
def test_adjustment_rule_delta_based() -> Dict[str, Any]:
    """Sample delta-based adjustment rule."""
    return {
        "id": "adj_2",
        "enabled": True,
        "name": "Delta Hedge Rule",
        "trigger": {
            "type": "delta_based",
            "condition": "exceeds",
            "value": 0.3
        },
        "action": {
            "type": "add_hedge",
            "params": {"hedge_type": "both"}
        },
        "execution_mode": "semi_auto",
        "max_executions": 3,
        "cooldown_seconds": 300
    }


@pytest.fixture
def test_adjustment_rule_time_based() -> Dict[str, Any]:
    """Sample time-based adjustment rule."""
    return {
        "id": "adj_3",
        "enabled": True,
        "name": "Auto Exit at Time",
        "trigger": {
            "type": "time_based",
            "condition": "after",
            "value": "15:15"
        },
        "action": {
            "type": "exit_all",
            "params": {"order_type": "MARKET"}
        },
        "execution_mode": "auto",
        "max_executions": 1,
        "cooldown_seconds": 0
    }


@pytest.fixture
def test_trailing_stop_config() -> Dict[str, Any]:
    """Sample trailing stop configuration."""
    return {
        "enabled": True,
        "activation_profit": 3000,
        "trail_distance": 1000,
        "trail_type": "fixed",
        "min_profit_lock": 500
    }


@pytest.fixture
def test_trailing_stop_config_percentage() -> Dict[str, Any]:
    """Sample trailing stop configuration with percentage trailing."""
    return {
        "enabled": True,
        "activation_profit": 5000,
        "trail_distance": 20,  # 20%
        "trail_type": "percentage",
        "min_profit_lock": 1000
    }


def get_sample_adjustment_rules() -> List[Dict[str, Any]]:
    """Return sample adjustment rules for testing."""
    return [
        {
            "id": "adj_1",
            "enabled": True,
            "name": "Stop Loss Rule",
            "trigger": {
                "type": "pnl_based",
                "condition": "loss_exceeds",
                "value": 5000
            },
            "action": {
                "type": "exit_all",
                "params": {"order_type": "MARKET"}
            },
            "execution_mode": "auto",
            "max_executions": 1,
            "cooldown_seconds": 0
        },
        {
            "id": "adj_2",
            "enabled": True,
            "name": "Profit Target",
            "trigger": {
                "type": "pnl_based",
                "condition": "profit_exceeds",
                "value": 10000
            },
            "action": {
                "type": "exit_all",
                "params": {"order_type": "LIMIT"}
            },
            "execution_mode": "semi_auto",
            "max_executions": 1,
            "cooldown_seconds": 0
        }
    ]


@pytest_asyncio.fixture
async def test_strategy_with_adjustments(
    db_session: AsyncSession,
    test_user: User,
    test_adjustment_rule: Dict[str, Any]
) -> AutoPilotStrategy:
    """Create a test strategy with adjustment rules configured."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Strategy With Adjustments",
        description="A strategy with adjustment rules",
        status="active",
        underlying="NIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        adjustment_rules=get_sample_adjustment_rules(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100,
        activated_at=datetime.utcnow(),
        runtime_state={
            "paper_trading": False,
            "current_pnl": 2500.0,
            "margin_used": 50000.0,
            "entry_time": datetime.utcnow().isoformat(),
            "current_positions": [
                {
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24D2624800PE",
                    "quantity": 25,
                    "transaction_type": "BUY",
                    "entry_price": 50.0,
                    "current_ltp": 45.0
                }
            ]
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_strategy_with_trailing_stop(
    db_session: AsyncSession,
    test_user: User,
    test_trailing_stop_config: Dict[str, Any]
) -> AutoPilotStrategy:
    """Create a test strategy with trailing stop configured."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Strategy With Trailing Stop",
        description="A strategy with trailing stop enabled",
        status="active",
        underlying="NIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        adjustment_rules=[],
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        trailing_stop_config=test_trailing_stop_config,
        priority=100,
        activated_at=datetime.utcnow(),
        runtime_state={
            "paper_trading": False,
            "current_pnl": 4000.0,
            "margin_used": 50000.0,
            "trailing_stop": {
                "active": True,
                "high_water_mark": 4000.0,
                "stop_level": 3000.0,
                "last_updated": datetime.utcnow().isoformat()
            },
            "current_positions": [
                {
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24D2624800PE",
                    "quantity": 25,
                    "transaction_type": "BUY",
                    "entry_price": 50.0,
                    "current_ltp": 60.0
                }
            ]
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_strategy_active_with_positions(
    db_session: AsyncSession,
    test_user: User
) -> AutoPilotStrategy:
    """Create a test strategy in active status with realistic positions."""
    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Active Strategy With Positions",
        description="An active strategy with full positions data",
        status="active",
        underlying="NIFTY",
        expiry_type="current_week",
        lots=2,
        position_type="intraday",
        legs_config=get_sample_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        adjustment_rules=get_sample_adjustment_rules(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        trailing_stop_config={
            "enabled": True,
            "activation_profit": 5000,
            "trail_distance": 2000,
            "trail_type": "fixed",
            "min_profit_lock": 1000
        },
        priority=100,
        activated_at=datetime.utcnow(),
        runtime_state={
            "paper_trading": False,
            "current_pnl": 3500.0,
            "margin_used": 100000.0,
            "entry_time": datetime.utcnow().isoformat(),
            "entry_prices": {
                "NIFTY24D2624800PE": 50.0,
                "NIFTY24D2624900PE": 80.0,
                "NIFTY24D2625100CE": 75.0,
                "NIFTY24D2625200CE": 45.0
            },
            "positions": [
                {
                    "leg_index": 0,
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24D2624800PE",
                    "instrument_token": 12345,
                    "exchange": "NFO",
                    "contract_type": "PE",
                    "strike": 24800,
                    "expiry": date.today().isoformat(),
                    "quantity": 50,
                    "transaction_type": "BUY",
                    "entry_price": 50.0,
                    "current_ltp": 45.0,
                    "product": "MIS"
                },
                {
                    "leg_index": 1,
                    "leg_id": "leg_2",
                    "tradingsymbol": "NIFTY24D2624900PE",
                    "instrument_token": 12346,
                    "exchange": "NFO",
                    "contract_type": "PE",
                    "strike": 24900,
                    "expiry": date.today().isoformat(),
                    "quantity": -50,
                    "transaction_type": "SELL",
                    "entry_price": 80.0,
                    "current_ltp": 70.0,
                    "product": "MIS"
                },
                {
                    "leg_index": 2,
                    "leg_id": "leg_3",
                    "tradingsymbol": "NIFTY24D2625100CE",
                    "instrument_token": 12347,
                    "exchange": "NFO",
                    "contract_type": "CE",
                    "strike": 25100,
                    "expiry": date.today().isoformat(),
                    "quantity": -50,
                    "transaction_type": "SELL",
                    "entry_price": 75.0,
                    "current_ltp": 65.0,
                    "product": "MIS"
                },
                {
                    "leg_index": 3,
                    "leg_id": "leg_4",
                    "tradingsymbol": "NIFTY24D2625200CE",
                    "instrument_token": 12348,
                    "exchange": "NFO",
                    "contract_type": "CE",
                    "strike": 25200,
                    "expiry": date.today().isoformat(),
                    "quantity": 50,
                    "transaction_type": "BUY",
                    "entry_price": 45.0,
                    "current_ltp": 40.0,
                    "product": "MIS"
                }
            ],
            "trailing_stop": {
                "active": False,
                "high_water_mark": 0,
                "stop_level": 0
            }
        },
        greeks_snapshot={
            "net_delta": -0.15,
            "net_gamma": 0.002,
            "net_theta": -50.0,
            "net_vega": 25.0,
            "calculated_at": datetime.utcnow().isoformat()
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_settings_with_kill_switch(
    db_session: AsyncSession,
    test_user: User
) -> AutoPilotUserSettings:
    """Create AutoPilot user settings with kill switch enabled."""
    settings = AutoPilotUserSettings(
        user_id=test_user.id,
        daily_loss_limit=Decimal("20000.00"),
        per_strategy_loss_limit=Decimal("10000.00"),
        max_capital_deployed=Decimal("500000.00"),
        max_active_strategies=3,
        no_trade_first_minutes=5,
        no_trade_last_minutes=5,
        cooldown_after_loss=False,
        cooldown_minutes=30,
        cooldown_threshold=Decimal("5000.00"),
        default_order_settings={
            "order_type": "MARKET",
            "execution_style": "sequential",
            "delay_between_legs": 2
        },
        notification_prefs={
            "enabled": True,
            "channels": ["in_app"]
        },
        failure_handling={
            "on_network_error": "retry",
            "max_retries": 3
        },
        paper_trading_mode=False,
        show_advanced_features=True,
        kill_switch_enabled=True,
        kill_switch_triggered_at=datetime.utcnow()
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(settings)
    return settings


# =============================================================================
# PHASE 3 - Pending Confirmation Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_pending_confirmation(
    db_session: AsyncSession,
    test_user: User,
    test_strategy_active: AutoPilotStrategy
):
    """Create a pending confirmation record."""
    from app.models.autopilot import AutoPilotPendingConfirmation, ConfirmationStatus

    confirmation = AutoPilotPendingConfirmation(
        user_id=test_user.id,
        strategy_id=test_strategy_active.id,
        action_type="adjustment_exit_all",
        action_description="Exit all positions due to stop loss trigger",
        action_data={
            "rule": {
                "id": "adj_1",
                "name": "Stop Loss Rule",
                "action": {"type": "exit_all", "params": {"order_type": "MARKET"}}
            },
            "evaluation": {
                "triggered": True,
                "trigger_type": "pnl_based",
                "current_value": -5500,
                "target_value": -5000
            }
        },
        rule_id="adj_1",
        rule_name="Stop Loss Rule",
        status=ConfirmationStatus.PENDING,
        timeout_seconds=30,
        expires_at=datetime.utcnow() + timedelta(seconds=30)
    )
    db_session.add(confirmation)
    await db_session.commit()
    await db_session.refresh(confirmation)
    return confirmation


@pytest_asyncio.fixture
async def test_pending_confirmation_expired(
    db_session: AsyncSession,
    test_user: User,
    test_strategy_active: AutoPilotStrategy
):
    """Create an expired pending confirmation record."""
    from app.models.autopilot import AutoPilotPendingConfirmation, ConfirmationStatus

    confirmation = AutoPilotPendingConfirmation(
        user_id=test_user.id,
        strategy_id=test_strategy_active.id,
        action_type="entry",
        action_description="Entry order confirmation",
        action_data={
            "legs": get_sample_legs_config()
        },
        status=ConfirmationStatus.PENDING,
        timeout_seconds=30,
        expires_at=datetime.utcnow() - timedelta(seconds=60)  # Expired 60 seconds ago
    )
    db_session.add(confirmation)
    await db_session.commit()
    await db_session.refresh(confirmation)
    return confirmation


# =============================================================================
# PHASE 3 - Adjustment Log Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def test_adjustment_log(
    db_session: AsyncSession,
    test_user: User,
    test_strategy_with_adjustments: AutoPilotStrategy
):
    """Create an adjustment log entry."""
    from app.models.autopilot import (
        AutoPilotAdjustmentLog,
        AdjustmentTriggerType,
        AdjustmentActionType,
        ExecutionMode
    )

    log = AutoPilotAdjustmentLog(
        strategy_id=test_strategy_with_adjustments.id,
        user_id=test_user.id,
        rule_id="adj_1",
        rule_name="Stop Loss Rule",
        trigger_type=AdjustmentTriggerType.PNL_BASED,
        trigger_condition="loss_exceeds",
        trigger_value=5000,
        actual_value=-5500,
        action_type=AdjustmentActionType.EXIT_ALL,
        action_params={"order_type": "MARKET"},
        execution_mode=ExecutionMode.AUTO,
        executed=True,
        executed_at=datetime.utcnow(),
        execution_result={"orders_placed": [1001, 1002, 1003, 1004]}
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)
    return log


# =============================================================================
# PHASE 3 - Mock Greeks Data
# =============================================================================

@pytest.fixture
def mock_greeks_data() -> Dict[str, Any]:
    """Sample Greeks data for testing."""
    return {
        "total_delta": -0.15,
        "total_gamma": 0.002,
        "total_theta": -50.0,
        "total_vega": 25.0,
        "total_rho": 5.0,
        "spot_price": 25000.0,
        "leg_greeks": [
            {
                "leg_index": 0,
                "strike": 24800,
                "option_type": "PE",
                "action": "BUY",
                "quantity": 50,
                "delta": 0.35,
                "gamma": 0.001,
                "theta": -15.0,
                "vega": 10.0,
                "iv": 18.5
            },
            {
                "leg_index": 1,
                "strike": 24900,
                "option_type": "PE",
                "action": "SELL",
                "quantity": 50,
                "delta": -0.45,
                "gamma": -0.001,
                "theta": 20.0,
                "vega": -12.0,
                "iv": 17.8
            },
            {
                "leg_index": 2,
                "strike": 25100,
                "option_type": "CE",
                "action": "SELL",
                "quantity": 50,
                "delta": -0.40,
                "gamma": -0.001,
                "theta": 18.0,
                "vega": -11.0,
                "iv": 16.5
            },
            {
                "leg_index": 3,
                "strike": 25200,
                "option_type": "CE",
                "action": "BUY",
                "quantity": 50,
                "delta": 0.35,
                "gamma": 0.001,
                "theta": -12.0,
                "vega": 8.0,
                "iv": 15.8
            }
        ]
    }


@pytest.fixture
def mock_position_legs() -> List[Dict[str, Any]]:
    """Sample position legs for Greeks calculation."""
    return [
        {
            "strike": 24800,
            "expiry": (date.today() + timedelta(days=7)).isoformat(),
            "option_type": "PE",
            "quantity": 25,
            "action": "BUY",
            "iv": 0.18
        },
        {
            "strike": 24900,
            "expiry": (date.today() + timedelta(days=7)).isoformat(),
            "option_type": "PE",
            "quantity": 25,
            "action": "SELL",
            "iv": 0.17
        },
        {
            "strike": 25100,
            "expiry": (date.today() + timedelta(days=7)).isoformat(),
            "option_type": "CE",
            "quantity": 25,
            "action": "SELL",
            "iv": 0.16
        },
        {
            "strike": 25200,
            "expiry": (date.today() + timedelta(days=7)).isoformat(),
            "option_type": "CE",
            "quantity": 25,
            "action": "BUY",
            "iv": 0.15
        }
    ]


# =============================================================================
# PHASE 3 - Position Sizing Fixtures
# =============================================================================

@pytest.fixture
def test_position_sizing_request() -> Dict[str, Any]:
    """Sample position sizing request."""
    return {
        "underlying": "NIFTY",
        "account_capital": 500000,
        "risk_per_trade_pct": 2.0,
        "spot_price": 25000,
        "current_vix": 15.5,
        "legs": [
            {
                "option_type": "PE",
                "action": "BUY",
                "strike": 24800,
                "premium": 50
            },
            {
                "option_type": "PE",
                "action": "SELL",
                "strike": 24900,
                "premium": 80
            },
            {
                "option_type": "CE",
                "action": "SELL",
                "strike": 25100,
                "premium": 75
            },
            {
                "option_type": "CE",
                "action": "BUY",
                "strike": 25200,
                "premium": 45
            }
        ],
        "min_lots": 1,
        "max_lots": 10
    }


# =============================================================================
# PHASE 3 - Mock Service Fixtures
# =============================================================================

@pytest.fixture
def mock_kill_switch_service():
    """Mock KillSwitchService."""
    from app.services.kill_switch import KillSwitchService
    from app.schemas.autopilot import KillSwitchStatus, KillSwitchTriggerResponse

    mock = AsyncMock(spec=KillSwitchService)

    async def mock_get_status():
        return KillSwitchStatus(
            enabled=False,
            triggered_at=None,
            affected_strategies=0,
            can_reset=True
        )

    async def mock_is_enabled():
        return False

    async def mock_trigger(reason=None, force=False):
        return KillSwitchTriggerResponse(
            success=True,
            strategies_affected=2,
            positions_exited=8,
            orders_placed=[1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008],
            triggered_at=datetime.utcnow(),
            message="Kill switch activated. 2 strategies affected, 8 exit orders placed."
        )

    async def mock_reset(confirm=True):
        return {
            "success": True,
            "message": "Kill switch has been reset. You can now activate strategies."
        }

    mock.get_status = mock_get_status
    mock.is_enabled = mock_is_enabled
    mock.trigger = mock_trigger
    mock.reset = mock_reset

    return mock


@pytest.fixture
def mock_adjustment_engine():
    """Mock AdjustmentEngine."""
    from app.services.adjustment_engine import AdjustmentEngine

    mock = AsyncMock(spec=AdjustmentEngine)

    async def mock_evaluate_rules(strategy, market_data):
        # Return empty list by default (no rules triggered)
        return []

    async def mock_execute_adjustment(strategy, rule, evaluation, execution_mode=None):
        return {
            'executed': True,
            'action': rule['action']['type'],
            'message': f"Adjustment '{rule['name']}' executed successfully"
        }

    mock.evaluate_rules = mock_evaluate_rules
    mock.execute_adjustment = mock_execute_adjustment

    return mock


@pytest.fixture
def mock_confirmation_service():
    """Mock ConfirmationService."""
    from app.services.confirmation_service import ConfirmationService
    from app.schemas.autopilot import ConfirmationActionResponse

    mock = AsyncMock(spec=ConfirmationService)

    async def mock_create_confirmation(strategy_id, action_type, action_description, action_data, **kwargs):
        # Return a mock confirmation object
        mock_conf = MagicMock()
        mock_conf.id = 1
        mock_conf.strategy_id = strategy_id
        mock_conf.action_type = action_type
        return mock_conf

    async def mock_confirm(confirmation_id):
        return ConfirmationActionResponse(
            success=True,
            confirmation_id=confirmation_id,
            action_taken='confirmed',
            execution_result={'executed': True},
            orders_placed=[1001, 1002],
            message="Action confirmed and executed successfully"
        )

    async def mock_reject(confirmation_id, reason=None):
        return ConfirmationActionResponse(
            success=True,
            confirmation_id=confirmation_id,
            action_taken='rejected',
            execution_result=None,
            orders_placed=[],
            message=f"Action rejected: {reason or 'User rejected'}"
        )

    mock.create_confirmation = mock_create_confirmation
    mock.confirm = mock_confirm
    mock.reject = mock_reject

    return mock


@pytest.fixture
def mock_trailing_stop_service():
    """Mock TrailingStopService."""
    from app.services.trailing_stop import TrailingStopService
    from app.schemas.autopilot import TrailingStopStatus

    mock = AsyncMock(spec=TrailingStopService)

    async def mock_get_status(strategy, current_pnl):
        return TrailingStopStatus(
            enabled=True,
            active=True,
            high_water_mark=Decimal("5000.0"),
            current_stop_level=Decimal("4000.0"),
            current_pnl=current_pnl,
            distance_to_stop=current_pnl - Decimal("4000.0")
        )

    async def mock_update_trailing_stop(strategy, current_pnl):
        # Return (should_exit, reason)
        if current_pnl <= Decimal("4000.0"):
            return (True, "Trailing stop triggered at 4000.0")
        return (False, None)

    async def mock_check_stop_triggered(strategy, current_pnl):
        return current_pnl <= Decimal("4000.0")

    mock.get_status = mock_get_status
    mock.update_trailing_stop = mock_update_trailing_stop
    mock.check_stop_triggered = mock_check_stop_triggered

    return mock


@pytest.fixture
def mock_position_sizing_service():
    """Mock PositionSizingService."""
    from app.services.position_sizing import PositionSizingService
    from app.schemas.autopilot import PositionSizingResponse

    mock = AsyncMock(spec=PositionSizingService)

    async def mock_calculate_position_size(request):
        return PositionSizingResponse(
            recommended_lots=2,
            recommended_quantity=50,
            lot_size=25,
            max_loss_allowed=Decimal("10000.0"),
            estimated_max_loss=Decimal("5000.0"),
            risk_percentage=Decimal("2.0"),
            vix_adjustment_applied=False,
            vix_regime="normal",
            is_undefined_risk=False,
            reasoning=[
                "Account capital: ₹500,000.00",
                "Max loss allowed per trade: ₹10,000.00",
                "Estimated max loss per lot: ₹2,500.00",
                "Base lots calculated: 4",
                "VIX regime: normal (multiplier: 1.0)",
                "Final recommended lots: 2"
            ]
        )

    mock.calculate_position_size = mock_calculate_position_size

    return mock


@pytest.fixture
def mock_greeks_calculator():
    """Mock GreeksCalculatorService."""
    from app.services.greeks_calculator import GreeksCalculatorService
    from app.schemas.autopilot import PositionGreeksResponse, GreeksSnapshot

    mock = AsyncMock(spec=GreeksCalculatorService)

    async def mock_calculate_position_greeks(legs, spot_price, current_time=None):
        return PositionGreeksResponse(
            total_delta=-0.15,
            total_gamma=0.002,
            total_theta=-50.0,
            total_vega=25.0,
            total_rho=5.0,
            spot_price=spot_price,
            calculated_at=current_time or datetime.utcnow(),
            leg_greeks=[]
        )

    def mock_calculate_greeks_snapshot(legs, spot_price, current_time=None):
        return GreeksSnapshot(
            delta=Decimal("-0.15"),
            gamma=Decimal("0.002"),
            theta=Decimal("-50.0"),
            vega=Decimal("25.0"),
            spot_price=Decimal(str(spot_price)),
            calculated_at=current_time or datetime.utcnow()
        )

    mock.calculate_position_greeks = mock_calculate_position_greeks
    mock.calculate_greeks_snapshot = mock_calculate_greeks_snapshot

    return mock


# =============================================================================
# PHASE 3 - Market Data Fixtures
# =============================================================================

@pytest.fixture
def sample_market_data() -> Dict[str, Any]:
    """Sample market data for testing adjustment triggers."""
    return {
        "spot": 25000.0,
        "vix": 15.5,
        "option_prices": {
            "NIFTY24D2624800PE": 45.0,
            "NIFTY24D2624900PE": 70.0,
            "NIFTY24D2625100CE": 65.0,
            "NIFTY24D2625200CE": 40.0
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_market_data_high_vix() -> Dict[str, Any]:
    """Sample market data with high VIX for testing."""
    return {
        "spot": 24500.0,
        "vix": 28.5,
        "option_prices": {
            "NIFTY24D2624800PE": 80.0,
            "NIFTY24D2624900PE": 120.0,
            "NIFTY24D2625100CE": 110.0,
            "NIFTY24D2625200CE": 75.0
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# PHASE 3 - Assertion Helpers
# =============================================================================

def assert_kill_switch_status(response_data: Dict[str, Any]):
    """Assert kill switch status response structure."""
    assert "enabled" in response_data
    assert "triggered_at" in response_data
    assert "affected_strategies" in response_data
    assert "can_reset" in response_data


def assert_confirmation_response(response_data: Dict[str, Any]):
    """Assert confirmation action response structure."""
    assert "success" in response_data
    assert "confirmation_id" in response_data
    assert "action_taken" in response_data
    assert "message" in response_data


def assert_greeks_response(response_data: Dict[str, Any]):
    """Assert Greeks response structure."""
    assert "total_delta" in response_data
    assert "total_gamma" in response_data
    assert "total_theta" in response_data
    assert "total_vega" in response_data
    assert "spot_price" in response_data


def assert_position_sizing_response(response_data: Dict[str, Any]):
    """Assert position sizing response structure."""
    assert "recommended_lots" in response_data
    assert "recommended_quantity" in response_data
    assert "lot_size" in response_data
    assert "max_loss_allowed" in response_data
    assert "reasoning" in response_data


def assert_trailing_stop_status(response_data: Dict[str, Any]):
    """Assert trailing stop status response structure."""
    assert "enabled" in response_data
    assert "active" in response_data
    if response_data.get("active"):
        assert "high_water_mark" in response_data
        assert "current_stop_level" in response_data


# =============================================================================
# PHASE 4 FIXTURES - Templates, Journal, Analytics, Reports, Backtests, Sharing
# =============================================================================

# -----------------------------------------------------------------------------
# Template Fixtures
# -----------------------------------------------------------------------------

def get_iron_condor_legs_config() -> List[Dict[str, Any]]:
    """Return Iron Condor legs configuration."""
    return [
        {
            "id": "leg_1",
            "contract_type": "PE",
            "transaction_type": "BUY",
            "strike_selection": {"mode": "atm_offset", "offset": -4},
            "quantity_multiplier": 1,
            "execution_order": 1
        },
        {
            "id": "leg_2",
            "contract_type": "PE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": -2},
            "quantity_multiplier": 1,
            "execution_order": 2
        },
        {
            "id": "leg_3",
            "contract_type": "CE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": 2},
            "quantity_multiplier": 1,
            "execution_order": 3
        },
        {
            "id": "leg_4",
            "contract_type": "CE",
            "transaction_type": "BUY",
            "strike_selection": {"mode": "atm_offset", "offset": 4},
            "quantity_multiplier": 1,
            "execution_order": 4
        }
    ]


def get_straddle_legs_config() -> List[Dict[str, Any]]:
    """Return Short Straddle legs configuration."""
    return [
        {
            "id": "leg_1",
            "contract_type": "CE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": 0},
            "quantity_multiplier": 1,
            "execution_order": 1
        },
        {
            "id": "leg_2",
            "contract_type": "PE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": 0},
            "quantity_multiplier": 1,
            "execution_order": 2
        }
    ]


@pytest.fixture
def test_template_iron_condor() -> Dict[str, Any]:
    """Sample Iron Condor template fixture for testing."""
    return {
        "name": "Iron Condor - Neutral",
        "description": "A neutral options strategy with limited risk and limited profit potential",
        "is_system": True,
        "is_public": True,
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "lots": 1,
            "legs_config": get_iron_condor_legs_config(),
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "c1", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:20"},
                    {"id": "c2", "variable": "VIX.VALUE", "operator": "less_than", "value": 18}
                ]
            },
            "risk_settings": {
                "max_loss": 5000,
                "max_loss_pct": 50,
                "trailing_stop": {"enabled": True, "trigger_profit": 3000, "trail_amount": 1000}
            }
        },
        "category": "income",
        "tags": ["neutral", "income", "defined-risk", "iron-condor"],
        "risk_level": "medium",
        "author_name": "AlgoChanakya",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "expected_return_pct": Decimal("2.5"),
        "max_risk_pct": Decimal("5.0"),
        "market_outlook": "neutral",
        "iv_environment": "normal",
        "educational_content": {
            "when_to_use": "Best used in range-bound markets with low to medium volatility",
            "pros": ["Limited risk", "Profit from time decay", "Works in flat markets"],
            "cons": ["Limited profit", "Can lose money in trending markets"],
            "example": "Sell NIFTY ATM-200 PE, Buy ATM-400 PE, Sell ATM+200 CE, Buy ATM+400 CE"
        }
    }


@pytest.fixture
def test_template_straddle() -> Dict[str, Any]:
    """Sample Short Straddle template fixture for testing."""
    return {
        "name": "Short Straddle - Income",
        "description": "Sell ATM Call and Put to collect premium in low volatility environments",
        "is_system": True,
        "is_public": True,
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "lots": 1,
            "legs_config": get_straddle_legs_config(),
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "c1", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"},
                    {"id": "c2", "variable": "VIX.VALUE", "operator": "less_than", "value": 15}
                ]
            },
            "risk_settings": {
                "max_loss": 10000,
                "max_loss_pct": 100,
                "trailing_stop": {"enabled": True, "trigger_profit": 5000, "trail_amount": 2000}
            }
        },
        "category": "income",
        "tags": ["neutral", "income", "undefined-risk", "straddle"],
        "risk_level": "high",
        "author_name": "AlgoChanakya",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "expected_return_pct": Decimal("5.0"),
        "max_risk_pct": Decimal("100.0"),
        "market_outlook": "neutral",
        "iv_environment": "low",
        "educational_content": {
            "when_to_use": "Best in low IV environment when expecting minimal market movement",
            "pros": ["High premium collection", "Profits from time decay"],
            "cons": ["Unlimited risk", "Can suffer large losses in volatile markets"],
            "example": "Sell NIFTY ATM CE + Sell NIFTY ATM PE"
        }
    }


@pytest_asyncio.fixture
async def test_template_in_db(
    db_session: AsyncSession,
    test_template_iron_condor: Dict[str, Any]
) -> AutoPilotTemplate:
    """Create an AutoPilot template in the database."""
    template = AutoPilotTemplate(
        name=test_template_iron_condor["name"],
        description=test_template_iron_condor["description"],
        is_system=test_template_iron_condor["is_system"],
        is_public=test_template_iron_condor["is_public"],
        strategy_config=test_template_iron_condor["strategy_config"],
        category=test_template_iron_condor["category"],
        tags=test_template_iron_condor["tags"],
        risk_level=test_template_iron_condor["risk_level"],
        author_name=test_template_iron_condor.get("author_name"),
        underlying=test_template_iron_condor.get("underlying"),
        position_type=test_template_iron_condor.get("position_type"),
        expected_return_pct=test_template_iron_condor.get("expected_return_pct"),
        max_risk_pct=test_template_iron_condor.get("max_risk_pct"),
        market_outlook=test_template_iron_condor.get("market_outlook"),
        iv_environment=test_template_iron_condor.get("iv_environment"),
        educational_content=test_template_iron_condor.get("educational_content"),
        usage_count=0,
        avg_rating=None,
        rating_count=0
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def test_template_straddle_in_db(
    db_session: AsyncSession,
    test_template_straddle: Dict[str, Any]
) -> AutoPilotTemplate:
    """Create a Straddle template in the database."""
    template = AutoPilotTemplate(
        name=test_template_straddle["name"],
        description=test_template_straddle["description"],
        is_system=test_template_straddle["is_system"],
        is_public=test_template_straddle["is_public"],
        strategy_config=test_template_straddle["strategy_config"],
        category=test_template_straddle["category"],
        tags=test_template_straddle["tags"],
        risk_level=test_template_straddle["risk_level"],
        author_name=test_template_straddle.get("author_name"),
        underlying=test_template_straddle.get("underlying"),
        position_type=test_template_straddle.get("position_type"),
        expected_return_pct=test_template_straddle.get("expected_return_pct"),
        max_risk_pct=test_template_straddle.get("max_risk_pct"),
        market_outlook=test_template_straddle.get("market_outlook"),
        iv_environment=test_template_straddle.get("iv_environment"),
        educational_content=test_template_straddle.get("educational_content"),
        usage_count=50,
        avg_rating=Decimal("4.2"),
        rating_count=15
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def test_multiple_templates(
    db_session: AsyncSession,
    test_user: User
) -> List[AutoPilotTemplate]:
    """Create multiple templates for listing and filtering tests."""
    templates_data = [
        {
            "name": "Iron Condor Weekly",
            "description": "Weekly Iron Condor",
            "is_system": True,
            "is_public": True,
            "category": "income",
            "tags": ["neutral", "income"],
            "risk_level": "medium",
            "market_outlook": "neutral",
            "underlying": "NIFTY",
            "usage_count": 100
        },
        {
            "name": "Bull Call Spread",
            "description": "Bullish strategy with limited risk",
            "is_system": True,
            "is_public": True,
            "category": "directional",
            "tags": ["bullish", "defined-risk"],
            "risk_level": "medium",
            "market_outlook": "bullish",
            "underlying": "NIFTY",
            "usage_count": 80
        },
        {
            "name": "Bear Put Spread",
            "description": "Bearish strategy with limited risk",
            "is_system": True,
            "is_public": True,
            "category": "directional",
            "tags": ["bearish", "defined-risk"],
            "risk_level": "medium",
            "market_outlook": "bearish",
            "underlying": "BANKNIFTY",
            "usage_count": 60
        },
        {
            "name": "Long Strangle",
            "description": "Volatility play for big moves",
            "is_system": True,
            "is_public": True,
            "category": "volatility",
            "tags": ["volatile", "defined-risk"],
            "risk_level": "high",
            "market_outlook": "volatile",
            "underlying": "NIFTY",
            "usage_count": 40
        },
        {
            "name": "User Custom Strategy",
            "description": "User created custom strategy",
            "is_system": False,
            "is_public": False,
            "category": "custom",
            "tags": ["custom"],
            "risk_level": "medium",
            "market_outlook": "neutral",
            "underlying": "NIFTY",
            "user_id": test_user.id,
            "usage_count": 5
        }
    ]

    templates = []
    for data in templates_data:
        template = AutoPilotTemplate(
            name=data["name"],
            description=data["description"],
            is_system=data["is_system"],
            is_public=data["is_public"],
            strategy_config={"legs_config": get_iron_condor_legs_config()},
            category=data["category"],
            tags=data["tags"],
            risk_level=data["risk_level"],
            market_outlook=data.get("market_outlook"),
            underlying=data.get("underlying"),
            user_id=data.get("user_id"),
            usage_count=data.get("usage_count", 0)
        )
        db_session.add(template)
        templates.append(template)

    await db_session.commit()
    for template in templates:
        await db_session.refresh(template)

    return templates


# -----------------------------------------------------------------------------
# Trade Journal Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def test_trade_journal_entry() -> Dict[str, Any]:
    """Sample trade journal entry fixture."""
    return {
        "strategy_name": "Test Iron Condor",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "entry_time": datetime.utcnow() - timedelta(hours=4),
        "exit_time": datetime.utcnow() - timedelta(hours=1),
        "holding_duration_minutes": 180,
        "legs": [
            {
                "leg_id": "leg_1",
                "tradingsymbol": "NIFTY24D2624800PE",
                "contract_type": "PE",
                "strike": 24800,
                "transaction_type": "BUY",
                "quantity": 25,
                "entry_price": 50.0,
                "exit_price": 45.0
            },
            {
                "leg_id": "leg_2",
                "tradingsymbol": "NIFTY24D2624900PE",
                "contract_type": "PE",
                "strike": 24900,
                "transaction_type": "SELL",
                "quantity": 25,
                "entry_price": 80.0,
                "exit_price": 70.0
            }
        ],
        "lots": 1,
        "total_quantity": 50,
        "entry_premium": Decimal("30.0"),  # Net credit = 80 - 50
        "exit_premium": Decimal("25.0"),   # Net exit = 70 - 45
        "gross_pnl": Decimal("125.0"),
        "brokerage": Decimal("40.0"),
        "taxes": Decimal("10.0"),
        "other_charges": Decimal("5.0"),
        "net_pnl": Decimal("70.0"),
        "pnl_percentage": Decimal("2.8"),
        "max_profit_reached": Decimal("200.0"),
        "max_loss_reached": Decimal("-50.0"),
        "max_drawdown": Decimal("150.0"),
        "exit_reason": "target_hit",
        "market_conditions": {
            "spot_at_entry": 25000.0,
            "spot_at_exit": 25050.0,
            "vix_at_entry": 14.5,
            "vix_at_exit": 14.2
        },
        "notes": "Good trade, exited at target",
        "tags": ["successful", "iron-condor"],
        "is_open": False
    }


@pytest_asyncio.fixture
async def test_trade_journal_in_db(
    db_session: AsyncSession,
    test_user: User,
    test_strategy: AutoPilotStrategy,
    test_trade_journal_entry: Dict[str, Any]
) -> AutoPilotTradeJournal:
    """Create a trade journal entry in the database."""
    journal = AutoPilotTradeJournal(
        user_id=test_user.id,
        strategy_id=test_strategy.id,
        strategy_name=test_trade_journal_entry["strategy_name"],
        underlying=test_trade_journal_entry["underlying"],
        position_type=test_trade_journal_entry["position_type"],
        entry_time=test_trade_journal_entry["entry_time"],
        exit_time=test_trade_journal_entry["exit_time"],
        holding_duration_minutes=test_trade_journal_entry["holding_duration_minutes"],
        legs=test_trade_journal_entry["legs"],
        lots=test_trade_journal_entry["lots"],
        total_quantity=test_trade_journal_entry["total_quantity"],
        entry_premium=test_trade_journal_entry["entry_premium"],
        exit_premium=test_trade_journal_entry["exit_premium"],
        gross_pnl=test_trade_journal_entry["gross_pnl"],
        brokerage=test_trade_journal_entry["brokerage"],
        taxes=test_trade_journal_entry["taxes"],
        other_charges=test_trade_journal_entry["other_charges"],
        net_pnl=test_trade_journal_entry["net_pnl"],
        pnl_percentage=test_trade_journal_entry["pnl_percentage"],
        max_profit_reached=test_trade_journal_entry["max_profit_reached"],
        max_loss_reached=test_trade_journal_entry["max_loss_reached"],
        max_drawdown=test_trade_journal_entry["max_drawdown"],
        exit_reason=test_trade_journal_entry["exit_reason"],
        market_conditions=test_trade_journal_entry["market_conditions"],
        notes=test_trade_journal_entry["notes"],
        tags=test_trade_journal_entry["tags"],
        is_open=test_trade_journal_entry["is_open"]
    )
    db_session.add(journal)
    await db_session.commit()
    await db_session.refresh(journal)
    return journal


@pytest_asyncio.fixture
async def test_journal_entries(
    db_session: AsyncSession,
    test_user: User
) -> List[AutoPilotTradeJournal]:
    """Create multiple journal entries for analytics testing."""
    entries = []
    base_date = datetime.utcnow() - timedelta(days=30)

    # Create 20 sample trades over 30 days
    trades_data = [
        # Winning trades
        {"day_offset": 1, "pnl": 2500, "exit_reason": "target_hit", "underlying": "NIFTY"},
        {"day_offset": 2, "pnl": 1800, "exit_reason": "target_hit", "underlying": "NIFTY"},
        {"day_offset": 3, "pnl": -1200, "exit_reason": "stop_loss", "underlying": "NIFTY"},
        {"day_offset": 4, "pnl": 3200, "exit_reason": "target_hit", "underlying": "BANKNIFTY"},
        {"day_offset": 5, "pnl": -800, "exit_reason": "time_exit", "underlying": "NIFTY"},
        {"day_offset": 8, "pnl": 1500, "exit_reason": "trailing_stop", "underlying": "NIFTY"},
        {"day_offset": 9, "pnl": -2000, "exit_reason": "stop_loss", "underlying": "BANKNIFTY"},
        {"day_offset": 10, "pnl": 2800, "exit_reason": "target_hit", "underlying": "NIFTY"},
        {"day_offset": 11, "pnl": 900, "exit_reason": "time_exit", "underlying": "NIFTY"},
        {"day_offset": 12, "pnl": -500, "exit_reason": "manual_exit", "underlying": "FINNIFTY"},
        {"day_offset": 15, "pnl": 4000, "exit_reason": "target_hit", "underlying": "NIFTY"},
        {"day_offset": 16, "pnl": 1200, "exit_reason": "trailing_stop", "underlying": "BANKNIFTY"},
        {"day_offset": 17, "pnl": -3000, "exit_reason": "stop_loss", "underlying": "NIFTY"},
        {"day_offset": 18, "pnl": 2200, "exit_reason": "target_hit", "underlying": "NIFTY"},
        {"day_offset": 19, "pnl": 600, "exit_reason": "time_exit", "underlying": "NIFTY"},
        {"day_offset": 22, "pnl": -1500, "exit_reason": "stop_loss", "underlying": "BANKNIFTY"},
        {"day_offset": 23, "pnl": 3500, "exit_reason": "target_hit", "underlying": "NIFTY"},
        {"day_offset": 24, "pnl": 1100, "exit_reason": "trailing_stop", "underlying": "NIFTY"},
        {"day_offset": 25, "pnl": -700, "exit_reason": "manual_exit", "underlying": "NIFTY"},
        {"day_offset": 26, "pnl": 2000, "exit_reason": "target_hit", "underlying": "FINNIFTY"},
    ]

    for trade in trades_data:
        entry_time = base_date + timedelta(days=trade["day_offset"], hours=9, minutes=30)
        exit_time = entry_time + timedelta(hours=4)

        journal = AutoPilotTradeJournal(
            user_id=test_user.id,
            strategy_name=f"Test Strategy {trade['day_offset']}",
            underlying=trade["underlying"],
            position_type="intraday",
            entry_time=entry_time,
            exit_time=exit_time,
            holding_duration_minutes=240,
            legs=[{"leg_id": "leg_1", "tradingsymbol": f"{trade['underlying']}24D26CE", "quantity": 25}],
            lots=1,
            total_quantity=25,
            gross_pnl=Decimal(str(trade["pnl"])),
            brokerage=Decimal("40.0"),
            taxes=Decimal("10.0"),
            net_pnl=Decimal(str(trade["pnl"] - 50)),
            pnl_percentage=Decimal(str(trade["pnl"] / 100)),
            exit_reason=trade["exit_reason"],
            market_conditions={"spot_at_entry": 25000.0, "vix_at_entry": 15.0},
            is_open=False
        )
        db_session.add(journal)
        entries.append(journal)

    await db_session.commit()
    for entry in entries:
        await db_session.refresh(entry)

    return entries


@pytest_asyncio.fixture
async def test_open_trade(
    db_session: AsyncSession,
    test_user: User,
    test_strategy_active: AutoPilotStrategy
) -> AutoPilotTradeJournal:
    """Create an open (running) trade for testing."""
    journal = AutoPilotTradeJournal(
        user_id=test_user.id,
        strategy_id=test_strategy_active.id,
        strategy_name="Active Running Trade",
        underlying="NIFTY",
        position_type="intraday",
        entry_time=datetime.utcnow() - timedelta(hours=2),
        exit_time=None,
        holding_duration_minutes=None,
        legs=[
            {
                "leg_id": "leg_1",
                "tradingsymbol": "NIFTY24D2625000CE",
                "contract_type": "CE",
                "strike": 25000,
                "transaction_type": "SELL",
                "quantity": 25,
                "entry_price": 100.0,
                "current_ltp": 85.0
            }
        ],
        lots=1,
        total_quantity=25,
        entry_premium=Decimal("100.0"),
        gross_pnl=Decimal("375.0"),  # (100 - 85) * 25
        net_pnl=Decimal("375.0"),
        is_open=True
    )
    db_session.add(journal)
    await db_session.commit()
    await db_session.refresh(journal)
    return journal


# -----------------------------------------------------------------------------
# Backtest Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def test_backtest_config() -> Dict[str, Any]:
    """Sample backtest configuration fixture."""
    return {
        "name": "Iron Condor Backtest - 2024",
        "description": "Testing Iron Condor on 2024 NIFTY data",
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "lots": 1,
            "legs_config": get_iron_condor_legs_config(),
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "c1", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:20"}
                ]
            },
            "risk_settings": {
                "max_loss": 5000,
                "trailing_stop": {"enabled": True, "trigger_profit": 3000, "trail_amount": 1000}
            }
        },
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 6, 30),
        "initial_capital": Decimal("500000.00"),
        "slippage_pct": Decimal("0.1"),
        "charges_per_lot": Decimal("40.0"),
        "data_interval": "1min"
    }


@pytest_asyncio.fixture
async def test_backtest_in_db(
    db_session: AsyncSession,
    test_user: User,
    test_backtest_config: Dict[str, Any]
) -> AutoPilotBacktest:
    """Create a backtest record in the database."""
    backtest = AutoPilotBacktest(
        user_id=test_user.id,
        name=test_backtest_config["name"],
        description=test_backtest_config["description"],
        strategy_config=test_backtest_config["strategy_config"],
        start_date=test_backtest_config["start_date"],
        end_date=test_backtest_config["end_date"],
        initial_capital=test_backtest_config["initial_capital"],
        slippage_pct=test_backtest_config["slippage_pct"],
        charges_per_lot=test_backtest_config["charges_per_lot"],
        data_interval=test_backtest_config["data_interval"],
        status="pending",
        progress_pct=0
    )
    db_session.add(backtest)
    await db_session.commit()
    await db_session.refresh(backtest)
    return backtest


@pytest_asyncio.fixture
async def test_backtest_completed(
    db_session: AsyncSession,
    test_user: User,
    test_backtest_config: Dict[str, Any]
) -> AutoPilotBacktest:
    """Create a completed backtest with results."""
    backtest = AutoPilotBacktest(
        user_id=test_user.id,
        name=test_backtest_config["name"],
        description=test_backtest_config["description"],
        strategy_config=test_backtest_config["strategy_config"],
        start_date=test_backtest_config["start_date"],
        end_date=test_backtest_config["end_date"],
        initial_capital=test_backtest_config["initial_capital"],
        slippage_pct=test_backtest_config["slippage_pct"],
        charges_per_lot=test_backtest_config["charges_per_lot"],
        data_interval=test_backtest_config["data_interval"],
        status="completed",
        progress_pct=100,
        total_trades=120,
        winning_trades=78,
        losing_trades=42,
        win_rate=Decimal("65.0"),
        gross_pnl=Decimal("185000.0"),
        net_pnl=Decimal("175200.0"),
        max_drawdown=Decimal("28000.0"),
        max_drawdown_pct=Decimal("5.6"),
        sharpe_ratio=Decimal("1.85"),
        profit_factor=Decimal("2.15"),
        results={
            "summary": {
                "total_trades": 120,
                "winning_trades": 78,
                "losing_trades": 42,
                "win_rate": 65.0,
                "avg_win": 3200,
                "avg_loss": 1800,
                "largest_win": 12000,
                "largest_loss": 8000
            },
            "monthly_returns": [
                {"month": "2024-01", "pnl": 28000},
                {"month": "2024-02", "pnl": 32000},
                {"month": "2024-03", "pnl": 25000},
                {"month": "2024-04", "pnl": 38000},
                {"month": "2024-05", "pnl": 22000},
                {"month": "2024-06", "pnl": 30200}
            ]
        },
        equity_curve=[
            {"date": "2024-01-02", "equity": 500000},
            {"date": "2024-01-15", "equity": 512000},
            {"date": "2024-02-01", "equity": 528000},
            {"date": "2024-03-01", "equity": 560000},
            {"date": "2024-04-01", "equity": 585000},
            {"date": "2024-05-01", "equity": 623000},
            {"date": "2024-06-01", "equity": 645000},
            {"date": "2024-06-30", "equity": 675200}
        ],
        trades=[
            {"trade_id": 1, "date": "2024-01-02", "pnl": 2500, "type": "win"},
            {"trade_id": 2, "date": "2024-01-03", "pnl": -1200, "type": "loss"},
            # ... more trades would be here
        ],
        started_at=datetime.utcnow() - timedelta(hours=2),
        completed_at=datetime.utcnow() - timedelta(hours=1)
    )
    db_session.add(backtest)
    await db_session.commit()
    await db_session.refresh(backtest)
    return backtest


@pytest.fixture
def mock_historical_data() -> List[Dict[str, Any]]:
    """Mock historical OHLC data for backtesting."""
    base_date = datetime(2024, 1, 2, 9, 15)
    data = []

    # Generate 390 minutes of data (9:15 to 15:30)
    for minute in range(390):
        timestamp = base_date + timedelta(minutes=minute)
        base_price = 25000 + (minute * 0.5)  # Slight uptrend

        data.append({
            "timestamp": timestamp.isoformat(),
            "open": base_price,
            "high": base_price + 10,
            "low": base_price - 8,
            "close": base_price + 2,
            "volume": 1000000 + (minute * 1000),
            "oi": 5000000
        })

    return data


@pytest.fixture
def mock_option_chain_data() -> Dict[str, Any]:
    """Mock option chain data for backtest simulations."""
    return {
        "expiry": date.today() + timedelta(days=7),
        "spot_price": 25000.0,
        "strikes": {
            24800: {
                "CE": {"ltp": 250, "iv": 18.5, "delta": 0.65, "theta": -12, "vega": 15},
                "PE": {"ltp": 50, "iv": 17.8, "delta": -0.35, "theta": -8, "vega": 12}
            },
            24900: {
                "CE": {"ltp": 180, "iv": 17.2, "delta": 0.55, "theta": -10, "vega": 14},
                "PE": {"ltp": 80, "iv": 17.5, "delta": -0.45, "theta": -9, "vega": 13}
            },
            25000: {
                "CE": {"ltp": 120, "iv": 16.5, "delta": 0.50, "theta": -11, "vega": 16},
                "PE": {"ltp": 120, "iv": 16.5, "delta": -0.50, "theta": -11, "vega": 16}
            },
            25100: {
                "CE": {"ltp": 75, "iv": 17.0, "delta": 0.42, "theta": -9, "vega": 13},
                "PE": {"ltp": 175, "iv": 17.8, "delta": -0.58, "theta": -10, "vega": 14}
            },
            25200: {
                "CE": {"ltp": 45, "iv": 17.5, "delta": 0.32, "theta": -7, "vega": 11},
                "PE": {"ltp": 245, "iv": 18.2, "delta": -0.68, "theta": -12, "vega": 15}
            }
        }
    }


# -----------------------------------------------------------------------------
# Strategy Sharing Fixtures
# -----------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_strategy_with_share_token(
    db_session: AsyncSession,
    test_user: User
) -> AutoPilotStrategy:
    """Create a strategy with sharing enabled."""
    import secrets
    share_token = secrets.token_urlsafe(16)

    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Shared Iron Condor Strategy",
        description="A strategy shared via link",
        status="completed",
        underlying="NIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_iron_condor_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100,
        share_mode="link",
        share_token=share_token,
        shared_at=datetime.utcnow(),
        runtime_state={
            "realized_pnl": 5000.0,
            "exit_reason": "Target profit reached"
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


@pytest_asyncio.fixture
async def test_strategy_public(
    db_session: AsyncSession,
    test_user: User
) -> AutoPilotStrategy:
    """Create a publicly shared strategy."""
    import secrets
    share_token = secrets.token_urlsafe(16)

    strategy = AutoPilotStrategy(
        user_id=test_user.id,
        name="Public Strategy Example",
        description="A publicly visible strategy",
        status="completed",
        underlying="BANKNIFTY",
        expiry_type="current_week",
        lots=1,
        position_type="intraday",
        legs_config=get_straddle_legs_config(),
        entry_conditions=get_sample_entry_conditions(),
        order_settings=get_sample_order_settings(),
        risk_settings=get_sample_risk_settings(),
        schedule_config=get_sample_schedule_config(),
        priority=100,
        share_mode="public",
        share_token=share_token,
        shared_at=datetime.utcnow() - timedelta(days=7),
        runtime_state={
            "realized_pnl": 8500.0,
            "exit_reason": "Target profit reached"
        }
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)
    return strategy


# -----------------------------------------------------------------------------
# Analytics Cache Fixtures
# -----------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_analytics_cache(
    db_session: AsyncSession,
    test_user: User
) -> AutoPilotAnalyticsCache:
    """Create an analytics cache entry."""
    cache = AutoPilotAnalyticsCache(
        user_id=test_user.id,
        cache_key="summary_30d",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today(),
        metrics={
            "total_trades": 50,
            "winning_trades": 32,
            "losing_trades": 18,
            "win_rate": 64.0,
            "gross_pnl": 125000,
            "net_pnl": 118500,
            "avg_daily_pnl": 3950,
            "max_drawdown": 15000,
            "sharpe_ratio": 1.65,
            "profit_factor": 1.95
        },
        is_valid=True,
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    db_session.add(cache)
    await db_session.commit()
    await db_session.refresh(cache)
    return cache


# -----------------------------------------------------------------------------
# Report Fixtures
# -----------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_report(
    db_session: AsyncSession,
    test_user: User
) -> AutoPilotReport:
    """Create a P&L report."""
    report = AutoPilotReport(
        user_id=test_user.id,
        report_type="monthly",
        name="November 2024 P&L Report",
        description="Monthly trading performance report",
        start_date=date(2024, 11, 1),
        end_date=date(2024, 11, 30),
        report_data={
            "summary": {
                "total_trades": 45,
                "winning_trades": 28,
                "losing_trades": 17,
                "win_rate": 62.2,
                "gross_pnl": 85000,
                "brokerage": 4500,
                "taxes": 2800,
                "net_pnl": 77700
            },
            "by_strategy": [
                {"name": "Iron Condor", "trades": 25, "pnl": 45000},
                {"name": "Straddle", "trades": 15, "pnl": 28000},
                {"name": "Bull Call", "trades": 5, "pnl": 12000}
            ],
            "by_underlying": [
                {"underlying": "NIFTY", "trades": 35, "pnl": 62000},
                {"underlying": "BANKNIFTY", "trades": 10, "pnl": 23000}
            ]
        },
        is_ready=True,
        generated_at=datetime.utcnow()
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


@pytest_asyncio.fixture
async def test_tax_report(
    db_session: AsyncSession,
    test_user: User
) -> AutoPilotReport:
    """Create a tax summary report."""
    report = AutoPilotReport(
        user_id=test_user.id,
        report_type="tax",
        name="FY 2024-25 Tax Summary",
        description="Annual tax summary for F&O trading",
        start_date=date(2024, 4, 1),
        end_date=date(2025, 3, 31),
        report_data={
            "financial_year": "2024-25",
            "total_turnover": 25000000,  # 2.5 Cr
            "gross_profit": 450000,
            "gross_loss": 280000,
            "net_profit_loss": 170000,
            "stt_paid": 12500,
            "gst_paid": 8100,
            "stamp_duty": 3750,
            "exchange_charges": 2500,
            "brokerage": 54000,
            "total_expenses": 80850,
            "taxable_income": 89150,
            "turnover_calculation": {
                "absolute_profit": 450000,
                "absolute_loss": 280000,
                "premium_received": 15000000,
                "premium_paid": 9500000,
                "total_turnover": 25000000
            },
            "quarter_wise": [
                {"quarter": "Q1", "profit": 45000, "loss": 25000, "net": 20000},
                {"quarter": "Q2", "profit": 120000, "loss": 80000, "net": 40000},
                {"quarter": "Q3", "profit": 150000, "loss": 95000, "net": 55000},
                {"quarter": "Q4", "profit": 135000, "loss": 80000, "net": 55000}
            ]
        },
        is_ready=True,
        generated_at=datetime.utcnow()
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


# -----------------------------------------------------------------------------
# Template Rating Fixtures
# -----------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_template_rating(
    db_session: AsyncSession,
    test_user: User,
    test_template_in_db: AutoPilotTemplate
) -> AutoPilotTemplateRating:
    """Create a template rating."""
    rating = AutoPilotTemplateRating(
        template_id=test_template_in_db.id,
        user_id=test_user.id,
        rating=4,
        review="Great strategy for sideways markets. Works well with proper risk management."
    )
    db_session.add(rating)
    await db_session.commit()
    await db_session.refresh(rating)
    return rating


# -----------------------------------------------------------------------------
# Phase 4 Assertion Helpers
# -----------------------------------------------------------------------------

def assert_template_response(response_data: Dict[str, Any]):
    """Assert template response structure."""
    assert "id" in response_data
    assert "name" in response_data
    assert "description" in response_data
    assert "is_system" in response_data
    assert "is_public" in response_data
    assert "strategy_config" in response_data
    assert "category" in response_data
    assert "risk_level" in response_data


def assert_trade_journal_response(response_data: Dict[str, Any]):
    """Assert trade journal response structure."""
    assert "id" in response_data
    assert "strategy_name" in response_data
    assert "underlying" in response_data
    assert "entry_time" in response_data
    assert "legs" in response_data
    assert "lots" in response_data
    assert "is_open" in response_data


def assert_backtest_response(response_data: Dict[str, Any]):
    """Assert backtest response structure."""
    assert "id" in response_data
    assert "name" in response_data
    assert "status" in response_data
    assert "strategy_config" in response_data
    assert "start_date" in response_data
    assert "end_date" in response_data
    assert "initial_capital" in response_data


def assert_report_response(response_data: Dict[str, Any]):
    """Assert report response structure."""
    assert "id" in response_data
    assert "report_type" in response_data
    assert "name" in response_data
    assert "start_date" in response_data
    assert "end_date" in response_data
    assert "report_data" in response_data
    assert "is_ready" in response_data


def assert_analytics_response(response_data: Dict[str, Any]):
    """Assert analytics response structure."""
    assert "total_trades" in response_data
    assert "winning_trades" in response_data
    assert "losing_trades" in response_data
    assert "win_rate" in response_data
    assert "gross_pnl" in response_data or "net_pnl" in response_data


def assert_share_response(response_data: Dict[str, Any]):
    """Assert strategy share response structure."""
    assert "share_mode" in response_data
    assert "share_token" in response_data or response_data.get("share_mode") == "private"
    if response_data.get("share_mode") != "private":
        assert "share_url" in response_data or "shared_at" in response_data
