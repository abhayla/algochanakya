"""
Pytest fixtures for Option Strategies testing.

Provides fixtures for:
- Async database sessions
- Sample strategy templates
- Mocked Kite API client
- Test users and broker connections
- Allure reporting hooks
"""

import pytest
import pytest_asyncio
import asyncio
import allure
import os
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from datetime import datetime, date

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PgUUID
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy import JSON, BigInteger, event
from httpx import AsyncClient, ASGITransport


# =============================================================================
# ALLURE CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure Allure environment information."""
    # Write environment.properties for Allure report
    allure_results_dir = config.getoption("--alluredir", default="allure-results")
    if allure_results_dir:
        os.makedirs(allure_results_dir, exist_ok=True)
        env_file = os.path.join(allure_results_dir, "environment.properties")
        with open(env_file, "w") as f:
            f.write("Project=AlgoChanakya\n")
            f.write("Backend=FastAPI\n")
            f.write("Database=PostgreSQL\n")
            f.write("Python=3.11\n")
            f.write("TestFramework=pytest\n")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach additional data on test failure for Allure reports."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # Attach any relevant data on failure
        if hasattr(item, "funcargs"):
            # Attach response data if available
            if "response" in item.funcargs:
                try:
                    response_data = str(item.funcargs["response"].json())
                    allure.attach(
                        response_data,
                        name="API Response",
                        attachment_type=allure.attachment_type.JSON
                    )
                except Exception:
                    pass

            # Attach request data if available
            if "client" in item.funcargs:
                allure.attach(
                    f"Client: {item.funcargs['client']}",
                    name="HTTP Client Info",
                    attachment_type=allure.attachment_type.TEXT
                )


def allure_step(title: str):
    """Decorator to add Allure step to async test functions."""
    def decorator(func):
        @allure.step(title)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


# =============================================================================
# DATABASE FIXTURES
# =============================================================================

# Import app components
from app.database import Base, get_db
from app.main import app
from app.models import User
from app.models.broker_connections import BrokerConnection
from app.models.strategy_templates import StrategyTemplate


# Test database URL - uses SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# SQLite doesn't support JSONB, so we need to render it as JSON
from sqlalchemy.ext.compiler import compiles

@compiles(JSONB, 'sqlite')
def compile_jsonb_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)


@compiles(ARRAY, 'sqlite')
def compile_array_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(BigInteger, 'sqlite')
def compile_biginteger_sqlite(element, compiler, **kw):
    return "INTEGER"


@compiles(PgUUID, 'sqlite')
def compile_uuid_sqlite(element, compiler, **kw):
    return "TEXT"


@compiles(PgEnum, 'sqlite')
def compile_pgenum_sqlite(element, compiler, **kw):
    return compiler.visit_VARCHAR(element, **kw)


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    # Use StaticPool to share the same connection across all sessions
    # This is necessary for SQLite in-memory databases
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
        # Clean up tables before each test for isolation
        await session.execute(StrategyTemplate.__table__.delete())
        await session.execute(BrokerConnection.__table__.delete())
        await session.execute(User.__table__.delete())
        await session.commit()

        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_broker_connection(db_session: AsyncSession, test_user: User) -> BrokerConnection:
    """Create a test broker connection."""
    broker_conn = BrokerConnection(
        id=uuid4(),
        user_id=test_user.id,
        broker="zerodha",
        broker_user_id="TEST123",
        access_token="test_access_token",
        is_active=True
    )
    db_session.add(broker_conn)
    await db_session.commit()
    await db_session.refresh(broker_conn)
    return broker_conn


