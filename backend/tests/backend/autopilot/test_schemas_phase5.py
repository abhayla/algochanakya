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
            "underlying": "NIFTY",
            "expiry": (date.today() + timedelta(days=7)).isoformat(),
            "strike": 25000,
            "option_type": "PE",
            "transaction_type": "SELL",
            "quantity": 25,
            "entry_price": 180.00
        }
        schema = PositionLegBase(**data)
        assert schema.strike == 25000
        assert schema.quantity == 25

    def test_position_leg_create_required_fields(self):
        """Test PositionLegCreate with required fields only."""
        data = {
            "leg_id": "leg_1",
            "underlying": "NIFTY",
            "expiry": date.today() + timedelta(days=7),
            "strike": 25000,
            "option_type": "PE",
            "transaction_type": "SELL",
            "quantity": 25,
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
            "underlying": "NIFTY",
            "expiry": date.today() + timedelta(days=7),
            "strike": 25000,
            "option_type": "PE",
            "transaction_type": "SELL",
            "quantity": 25,
            "entry_price": 180.00,
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
            "strike": 25000,
            "ce": {
                "ltp": 150.00,
                "bid": 148.00,
                "ask": 152.00,
                "volume": 1000,
                "oi": 50000,
                "delta": 0.15,
                "gamma": 0.002,
                "theta": -12.00,
                "vega": 8.50,
                "iv": 0.17
            },
            "pe": {
                "ltp": 145.00,
                "bid": 143.00,
                "ask": 147.00,
                "volume": 1200,
                "oi": 52000,
                "delta": -0.15,
                "gamma": 0.002,
                "theta": -11.50,
                "vega": 8.30,
                "iv": 0.16
            }
        }
        schema = OptionChainEntry(**data)
        assert schema.strike == 25000

    def test_option_chain_response_structure(self):
        """Test OptionChainResponse structure."""
        data = {
            "underlying": "NIFTY",
            "spot_price": 25250,
            "strikes": [],
            "timestamp": datetime.utcnow()
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
            "delta": 0.15,
            "premium": 185.00
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
            "target_expiry": "2024-02-01",
            "target_strike": 25000,
            "execution_mode": "market"
        }
        schema = RollLegRequest(**data)
        assert schema.target_expiry == "2024-02-01"

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
            "exit_cost": 140.00,
            "recovery_premium_per_leg": 70.00,
            "new_put_strike": 24800,
            "new_call_strike": 25700,
            "estimated_recovery": 3500.00
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
            "suggestion_type": "shift",
            "title": "Shift leg closer",
            "description": "Premium decayed",
            "urgency": "medium",
            "confidence": 0.75,
            "expected_impact": {"premium_captured": 65},
            "one_click_params": {"target_strike": 24900}
        }
        schema = AdjustmentSuggestionBase(**data)
        assert schema.confidence == Decimal("0.75")

    def test_suggestion_create_validation(self):
        """Test AdjustmentSuggestionCreate validation."""
        data = {
            "leg_id": 1,
            "suggestion_type": "break",
            "title": "Execute break trade",
            "description": "Delta doubled",
            "urgency": "critical",
            "confidence": 0.85,
            "expected_impact": {},
            "one_click_params": {},
            "expires_at": datetime.utcnow() + timedelta(hours=2)
        }
        schema = AdjustmentSuggestionCreate(**data)
        assert schema.urgency == "critical"

    def test_suggestion_response_structure(self):
        """Test AdjustmentSuggestionResponse structure."""
        data = {
            "id": 1,
            "strategy_id": 1,
            "leg_id": 1,
            "suggestion_type": "shift",
            "title": "Test",
            "description": "Test",
            "urgency": "low",
            "confidence": 0.50,
            "expected_impact": {},
            "one_click_params": {},
            "status": "active",
            "created_at": datetime.utcnow()
        }
        schema = AdjustmentSuggestionResponse(**data)
        assert schema.id == 1

    def test_suggestion_one_click_params(self):
        """Test one_click_params structure."""
        data = {
            "suggestion_type": "shift",
            "title": "Test",
            "description": "Test",
            "urgency": "medium",
            "confidence": 0.70,
            "expected_impact": {"cost": 15.00},
            "one_click_params": {
                "target_strike": 24900,
                "execution_mode": "market",
                "confirm_required": False
            }
        }
        schema = AdjustmentSuggestionBase(**data)
        assert "target_strike" in schema.one_click_params


# =============================================================================
# WHAT-IF SCHEMAS
# =============================================================================

class TestWhatIfSchemas:
    """Tests for what-if simulation schemas."""

    def test_whatif_scenario_validation(self):
        """Test WhatIfScenario validation."""
        data = {
            "name": "Shift PE leg",
            "action_type": "shift",
            "parameters": {"leg_id": 1, "target_strike": 24900}
        }
        schema = WhatIfScenario(**data)
        assert schema.action_type == "shift"

    def test_whatif_request_structure(self):
        """Test WhatIfRequest structure."""
        data = {
            "scenarios": [
                {
                    "name": "Scenario 1",
                    "action_type": "shift",
                    "parameters": {}
                }
            ]
        }
        schema = WhatIfRequest(**data)
        assert len(schema.scenarios) == 1

    def test_position_metrics_fields(self):
        """Test PositionMetrics structure."""
        data = {
            "net_delta": 0.05,
            "net_theta": -25.00,
            "max_profit": 5000.00,
            "max_loss": -3000.00,
            "breakeven_lower": 25100.00,
            "breakeven_upper": 25400.00
        }
        schema = PositionMetrics(**data)
        assert schema.net_delta == Decimal("0.05")

    def test_whatif_response_before_after(self):
        """Test WhatIfResponse before/after structure."""
        metrics_data = {
            "net_delta": 0.05,
            "net_theta": -25.00,
            "max_profit": 5000.00,
            "max_loss": -3000.00
        }
        data = {
            "scenario_name": "Test",
            "before": PositionMetrics(**metrics_data),
            "after": PositionMetrics(**metrics_data),
            "impact": {
                "delta_change": 0.02,
                "risk_change": -500.00
            },
            "recommendation": "Execute"
        }
        schema = WhatIfResponse(**data)
        assert schema.recommendation == "Execute"


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
            "net_delta": 0.05,
            "net_theta": -25.00
        }
        schema = PayoffDataPoint(**data)
        assert schema.spot_price == Decimal("25250")

    def test_payoff_chart_response(self):
        """Test PayoffChartResponse structure."""
        data = {
            "current_spot": 25250,
            "payoff_data": [
                {
                    "spot_price": 25000,
                    "pnl": 1000.00
                },
                {
                    "spot_price": 25500,
                    "pnl": 800.00
                }
            ],
            "max_profit": 5000.00,
            "max_loss": -3000.00,
            "breakevens": [25100.00, 25400.00]
        }
        schema = PayoffChartResponse(**data)
        assert len(schema.payoff_data) == 2

    def test_risk_metrics_structure(self):
        """Test risk metrics in payoff response."""
        data = {
            "current_spot": 25250,
            "payoff_data": [],
            "max_profit": 5000.00,
            "max_loss": -3000.00,
            "breakevens": [25100.00],
            "risk_reward_ratio": 1.67
        }
        schema = PayoffChartResponse(**data)
        assert schema.max_profit == Decimal("5000.00")
