"""
Condition Engine Service Tests

Tests for app/services/condition_engine.py:
- evaluate() - Main evaluation method
- Variable resolution (TIME, SPOT, VIX, PREMIUM, WEEKDAY)
- Comparison operators (equals, greater_than, between, crosses_above, etc.)
- AND/OR logic
- Progress and distance calculations
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, time, date
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock, patch
from freezegun import freeze_time

from app.services.condition_engine import (
    ConditionEngine, ConditionResult, EvaluationResult,
    ConditionOperator, ConditionLogic,
    get_condition_engine, clear_condition_engines
)
from app.services.legacy.market_data import MarketDataService, SpotData


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_market_data():
    """Create mock MarketDataService."""
    mock = AsyncMock(spec=MarketDataService)
    mock.kite = MagicMock()
    mock.kite.access_token = "test_token"

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
                change=Decimal("-100.0"),
                change_pct=-0.19,
                timestamp=datetime.now()
            )
        }
        return spot_prices.get(underlying.upper(), spot_prices["NIFTY"])

    mock.get_spot_price = get_spot_price

    # Mock get_vix
    async def get_vix():
        return Decimal("15.50")

    mock.get_vix = get_vix

    # Mock get_ltp
    async def get_ltp(instruments):
        return {inst: Decimal("100.0") for inst in instruments}

    mock.get_ltp = get_ltp

    return mock


@pytest.fixture
def condition_engine(mock_market_data):
    """Create ConditionEngine with mock market data."""
    clear_condition_engines()
    return ConditionEngine(mock_market_data)


@pytest.fixture
def sample_legs_config():
    """Sample legs configuration."""
    return [
        {
            "id": "leg_1",
            "contract_type": "CE",
            "transaction_type": "SELL",
            "tradingsymbol": "NIFTY24DEC25000CE"
        },
        {
            "id": "leg_2",
            "contract_type": "PE",
            "transaction_type": "SELL",
            "tradingsymbol": "NIFTY24DEC24500PE"
        }
    ]


# =============================================================================
# EVALUATE METHOD TESTS
# =============================================================================

class TestEvaluate:
    """Tests for evaluate() method."""

    @pytest.mark.asyncio
    async def test_evaluate_empty_conditions(self, condition_engine):
        """Test evaluation with no conditions returns met."""
        entry_conditions = {
            "logic": "AND",
            "conditions": []
        }

        result = await condition_engine.evaluate(
            strategy_id=1,
            entry_conditions=entry_conditions,
            underlying="NIFTY",
            legs_config=[]
        )

        assert isinstance(result, EvaluationResult)
        assert result.all_conditions_met is True
        assert result.individual_results == []
        assert result.error is None

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")
    async def test_evaluate_and_logic_all_met(self, condition_engine, sample_legs_config):
        """Test AND logic when all conditions are met."""
        entry_conditions = {
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

        result = await condition_engine.evaluate(
            strategy_id=1,
            entry_conditions=entry_conditions,
            underlying="NIFTY",
            legs_config=sample_legs_config
        )

        assert result.all_conditions_met is True
        assert len(result.individual_results) == 2
        assert all(r.is_met for r in result.individual_results)

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")
    async def test_evaluate_and_logic_one_not_met(self, condition_engine, sample_legs_config):
        """Test AND logic when one condition is not met."""
        entry_conditions = {
            "logic": "AND",
            "conditions": [
                {
                    "id": "cond_1",
                    "enabled": True,
                    "variable": "TIME.CURRENT",
                    "operator": "greater_than",
                    "value": "09:20"  # Met at 10:30
                },
                {
                    "id": "cond_2",
                    "enabled": True,
                    "variable": "VIX.VALUE",
                    "operator": "less_than",
                    "value": 10  # Not met (VIX is 15.5)
                }
            ]
        }

        result = await condition_engine.evaluate(
            strategy_id=1,
            entry_conditions=entry_conditions,
            underlying="NIFTY",
            legs_config=sample_legs_config
        )

        assert result.all_conditions_met is False
        assert len(result.individual_results) == 2

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")
    async def test_evaluate_or_logic_one_met(self, condition_engine, sample_legs_config):
        """Test OR logic when at least one condition is met."""
        entry_conditions = {
            "logic": "OR",
            "conditions": [
                {
                    "id": "cond_1",
                    "enabled": True,
                    "variable": "TIME.CURRENT",
                    "operator": "greater_than",
                    "value": "12:00"  # Not met at 10:30
                },
                {
                    "id": "cond_2",
                    "enabled": True,
                    "variable": "VIX.VALUE",
                    "operator": "less_than",
                    "value": 20  # Met (VIX is 15.5)
                }
            ]
        }

        result = await condition_engine.evaluate(
            strategy_id=1,
            entry_conditions=entry_conditions,
            underlying="NIFTY",
            legs_config=sample_legs_config
        )

        assert result.all_conditions_met is True

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")
    async def test_evaluate_or_logic_none_met(self, condition_engine, sample_legs_config):
        """Test OR logic when no conditions are met."""
        entry_conditions = {
            "logic": "OR",
            "conditions": [
                {
                    "id": "cond_1",
                    "enabled": True,
                    "variable": "TIME.CURRENT",
                    "operator": "greater_than",
                    "value": "12:00"  # Not met at 10:30
                },
                {
                    "id": "cond_2",
                    "enabled": True,
                    "variable": "VIX.VALUE",
                    "operator": "greater_than",
                    "value": 20  # Not met (VIX is 15.5)
                }
            ]
        }

        result = await condition_engine.evaluate(
            strategy_id=1,
            entry_conditions=entry_conditions,
            underlying="NIFTY",
            legs_config=sample_legs_config
        )

        assert result.all_conditions_met is False

    @pytest.mark.asyncio
    async def test_evaluate_disabled_conditions_skipped(self, condition_engine, sample_legs_config):
        """Test disabled conditions are skipped."""
        entry_conditions = {
            "logic": "AND",
            "conditions": [
                {
                    "id": "cond_1",
                    "enabled": False,  # Disabled
                    "variable": "VIX.VALUE",
                    "operator": "less_than",
                    "value": 1  # Would fail if evaluated
                },
                {
                    "id": "cond_2",
                    "enabled": True,
                    "variable": "VIX.VALUE",
                    "operator": "less_than",
                    "value": 20  # Met
                }
            ]
        }

        result = await condition_engine.evaluate(
            strategy_id=1,
            entry_conditions=entry_conditions,
            underlying="NIFTY",
            legs_config=sample_legs_config
        )

        assert result.all_conditions_met is True
        assert len(result.individual_results) == 1  # Only enabled condition

    @pytest.mark.asyncio
    async def test_evaluate_error_handling(self, condition_engine, sample_legs_config):
        """Test evaluation handles errors gracefully."""
        entry_conditions = {
            "logic": "AND",
            "conditions": [
                {
                    "id": "cond_1",
                    "enabled": True,
                    "variable": "INVALID.VARIABLE",  # Unknown variable
                    "operator": "equals",
                    "value": 100
                }
            ]
        }

        result = await condition_engine.evaluate(
            strategy_id=1,
            entry_conditions=entry_conditions,
            underlying="NIFTY",
            legs_config=sample_legs_config
        )

        # Should not crash, but condition fails
        assert result.all_conditions_met is False
        assert len(result.individual_results) == 1
        assert result.individual_results[0].error is not None


# =============================================================================
# VARIABLE RESOLUTION TESTS
# =============================================================================

class TestVariableResolution:
    """Tests for _get_variable_value method."""

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")
    async def test_time_current(self, condition_engine):
        """Test TIME.CURRENT returns current time."""
        value = await condition_engine._get_variable_value(
            "TIME.CURRENT", "NIFTY", []
        )

        assert value == "10:30"

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")
    async def test_time_minutes_since_open(self, condition_engine):
        """Test TIME.MINUTES_SINCE_OPEN calculation."""
        value = await condition_engine._get_variable_value(
            "TIME.MINUTES_SINCE_OPEN", "NIFTY", []
        )

        # Market opens at 9:15, current is 10:30
        # 10:30 - 9:15 = 1h 15m = 75 minutes
        assert value == 75

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 09:00:00")
    async def test_time_minutes_before_open(self, condition_engine):
        """Test minutes since open before market opens."""
        value = await condition_engine._get_variable_value(
            "TIME.MINUTES_SINCE_OPEN", "NIFTY", []
        )

        # Before market open should return 0
        assert value == 0

    @pytest.mark.asyncio
    @freeze_time("2024-12-26 10:30:00")  # Thursday
    async def test_weekday(self, condition_engine):
        """Test WEEKDAY returns day abbreviation."""
        value = await condition_engine._get_variable_value(
            "WEEKDAY", "NIFTY", []
        )

        assert value == "THU"

    @pytest.mark.asyncio
    async def test_spot_price(self, condition_engine):
        """Test SPOT.{UNDERLYING} returns spot price."""
        value = await condition_engine._get_variable_value(
            "SPOT.NIFTY", "NIFTY", []
        )

        assert value == 25000.0

    @pytest.mark.asyncio
    async def test_spot_change_pct(self, condition_engine):
        """Test SPOT.{UNDERLYING}.CHANGE_PCT returns change percentage."""
        value = await condition_engine._get_variable_value(
            "SPOT.NIFTY.CHANGE_PCT", "NIFTY", []
        )

        assert value == 0.2

    @pytest.mark.asyncio
    async def test_vix_value(self, condition_engine):
        """Test VIX.VALUE returns VIX."""
        value = await condition_engine._get_variable_value(
            "VIX.VALUE", "NIFTY", []
        )

        assert value == 15.5

    @pytest.mark.asyncio
    async def test_premium_leg(self, condition_engine, sample_legs_config):
        """Test PREMIUM.{LEG_ID} returns leg premium."""
        value = await condition_engine._get_variable_value(
            "PREMIUM.leg_1", "NIFTY", sample_legs_config
        )

        assert value == 100.0  # From mock

    @pytest.mark.asyncio
    async def test_premium_unknown_leg(self, condition_engine, sample_legs_config):
        """Test PREMIUM with unknown leg ID."""
        value = await condition_engine._get_variable_value(
            "PREMIUM.unknown_leg", "NIFTY", sample_legs_config
        )

        assert value == 0.0

    @pytest.mark.asyncio
    async def test_unknown_variable(self, condition_engine):
        """Test unknown variable raises error."""
        with pytest.raises(ValueError) as exc_info:
            await condition_engine._get_variable_value(
                "UNKNOWN.VARIABLE", "NIFTY", []
            )

        assert "Unknown variable" in str(exc_info.value)


# =============================================================================
# COMPARISON OPERATOR TESTS
# =============================================================================

class TestComparisonOperators:
    """Tests for _compare_values method."""

    def test_equals_true(self, condition_engine):
        """Test equals operator - true case."""
        result = condition_engine._compare_values(
            current=100,
            target=100,
            operator=ConditionOperator.EQUALS,
            variable="TEST"
        )
        assert result is True

    def test_equals_false(self, condition_engine):
        """Test equals operator - false case."""
        result = condition_engine._compare_values(
            current=100,
            target=200,
            operator=ConditionOperator.EQUALS,
            variable="TEST"
        )
        assert result is False

    def test_not_equals_true(self, condition_engine):
        """Test not_equals operator - true case."""
        result = condition_engine._compare_values(
            current=100,
            target=200,
            operator=ConditionOperator.NOT_EQUALS,
            variable="TEST"
        )
        assert result is True

    def test_greater_than_true(self, condition_engine):
        """Test greater_than operator - true case."""
        result = condition_engine._compare_values(
            current=150,
            target=100,
            operator=ConditionOperator.GREATER_THAN,
            variable="TEST"
        )
        assert result is True

    def test_greater_than_false(self, condition_engine):
        """Test greater_than operator - false case."""
        result = condition_engine._compare_values(
            current=100,
            target=100,
            operator=ConditionOperator.GREATER_THAN,
            variable="TEST"
        )
        assert result is False

    def test_less_than_true(self, condition_engine):
        """Test less_than operator - true case."""
        result = condition_engine._compare_values(
            current=50,
            target=100,
            operator=ConditionOperator.LESS_THAN,
            variable="TEST"
        )
        assert result is True

    def test_greater_equal_true(self, condition_engine):
        """Test greater_equal operator - true case (equal)."""
        result = condition_engine._compare_values(
            current=100,
            target=100,
            operator=ConditionOperator.GREATER_EQUAL,
            variable="TEST"
        )
        assert result is True

    def test_less_equal_true(self, condition_engine):
        """Test less_equal operator - true case."""
        result = condition_engine._compare_values(
            current=100,
            target=100,
            operator=ConditionOperator.LESS_EQUAL,
            variable="TEST"
        )
        assert result is True

    def test_between_true(self, condition_engine):
        """Test between operator - true case."""
        result = condition_engine._compare_values(
            current=50,
            target=[0, 100],
            operator=ConditionOperator.BETWEEN,
            variable="TEST"
        )
        assert result is True

    def test_between_false(self, condition_engine):
        """Test between operator - false case."""
        result = condition_engine._compare_values(
            current=150,
            target=[0, 100],
            operator=ConditionOperator.BETWEEN,
            variable="TEST"
        )
        assert result is False

    def test_not_between_true(self, condition_engine):
        """Test not_between operator - true case."""
        result = condition_engine._compare_values(
            current=150,
            target=[0, 100],
            operator=ConditionOperator.NOT_BETWEEN,
            variable="TEST"
        )
        assert result is True

    def test_crosses_above_first_call(self, condition_engine):
        """Test crosses_above returns False on first call (no previous)."""
        result = condition_engine._compare_values(
            current=150,
            target=100,
            operator=ConditionOperator.CROSSES_ABOVE,
            variable="TEST"
        )
        assert result is False

    def test_crosses_above_true(self, condition_engine):
        """Test crosses_above when condition is met."""
        # First call to set previous value (below target)
        condition_engine._compare_values(
            current=80,
            target=100,
            operator=ConditionOperator.CROSSES_ABOVE,
            variable="TEST_CROSS"
        )

        # Second call (crosses above)
        result = condition_engine._compare_values(
            current=120,
            target=100,
            operator=ConditionOperator.CROSSES_ABOVE,
            variable="TEST_CROSS"
        )
        assert result is True

    def test_crosses_above_false(self, condition_engine):
        """Test crosses_above when no crossing occurs."""
        # First call (already above target)
        condition_engine._compare_values(
            current=120,
            target=100,
            operator=ConditionOperator.CROSSES_ABOVE,
            variable="TEST_NO_CROSS"
        )

        # Second call (still above, no crossing)
        result = condition_engine._compare_values(
            current=130,
            target=100,
            operator=ConditionOperator.CROSSES_ABOVE,
            variable="TEST_NO_CROSS"
        )
        assert result is False

    def test_crosses_below_true(self, condition_engine):
        """Test crosses_below when condition is met."""
        # First call (above target)
        condition_engine._compare_values(
            current=120,
            target=100,
            operator=ConditionOperator.CROSSES_BELOW,
            variable="TEST_CROSS_BELOW"
        )

        # Second call (crosses below)
        result = condition_engine._compare_values(
            current=80,
            target=100,
            operator=ConditionOperator.CROSSES_BELOW,
            variable="TEST_CROSS_BELOW"
        )
        assert result is True

    def test_time_comparison(self, condition_engine):
        """Test time string comparisons."""
        result = condition_engine._compare_values(
            current="10:30",
            target="09:20",
            operator=ConditionOperator.GREATER_THAN,
            variable="TIME.CURRENT"
        )
        assert result is True

    def test_string_to_number_conversion(self, condition_engine):
        """Test string target is converted to number."""
        result = condition_engine._compare_values(
            current=150.0,
            target="100",
            operator=ConditionOperator.GREATER_THAN,
            variable="TEST"
        )
        assert result is True


# =============================================================================
# PROGRESS CALCULATION TESTS
# =============================================================================

class TestProgressCalculation:
    """Tests for _calculate_progress method."""

    def test_progress_greater_than(self, condition_engine):
        """Test progress for greater_than operator."""
        # Current is 50% of target
        progress = condition_engine._calculate_progress(
            current=50,
            target=100,
            operator="greater_than",
            variable="TEST"
        )
        assert progress == 50.0

    def test_progress_greater_than_exceeded(self, condition_engine):
        """Test progress caps at 100%."""
        progress = condition_engine._calculate_progress(
            current=150,
            target=100,
            operator="greater_than",
            variable="TEST"
        )
        assert progress == 100.0

    def test_progress_less_than(self, condition_engine):
        """Test progress for less_than operator."""
        # Target is 50, current is 100 (target/current = 50%)
        progress = condition_engine._calculate_progress(
            current=100,
            target=50,
            operator="less_than",
            variable="TEST"
        )
        assert progress == 50.0

    def test_progress_time_condition(self, condition_engine):
        """Test progress for time conditions."""
        # Market opens 9:15 (555 mins)
        # Target 10:00 (600 mins) = 45 mins from open
        # Current 9:45 (585 mins) = 30 mins from open
        # Progress = 30/45 * 100 = 66.67%
        progress = condition_engine._calculate_progress(
            current="09:45",
            target="10:00",
            operator="greater_than",
            variable="TIME.CURRENT"
        )
        assert progress is not None
        assert 66 <= progress <= 67


# =============================================================================
# DISTANCE CALCULATION TESTS
# =============================================================================

class TestDistanceCalculation:
    """Tests for _calculate_distance method."""

    def test_distance_time_future(self, condition_engine):
        """Test distance for future time."""
        distance = condition_engine._calculate_distance(
            current="09:30",
            target="10:45",
            operator="greater_than",
            variable="TIME.CURRENT"
        )
        assert distance == "1h 15m"

    def test_distance_time_minutes_only(self, condition_engine):
        """Test distance for time less than an hour away."""
        distance = condition_engine._calculate_distance(
            current="10:00",
            target="10:30",
            operator="greater_than",
            variable="TIME.CURRENT"
        )
        assert distance == "30m"

    def test_distance_time_now(self, condition_engine):
        """Test distance when time is reached."""
        distance = condition_engine._calculate_distance(
            current="10:30",
            target="10:30",
            operator="greater_than",
            variable="TIME.CURRENT"
        )
        assert distance == "Now"

    def test_distance_time_passed(self, condition_engine):
        """Test distance when time has passed."""
        distance = condition_engine._calculate_distance(
            current="11:00",
            target="10:30",
            operator="greater_than",
            variable="TIME.CURRENT"
        )
        assert distance == "Passed"

    def test_distance_numeric_small(self, condition_engine):
        """Test distance for small numeric difference."""
        distance = condition_engine._calculate_distance(
            current=99.5,
            target=100.0,
            operator="greater_than",
            variable="TEST"
        )
        assert distance == "+0.50"

    def test_distance_numeric_medium(self, condition_engine):
        """Test distance for medium numeric difference."""
        distance = condition_engine._calculate_distance(
            current=75,
            target=100,
            operator="greater_than",
            variable="TEST"
        )
        assert distance == "+25.0"

    def test_distance_numeric_large(self, condition_engine):
        """Test distance for large numeric difference."""
        distance = condition_engine._calculate_distance(
            current=24500,
            target=25000,
            operator="greater_than",
            variable="TEST"
        )
        assert distance == "+500"


# =============================================================================
# TIME PARSING TESTS
# =============================================================================

class TestTimeParsing:
    """Tests for _parse_time method."""

    def test_parse_time_valid(self, condition_engine):
        """Test parsing valid time string."""
        minutes = condition_engine._parse_time("10:30")
        assert minutes == 10 * 60 + 30  # 630

    def test_parse_time_with_seconds(self, condition_engine):
        """Test parsing time with seconds (ignored)."""
        minutes = condition_engine._parse_time("10:30:45")
        assert minutes == 10 * 60 + 30  # 630

    def test_parse_time_integer_input(self, condition_engine):
        """Test parsing integer input (passthrough)."""
        minutes = condition_engine._parse_time(630)
        assert minutes == 630

    def test_parse_time_empty_string(self, condition_engine):
        """Test parsing empty string."""
        minutes = condition_engine._parse_time("")
        assert minutes == 0

    def test_parse_time_none(self, condition_engine):
        """Test parsing None value."""
        minutes = condition_engine._parse_time(None)
        assert minutes == 0


# =============================================================================
# SERVICE FACTORY TESTS
# =============================================================================

class TestServiceFactory:
    """Tests for service factory functions."""

    def test_get_condition_engine_creates_new(self, mock_market_data):
        """Test get_condition_engine creates new instance."""
        clear_condition_engines()

        engine = get_condition_engine(mock_market_data)

        assert isinstance(engine, ConditionEngine)
        assert engine.market_data == mock_market_data

    def test_get_condition_engine_returns_cached(self, mock_market_data):
        """Test get_condition_engine returns cached instance."""
        clear_condition_engines()

        engine1 = get_condition_engine(mock_market_data)
        engine2 = get_condition_engine(mock_market_data)

        assert engine1 is engine2

    def test_clear_condition_engines(self, mock_market_data):
        """Test clear_condition_engines clears all instances."""
        get_condition_engine(mock_market_data)
        clear_condition_engines()

        # Should create new instance
        engine = get_condition_engine(mock_market_data)
        assert isinstance(engine, ConditionEngine)


# =============================================================================
# CLEAR PREVIOUS VALUES TESTS
# =============================================================================

class TestClearPreviousValues:
    """Tests for clear_previous_values method."""

    def test_clear_previous_values(self, condition_engine):
        """Test clearing previous values for crosses operators."""
        # Set some previous values
        condition_engine._previous_values["TEST1"] = 100
        condition_engine._previous_values["TEST2"] = 200

        condition_engine.clear_previous_values()

        assert len(condition_engine._previous_values) == 0


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestDataClasses:
    """Tests for data classes."""

    def test_condition_result_creation(self):
        """Test ConditionResult dataclass."""
        result = ConditionResult(
            condition_id="cond_1",
            variable="TIME.CURRENT",
            operator="greater_than",
            target_value="09:20",
            current_value="10:30",
            is_met=True,
            progress_pct=100.0,
            distance_to_trigger="Passed"
        )

        assert result.condition_id == "cond_1"
        assert result.is_met is True
        assert result.error is None

    def test_condition_result_with_error(self):
        """Test ConditionResult with error."""
        result = ConditionResult(
            condition_id="cond_1",
            variable="INVALID",
            operator="equals",
            target_value=100,
            current_value=None,
            is_met=False,
            error="Unknown variable"
        )

        assert result.is_met is False
        assert result.error == "Unknown variable"

    def test_evaluation_result_creation(self):
        """Test EvaluationResult dataclass."""
        result = EvaluationResult(
            strategy_id=1,
            all_conditions_met=True,
            individual_results=[],
            evaluation_time=datetime.now()
        )

        assert result.strategy_id == 1
        assert result.all_conditions_met is True
        assert result.error is None


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Tests for enum classes."""

    def test_condition_operator_values(self):
        """Test ConditionOperator enum values."""
        assert ConditionOperator.EQUALS.value == "equals"
        assert ConditionOperator.GREATER_THAN.value == "greater_than"
        assert ConditionOperator.BETWEEN.value == "between"
        assert ConditionOperator.CROSSES_ABOVE.value == "crosses_above"

    def test_condition_logic_values(self):
        """Test ConditionLogic enum values."""
        assert ConditionLogic.AND.value == "AND"
        assert ConditionLogic.OR.value == "OR"
