"""
AutoPilot Schema Tests

Tests for Pydantic schemas:
- StrikeSelection modes
- LegConfig validation
- EntryConditions logic
- StrategyCreateRequest validation
- StrategyUpdateRequest partial updates
- RiskSettings fields
- OrderSettings fields
- ScheduleConfig fields
"""

import pytest
from datetime import date
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.autopilot import (
    # Enums
    StrategyStatus, Underlying, PositionType, ContractType,
    TransactionType, OrderType, ExpiryType, ExecutionStyle,
    ConditionOperator, ConditionLogic,
    # Nested models
    StrikeSelection, LegConfig, Condition, EntryConditions,
    SlippageProtection, OrderSettings, TrailingStop, RiskSettings,
    ScheduleConfig,
    # Request schemas
    StrategyCreateRequest, StrategyUpdateRequest, ActivateRequest,
    ExitRequest, CloneRequest, UserSettingsUpdateRequest,
    # Response schemas
    StrategyListItem, StrategyResponse, UserSettingsResponse,
    RiskMetrics, DashboardSummary, DataResponse, PaginatedResponse
)


# =============================================================================
# STRIKE SELECTION TESTS
# =============================================================================

class TestStrikeSelection:
    """Tests for StrikeSelection schema."""

    def test_strike_selection_atm_offset(self):
        """Test ATM offset mode."""
        ss = StrikeSelection(mode="atm_offset", offset=2)
        assert ss.mode == "atm_offset"
        assert ss.offset == 2
        assert ss.fixed_strike is None
        assert ss.target_premium is None
        assert ss.target_delta is None

    def test_strike_selection_atm_offset_negative(self):
        """Test ATM offset with negative value."""
        ss = StrikeSelection(mode="atm_offset", offset=-3)
        assert ss.mode == "atm_offset"
        assert ss.offset == -3

    def test_strike_selection_fixed(self):
        """Test fixed strike mode."""
        ss = StrikeSelection(mode="fixed", fixed_strike=Decimal("25000"))
        assert ss.mode == "fixed"
        assert ss.fixed_strike == Decimal("25000")
        assert ss.offset is None

    def test_strike_selection_premium_based(self):
        """Test premium based mode."""
        ss = StrikeSelection(mode="premium_based", target_premium=Decimal("100.50"))
        assert ss.mode == "premium_based"
        assert ss.target_premium == Decimal("100.50")

    def test_strike_selection_delta_based(self):
        """Test delta based mode."""
        ss = StrikeSelection(mode="delta_based", target_delta=0.3)
        assert ss.mode == "delta_based"
        assert ss.target_delta == 0.3

    def test_strike_selection_missing_mode(self):
        """Test that mode is required."""
        with pytest.raises(ValidationError) as exc_info:
            StrikeSelection()
        assert "mode" in str(exc_info.value)


# =============================================================================
# LEG CONFIG TESTS
# =============================================================================

class TestLegConfig:
    """Tests for LegConfig schema."""

    def test_leg_config_valid(self):
        """Test valid leg configuration."""
        leg = LegConfig(
            id="leg_1",
            contract_type=ContractType.CE,
            transaction_type=TransactionType.SELL,
            strike_selection=StrikeSelection(mode="atm_offset", offset=2),
            quantity_multiplier=1,
            execution_order=1
        )
        assert leg.id == "leg_1"
        assert leg.contract_type == ContractType.CE
        assert leg.transaction_type == TransactionType.SELL
        assert leg.strike_selection.mode == "atm_offset"
        assert leg.quantity_multiplier == 1
        assert leg.execution_order == 1

    def test_leg_config_pe_buy(self):
        """Test PE buy leg."""
        leg = LegConfig(
            id="leg_pe_buy",
            contract_type=ContractType.PE,
            transaction_type=TransactionType.BUY,
            strike_selection=StrikeSelection(mode="atm_offset", offset=-4)
        )
        assert leg.contract_type == ContractType.PE
        assert leg.transaction_type == TransactionType.BUY

    def test_leg_config_fut(self):
        """Test FUT contract type."""
        leg = LegConfig(
            id="leg_fut",
            contract_type=ContractType.FUT,
            transaction_type=TransactionType.BUY,
            strike_selection=StrikeSelection(mode="fixed", fixed_strike=None)
        )
        assert leg.contract_type == ContractType.FUT

    def test_leg_config_invalid_contract_type(self):
        """Test invalid contract type fails."""
        with pytest.raises(ValidationError) as exc_info:
            LegConfig(
                id="leg_invalid",
                contract_type="INVALID",  # Invalid
                transaction_type=TransactionType.SELL,
                strike_selection=StrikeSelection(mode="atm_offset", offset=0)
            )
        assert "contract_type" in str(exc_info.value)

    def test_leg_config_missing_required_fields(self):
        """Test missing required fields."""
        with pytest.raises(ValidationError):
            LegConfig(
                id="leg_1"
                # Missing contract_type, transaction_type, strike_selection
            )

    def test_leg_config_defaults(self):
        """Test default values."""
        leg = LegConfig(
            id="leg_defaults",
            contract_type=ContractType.CE,
            transaction_type=TransactionType.SELL,
            strike_selection=StrikeSelection(mode="atm_offset", offset=0)
        )
        assert leg.quantity_multiplier == 1
        assert leg.execution_order == 1


