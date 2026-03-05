"""
Phase 5 Schema Tests

Tests for all Phase 5 Pydantic schemas and validation.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta
from pydantic import ValidationError

from app.schemas.autopilot import (
    # Position Leg Schemas
    PositionLegBase, PositionLegCreate, PositionLegUpdate, PositionLegResponse,
    # Option Chain Schemas
    OptionChainEntry, OptionChainResponse, StrikeFindByDeltaRequest,
    StrikeFindByPremiumRequest, StrikeFindResponse,
    # Leg Action Schemas
    ExitLegRequest, ShiftLegRequest, RollLegRequest, BreakTradeRequest, BreakTradeResponse,
    # Suggestion Schemas
    AdjustmentSuggestionBase, AdjustmentSuggestionCreate, AdjustmentSuggestionResponse,
    # WhatIf Schemas
    WhatIfScenario, WhatIfRequest, PositionMetrics, WhatIfResponse,
    # Payoff Schemas
    PayoffDataPoint, PayoffChartResponse
)


# =============================================================================
# POSITION LEG SCHEMAS
# =============================================================================

class TestPositionLegSchemas:
    """Tests for PositionLeg schemas."""

    def test_position_leg_base_validation(self):
        """Test PositionLegBase with valid data."""
        data = {
            "leg_id": "leg_1",
            "contract_type": "PE",
            "action": "SELL",
            "strike": 25000,
            "expiry": date.today() + timedelta(days=7),
            "lots": 1,
        }
        schema = PositionLegBase(**data)
        assert schema.strike == 25000
        assert schema.lots == 1

    def test_position_leg_create_required_fields(self):
        """Test PositionLegCreate with required fields only."""
        data = {
            "leg_id": "leg_1",
            "contract_type": "PE",
            "action": "SELL",
            "strike": 25000,
            "expiry": date.today() + timedelta(days=7),
            "lots": 1,
            "entry_price": 180.00
        }
        schema = PositionLegCreate(**data)
        assert schema.leg_id == "leg_1"

    def test_position_leg_update_partial(self):
        """Test PositionLegUpdate allows partial updates."""
        data = {"delta": -0.18, "unrealized_pnl": 250.00}
        schema = PositionLegUpdate(**data)
        assert schema.delta == Decimal("-0.18")

    def test_position_leg_response_all_fields(self):
        """Test PositionLegResponse includes all fields."""
        data = {
            "id": 1,
            "strategy_id": 1,
            "leg_id": "leg_1",
            "contract_type": "PE",
            "action": "SELL",
            "strike": 25000,
            "expiry": date.today() + timedelta(days=7),
            "lots": 1,
            "entry_price": 180.00,
            "entry_time": None,
            "exit_price": None,
            "exit_time": None,
            "exit_reason": None,
            "rolled_from_leg_id": None,
            "rolled_to_leg_id": None,
            "status": "open",
            "delta": -0.15,
            "gamma": 0.002,
            "theta": -12.50,
            "vega": 8.75,
            "iv": 0.18,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        schema = PositionLegResponse(**data)
        assert schema.id == 1
        assert schema.delta == Decimal("-0.15")


# =============================================================================
# OPTION CHAIN SCHEMAS
# =============================================================================

class TestOptionChainSchemas:
    """Tests for Option Chain schemas."""

    def test_option_chain_entry_all_fields(self):
        """Test OptionChainEntry with all fields."""
        data = {
            "instrument_token": 12345,
            "tradingsymbol": "NIFTY24D2625000PE",
            "strike": 25000,
            "option_type": "PE",
            "expiry": date.today() + timedelta(days=7),
            "ltp": 145.00,
            "bid": 143.00,
            "ask": 147.00,
            "volume": 1200,
            "oi": 52000,
            "oi_change": None,
            "delta": -0.15,
            "gamma": 0.002,
            "theta": -11.50,
            "vega": 8.30,
            "iv": 0.16
        }
        schema = OptionChainEntry(**data)
        assert schema.strike == 25000

    def test_option_chain_response_structure(self):
        """Test OptionChainResponse structure."""
        data = {
            "underlying": "NIFTY",
            "expiry": date.today() + timedelta(days=7),
            "spot_price": 25250,
            "options": []
        }
        schema = OptionChainResponse(**data)
        assert schema.underlying == "NIFTY"

    def test_strike_find_by_delta_request(self):
        """Test StrikeFindByDeltaRequest validation."""
        data = {
            "underlying": "NIFTY",
            "expiry": "2024-01-25",
            "option_type": "CE",
            "target_delta": 0.15,
            "tolerance": 0.05,
            "prefer_round_strike": True
        }
        schema = StrikeFindByDeltaRequest(**data)
        assert schema.target_delta == Decimal("0.15")

    def test_strike_find_by_delta_invalid_delta_rejected(self):
        """Test invalid delta value is rejected."""
        data = {
            "underlying": "NIFTY",
            "expiry": "2024-01-25",
            "option_type": "CE",
            "target_delta": 1.5  # Invalid: > 1.0
        }
        with pytest.raises(ValidationError):
            StrikeFindByDeltaRequest(**data)

    def test_strike_find_by_premium_request(self):
        """Test StrikeFindByPremiumRequest validation."""
        data = {
            "underlying": "NIFTY",
            "expiry": "2024-01-25",
            "option_type": "PE",
            "target_premium": 185.00,
            "tolerance": 10.00
        }
        schema = StrikeFindByPremiumRequest(**data)
        assert schema.target_premium == Decimal("185.00")

    def test_strike_find_by_premium_invalid_premium_rejected(self):
        """Test invalid premium value is rejected."""
        data = {
            "underlying": "NIFTY",
            "expiry": "2024-01-25",
            "option_type": "PE",
            "target_premium": -100  # Invalid: negative
        }
        with pytest.raises(ValidationError):
            StrikeFindByPremiumRequest(**data)

    def test_strike_find_response(self):
        """Test StrikeFindResponse structure."""
        data = {
            "strike": 25000,
            "tradingsymbol": "NIFTY24D2625000PE",
            "instrument_token": 12345,
            "ltp": 185.00,
            "delta": 0.15,
            "iv": 0.17,
            "distance_from_target": 0.01
        }
        schema = StrikeFindResponse(**data)
        assert schema.strike == 25000


# =============================================================================
# LEG ACTION SCHEMAS
# =============================================================================

class TestLegActionSchemas:
    """Tests for leg action request/response schemas."""

    def test_exit_leg_request(self):
        """Test ExitLegRequest validation."""
        data = {
            "execution_mode": "market",
            "limit_price": None
        }
        schema = ExitLegRequest(**data)
        assert schema.execution_mode == "market"

    def test_shift_leg_request_by_strike(self):
        """Test ShiftLegRequest with target strike."""
        data = {
            "target_strike": 24900,
            "execution_mode": "market"
        }
        schema = ShiftLegRequest(**data)
        assert schema.target_strike == 24900

    def test_shift_leg_request_by_delta(self):
        """Test ShiftLegRequest with target delta."""
        data = {
            "target_delta": 0.18,
            "execution_mode": "limit",
            "limit_offset": 2.00
        }
        schema = ShiftLegRequest(**data)
        assert schema.target_delta == Decimal("0.18")

    def test_shift_leg_request_by_direction(self):
        """Test ShiftLegRequest with direction and amount."""
        data = {
            "shift_direction": "closer",
            "shift_amount": 100,
            "execution_mode": "market"
        }
        schema = ShiftLegRequest(**data)
        assert schema.shift_direction == "closer"

    def test_roll_leg_request(self):
        """Test RollLegRequest validation."""
        data = {
            "target_expiry": date(2024, 2, 1),
            "target_strike": 25000,
            "execution_mode": "market"
        }
        schema = RollLegRequest(**data)
        assert schema.target_expiry == date(2024, 2, 1)

    def test_break_trade_request(self):
        """Test BreakTradeRequest validation."""
        data = {
            "execution_mode": "market",
            "premium_split": "equal",
            "prefer_round_strikes": True,
            "max_delta": 0.20
        }
        schema = BreakTradeRequest(**data)
        assert schema.premium_split == "equal"

    def test_break_trade_response(self):
        """Test BreakTradeResponse structure."""
        data = {
            "break_trade_id": "bt_001",
            "exit_order": {"order_id": "123", "status": "complete"},
            "new_positions": [{"leg": "PE", "strike": 24800}],
            "recovery_premium": 70.00,
            "exit_cost": 140.00,
            "net_cost": 70.00,
            "status": "completed"
        }
        schema = BreakTradeResponse(**data)
        assert schema.exit_cost == Decimal("140.00")


# =============================================================================
# SUGGESTION SCHEMAS
# =============================================================================

class TestSuggestionSchemas:
    """Tests for adjustment suggestion schemas."""

    def test_suggestion_base_fields(self):
        """Test AdjustmentSuggestionBase validation."""
        data = {
            "trigger_reason": "Premium decayed",
            "suggestion_type": "shift",
            "description": "Shift leg closer",
            "urgency": "medium",
            "confidence": 75,
            "action_params": {"target_strike": 24900}
        }
        schema = AdjustmentSuggestionBase(**data)
        assert schema.confidence == 75

    def test_suggestion_create_validation(self):
        """Test AdjustmentSuggestionCreate validation."""
        data = {
            "leg_id": "leg_1",
            "trigger_reason": "Delta doubled",
            "suggestion_type": "break",
            "description": "Execute break trade",
            "urgency": "critical",
            "confidence": 85,
            "expires_at": datetime.utcnow() + timedelta(hours=2)
        }
        schema = AdjustmentSuggestionCreate(**data)
        assert schema.urgency == "critical"

    def test_suggestion_response_structure(self):
        """Test AdjustmentSuggestionResponse structure."""
        data = {
            "id": 1,
            "strategy_id": 1,
            "leg_id": "leg_1",
            "trigger_reason": "Delta exceeded threshold",
            "suggestion_type": "shift",
            "description": "Test",
            "urgency": "low",
            "confidence": 50,
            "status": "active",
            "created_at": datetime.utcnow(),
            "expires_at": None,
            "responded_at": None
        }
        schema = AdjustmentSuggestionResponse(**data)
        assert schema.id == 1

    def test_suggestion_action_params(self):
        """Test action_params structure."""
        data = {
            "trigger_reason": "Test trigger",
            "suggestion_type": "shift",
            "description": "Test",
            "urgency": "medium",
            "confidence": 70,
            "action_params": {
                "target_strike": 24900,
                "execution_mode": "market",
                "confirm_required": False
            }
        }
        schema = AdjustmentSuggestionBase(**data)
        assert "target_strike" in schema.action_params


# =============================================================================
# WHAT-IF SCHEMAS
# =============================================================================

class TestWhatIfSchemas:
    """Tests for what-if simulation schemas."""

    def test_whatif_scenario_validation(self):
        """Test WhatIfScenario validation."""
        data = {
            "spot_change": 100.00,
            "iv_change": -2.0,
            "days_forward": 1
        }
        schema = WhatIfScenario(**data)
        assert schema.spot_change == Decimal("100.00")

    def test_whatif_request_structure(self):
        """Test WhatIfRequest structure."""
        data = {
            "strategy_id": 1,
            "adjustment_type": "shift",
            "adjustment_params": {"leg_id": "leg_1", "target_strike": 24900},
            "scenarios": [
                {"spot_change": 100, "days_forward": 1}
            ]
        }
        schema = WhatIfRequest(**data)
        assert len(schema.scenarios) == 1
        assert schema.adjustment_type == "shift"

    def test_position_metrics_fields(self):
        """Test PositionMetrics structure."""
        data = {
            "net_delta": 0.05,
            "net_theta": -25.00,
            "net_gamma": 0.002,
            "net_vega": 8.50,
            "max_profit": 5000.00,
            "max_loss": -3000.00,
            "breakeven_lower": 25100.00,
            "breakeven_upper": 25400.00,
            "current_pnl": 1500.00
        }
        schema = PositionMetrics(**data)
        assert schema.net_delta == Decimal("0.05")
        assert schema.current_pnl == Decimal("1500.00")

    def test_whatif_response_structure(self):
        """Test WhatIfResponse structure."""
        metrics_data = {
            "net_delta": 0.05,
            "net_theta": -25.00,
            "net_gamma": 0.002,
            "net_vega": 8.50,
            "max_profit": 5000.00,
            "max_loss": -3000.00,
            "breakeven_lower": 25100.00,
            "breakeven_upper": 25400.00,
            "current_pnl": 1500.00
        }
        data = {
            "current_position": PositionMetrics(**metrics_data),
            "after_adjustment": PositionMetrics(**metrics_data),
            "comparison": {"delta_change": 0.02},
            "scenario_results": []
        }
        schema = WhatIfResponse(**data)
        assert schema.current_position.net_delta == Decimal("0.05")


# =============================================================================
# PAYOFF SCHEMAS
# =============================================================================

class TestPayoffSchemas:
    """Tests for payoff calculation schemas."""

    def test_payoff_data_point(self):
        """Test PayoffDataPoint structure."""
        data = {
            "spot_price": 25250,
            "pnl": 1250.00,
        }
        schema = PayoffDataPoint(**data)
        assert schema.spot_price == Decimal("25250")

    def test_payoff_chart_response(self):
        """Test PayoffChartResponse structure."""
        data = {
            "current_spot": 25250,
            "current_pnl": 0.00,
            "data_points": [
                {"spot_price": 25000, "pnl": 1000.00},
                {"spot_price": 25500, "pnl": 800.00}
            ],
            "breakeven_points": [25100.00, 25400.00],
            "max_profit": 5000.00,
            "max_loss": -3000.00,
        }
        schema = PayoffChartResponse(**data)
        assert len(schema.data_points) == 2

    def test_risk_metrics_structure(self):
        """Test risk metrics in payoff response."""
        data = {
            "current_spot": 25250,
            "current_pnl": 0.00,
            "data_points": [],
            "breakeven_points": [25100.00],
            "max_profit": 5000.00,
            "max_loss": -3000.00,
        }
        schema = PayoffChartResponse(**data)
        assert schema.max_profit == Decimal("5000.00")