@pytest_asyncio.fixture
async def sample_strategy_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create a sample strategy template for testing."""
    template = StrategyTemplate(
        id=uuid4(),
        name="test_strategy",
        display_name="Test Strategy",
        category="neutral",
        description="A test strategy for unit testing",
        legs_config=[
            {"type": "CE", "position": "SELL", "strike_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": 0}
        ],
        max_profit="Limited",
        max_loss="Unlimited",
        breakeven="ATM ± Premium",
        market_outlook="neutral",
        volatility_preference="high_iv",
        ideal_iv_rank=">50%",
        risk_level="high",
        capital_requirement="high",
        margin_requirement="High margin required",
        theta_positive=True,
        vega_positive=False,
        delta_neutral=True,
        gamma_risk="high",
        win_probability="~45%",
        profit_target="25% of max profit",
        when_to_use="When you expect minimal movement",
        pros=["Time decay works in your favor", "Premium collection"],
        cons=["Unlimited risk on both sides", "High margin"],
        common_mistakes=["Not having stop loss", "Over-sizing positions"],
        exit_rules=["Exit at 25% profit", "Exit if underlying moves 1.5%"],
        adjustments=[{"trigger": "Delta > 0.3", "action": "Roll tested side"}],
        example_underlying="NIFTY",
        example_spot=26000.0,
        example_setup="Sell 26000 CE + 26000 PE",
        popularity_score=70,
        difficulty_level="intermediate",
        tags=["theta", "neutral", "income"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def iron_condor_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create Iron Condor strategy template."""
    template = StrategyTemplate(
        id=uuid4(),
        name="iron_condor",
        display_name="Iron Condor",
        category="neutral",
        description="Sell an OTM put spread and an OTM call spread simultaneously.",
        legs_config=[
            {"type": "PE", "position": "BUY", "strike_offset": -400},
            {"type": "PE", "position": "SELL", "strike_offset": -200},
            {"type": "CE", "position": "SELL", "strike_offset": 200},
            {"type": "CE", "position": "BUY", "strike_offset": 400}
        ],
        max_profit="Limited",
        max_loss="Limited",
        breakeven="Two breakevens",
        market_outlook="neutral",
        volatility_preference="high_iv",
        ideal_iv_rank=">50%",
        risk_level="medium",
        capital_requirement="medium",
        theta_positive=True,
        vega_positive=False,
        delta_neutral=True,
        gamma_risk="medium",
        win_probability="~68%",
        profit_target="50% of max profit",
        when_to_use="Market is range-bound",
        pros=["High probability", "Defined risk", "Benefits from time decay"],
        cons=["Limited profit", "Requires active management"],
        common_mistakes=["Setting wings too narrow", "Not adjusting when tested"],
        exit_rules=["Exit at 50% profit", "Exit if short strike breached"],
        popularity_score=95,
        difficulty_level="intermediate",
        tags=["neutral", "income", "defined-risk"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def bull_call_spread_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create Bull Call Spread strategy template."""
    template = StrategyTemplate(
        id=uuid4(),
        name="bull_call_spread",
        display_name="Bull Call Spread",
        category="bullish",
        description="Buy a call at lower strike and sell a call at higher strike.",
        legs_config=[
            {"type": "CE", "position": "BUY", "strike_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 200}
        ],
        max_profit="Limited",
        max_loss="Limited",
        breakeven="Lower strike + net debit",
        market_outlook="bullish",
        volatility_preference="low_iv",
        ideal_iv_rank="<50%",
        risk_level="low",
        capital_requirement="low",
        theta_positive=False,
        vega_positive=True,
        delta_neutral=False,
        gamma_risk="low",
        win_probability="~45%",
        profit_target="50% of max profit",
        when_to_use="Moderate upward movement expected",
        pros=["Limited risk", "Lower cost than buying calls"],
        cons=["Limited profit", "Time decay works against you"],
        common_mistakes=["Setting strikes too wide"],
        exit_rules=["Exit at 50% profit", "Exit if underlying breaks support"],
        popularity_score=85,
        difficulty_level="beginner",
        tags=["bullish", "debit", "defined-risk"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def bull_put_spread_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create Bull Put Spread strategy template."""
    template = StrategyTemplate(
        id=uuid4(),
        name="bull_put_spread",
        display_name="Bull Put Spread",
        category="bullish",
        description="Sell a put at higher strike and buy a put at lower strike.",
        legs_config=[
            {"type": "PE", "position": "SELL", "strike_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": -200}
        ],
        max_profit="Limited",
        max_loss="Limited",
        breakeven="Short strike - net credit",
        market_outlook="bullish",
        volatility_preference="high_iv",
        ideal_iv_rank=">50%",
        risk_level="low",
        capital_requirement="medium",
        theta_positive=True,
        vega_positive=False,
        delta_neutral=False,
        gamma_risk="low",
        win_probability="~65%",
        profit_target="50% of max profit",
        when_to_use="Mildly bullish or neutral outlook",
        pros=["Time decay works for you", "High probability"],
        cons=["Limited profit", "Requires margin"],
        common_mistakes=["Selling strikes too close to spot"],
        exit_rules=["Exit at 50% profit", "Exit if short put goes ITM"],
        popularity_score=92,
        difficulty_level="beginner",
        tags=["bullish", "credit", "income"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def bear_call_spread_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create Bear Call Spread strategy template."""
    template = StrategyTemplate(
        id=uuid4(),
        name="bear_call_spread",
        display_name="Bear Call Spread",
        category="bearish",
        description="Sell a call at lower strike, buy a call at higher strike.",
        legs_config=[
            {"type": "CE", "position": "SELL", "strike_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 200}
        ],
        max_profit="Limited",
        max_loss="Limited",
        market_outlook="bearish",
        volatility_preference="high_iv",
        risk_level="low",
        capital_requirement="medium",
        theta_positive=True,
        vega_positive=False,
        delta_neutral=False,
        gamma_risk="low",
        win_probability="~65%",
        popularity_score=88,
        difficulty_level="beginner",
        tags=["bearish", "credit"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def long_straddle_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create Long Straddle strategy template."""
    template = StrategyTemplate(
        id=uuid4(),
        name="long_straddle",
        display_name="Long Straddle",
        category="volatile",
        description="Buy ATM call and ATM put. Profits from big move either direction.",
        legs_config=[
            {"type": "CE", "position": "BUY", "strike_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": 0}
        ],
        max_profit="Unlimited",
        max_loss="Limited",
        breakeven="Two breakevens",
        market_outlook="volatile",
        volatility_preference="low_iv",
        ideal_iv_rank="<30%",
        risk_level="medium",
        capital_requirement="medium",
        theta_positive=False,
        vega_positive=True,
        delta_neutral=True,
        gamma_risk="high",
        win_probability="~35%",
        popularity_score=75,
        difficulty_level="intermediate",
        tags=["volatile", "debit", "vega-positive"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def short_straddle_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create Short Straddle strategy template."""
    template = StrategyTemplate(
        id=uuid4(),
        name="short_straddle",
        display_name="Short Straddle",
        category="neutral",
        description="Sell ATM call and ATM put. Maximum premium collection.",
        legs_config=[
            {"type": "CE", "position": "SELL", "strike_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": 0}
        ],
        max_profit="Limited",
        max_loss="Unlimited",
        market_outlook="neutral",
        volatility_preference="high_iv",
        risk_level="high",
        capital_requirement="high",
        theta_positive=True,
        vega_positive=False,
        delta_neutral=True,
        gamma_risk="high",
        win_probability="~45%",
        popularity_score=70,
        difficulty_level="advanced",
        tags=["neutral", "income", "high-risk"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def short_strangle_template(db_session: AsyncSession) -> StrategyTemplate:
    """Create Short Strangle strategy template."""
    template = StrategyTemplate(
        id=uuid4(),
        name="short_strangle",
        display_name="Short Strangle",
        category="neutral",
        description="Sell OTM call and OTM put. Wide profit zone.",
        legs_config=[
            {"type": "CE", "position": "SELL", "strike_offset": 200},
            {"type": "PE", "position": "SELL", "strike_offset": -200}
        ],
        max_profit="Limited",
        max_loss="Unlimited",
        market_outlook="neutral",
        volatility_preference="high_iv",
        risk_level="high",
        capital_requirement="high",
        theta_positive=True,
        vega_positive=False,
        delta_neutral=True,
        gamma_risk="high",
        win_probability="~68%",
        popularity_score=90,
        difficulty_level="advanced",
        tags=["neutral", "income", "high-risk"]
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest_asyncio.fixture
async def seeded_templates(
    db_session: AsyncSession,
    iron_condor_template,
    bull_call_spread_template,
    bull_put_spread_template,
    bear_call_spread_template,
    long_straddle_template,
    short_straddle_template,
    short_strangle_template
) -> list[StrategyTemplate]:
    """Seed all strategy templates for comprehensive testing."""
    return [
        iron_condor_template,
        bull_call_spread_template,
        bull_put_spread_template,
        bear_call_spread_template,
        long_straddle_template,
        short_straddle_template,
        short_strangle_template
    ]


@pytest.fixture
def mock_kite_client():
    """Mock Kite Connect client for deploy tests."""
    mock_kite = MagicMock()

    # Mock LTP response
    mock_kite.ltp.return_value = {
        "NSE:NIFTY 50": {"last_price": 26000.0, "instrument_token": 256265},
        "NSE:NIFTY BANK": {"last_price": 52000.0, "instrument_token": 260105},
        "NFO:NIFTY24DEC26000CE": {"last_price": 150.0, "instrument_token": 12345},
        "NFO:NIFTY24DEC26000PE": {"last_price": 140.0, "instrument_token": 12346},
        "NFO:NIFTY24DEC26200CE": {"last_price": 80.0, "instrument_token": 12347},
        "NFO:NIFTY24DEC25800PE": {"last_price": 90.0, "instrument_token": 12348},
    }

    # Mock quote response
    mock_kite.quote.return_value = {
        "NSE:NIFTY 50": {"last_price": 26000.0, "ohlc": {"open": 25900, "high": 26100, "low": 25850, "close": 25950}},
        "NSE:NIFTY BANK": {"last_price": 52000.0}
    }

    return mock_kite


@pytest.fixture
def mock_get_current_user(test_user: User):
    """Mock the get_current_user dependency."""
    async def override():
        return test_user
    return override


@pytest.fixture
def mock_get_current_broker_connection(test_broker_connection: BrokerConnection):
    """Mock the get_current_broker_connection dependency."""
    async def override():
        return test_broker_connection
    return override


@pytest.fixture
def auth_headers() -> dict:
    """Return authorization headers for authenticated requests."""
    return {"Authorization": "Bearer test_token"}


# Helper assertion functions
def assert_template_structure(template_dict: dict):
    """Assert that a template dictionary has all required fields."""
    required_fields = [
        "id", "name", "display_name", "category", "description",
        "legs_config", "max_profit", "max_loss", "market_outlook",
        "volatility_preference", "risk_level", "capital_requirement",
        "theta_positive", "vega_positive", "delta_neutral",
        "difficulty_level", "popularity_score"
    ]
    for field in required_fields:
        assert field in template_dict, f"Missing required field: {field}"


def assert_wizard_recommendation_structure(rec: dict):
    """Assert that a wizard recommendation has all required fields."""
    assert "template" in rec
    assert "score" in rec
    assert "match_reasons" in rec
    assert isinstance(rec["score"], int)
    assert 0 <= rec["score"] <= 100
    assert isinstance(rec["match_reasons"], list)