# =============================================================================
# CONDITION TESTS
# =============================================================================

class TestCondition:
    """Tests for Condition schema."""

    def test_condition_schema(self):
        """Test valid condition."""
        cond = Condition(
            id="cond_1",
            enabled=True,
            variable="TIME.CURRENT",
            operator=ConditionOperator.greater_than,
            value="09:20"
        )
        assert cond.id == "cond_1"
        assert cond.enabled is True
        assert cond.variable == "TIME.CURRENT"
        assert cond.operator == ConditionOperator.greater_than
        assert cond.value == "09:20"

    def test_condition_numeric_value(self):
        """Test condition with numeric value."""
        cond = Condition(
            id="cond_vix",
            variable="VIX.VALUE",
            operator=ConditionOperator.less_than,
            value=20
        )
        assert cond.value == 20

    def test_condition_float_value(self):
        """Test condition with float value."""
        cond = Condition(
            id="cond_spot",
            variable="SPOT.NIFTY.CHANGE_PCT",
            operator=ConditionOperator.between,
            value=[-1.5, 1.5]
        )
        assert cond.value == [-1.5, 1.5]

    def test_condition_disabled(self):
        """Test disabled condition."""
        cond = Condition(
            id="cond_disabled",
            enabled=False,
            variable="TIME.CURRENT",
            operator=ConditionOperator.equals,
            value="10:00"
        )
        assert cond.enabled is False

    def test_condition_default_enabled(self):
        """Test condition enabled by default."""
        cond = Condition(
            id="cond_default",
            variable="VIX.VALUE",
            operator=ConditionOperator.less_than,
            value=25
        )
        assert cond.enabled is True

    def test_condition_all_operators(self):
        """Test all operator values are valid."""
        operators = [
            ConditionOperator.equals,
            ConditionOperator.not_equals,
            ConditionOperator.greater_than,
            ConditionOperator.less_than,
            ConditionOperator.between,
            ConditionOperator.crosses_above,
            ConditionOperator.crosses_below
        ]
        for op in operators:
            cond = Condition(
                id=f"cond_{op.value}",
                variable="TEST",
                operator=op,
                value=100
            )
            assert cond.operator == op


# =============================================================================
# ENTRY CONDITIONS TESTS
# =============================================================================

class TestEntryConditions:
    """Tests for EntryConditions schema."""

    def test_entry_conditions_and_logic(self):
        """Test AND logic entry conditions."""
        ec = EntryConditions(
            logic=ConditionLogic.AND,
            conditions=[
                Condition(id="c1", variable="TIME.CURRENT", operator=ConditionOperator.greater_than, value="09:20"),
                Condition(id="c2", variable="VIX.VALUE", operator=ConditionOperator.less_than, value=20)
            ]
        )
        assert ec.logic == ConditionLogic.AND
        assert len(ec.conditions) == 2

    def test_entry_conditions_or_logic(self):
        """Test OR logic entry conditions."""
        ec = EntryConditions(
            logic=ConditionLogic.OR,
            conditions=[
                Condition(id="c1", variable="VIX.VALUE", operator=ConditionOperator.less_than, value=15),
                Condition(id="c2", variable="SPOT.NIFTY.CHANGE_PCT", operator=ConditionOperator.between, value=[-0.5, 0.5])
            ]
        )
        assert ec.logic == ConditionLogic.OR
        assert len(ec.conditions) == 2

    def test_entry_conditions_defaults(self):
        """Test default values."""
        ec = EntryConditions()
        assert ec.logic == ConditionLogic.AND
        assert ec.conditions == []
        assert ec.custom_expression is None

    def test_entry_conditions_custom_expression(self):
        """Test custom expression field."""
        ec = EntryConditions(
            logic=ConditionLogic.AND,
            custom_expression="(c1 AND c2) OR c3",
            conditions=[]
        )
        assert ec.custom_expression == "(c1 AND c2) OR c3"

    def test_entry_conditions_empty_conditions(self):
        """Test empty conditions list."""
        ec = EntryConditions(logic=ConditionLogic.AND, conditions=[])
        assert ec.conditions == []


