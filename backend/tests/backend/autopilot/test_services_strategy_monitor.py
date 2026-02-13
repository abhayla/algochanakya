"""
Strategy Monitor Service Tests

Tests for app/services/strategy_monitor.py:
- is_market_open() - Market hours checking
- _is_schedule_active() - Strategy schedule validation
- _check_risk_limits() - User risk limit checks
- _update_pnl() - P&L calculations
- _check_risk_exits() - Risk-based exit triggers
- start()/stop() - Monitor lifecycle
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from freezegun import freeze_time

from app.services.strategy_monitor import (
    StrategyMonitor, get_strategy_monitor, stop_strategy_monitor
)
from app.services.legacy.market_data import MarketDataService, SpotData
from app.services.condition_engine import ConditionEngine, EvaluationResult, ConditionResult
from app.services.order_executor import OrderExecutor, OrderResult
from app.models.autopilot import AutoPilotStrategy, AutoPilotUserSettings


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_kite():
    """Create mock KiteConnect client."""
    kite = MagicMock()
    kite.access_token = "test_token"
    return kite


@pytest.fixture
def mock_market_data():
    """Create mock MarketDataService."""
    mock = AsyncMock(spec=MarketDataService)

    async def get_spot_price(underlying):
        return SpotData(
            symbol=underlying,
            ltp=Decimal("25000.0"),
            change=Decimal("50.0"),
            change_pct=0.2,
            timestamp=datetime.now()
        )

    mock.get_spot_price = get_spot_price

    async def get_ltp(instruments):
        return {inst: Decimal("100.0") for inst in instruments}

    mock.get_ltp = get_ltp

    return mock


@pytest.fixture
def mock_condition_engine():
    """Create mock ConditionEngine."""
    mock = AsyncMock(spec=ConditionEngine)

    async def evaluate(strategy_id, entry_conditions, underlying, legs_config):
        return EvaluationResult(
            strategy_id=strategy_id,
            all_conditions_met=True,
            individual_results=[],
            evaluation_time=datetime.now()
        )

    mock.evaluate = evaluate
    return mock


@pytest.fixture
def mock_ws_manager():
    """Create mock WebSocket manager."""
    mock = AsyncMock()
    mock.sent_messages = []

    async def send_status_change(user_id, strategy_id, old_status, new_status, reason=""):
        mock.sent_messages.append({
            "type": "status_change",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "old_status": old_status,
            "new_status": new_status
        })

    async def send_condition_update(user_id, strategy_id, conditions_met, condition_states):
        mock.sent_messages.append({
            "type": "condition_update",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "conditions_met": conditions_met
        })

    async def send_pnl_update(user_id, strategy_id, realized_pnl, unrealized_pnl, total_pnl):
        mock.sent_messages.append({
            "type": "pnl_update",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "total_pnl": total_pnl
        })

    async def send_risk_alert(user_id, alert_type, message, data):
        mock.sent_messages.append({
            "type": "risk_alert",
            "user_id": user_id,
            "alert_type": alert_type,
            "message": message
        })

    async def send_market_status(is_open, message=""):
        mock.sent_messages.append({
            "type": "market_status",
            "is_open": is_open
        })

    async def send_order_update(user_id, strategy_id, order_id, event_type, order_data):
        mock.sent_messages.append({
            "type": "order_update",
            "user_id": user_id,
            "strategy_id": strategy_id,
            "order_id": order_id
        })

    mock.send_status_change = send_status_change
    mock.send_condition_update = send_condition_update
    mock.send_pnl_update = send_pnl_update
    mock.send_risk_alert = send_risk_alert
    mock.send_market_status = send_market_status
    mock.send_order_update = send_order_update

    return mock


@pytest.fixture
def strategy_monitor(mock_kite, mock_market_data, mock_condition_engine, mock_ws_manager):
    """Create StrategyMonitor with mocks."""
    with patch('app.services.strategy_monitor.get_ws_manager', return_value=mock_ws_manager):
        with patch('app.services.strategy_monitor.get_order_executor') as mock_executor:
            mock_executor.return_value = AsyncMock(spec=OrderExecutor)
            monitor = StrategyMonitor(mock_kite, mock_market_data, mock_condition_engine)
            monitor.ws_manager = mock_ws_manager
            return monitor


@pytest.fixture
def sample_strategy():
    """Create sample strategy."""
    strategy = MagicMock(spec=AutoPilotStrategy)
    strategy.id = 1
    strategy.user_id = uuid4()
    strategy.name = "Test Strategy"
    strategy.status = "waiting"
    strategy.underlying = "NIFTY"
    strategy.expiry_type = "current_week"
    strategy.lots = 1
    strategy.position_type = "intraday"
    strategy.legs_config = [
        {
            "id": "leg_1",
            "contract_type": "CE",
            "transaction_type": "SELL",
            "strike_selection": {"mode": "atm_offset", "offset": 0},
            "tradingsymbol": "NIFTY24DEC25000CE"
        }
    ]
    strategy.entry_conditions = {"logic": "AND", "conditions": []}
    strategy.order_settings = {"order_type": "MARKET"}
    strategy.risk_settings = {}
    strategy.schedule_config = {}
    strategy.runtime_state = {}
    return strategy


@pytest.fixture
def sample_user_settings():
    """Create sample user settings."""
    settings = MagicMock(spec=AutoPilotUserSettings)
    settings.daily_loss_limit = Decimal("20000.00")
    settings.per_strategy_loss_limit = Decimal("10000.00")
    settings.max_active_strategies = 3
    settings.no_trade_first_minutes = 5
    settings.no_trade_last_minutes = 5
    settings.paper_trading_mode = False
    return settings


# =============================================================================
# IS_MARKET_OPEN TESTS
# =============================================================================

class TestIsMarketOpen:
    """Tests for is_market_open method."""

    @freeze_time("2024-12-26 10:30:00")  # Thursday during market hours
    def test_market_open_during_trading_hours(self, strategy_monitor):
        """Test market is open during trading hours."""
        assert strategy_monitor.is_market_open() is True

    @freeze_time("2024-12-26 09:14:00")  # Thursday before open
    def test_market_closed_before_open(self, strategy_monitor):
        """Test market is closed before 9:15."""
        assert strategy_monitor.is_market_open() is False

    @freeze_time("2024-12-26 15:31:00")  # Thursday after close
    def test_market_closed_after_close(self, strategy_monitor):
        """Test market is closed after 15:30."""
        assert strategy_monitor.is_market_open() is False

    @freeze_time("2024-12-26 09:15:00")  # Thursday at exactly 9:15
    def test_market_open_at_exact_open(self, strategy_monitor):
        """Test market is open at exact open time."""
        assert strategy_monitor.is_market_open() is True

    @freeze_time("2024-12-26 15:30:00")  # Thursday at exactly 15:30
    def test_market_open_at_exact_close(self, strategy_monitor):
        """Test market is open at exact close time."""
        assert strategy_monitor.is_market_open() is True

    @freeze_time("2024-12-28 10:30:00")  # Saturday
    def test_market_closed_weekend_saturday(self, strategy_monitor):
        """Test market is closed on Saturday."""
        assert strategy_monitor.is_market_open() is False

    @freeze_time("2024-12-29 10:30:00")  # Sunday
    def test_market_closed_weekend_sunday(self, strategy_monitor):
        """Test market is closed on Sunday."""
        assert strategy_monitor.is_market_open() is False


# =============================================================================
# IS_SCHEDULE_ACTIVE TESTS
# =============================================================================

class TestIsScheduleActive:
    """Tests for _is_schedule_active method."""

    @freeze_time("2024-12-26 10:30:00")  # Thursday
    def test_schedule_active_default(self, strategy_monitor, sample_strategy):
        """Test schedule is active with default config."""
        sample_strategy.schedule_config = {}

        assert strategy_monitor._is_schedule_active(sample_strategy) is True

    @freeze_time("2024-12-28 10:30:00")  # Saturday
    def test_schedule_inactive_weekend(self, strategy_monitor, sample_strategy):
        """Test schedule is inactive on weekends."""
        sample_strategy.schedule_config = {
            "active_days": ["MON", "TUE", "WED", "THU", "FRI"]
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is False

    @freeze_time("2024-12-26 10:30:00")  # Thursday
    def test_schedule_active_custom_days(self, strategy_monitor, sample_strategy):
        """Test schedule with custom active days."""
        sample_strategy.schedule_config = {
            "active_days": ["THU", "FRI"]
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is True

    @freeze_time("2024-12-25 10:30:00")  # Wednesday
    def test_schedule_inactive_not_in_active_days(self, strategy_monitor, sample_strategy):
        """Test schedule inactive when not in active days."""
        sample_strategy.schedule_config = {
            "active_days": ["THU", "FRI"]  # Only Thursday and Friday
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is False

    @freeze_time("2024-12-26 08:30:00")  # Thursday before start time
    def test_schedule_inactive_before_start_time(self, strategy_monitor, sample_strategy):
        """Test schedule inactive before start time."""
        sample_strategy.schedule_config = {
            "start_time": "09:30",
            "end_time": "15:00"
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is False

    @freeze_time("2024-12-26 15:30:00")  # Thursday after end time
    def test_schedule_inactive_after_end_time(self, strategy_monitor, sample_strategy):
        """Test schedule inactive after end time."""
        sample_strategy.schedule_config = {
            "start_time": "09:30",
            "end_time": "15:00"
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is False

    @freeze_time("2024-12-26 10:30:00")  # Thursday
    def test_schedule_with_date_range(self, strategy_monitor, sample_strategy):
        """Test schedule with start and end dates."""
        sample_strategy.schedule_config = {
            "start_date": "2024-12-01",
            "end_date": "2024-12-31"
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is True

    @freeze_time("2024-12-26 10:30:00")  # Thursday
    def test_schedule_before_start_date(self, strategy_monitor, sample_strategy):
        """Test schedule inactive before start date."""
        sample_strategy.schedule_config = {
            "start_date": "2024-12-27"  # Tomorrow
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is False

    @freeze_time("2024-12-26 10:30:00")  # Thursday
    def test_schedule_after_end_date(self, strategy_monitor, sample_strategy):
        """Test schedule inactive after end date."""
        sample_strategy.schedule_config = {
            "end_date": "2024-12-25"  # Yesterday
        }

        assert strategy_monitor._is_schedule_active(sample_strategy) is False


# =============================================================================
# CHECK_RISK_LIMITS TESTS
# =============================================================================

class TestCheckRiskLimits:
    """Tests for _check_risk_limits method."""

    @pytest.mark.asyncio
    async def test_risk_limits_no_settings(self, strategy_monitor, sample_strategy):
        """Test risk limits pass when no settings exist."""
        mock_db = AsyncMock()

        with patch.object(strategy_monitor, '_get_user_settings', return_value=None):
            ok, message = await strategy_monitor._check_risk_limits(mock_db, sample_strategy)

        assert ok is True
        assert message == ""

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 09:17:00")  # 2 minutes after open
    async def test_risk_limits_no_trade_first_minutes(
        self, strategy_monitor, sample_strategy, sample_user_settings
    ):
        """Test no trading in first minutes of market."""
        mock_db = AsyncMock()
        sample_user_settings.no_trade_first_minutes = 5  # No trade first 5 minutes

        with patch.object(strategy_monitor, '_get_user_settings', return_value=sample_user_settings):
            ok, message = await strategy_monitor._check_risk_limits(mock_db, sample_strategy)

        assert ok is False
        assert "first" in message.lower()

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 15:28:00")  # 2 minutes before close
    async def test_risk_limits_no_trade_last_minutes(
        self, strategy_monitor, sample_strategy, sample_user_settings
    ):
        """Test no trading in last minutes of market."""
        mock_db = AsyncMock()
        sample_user_settings.no_trade_last_minutes = 5  # No trade last 5 minutes

        with patch.object(strategy_monitor, '_get_user_settings', return_value=sample_user_settings):
            ok, message = await strategy_monitor._check_risk_limits(mock_db, sample_strategy)

        assert ok is False
        assert "last" in message.lower()

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")
    async def test_risk_limits_max_active_strategies(
        self, strategy_monitor, sample_strategy, sample_user_settings
    ):
        """Test max active strategies limit."""
        mock_db = AsyncMock()
        sample_user_settings.max_active_strategies = 2

        # Mock that there are already 2 active strategies
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [MagicMock(), MagicMock()]  # 2 strategies
        mock_db.execute.return_value = mock_result

        with patch.object(strategy_monitor, '_get_user_settings', return_value=sample_user_settings):
            ok, message = await strategy_monitor._check_risk_limits(mock_db, sample_strategy)

        assert ok is False
        assert "max active" in message.lower()


# =============================================================================
# UPDATE_PNL TESTS
# =============================================================================

class TestUpdatePnl:
    """Tests for _update_pnl method."""

    @pytest.mark.asyncio
    async def test_update_pnl_no_positions(self, strategy_monitor, sample_strategy):
        """Test P&L update with no positions."""
        mock_db = AsyncMock()
        sample_strategy.runtime_state = {"current_positions": []}

        await strategy_monitor._update_pnl(mock_db, sample_strategy)

        # Should not try to get LTP
        strategy_monitor.market_data.get_ltp.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_pnl_with_positions(
        self, strategy_monitor, sample_strategy, mock_ws_manager
    ):
        """Test P&L update calculates correctly."""
        mock_db = AsyncMock()
        sample_strategy.runtime_state = {
            "current_positions": [
                {
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24DEC25000CE",
                    "quantity": 25,  # Long position
                    "entry_price": 100.0
                }
            ]
        }

        # Mock LTP at 110 (profit of 10 * 25 = 250)
        async def mock_get_ltp(instruments):
            return {"NFO:NIFTY24DEC25000CE": Decimal("110.0")}

        strategy_monitor.market_data.get_ltp = mock_get_ltp

        await strategy_monitor._update_pnl(mock_db, sample_strategy)

        # Check P&L was calculated
        runtime_state = sample_strategy.runtime_state
        assert runtime_state["current_pnl"] == 250.0  # (110 - 100) * 25

    @pytest.mark.asyncio
    async def test_update_pnl_short_position(
        self, strategy_monitor, sample_strategy, mock_ws_manager
    ):
        """Test P&L for short positions."""
        mock_db = AsyncMock()
        sample_strategy.runtime_state = {
            "current_positions": [
                {
                    "leg_id": "leg_1",
                    "tradingsymbol": "NIFTY24DEC25000CE",
                    "quantity": -25,  # Short position
                    "entry_price": 100.0
                }
            ]
        }

        # Mock LTP at 90 (profit for short: (100 - 90) * 25 = 250)
        async def mock_get_ltp(instruments):
            return {"NFO:NIFTY24DEC25000CE": Decimal("90.0")}

        strategy_monitor.market_data.get_ltp = mock_get_ltp

        await strategy_monitor._update_pnl(mock_db, sample_strategy)

        # For short: (LTP - Entry) * Qty = (90 - 100) * -25 = 250
        runtime_state = sample_strategy.runtime_state
        assert runtime_state["current_pnl"] == 250.0


# =============================================================================
# CHECK_RISK_EXITS TESTS
# =============================================================================

class TestCheckRiskExits:
    """Tests for _check_risk_exits method."""

    @pytest.mark.asyncio
    async def test_max_loss_exit(self, strategy_monitor, sample_strategy):
        """Test exit triggered on max loss."""
        mock_db = AsyncMock()
        sample_strategy.risk_settings = {"max_loss": 5000}
        sample_strategy.runtime_state = {
            "current_pnl": -5500,  # Loss exceeds max
            "paper_trading": True
        }

        # Mock order executor
        async def mock_execute_exit(db, strategy, exit_type, reason, dry_run):
            return True, []

        strategy_monitor.order_executor.execute_exit = mock_execute_exit

        await strategy_monitor._check_risk_exits(mock_db, sample_strategy)

        # Status should be completed
        assert sample_strategy.status == "completed"
        assert "max loss" in sample_strategy.runtime_state.get("exit_reason", "").lower()

    @pytest.mark.asyncio
    async def test_max_profit_exit(self, strategy_monitor, sample_strategy):
        """Test exit triggered on max profit (target)."""
        mock_db = AsyncMock()
        sample_strategy.risk_settings = {"max_profit": 5000}
        sample_strategy.runtime_state = {
            "current_pnl": 5500,  # Profit exceeds target
            "paper_trading": True
        }

        async def mock_execute_exit(db, strategy, exit_type, reason, dry_run):
            return True, []

        strategy_monitor.order_executor.execute_exit = mock_execute_exit

        await strategy_monitor._check_risk_exits(mock_db, sample_strategy)

        assert sample_strategy.status == "completed"
        assert "target profit" in sample_strategy.runtime_state.get("exit_reason", "").lower()

    @pytest.mark.asyncio
    async def test_trailing_stop_exit(self, strategy_monitor, sample_strategy):
        """Test trailing stop loss exit."""
        mock_db = AsyncMock()
        sample_strategy.risk_settings = {"trailing_stop_loss": 1000}
        sample_strategy.runtime_state = {
            "current_pnl": 3000,
            "peak_pnl": 4500,  # Peak was 4500, now at 3000 (dropped 1500)
            "paper_trading": True
        }

        async def mock_execute_exit(db, strategy, exit_type, reason, dry_run):
            return True, []

        strategy_monitor.order_executor.execute_exit = mock_execute_exit

        await strategy_monitor._check_risk_exits(mock_db, sample_strategy)

        assert sample_strategy.status == "completed"
        assert "trailing" in sample_strategy.runtime_state.get("exit_reason", "").lower()

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 15:20:00")
    async def test_time_stop_exit(self, strategy_monitor, sample_strategy):
        """Test time stop exit."""
        mock_db = AsyncMock()
        sample_strategy.risk_settings = {"time_stop": "15:15"}  # Stop at 15:15
        sample_strategy.runtime_state = {
            "current_pnl": 1000,
            "paper_trading": True
        }

        async def mock_execute_exit(db, strategy, exit_type, reason, dry_run):
            return True, []

        strategy_monitor.order_executor.execute_exit = mock_execute_exit

        await strategy_monitor._check_risk_exits(mock_db, sample_strategy)

        assert sample_strategy.status == "completed"
        assert "time stop" in sample_strategy.runtime_state.get("exit_reason", "").lower()

    @pytest.mark.asyncio
    async def test_no_exit_within_limits(self, strategy_monitor, sample_strategy):
        """Test no exit when within all limits."""
        mock_db = AsyncMock()
        sample_strategy.risk_settings = {
            "max_loss": 5000,
            "max_profit": 10000
        }
        sample_strategy.runtime_state = {
            "current_pnl": 2000,  # Within limits
            "paper_trading": True
        }

        original_status = sample_strategy.status

        await strategy_monitor._check_risk_exits(mock_db, sample_strategy)

        # Status should not change
        assert sample_strategy.status == original_status

    @pytest.mark.asyncio
    async def test_peak_pnl_tracking(self, strategy_monitor, sample_strategy):
        """Test peak P&L is tracked for trailing stop."""
        mock_db = AsyncMock()
        sample_strategy.risk_settings = {"trailing_stop_loss": 2000}
        sample_strategy.runtime_state = {
            "current_pnl": 5000,
            "peak_pnl": 4000  # Current is higher than peak
        }

        await strategy_monitor._check_risk_exits(mock_db, sample_strategy)

        # Peak should be updated
        assert sample_strategy.runtime_state["peak_pnl"] == 5000


# =============================================================================
# START/STOP TESTS
# =============================================================================

class TestStartStop:
    """Tests for start and stop methods."""

    @pytest.mark.asyncio
    async def test_start_creates_task(self, strategy_monitor):
        """Test start creates background task."""
        await strategy_monitor.start()

        assert strategy_monitor._running is True
        assert strategy_monitor._task is not None

        await strategy_monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, strategy_monitor):
        """Test stop cancels background task."""
        await strategy_monitor.start()
        await strategy_monitor.stop()

        assert strategy_monitor._running is False

    @pytest.mark.asyncio
    async def test_double_start_warning(self, strategy_monitor):
        """Test starting twice logs warning."""
        await strategy_monitor.start()
        await strategy_monitor.start()  # Second start should be ignored

        assert strategy_monitor._running is True

        await strategy_monitor.stop()


# =============================================================================
# LOT SIZE TESTS
# =============================================================================

class TestGetLotSize:
    """Tests for _get_lot_size method."""

    def test_nifty_lot_size(self, strategy_monitor):
        """Test NIFTY lot size."""
        assert strategy_monitor._get_lot_size("NIFTY") == 25

    def test_banknifty_lot_size(self, strategy_monitor):
        """Test BANKNIFTY lot size."""
        assert strategy_monitor._get_lot_size("BANKNIFTY") == 15

    def test_finnifty_lot_size(self, strategy_monitor):
        """Test FINNIFTY lot size."""
        assert strategy_monitor._get_lot_size("FINNIFTY") == 25

    def test_sensex_lot_size(self, strategy_monitor):
        """Test SENSEX lot size."""
        assert strategy_monitor._get_lot_size("SENSEX") == 10

    def test_unknown_underlying_default(self, strategy_monitor):
        """Test unknown underlying returns default lot size."""
        assert strategy_monitor._get_lot_size("UNKNOWN") == 25

    def test_case_insensitive(self, strategy_monitor):
        """Test lot size lookup is case insensitive."""
        assert strategy_monitor._get_lot_size("nifty") == 25
        assert strategy_monitor._get_lot_size("BankNifty") == 15


# =============================================================================
# CONSTANTS TESTS
# =============================================================================

class TestConstants:
    """Tests for monitor constants."""

    def test_market_times(self, strategy_monitor):
        """Test market open/close times."""
        assert strategy_monitor.MARKET_OPEN == time(9, 15)
        assert strategy_monitor.MARKET_CLOSE == time(15, 30)

    def test_poll_interval(self, strategy_monitor):
        """Test poll interval."""
        assert strategy_monitor.POLL_INTERVAL == 5


# =============================================================================
# SERVICE FACTORY TESTS
# =============================================================================

class TestServiceFactory:
    """Tests for service factory functions."""

    @pytest.mark.asyncio
    async def test_get_strategy_monitor(self, mock_kite):
        """Test get_strategy_monitor creates instance."""
        await stop_strategy_monitor()  # Clear any existing

        with patch('app.services.strategy_monitor.get_market_data_service') as mock_md:
            with patch('app.services.strategy_monitor.get_condition_engine') as mock_ce:
                mock_md.return_value = MagicMock()
                mock_ce.return_value = MagicMock()

                monitor = await get_strategy_monitor(mock_kite)

                assert isinstance(monitor, StrategyMonitor)

        await stop_strategy_monitor()

    @pytest.mark.asyncio
    async def test_stop_strategy_monitor(self, mock_kite):
        """Test stop_strategy_monitor clears instance."""
        await stop_strategy_monitor()  # Clear any existing

        with patch('app.services.strategy_monitor.get_market_data_service') as mock_md:
            with patch('app.services.strategy_monitor.get_condition_engine') as mock_ce:
                mock_md.return_value = MagicMock()
                mock_ce.return_value = MagicMock()

                monitor = await get_strategy_monitor(mock_kite)
                await monitor.start()

                await stop_strategy_monitor()

                # Should be able to get new instance
                monitor2 = await get_strategy_monitor(mock_kite)
                assert monitor2 is not monitor

        await stop_strategy_monitor()


# =============================================================================
# EVALUATE AND EXECUTE TESTS
# =============================================================================

class TestEvaluateAndExecute:
    """Tests for _evaluate_and_execute method."""

    @pytest.mark.asyncio
    async def test_conditions_not_met(
        self, strategy_monitor, sample_strategy, mock_condition_engine, mock_ws_manager
    ):
        """Test when conditions are not met."""
        mock_db = AsyncMock()

        # Mock condition engine to return not met
        async def evaluate_not_met(strategy_id, entry_conditions, underlying, legs_config):
            return EvaluationResult(
                strategy_id=strategy_id,
                all_conditions_met=False,
                individual_results=[],
                evaluation_time=datetime.now()
            )

        strategy_monitor.condition_engine.evaluate = evaluate_not_met

        with patch.object(strategy_monitor, '_store_condition_eval', return_value=None):
            await strategy_monitor._evaluate_and_execute(mock_db, sample_strategy)

        # Order executor should not be called
        strategy_monitor.order_executor.execute_entry.assert_not_called()

        # Status should remain waiting
        assert sample_strategy.status == "waiting"

    @pytest.mark.asyncio
    async def test_conditions_met_execution_success(
        self, strategy_monitor, sample_strategy, mock_condition_engine, mock_ws_manager
    ):
        """Test successful execution when conditions are met."""
        mock_db = AsyncMock()

        # Mock successful execution
        async def mock_execute_entry(db, strategy, dry_run):
            return True, [
                OrderResult(success=True, order_id="1", leg_id="leg_1", executed_price=Decimal("100.0"))
            ]

        strategy_monitor.order_executor.execute_entry = mock_execute_entry

        with patch.object(strategy_monitor, '_store_condition_eval', return_value=None):
            with patch.object(strategy_monitor, '_get_user_settings', return_value=None):
                await strategy_monitor._evaluate_and_execute(mock_db, sample_strategy)

        # Status should change to active
        assert sample_strategy.status == "active"

    @pytest.mark.asyncio
    async def test_conditions_met_execution_failure(
        self, strategy_monitor, sample_strategy, mock_condition_engine, mock_ws_manager
    ):
        """Test status changes to error on execution failure."""
        mock_db = AsyncMock()

        # Mock failed execution
        async def mock_execute_entry(db, strategy, dry_run):
            return False, [
                OrderResult(success=False, error="Order failed", leg_id="leg_1")
            ]

        strategy_monitor.order_executor.execute_entry = mock_execute_entry

        with patch.object(strategy_monitor, '_store_condition_eval', return_value=None):
            with patch.object(strategy_monitor, '_get_user_settings', return_value=None):
                await strategy_monitor._evaluate_and_execute(mock_db, sample_strategy)

        # Status should change to error
        assert sample_strategy.status == "error"
        assert "error" in sample_strategy.runtime_state
