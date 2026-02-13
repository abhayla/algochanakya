"""
Order Executor Service Tests

Tests for app/services/order_executor.py:
- execute_entry() - Entry order execution
- execute_exit() - Exit order execution
- Strike calculation (atm_offset, fixed, premium_based, delta_based)
- Tradingsymbol construction
- Expiry calculation
- Sequential and simultaneous execution
- Dry run mode
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, date, timedelta, time
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.users import User
from app.models.autopilot import AutoPilotStrategy, AutoPilotOrder, AutoPilotLog
from app.services.autopilot.order_executor import (
    OrderExecutor, OrderRequest, OrderResult,
    LOT_SIZES, STRIKE_STEPS, get_order_executor
)
from app.services.legacy.market_data import MarketDataService, SpotData


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_kite():
    """Create mock KiteConnect client."""
    kite = MagicMock()
    kite.access_token = "test_token"

    # Mock place_order
    kite.place_order.return_value = "220101000001"

    # Mock order_history
    kite.order_history.return_value = [
        {
            "order_id": "220101000001",
            "status": "COMPLETE",
            "filled_quantity": 25,
            "average_price": 100.50
        }
    ]

    return kite


@pytest.fixture
def mock_market_data():
    """Create mock MarketDataService."""
    mock = AsyncMock(spec=MarketDataService)

    # Mock get_spot_price
    async def get_spot_price(underlying):
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

    mock.get_spot_price = get_spot_price

    # Mock get_ltp
    async def get_ltp(instruments):
        return {inst: Decimal("100.0") for inst in instruments}

    mock.get_ltp = get_ltp

    return mock


@pytest.fixture
def order_executor(mock_kite, mock_market_data):
    """Create OrderExecutor with mocks."""
    return OrderExecutor(mock_kite, mock_market_data)


@pytest.fixture
def sample_strategy():
    """Create a sample strategy object."""
    strategy = MagicMock(spec=AutoPilotStrategy)
    strategy.id = 1
    strategy.user_id = uuid4()
    strategy.underlying = "NIFTY"
    strategy.expiry_type = "current_week"
    strategy.expiry_date = None
    strategy.lots = 1
    strategy.position_type = "intraday"
    strategy.legs_config = [
        {
            "id": "leg_1",
            "contract_type": "PE",
            "transaction_type": "BUY",
            "strike_selection": {"mode": "atm_offset", "offset": -2},
            "quantity_multiplier": 1,
            "execution_order": 1
        },
        {
            "id": "leg_2",
            "contract_type": "CE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": 2},
            "quantity_multiplier": 1,
            "execution_order": 2
        }
    ]
    strategy.order_settings = {
        "order_type": "MARKET",
        "execution_style": "sequential",
        "delay_between_legs": 0,
        "on_leg_failure": "stop"
    }
    strategy.risk_settings = {}
    strategy.runtime_state = {}
    return strategy


@pytest.fixture
def db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


# =============================================================================
# LOT SIZE AND STRIKE STEP TESTS
# =============================================================================

class TestConstants:
    """Tests for constant values."""

    def test_lot_sizes(self):
        """Test lot sizes are correct."""
        assert LOT_SIZES["NIFTY"] == 25
        assert LOT_SIZES["BANKNIFTY"] == 15
        assert LOT_SIZES["FINNIFTY"] == 25
        assert LOT_SIZES["SENSEX"] == 10

    def test_strike_steps(self):
        """Test strike steps are correct."""
        assert STRIKE_STEPS["NIFTY"] == 50
        assert STRIKE_STEPS["BANKNIFTY"] == 100
        assert STRIKE_STEPS["FINNIFTY"] == 50
        assert STRIKE_STEPS["SENSEX"] == 100


# =============================================================================
# STRIKE CALCULATION TESTS
# =============================================================================

class TestStrikeCalculation:
    """Tests for _calculate_strike method."""

    @pytest.mark.asyncio
    async def test_atm_strike_nifty(self, order_executor):
        """Test ATM strike calculation for NIFTY."""
        leg = {
            "contract_type": "CE",
            "strike_selection": {"mode": "atm_offset", "offset": 0}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25000.0,
            underlying="NIFTY"
        )

        # NIFTY strike step is 50, spot 25000 should give ATM 25000
        assert strike == 25000.0

    @pytest.mark.asyncio
    async def test_atm_strike_rounding(self, order_executor):
        """Test ATM strike rounds to nearest step."""
        leg = {
            "contract_type": "CE",
            "strike_selection": {"mode": "atm_offset", "offset": 0}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25023.0,
            underlying="NIFTY"
        )

        # Should round to 25000 (nearest 50)
        assert strike == 25000.0

        strike2 = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25030.0,
            underlying="NIFTY"
        )

        # Should round to 25050 (nearest 50)
        assert strike2 == 25050.0

    @pytest.mark.asyncio
    async def test_atm_offset_positive(self, order_executor):
        """Test ATM offset with positive value (OTM CE / ITM PE)."""
        leg = {
            "contract_type": "CE",
            "strike_selection": {"mode": "atm_offset", "offset": 2}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25000.0,
            underlying="NIFTY"
        )

        # Offset +2 = ATM + (2 * 50) = 25000 + 100 = 25100
        assert strike == 25100.0

    @pytest.mark.asyncio
    async def test_atm_offset_negative(self, order_executor):
        """Test ATM offset with negative value (ITM CE / OTM PE)."""
        leg = {
            "contract_type": "PE",
            "strike_selection": {"mode": "atm_offset", "offset": -2}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25000.0,
            underlying="NIFTY"
        )

        # Offset -2 = ATM + (-2 * 50) = 25000 - 100 = 24900
        assert strike == 24900.0

    @pytest.mark.asyncio
    async def test_fixed_strike(self, order_executor):
        """Test fixed strike mode."""
        leg = {
            "contract_type": "CE",
            "strike_selection": {"mode": "fixed", "fixed_strike": 25500}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25000.0,
            underlying="NIFTY"
        )

        assert strike == 25500

    @pytest.mark.asyncio
    async def test_premium_based_strike_ce(self, order_executor):
        """Test premium-based strike for CE."""
        leg = {
            "contract_type": "CE",
            "strike_selection": {"mode": "premium_based", "target_premium": 100}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25000.0,
            underlying="NIFTY"
        )

        # With target_premium 100, steps_away = 100/25 = 4
        # CE: ATM + (4 * 50) = 25000 + 200 = 25200
        assert strike == 25200.0

    @pytest.mark.asyncio
    async def test_premium_based_strike_pe(self, order_executor):
        """Test premium-based strike for PE."""
        leg = {
            "contract_type": "PE",
            "strike_selection": {"mode": "premium_based", "target_premium": 100}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25000.0,
            underlying="NIFTY"
        )

        # With target_premium 100, steps_away = 100/25 = 4
        # PE: ATM - (4 * 50) = 25000 - 200 = 24800
        assert strike == 24800.0

    @pytest.mark.asyncio
    async def test_delta_based_strike(self, order_executor):
        """Test delta-based strike calculation."""
        leg = {
            "contract_type": "CE",
            "strike_selection": {"mode": "delta_based", "target_delta": 0.3}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=25000.0,
            underlying="NIFTY"
        )

        # target_delta 0.3, steps_away = (0.5 - 0.3) / 0.05 = 4
        # CE: ATM + (4 * 50) = 25200
        assert strike == 25200.0

    @pytest.mark.asyncio
    async def test_strike_banknifty(self, order_executor):
        """Test strike calculation for BANKNIFTY with 100 step."""
        leg = {
            "contract_type": "CE",
            "strike_selection": {"mode": "atm_offset", "offset": 1}
        }

        strike = await order_executor._calculate_strike(
            leg=leg,
            spot_price=52000.0,
            underlying="BANKNIFTY"
        )

        # BANKNIFTY step is 100
        # ATM 52000 + (1 * 100) = 52100
        assert strike == 52100.0


# =============================================================================
# TRADINGSYMBOL TESTS
# =============================================================================

class TestTradingsymbol:
    """Tests for _build_tradingsymbol method."""

    def test_tradingsymbol_weekly(self, order_executor):
        """Test tradingsymbol for weekly expiry."""
        expiry = date(2024, 12, 19)  # Thursday (not last Thursday)

        symbol = order_executor._build_tradingsymbol(
            underlying="NIFTY",
            expiry=expiry,
            strike=25000,
            contract_type="CE"
        )

        # Weekly format: NIFTY24D1925000CE
        assert "NIFTY" in symbol
        assert "25000" in symbol
        assert "CE" in symbol

    def test_tradingsymbol_monthly(self, order_executor):
        """Test tradingsymbol for monthly expiry."""
        expiry = date(2024, 12, 26)  # Last Thursday of December

        # Mock _is_monthly_expiry to return True
        with patch.object(order_executor, '_is_monthly_expiry', return_value=True):
            symbol = order_executor._build_tradingsymbol(
                underlying="NIFTY",
                expiry=expiry,
                strike=25000,
                contract_type="PE"
            )

        # Monthly format: NIFTY24DEC25000PE
        assert symbol == "NIFTY24DEC25000PE"

    def test_tradingsymbol_banknifty(self, order_executor):
        """Test tradingsymbol for BANKNIFTY."""
        expiry = date(2024, 12, 26)

        with patch.object(order_executor, '_is_monthly_expiry', return_value=True):
            symbol = order_executor._build_tradingsymbol(
                underlying="BANKNIFTY",
                expiry=expiry,
                strike=52000,
                contract_type="CE"
            )

        assert symbol == "BANKNIFTY24DEC52000CE"


# =============================================================================
# EXPIRY CALCULATION TESTS
# =============================================================================

class TestExpiryCalculation:
    """Tests for _calculate_expiry method."""

    def test_current_week_before_thursday(self, order_executor):
        """Test current_week expiry before Thursday."""
        with patch('app.services.order_executor.date') as mock_date:
            mock_date.today.return_value = date(2024, 12, 23)  # Monday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            expiry = order_executor._calculate_expiry("current_week", "NIFTY")

            # Should be Thursday Dec 26
            assert expiry == date(2024, 12, 26)

    def test_next_week_expiry(self, order_executor):
        """Test next_week expiry."""
        with patch('app.services.order_executor.date') as mock_date:
            mock_date.today.return_value = date(2024, 12, 23)  # Monday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            expiry = order_executor._calculate_expiry("next_week", "NIFTY")

            # Should be Thursday Jan 2, 2025
            assert expiry == date(2025, 1, 2)

    def test_get_last_thursday(self, order_executor):
        """Test _get_last_thursday method."""
        # December 2024 - last Thursday is Dec 26
        last_thursday = order_executor._get_last_thursday(2024, 12)
        assert last_thursday == date(2024, 12, 26)

        # January 2025 - last Thursday is Jan 30
        last_thursday_jan = order_executor._get_last_thursday(2025, 1)
        assert last_thursday_jan == date(2025, 1, 30)

    def test_is_monthly_expiry_true(self, order_executor):
        """Test _is_monthly_expiry for last Thursday."""
        # Dec 26, 2024 is last Thursday of December
        is_monthly = order_executor._is_monthly_expiry(date(2024, 12, 26))
        assert is_monthly is True

    def test_is_monthly_expiry_false(self, order_executor):
        """Test _is_monthly_expiry for non-last Thursday."""
        # Dec 19, 2024 is a Thursday but not the last one
        is_monthly = order_executor._is_monthly_expiry(date(2024, 12, 19))
        assert is_monthly is False


# =============================================================================
# BUILD ORDER REQUESTS TESTS
# =============================================================================

class TestBuildOrderRequests:
    """Tests for _build_order_requests method."""

    @pytest.mark.asyncio
    async def test_build_requests_basic(self, order_executor, sample_strategy):
        """Test building order requests from leg config."""
        requests = await order_executor._build_order_requests(
            strategy=sample_strategy,
            legs=sample_strategy.legs_config,
            purpose="entry"
        )

        assert len(requests) == 2

        # First leg (PE BUY)
        assert requests[0].leg_id == "leg_1"
        assert requests[0].transaction_type == "BUY"
        assert requests[0].contract_type == "PE"
        assert requests[0].quantity == 25  # 1 lot * 25 lot size

        # Second leg (CE SELL)
        assert requests[1].leg_id == "leg_2"
        assert requests[1].transaction_type == "SELL"
        assert requests[1].contract_type == "CE"

    @pytest.mark.asyncio
    async def test_build_requests_multiple_lots(self, order_executor, sample_strategy):
        """Test quantity calculation with multiple lots."""
        sample_strategy.lots = 3

        requests = await order_executor._build_order_requests(
            strategy=sample_strategy,
            legs=sample_strategy.legs_config,
            purpose="entry"
        )

        # 3 lots * 25 lot size = 75
        assert requests[0].quantity == 75
        assert requests[1].quantity == 75

    @pytest.mark.asyncio
    async def test_build_requests_quantity_multiplier(self, order_executor, sample_strategy):
        """Test quantity multiplier."""
        sample_strategy.legs_config[0]["quantity_multiplier"] = 2

        requests = await order_executor._build_order_requests(
            strategy=sample_strategy,
            legs=sample_strategy.legs_config,
            purpose="entry"
        )

        # 1 lot * 25 * 2 multiplier = 50
        assert requests[0].quantity == 50
        assert requests[1].quantity == 25  # No multiplier

    @pytest.mark.asyncio
    async def test_build_requests_positional_product(self, order_executor, sample_strategy):
        """Test product type for positional trades."""
        sample_strategy.position_type = "positional"

        requests = await order_executor._build_order_requests(
            strategy=sample_strategy,
            legs=sample_strategy.legs_config,
            purpose="entry"
        )

        assert requests[0].product == "NRML"
        assert requests[1].product == "NRML"

    @pytest.mark.asyncio
    async def test_build_requests_intraday_product(self, order_executor, sample_strategy):
        """Test product type for intraday trades."""
        sample_strategy.position_type = "intraday"

        requests = await order_executor._build_order_requests(
            strategy=sample_strategy,
            legs=sample_strategy.legs_config,
            purpose="entry"
        )

        assert requests[0].product == "MIS"
        assert requests[1].product == "MIS"


# =============================================================================
# EXECUTE ENTRY TESTS
# =============================================================================

class TestExecuteEntry:
    """Tests for execute_entry method."""

    @pytest.mark.asyncio
    async def test_execute_entry_sequential_success(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test successful sequential entry execution."""
        success, results = await order_executor.execute_entry(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        assert success is True
        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_entry_simultaneous(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test simultaneous entry execution."""
        sample_strategy.order_settings["execution_style"] = "simultaneous"

        success, results = await order_executor.execute_entry(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        assert success is True
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_execute_entry_custom_leg_sequence(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test entry with custom leg sequence."""
        # Reverse the order
        sample_strategy.order_settings["leg_sequence"] = ["leg_2", "leg_1"]

        success, results = await order_executor.execute_entry(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        assert success is True
        # First result should be leg_2
        assert results[0].leg_id == "leg_2"
        assert results[1].leg_id == "leg_1"

    @pytest.mark.asyncio
    async def test_execute_entry_dry_run_creates_records(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test dry run creates order records."""
        success, results = await order_executor.execute_entry(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        # Should have called db.add for each order
        assert db_session.add.call_count >= 2
        assert db_session.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_execute_entry_empty_legs(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test entry with no legs."""
        sample_strategy.legs_config = []

        success, results = await order_executor.execute_entry(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        assert success is True
        assert len(results) == 0


# =============================================================================
# EXECUTE EXIT TESTS
# =============================================================================

class TestExecuteExit:
    """Tests for execute_exit method."""

    @pytest.mark.asyncio
    async def test_execute_exit_no_positions(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test exit with no positions."""
        sample_strategy.runtime_state = {"current_positions": []}

        success, results = await order_executor.execute_exit(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        assert success is True
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_execute_exit_with_positions(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test exit with existing positions."""
        sample_strategy.runtime_state = {
            "current_positions": [
                {
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24DEC24900PE",
                    "quantity": 25,
                    "exchange": "NFO",
                    "product": "MIS",
                    "contract_type": "PE"
                },
                {
                    "leg_id": "leg_2",
                    "tradingsymbol": "NIFTY24DEC25100CE",
                    "quantity": -25,  # Short position
                    "exchange": "NFO",
                    "product": "MIS",
                    "contract_type": "CE"
                }
            ]
        }

        success, results = await order_executor.execute_exit(
            db=db_session,
            strategy=sample_strategy,
            exit_type="market",
            dry_run=True
        )

        assert success is True
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_execute_exit_reverses_transaction(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test exit creates reverse transactions."""
        sample_strategy.runtime_state = {
            "current_positions": [
                {
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24DEC24900PE",
                    "quantity": 25,  # Long position
                    "exchange": "NFO",
                    "product": "MIS"
                }
            ]
        }

        # Capture the order request
        original_place_order = order_executor._place_order

        captured_requests = []

        async def capture_place_order(db, request, strategy, dry_run):
            captured_requests.append(request)
            return OrderResult(success=True, leg_id=request.leg_id)

        order_executor._place_order = capture_place_order

        await order_executor.execute_exit(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        # Long position (qty 25) should result in SELL order
        assert captured_requests[0].transaction_type == "SELL"
        assert captured_requests[0].quantity == 25

        order_executor._place_order = original_place_order


# =============================================================================
# PLACE ORDER TESTS
# =============================================================================

class TestPlaceOrder:
    """Tests for _place_order method."""

    @pytest.mark.asyncio
    async def test_place_order_dry_run(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test dry run order placement."""
        request = OrderRequest(
            strategy_id=sample_strategy.id,
            leg_id="leg_1",
            leg_index=0,
            purpose="entry",
            exchange="NFO",
            tradingsymbol="NIFTY24DEC25000CE",
            transaction_type="SELL",
            quantity=25,
            order_type="MARKET",
            product="MIS",
            underlying="NIFTY",
            contract_type="CE"
        )

        result = await order_executor._place_order(
            db=db_session,
            request=request,
            strategy=sample_strategy,
            dry_run=True
        )

        assert result.success is True
        assert "DRY" in result.kite_order_id
        assert "simulated" in result.message.lower()

    @pytest.mark.asyncio
    async def test_place_order_real_success(
        self,
        order_executor,
        mock_kite,
        sample_strategy,
        db_session
    ):
        """Test real order placement."""
        request = OrderRequest(
            strategy_id=sample_strategy.id,
            leg_id="leg_1",
            leg_index=0,
            purpose="entry",
            exchange="NFO",
            tradingsymbol="NIFTY24DEC25000CE",
            transaction_type="SELL",
            quantity=25,
            order_type="MARKET",
            product="MIS",
            underlying="NIFTY",
            contract_type="CE"
        )

        result = await order_executor._place_order(
            db=db_session,
            request=request,
            strategy=sample_strategy,
            dry_run=False
        )

        assert result.success is True
        assert result.kite_order_id == "220101000001"
        mock_kite.place_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_place_order_real_failure(
        self,
        order_executor,
        mock_kite,
        sample_strategy,
        db_session
    ):
        """Test order placement failure."""
        mock_kite.place_order.side_effect = Exception("Insufficient funds")

        request = OrderRequest(
            strategy_id=sample_strategy.id,
            leg_id="leg_1",
            leg_index=0,
            purpose="entry",
            exchange="NFO",
            tradingsymbol="NIFTY24DEC25000CE",
            transaction_type="SELL",
            quantity=25,
            order_type="MARKET",
            product="MIS",
            underlying="NIFTY",
            contract_type="CE"
        )

        result = await order_executor._place_order(
            db=db_session,
            request=request,
            strategy=sample_strategy,
            dry_run=False
        )

        assert result.success is False
        assert "Insufficient funds" in result.error

    @pytest.mark.asyncio
    async def test_place_order_with_limit_price(
        self,
        order_executor,
        mock_kite,
        sample_strategy,
        db_session
    ):
        """Test order with limit price."""
        request = OrderRequest(
            strategy_id=sample_strategy.id,
            leg_id="leg_1",
            leg_index=0,
            purpose="entry",
            exchange="NFO",
            tradingsymbol="NIFTY24DEC25000CE",
            transaction_type="SELL",
            quantity=25,
            order_type="LIMIT",
            product="MIS",
            underlying="NIFTY",
            contract_type="CE",
            price=Decimal("105.50")
        )

        await order_executor._place_order(
            db=db_session,
            request=request,
            strategy=sample_strategy,
            dry_run=False
        )

        call_kwargs = mock_kite.place_order.call_args[1]
        assert call_kwargs["price"] == 105.50


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestDataClasses:
    """Tests for data classes."""

    def test_order_request_creation(self):
        """Test OrderRequest dataclass."""
        request = OrderRequest(
            strategy_id=1,
            leg_id="leg_1",
            leg_index=0,
            purpose="entry",
            exchange="NFO",
            tradingsymbol="NIFTY24DEC25000CE",
            transaction_type="SELL",
            quantity=25,
            order_type="MARKET",
            product="MIS"
        )

        assert request.strategy_id == 1
        assert request.tradingsymbol == "NIFTY24DEC25000CE"
        assert request.price is None  # Optional

    def test_order_result_success(self):
        """Test OrderResult for successful order."""
        result = OrderResult(
            success=True,
            order_id="123",
            kite_order_id="220101000001",
            message="Order placed",
            executed_price=Decimal("100.50"),
            leg_id="leg_1"
        )

        assert result.success is True
        assert result.error is None

    def test_order_result_failure(self):
        """Test OrderResult for failed order."""
        result = OrderResult(
            success=False,
            error="Insufficient margin",
            message="Order failed",
            leg_id="leg_1"
        )

        assert result.success is False
        assert result.error == "Insufficient margin"


# =============================================================================
# SERVICE FACTORY TESTS
# =============================================================================

class TestServiceFactory:
    """Tests for service factory."""

    def test_get_order_executor(self, mock_kite, mock_market_data):
        """Test get_order_executor creates instance."""
        executor = get_order_executor(mock_kite, mock_market_data)

        assert isinstance(executor, OrderExecutor)
        assert executor.kite == mock_kite
        assert executor.market_data == mock_market_data


# =============================================================================
# ON LEG FAILURE TESTS
# =============================================================================

class TestOnLegFailure:
    """Tests for leg failure handling."""

    @pytest.mark.asyncio
    async def test_stop_on_leg_failure(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test execution stops on leg failure when on_leg_failure='stop'."""
        sample_strategy.order_settings["on_leg_failure"] = "stop"

        # Make first order fail
        call_count = [0]
        original_place = order_executor._place_order

        async def failing_place_order(db, request, strategy, dry_run):
            call_count[0] += 1
            if call_count[0] == 1:
                return OrderResult(success=False, error="Failed", leg_id=request.leg_id)
            return OrderResult(success=True, leg_id=request.leg_id)

        order_executor._place_order = failing_place_order

        success, results = await order_executor.execute_entry(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        # Should have stopped after first failure
        assert success is False
        assert len(results) == 1
        assert results[0].success is False

        order_executor._place_order = original_place

    @pytest.mark.asyncio
    async def test_continue_on_leg_failure(
        self,
        order_executor,
        sample_strategy,
        db_session
    ):
        """Test execution continues on leg failure when on_leg_failure='continue'."""
        sample_strategy.order_settings["on_leg_failure"] = "continue"

        # Make first order fail
        call_count = [0]
        original_place = order_executor._place_order

        async def failing_place_order(db, request, strategy, dry_run):
            call_count[0] += 1
            if call_count[0] == 1:
                return OrderResult(success=False, error="Failed", leg_id=request.leg_id)
            return OrderResult(success=True, leg_id=request.leg_id)

        order_executor._place_order = failing_place_order

        success, results = await order_executor.execute_entry(
            db=db_session,
            strategy=sample_strategy,
            dry_run=True
        )

        # Should have continued to second leg
        assert success is False  # Overall still false
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True

        order_executor._place_order = original_place