# =============================================================================
# ORDER SETTINGS TESTS
# =============================================================================

class TestOrderSettings:
    """Tests for OrderSettings schema."""

    def test_order_settings_all_fields(self):
        """Test all order settings fields."""
        os = OrderSettings(
            order_type=OrderType.LIMIT,
            execution_style=ExecutionStyle.sequential,
            leg_sequence=["leg_2", "leg_3", "leg_1", "leg_4"],
            delay_between_legs=3,
            slippage_protection=SlippageProtection(
                enabled=True,
                max_per_leg_pct=1.5,
                max_total_pct=4.0,
                on_exceed="cancel",
                max_retries=2
            ),
            on_leg_failure="exit_all"
        )
        assert os.order_type == OrderType.LIMIT
        assert os.execution_style == ExecutionStyle.sequential
        assert os.leg_sequence == ["leg_2", "leg_3", "leg_1", "leg_4"]
        assert os.delay_between_legs == 3
        assert os.slippage_protection.enabled is True
        assert os.slippage_protection.max_per_leg_pct == 1.5
        assert os.on_leg_failure == "exit_all"

    def test_order_settings_defaults(self):
        """Test default values."""
        os = OrderSettings()
        assert os.order_type == OrderType.MARKET
        assert os.execution_style == ExecutionStyle.sequential
        assert os.leg_sequence == []
        assert os.delay_between_legs == 2
        assert os.on_leg_failure == "stop"

    def test_slippage_protection_defaults(self):
        """Test slippage protection defaults."""
        sp = SlippageProtection()
        assert sp.enabled is True
        assert sp.max_per_leg_pct == 2.0
        assert sp.max_total_pct == 5.0
        assert sp.on_exceed == "retry"
        assert sp.max_retries == 3

    def test_order_settings_simultaneous(self):
        """Test simultaneous execution style."""
        os = OrderSettings(
            execution_style=ExecutionStyle.simultaneous,
            delay_between_legs=0
        )
        assert os.execution_style == ExecutionStyle.simultaneous

    def test_order_settings_with_delay(self):
        """Test with_delay execution style."""
        os = OrderSettings(
            execution_style=ExecutionStyle.with_delay,
            delay_between_legs=5
        )
        assert os.execution_style == ExecutionStyle.with_delay
        assert os.delay_between_legs == 5


# =============================================================================
# RISK SETTINGS TESTS
# =============================================================================

class TestRiskSettings:
    """Tests for RiskSettings schema."""

    def test_risk_settings_all_fields(self):
        """Test all risk settings fields."""
        rs = RiskSettings(
            max_loss=Decimal("5000"),
            max_loss_pct=50.0,
            trailing_stop=TrailingStop(
                enabled=True,
                trigger_profit=Decimal("3000"),
                trail_amount=Decimal("1000")
            ),
            max_margin=Decimal("100000"),
            time_stop="15:15"
        )
        assert rs.max_loss == Decimal("5000")
        assert rs.max_loss_pct == 50.0
        assert rs.trailing_stop.enabled is True
        assert rs.trailing_stop.trigger_profit == Decimal("3000")
        assert rs.trailing_stop.trail_amount == Decimal("1000")
        assert rs.max_margin == Decimal("100000")
        assert rs.time_stop == "15:15"

    def test_risk_settings_defaults(self):
        """Test default values."""
        rs = RiskSettings()
        assert rs.max_loss is None
        assert rs.max_loss_pct is None
        assert rs.trailing_stop.enabled is False
        assert rs.max_margin is None
        assert rs.time_stop is None

    def test_trailing_stop_defaults(self):
        """Test trailing stop defaults."""
        ts = TrailingStop()
        assert ts.enabled is False
        assert ts.trigger_profit is None
        assert ts.trail_amount is None


# =============================================================================
# SCHEDULE CONFIG TESTS
# =============================================================================

