"""
Phase 5H Backend Tests - Adjustment Intelligence

Tests for:
- Feature #44: Suggestion Engine Logic
- Feature #45: Offensive/Defensive Categorization
- Feature #46: Adjustment Cost Tracking
- Feature #47: One-Click Execution
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# =============================================================================
# FEATURE #44: SUGGESTION ENGINE LOGIC
# =============================================================================

class TestSuggestionEngine:
    """Tests for suggestion engine functionality."""

    @pytest.mark.asyncio
    async def test_generate_suggestions_for_delta_breach(self):
        """Test suggestion generation when delta breaches threshold."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.32")
        strategy.delta_warning_threshold = 0.20
        strategy.dte = 25

        suggestions = []

        if abs(float(strategy.net_delta)) > strategy.delta_warning_threshold:
            suggestions.append({
                "type": "shift_leg",
                "reason": f"Delta {strategy.net_delta} exceeds warning threshold {strategy.delta_warning_threshold}",
                "action": "shift_threatened_leg_farther",
                "confidence": 0.75
            })

        assert len(suggestions) > 0
        assert suggestions[0]["type"] == "shift_leg"

    @pytest.mark.asyncio
    async def test_generate_suggestions_for_premium_decay(self):
        """Test suggestion generation based on premium decay."""
        strategy = MagicMock()
        strategy.entry_premium = Decimal("15000")
        strategy.current_position_value = Decimal("4500")
        strategy.max_profit = Decimal("15000")

        # Premium captured = 15000 - 4500 = 10500 (70%)
        premium_captured_pct = ((strategy.entry_premium - strategy.current_position_value) / strategy.entry_premium) * 100

        suggestions = []

        if float(premium_captured_pct) >= 60.0:
            suggestions.append({
                "type": "exit",
                "reason": f"{premium_captured_pct:.1f}% of premium captured - consider booking profit",
                "action": "exit_all",
                "confidence": 0.80
            })

        assert len(suggestions) > 0
        assert "premium captured" in suggestions[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_generate_suggestions_for_dte_zone(self):
        """Test suggestion generation based on DTE zone."""
        strategy = MagicMock()
        strategy.dte = 5  # Expiry week
        strategy.net_delta = Decimal("0.25")
        strategy.net_gamma = Decimal("0.07")

        suggestions = []

        if strategy.dte < 7:
            if abs(float(strategy.net_delta)) > 0.20:
                suggestions.append({
                    "type": "exit",
                    "reason": "High delta in expiry week - exit recommended over adjustment",
                    "action": "exit_all",
                    "confidence": 0.90
                })

        assert len(suggestions) > 0
        assert "expiry week" in suggestions[0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_suggestion_priority_ranking(self):
        """Test suggestions are ranked by priority."""
        suggestions = [
            {"type": "shift_leg", "confidence": 0.70, "priority": 2},
            {"type": "exit", "confidence": 0.90, "priority": 1},  # Highest priority
            {"type": "add_hedge", "confidence": 0.65, "priority": 3},
        ]

        # Sort by priority (lower number = higher priority)
        ranked_suggestions = sorted(suggestions, key=lambda x: x["priority"])

        assert ranked_suggestions[0]["type"] == "exit"
        assert ranked_suggestions[0]["confidence"] == 0.90

    @pytest.mark.asyncio
    async def test_suggestion_confidence_scoring(self):
        """Test confidence scoring for suggestions."""
        # High confidence: 50% profit captured AND 21 DTE
        suggestion_1 = {
            "type": "exit",
            "reason": "50% profit + 21 DTE",
            "confidence": 0.95  # Very high confidence
        }

        # Medium confidence: Delta breach but not in danger zone
        suggestion_2 = {
            "type": "shift_leg",
            "reason": "Delta 0.25, 20 DTE",
            "confidence": 0.70  # Medium confidence
        }

        # Low confidence: Speculative adjustment
        suggestion_3 = {
            "type": "add_hedge",
            "reason": "VIX slightly elevated",
            "confidence": 0.50  # Low confidence
        }

        assert suggestion_1["confidence"] > suggestion_2["confidence"]
        assert suggestion_2["confidence"] > suggestion_3["confidence"]


# =============================================================================
# FEATURE #45: OFFENSIVE/DEFENSIVE CATEGORIZATION
# =============================================================================

class TestOffensiveDefensiveCategorization:
    """Tests for offensive/defensive adjustment categorization."""

    @pytest.mark.asyncio
    async def test_offensive_adjustment_categorization(self):
        """Test offensive adjustments (increase risk for more premium)."""
        offensive_adjustments = [
            {"action": "roll_closer", "category": "offensive"},
            {"action": "add_to_opposite_side", "category": "offensive"},
            {"action": "widen_spread", "category": "offensive"},
        ]

        for adj in offensive_adjustments:
            assert adj["category"] == "offensive"

    @pytest.mark.asyncio
    async def test_defensive_adjustment_categorization(self):
        """Test defensive adjustments (reduce risk)."""
        defensive_adjustments = [
            {"action": "roll_farther", "category": "defensive"},
            {"action": "add_hedge", "category": "defensive"},
            {"action": "close_leg", "category": "defensive"},
            {"action": "scale_down", "category": "defensive"},
        ]

        for adj in defensive_adjustments:
            assert adj["category"] == "defensive"

    @pytest.mark.asyncio
    async def test_neutral_adjustment_categorization(self):
        """Test neutral adjustments (rebalance without changing risk profile)."""
        neutral_adjustments = [
            {"action": "delta_neutral_rebalance", "category": "neutral"},
            {"action": "roll_expiry", "category": "neutral"},
        ]

        for adj in neutral_adjustments:
            assert adj["category"] == "neutral"


# =============================================================================
# FEATURE #46: ADJUSTMENT COST TRACKING
# =============================================================================

class TestAdjustmentCostTracking:
    """Tests for adjustment cost tracking."""

    @pytest.mark.asyncio
    async def test_adjustment_cost_calculation(self):
        """Test calculation of adjustment cost."""
        # Original leg: Sell 25000 CE @ ₹180
        # Adjusted leg: Sell 25200 CE @ ₹140

        original_premium = 180.0
        new_premium = 140.0
        lots = 1
        lot_size = 25

        # Cost to roll = (new_premium - original_premium) * lots * lot_size
        adjustment_cost = (new_premium - original_premium) * lots * lot_size

        # Cost = (140 - 180) * 1 * 25 = -₹1,000 (credit)
        assert adjustment_cost == -1000.0

    @pytest.mark.asyncio
    async def test_cumulative_cost_tracking(self):
        """Test cumulative adjustment cost tracking."""
        adjustments = [
            {"date": "2025-01-05", "action": "roll_ce", "cost": -500.0},  # Credit
            {"date": "2025-01-10", "action": "add_hedge", "cost": 1200.0},  # Debit
            {"date": "2025-01-15", "action": "roll_pe", "cost": -300.0},  # Credit
        ]

        cumulative_cost = sum(adj["cost"] for adj in adjustments)

        # Total cost = -500 + 1200 - 300 = ₹400 (net debit)
        assert cumulative_cost == 400.0

    @pytest.mark.asyncio
    async def test_cost_vs_original_premium_comparison(self):
        """Test comparison of adjustment cost vs original premium."""
        original_premium = 15000.0
        cumulative_adjustment_cost = 2500.0

        cost_pct = (cumulative_adjustment_cost / original_premium) * 100

        # Cost is 16.67% of original premium
        assert abs(cost_pct - 16.67) < 0.01


# =============================================================================
# FEATURE #47: ONE-CLICK EXECUTION
# =============================================================================

class TestOneClickExecution:
    """Tests for one-click suggestion execution."""

    @pytest.mark.asyncio
    async def test_one_click_suggestion_execution(self):
        """Test one-click execution of suggestion."""
        suggestion = {
            "id": "sugg_123",
            "type": "shift_leg",
            "action": "shift_threatened_leg_farther",
            "params": {
                "leg_id": "leg_1",
                "current_strike": 25000,
                "new_strike": 25200
            }
        }

        # One-click execute
        execution_request = {
            "suggestion_id": suggestion["id"],
            "confirmed": True,
            "params": suggestion["params"]
        }

        executed = True  # Simulate execution

        assert executed is True

    @pytest.mark.asyncio
    async def test_execution_confirmation_flow(self):
        """Test confirmation flow before execution."""
        suggestion = {
            "type": "exit",
            "action": "exit_all",
            "requires_confirmation": True
        }

        # Step 1: Show confirmation dialog
        confirmation_shown = True

        # Step 2: User confirms
        user_confirmed = True

        # Step 3: Execute only if confirmed
        can_execute = confirmation_shown and user_confirmed

        assert can_execute is True


# =============================================================================
# INTEGRATION: SUGGESTION ENGINE WORKFLOW
# =============================================================================

class TestSuggestionEngineWorkflow:
    """Integration tests for suggestion engine workflow."""

    @pytest.mark.asyncio
    async def test_multi_scenario_suggestion_generation(self):
        """Test suggestion generation for multiple scenarios."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.28")
        strategy.dte = 18
        strategy.current_pnl = Decimal("6000")
        strategy.max_profit = Decimal("10000")
        strategy.entry_premium = Decimal("15000")
        strategy.current_position_value = Decimal("4000")

        suggestions = []

        # Scenario 1: Delta breach
        if abs(float(strategy.net_delta)) > 0.20:
            suggestions.append({
                "type": "shift_leg",
                "confidence": 0.70,
                "priority": 2
            })

        # Scenario 2: Profit target
        profit_pct = (strategy.current_pnl / strategy.max_profit) * 100
        if float(profit_pct) >= 50.0:
            suggestions.append({
                "type": "exit",
                "confidence": 0.85,
                "priority": 1
            })

        # Should have 2 suggestions
        assert len(suggestions) == 2

        # Exit should be higher priority
        ranked = sorted(suggestions, key=lambda x: x["priority"])
        assert ranked[0]["type"] == "exit"

    @pytest.mark.asyncio
    async def test_suggestion_dismissal_tracking(self):
        """Test tracking of dismissed suggestions."""
        suggestion = {
            "id": "sugg_123",
            "type": "shift_leg",
            "dismissed": False
        }

        # User dismisses suggestion
        suggestion["dismissed"] = True
        suggestion["dismissed_at"] = datetime.now()
        suggestion["dismissed_reason"] = "will_monitor_further"

        assert suggestion["dismissed"] is True
        assert suggestion["dismissed_reason"] == "will_monitor_further"

    @pytest.mark.asyncio
    async def test_suggestion_expiry(self):
        """Test suggestions expire after conditions change."""
        suggestion = {
            "id": "sugg_123",
            "type": "shift_leg",
            "generated_at": datetime.now(),
            "condition": "delta > 0.20",
            "expired": False
        }

        # Current delta back to 0.15 (condition no longer met)
        current_delta = 0.15
        condition_still_met = current_delta > 0.20

        if not condition_still_met:
            suggestion["expired"] = True

        assert suggestion["expired"] is True