class TestScheduleConfig:
    """Tests for ScheduleConfig schema."""

    def test_schedule_config(self):
        """Test schedule configuration."""
        sc = ScheduleConfig(
            activation_mode="scheduled",
            active_days=["MON", "WED", "FRI"],
            start_time="09:30",
            end_time="15:00",
            expiry_days_only=True,
            date_range={"start": "2024-01-01", "end": "2024-03-31"}
        )
        assert sc.activation_mode == "scheduled"
        assert sc.active_days == ["MON", "WED", "FRI"]
        assert sc.start_time == "09:30"
        assert sc.end_time == "15:00"
        assert sc.expiry_days_only is True
        assert sc.date_range["start"] == "2024-01-01"

    def test_schedule_config_defaults(self):
        """Test default values."""
        sc = ScheduleConfig()
        assert sc.activation_mode == "always"
        assert sc.active_days == ["MON", "TUE", "WED", "THU", "FRI"]
        assert sc.start_time == "09:15"
        assert sc.end_time == "15:30"
        assert sc.expiry_days_only is False
        assert sc.date_range is None


# =============================================================================
# STRATEGY CREATE REQUEST TESTS
# =============================================================================

class TestStrategyCreateRequest:
    """Tests for StrategyCreateRequest schema."""

    def test_strategy_create_request_valid(self):
        """Test full valid request."""
        request = StrategyCreateRequest(
            name="Iron Condor Strategy",
            description="Weekly Iron Condor on NIFTY",
            underlying=Underlying.NIFTY,
            expiry_type=ExpiryType.current_week,
            expiry_date=None,
            lots=2,
            position_type=PositionType.intraday,
            legs_config=[
                LegConfig(
                    id="leg_1",
                    contract_type=ContractType.PE,
                    transaction_type=TransactionType.BUY,
                    strike_selection=StrikeSelection(mode="atm_offset", offset=-4)
                ),
                LegConfig(
                    id="leg_2",
                    contract_type=ContractType.PE,
                    transaction_type=TransactionType.SELL,
                    strike_selection=StrikeSelection(mode="atm_offset", offset=-2)
                ),
                LegConfig(
                    id="leg_3",
                    contract_type=ContractType.CE,
                    transaction_type=TransactionType.SELL,
                    strike_selection=StrikeSelection(mode="atm_offset", offset=2)
                ),
                LegConfig(
                    id="leg_4",
                    contract_type=ContractType.CE,
                    transaction_type=TransactionType.BUY,
                    strike_selection=StrikeSelection(mode="atm_offset", offset=4)
                )
            ],
            entry_conditions=EntryConditions(
                logic=ConditionLogic.AND,
                conditions=[
                    Condition(id="c1", variable="TIME.CURRENT", operator=ConditionOperator.greater_than, value="09:20")
                ]
            ),
            adjustment_rules=[],
            order_settings=OrderSettings(),
            risk_settings=RiskSettings(max_loss=Decimal("5000")),
            schedule_config=ScheduleConfig(),
            priority=50
        )
        assert request.name == "Iron Condor Strategy"
        assert request.underlying == Underlying.NIFTY
        assert request.lots == 2
        assert len(request.legs_config) == 4
        assert request.priority == 50

    def test_strategy_create_request_missing_fields(self):
        """Test validation error for missing fields."""
        with pytest.raises(ValidationError) as exc_info:
            StrategyCreateRequest(
                name="Incomplete Strategy"
                # Missing: underlying, legs_config, entry_conditions
            )
        errors = exc_info.value.errors()
        error_fields = {e['loc'][0] for e in errors}
        assert 'underlying' in error_fields
        assert 'legs_config' in error_fields
        assert 'entry_conditions' in error_fields

    def test_strategy_create_request_invalid_underlying(self):
        """Test invalid underlying fails."""
        with pytest.raises(ValidationError) as exc_info:
            StrategyCreateRequest(
                name="Invalid Strategy",
                underlying="INVALID_INDEX",
                legs_config=[
                    LegConfig(
                        id="leg_1",
                        contract_type=ContractType.CE,
                        transaction_type=TransactionType.SELL,
                        strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                    )
                ],
                entry_conditions=EntryConditions()
            )
        assert "underlying" in str(exc_info.value)

    def test_strategy_create_request_name_too_long(self):
        """Test name length validation."""
        with pytest.raises(ValidationError) as exc_info:
            StrategyCreateRequest(
                name="A" * 101,  # Max is 100
                underlying=Underlying.NIFTY,
                legs_config=[
                    LegConfig(
                        id="leg_1",
                        contract_type=ContractType.CE,
                        transaction_type=TransactionType.SELL,
                        strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                    )
                ],
                entry_conditions=EntryConditions()
            )
        assert "name" in str(exc_info.value)

    def test_strategy_create_request_lots_validation(self):
        """Test lots min/max validation."""
        # Too few lots
        with pytest.raises(ValidationError):
            StrategyCreateRequest(
                name="Test",
                underlying=Underlying.NIFTY,
                lots=0,  # Min is 1
                legs_config=[
                    LegConfig(
                        id="leg_1",
                        contract_type=ContractType.CE,
                        transaction_type=TransactionType.SELL,
                        strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                    )
                ],
                entry_conditions=EntryConditions()
            )

        # Too many lots
        with pytest.raises(ValidationError):
            StrategyCreateRequest(
                name="Test",
                underlying=Underlying.NIFTY,
                lots=51,  # Max is 50
                legs_config=[
                    LegConfig(
                        id="leg_1",
                        contract_type=ContractType.CE,
                        transaction_type=TransactionType.SELL,
                        strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                    )
                ],
                entry_conditions=EntryConditions()
            )

    def test_strategy_create_request_unique_leg_ids(self):
        """Test leg IDs must be unique."""
        with pytest.raises(ValidationError) as exc_info:
            StrategyCreateRequest(
                name="Duplicate Legs",
                underlying=Underlying.NIFTY,
                legs_config=[
                    LegConfig(
                        id="leg_1",  # Duplicate
                        contract_type=ContractType.CE,
                        transaction_type=TransactionType.SELL,
                        strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                    ),
                    LegConfig(
                        id="leg_1",  # Duplicate
                        contract_type=ContractType.PE,
                        transaction_type=TransactionType.SELL,
                        strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                    )
                ],
                entry_conditions=EntryConditions()
            )
        assert "unique" in str(exc_info.value).lower()

    def test_strategy_create_request_empty_legs(self):
        """Test empty legs_config fails."""
        with pytest.raises(ValidationError):
            StrategyCreateRequest(
                name="No Legs",
                underlying=Underlying.NIFTY,
                legs_config=[],  # min_length is 1
                entry_conditions=EntryConditions()
            )

    def test_strategy_create_request_priority_validation(self):
        """Test priority min/max validation."""
        # Valid priority
        request = StrategyCreateRequest(
            name="Priority Test",
            underlying=Underlying.NIFTY,
            legs_config=[
                LegConfig(
                    id="leg_1",
                    contract_type=ContractType.CE,
                    transaction_type=TransactionType.SELL,
                    strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                )
            ],
            entry_conditions=EntryConditions(),
            priority=500
        )
        assert request.priority == 500

        # Invalid priority (too high)
        with pytest.raises(ValidationError):
            StrategyCreateRequest(
                name="Invalid Priority",
                underlying=Underlying.NIFTY,
                legs_config=[
                    LegConfig(
                        id="leg_1",
                        contract_type=ContractType.CE,
                        transaction_type=TransactionType.SELL,
                        strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                    )
                ],
                entry_conditions=EntryConditions(),
                priority=1001  # Max is 1000
            )


# =============================================================================
# STRATEGY UPDATE REQUEST TESTS
# =============================================================================

class TestStrategyUpdateRequest:
    """Tests for StrategyUpdateRequest schema."""

    def test_strategy_update_request_partial(self):
        """Test partial update works."""
        request = StrategyUpdateRequest(
            name="Updated Name"
        )
        assert request.name == "Updated Name"
        assert request.description is None
        assert request.lots is None
        assert request.legs_config is None

    def test_strategy_update_request_multiple_fields(self):
        """Test updating multiple fields."""
        request = StrategyUpdateRequest(
            name="New Name",
            description="New description",
            lots=3,
            priority=75
        )
        assert request.name == "New Name"
        assert request.description == "New description"
        assert request.lots == 3
        assert request.priority == 75

    def test_strategy_update_request_legs_config(self):
        """Test updating legs_config."""
        request = StrategyUpdateRequest(
            legs_config=[
                LegConfig(
                    id="new_leg",
                    contract_type=ContractType.CE,
                    transaction_type=TransactionType.SELL,
                    strike_selection=StrikeSelection(mode="atm_offset", offset=0)
                )
            ]
        )
        assert len(request.legs_config) == 1
        assert request.legs_config[0].id == "new_leg"

    def test_strategy_update_request_empty(self):
        """Test empty update is valid."""
        request = StrategyUpdateRequest()
        assert request.name is None
        assert request.description is None
        assert request.lots is None


# =============================================================================
# OTHER REQUEST SCHEMAS TESTS
# =============================================================================

class TestOtherRequestSchemas:
    """Tests for other request schemas."""

    def test_activate_request(self):
        """Test ActivateRequest schema."""
        request = ActivateRequest(confirm=True, paper_trading=False)
        assert request.confirm is True
        assert request.paper_trading is False

        # Test defaults
        request = ActivateRequest()
        assert request.confirm is True
        assert request.paper_trading is False

    def test_activate_request_paper_trading(self):
        """Test ActivateRequest with paper trading."""
        request = ActivateRequest(paper_trading=True)
        assert request.paper_trading is True

    def test_exit_request(self):
        """Test ExitRequest schema."""
        request = ExitRequest(
            confirm=True,
            exit_type="limit",
            reason="Target reached"
        )
        assert request.confirm is True
        assert request.exit_type == "limit"
        assert request.reason == "Target reached"

        # Test defaults
        request = ExitRequest()
        assert request.exit_type == "market"
        assert request.reason is None

    def test_clone_request(self):
        """Test CloneRequest schema."""
        request = CloneRequest(
            new_name="My Clone",
            reset_schedule=False
        )
        assert request.new_name == "My Clone"
        assert request.reset_schedule is False

        # Test defaults
        request = CloneRequest()
        assert request.new_name is None
        assert request.reset_schedule is True


# =============================================================================
# USER SETTINGS UPDATE REQUEST TESTS
# =============================================================================

class TestUserSettingsUpdateRequest:
    """Tests for UserSettingsUpdateRequest schema."""

    def test_user_settings_update_partial(self):
        """Test partial settings update."""
        request = UserSettingsUpdateRequest(
            daily_loss_limit=Decimal("30000")
        )
        assert request.daily_loss_limit == Decimal("30000")
        assert request.per_strategy_loss_limit is None

    def test_user_settings_update_all_fields(self):
        """Test updating all fields."""
        request = UserSettingsUpdateRequest(
            daily_loss_limit=Decimal("25000"),
            per_strategy_loss_limit=Decimal("12500"),
            max_capital_deployed=Decimal("750000"),
            max_active_strategies=5,
            no_trade_first_minutes=10,
            no_trade_last_minutes=10,
            cooldown_after_loss=True,
            cooldown_minutes=60,
            cooldown_threshold=Decimal("7500"),
            paper_trading_mode=True,
            show_advanced_features=True
        )
        assert request.daily_loss_limit == Decimal("25000")
        assert request.max_active_strategies == 5
        assert request.cooldown_minutes == 60
        assert request.paper_trading_mode is True

    def test_user_settings_update_validation(self):
        """Test field validation."""
        # max_active_strategies max is 10
        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(max_active_strategies=11)

        # cooldown_minutes max is 240
        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(cooldown_minutes=300)

        # no_trade_first_minutes max is 60
        with pytest.raises(ValidationError):
            UserSettingsUpdateRequest(no_trade_first_minutes=61)


# =============================================================================
# RESPONSE SCHEMAS TESTS
# =============================================================================

class TestResponseSchemas:
    """Tests for response schemas."""

    def test_data_response(self):
        """Test DataResponse schema."""
        response = DataResponse(
            status="success",
            message="Operation completed",
            data={"key": "value"}
        )
        assert response.status == "success"
        assert response.message == "Operation completed"
        assert response.data == {"key": "value"}
        assert response.timestamp is not None

    def test_paginated_response(self):
        """Test PaginatedResponse schema."""
        response = PaginatedResponse(
            data=[{"id": 1}, {"id": 2}],
            total=50,
            page=1,
            page_size=20,
            total_pages=3,
            has_next=True,
            has_prev=False
        )
        assert len(response.data) == 2
        assert response.total == 50
        assert response.page == 1
        assert response.has_next is True
        assert response.has_prev is False

    def test_risk_metrics(self):
        """Test RiskMetrics schema."""
        metrics = RiskMetrics(
            daily_loss_limit=Decimal("20000"),
            daily_loss_used=Decimal("5000"),
            daily_loss_pct=25.0,
            max_capital=Decimal("500000"),
            capital_used=Decimal("100000"),
            capital_pct=20.0,
            max_active_strategies=3,
            active_strategies_count=2,
            status="safe"
        )
        assert metrics.daily_loss_pct == 25.0
        assert metrics.capital_pct == 20.0
        assert metrics.status == "safe"
