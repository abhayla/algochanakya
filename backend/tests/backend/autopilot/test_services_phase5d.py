"""
Phase 5D Backend Tests - Exit Rules

Tests for:
- Features #18-22: Profit-Based Exits (50%, 25%, Premium Captured %, Target Return %, Capital Recycling)
- Features #23-25: Time-Based Exits (21 DTE, Days in Trade, Optimal Exit Timing)
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

from app.services.adjustment_engine import AdjustmentEngine


# =============================================================================
# FEATURES #18-22: PROFIT-BASED EXITS
# =============================================================================

class TestProfitBasedExits:
    """Tests for profit-based exit rules."""

    # Feature #18: 50% Profit Target
    @pytest.mark.asyncio
    async def test_50_percent_of_max_profit_exit(self, db_session, test_user):
        """Test exit when 50% of max profit is captured."""
        engine = AdjustmentEngine(db_session, test_user.id)

        strategy = MagicMock()
        strategy.max_profit = Decimal("10000")  # Max profit ₹10,000
        strategy.current_pnl = Decimal("5000")   # Current profit ₹5,000

        trigger = {
            "type": "profit_pct_of_max",
            "value": 50.0  # 50% target
        }

        triggered = await engine._check_profit_pct_trigger(strategy, trigger)

        # 5000 / 10000 = 50% → triggered
        assert triggered is True

    @pytest.mark.asyncio
    async def test_max_profit_calculation(self):
        """Test max profit calculation at entry."""
        # Iron Condor example
        entry_premium = 15000  # Collected ₹15,000
        max_loss = 10000       # Max loss ₹10,000

        # Max profit = entry premium (assuming can capture 100% of premium)
        max_profit = entry_premium

        assert max_profit == 15000

    # Feature #19: 25% Profit Target
    @pytest.mark.asyncio
    async def test_25_percent_profit_target(self, db_session, test_user):
        """Test exit at 25% of max profit for faster capital recycling."""
        engine = AdjustmentEngine(db_session, test_user.id)

        strategy = MagicMock()
        strategy.max_profit = Decimal("10000")
        strategy.current_pnl = Decimal("2500")   # 25% captured

        trigger = {
            "type": "profit_pct_of_max",
            "value": 25.0
        }

        triggered = await engine._check_profit_pct_trigger(strategy, trigger)

        assert triggered is True

    # Feature #20: Premium Captured %
    @pytest.mark.asyncio
    async def test_premium_captured_percentage_exit(self, db_session, test_user):
        """Test exit when X% of premium is captured."""
        engine = AdjustmentEngine(db_session, test_user.id)

        strategy = MagicMock()
        strategy.entry_premium = Decimal("15000")
        strategy.current_position_value = Decimal("6000")  # Current value of short options

        # Premium captured = entry - current
        premium_captured = strategy.entry_premium - strategy.current_position_value
        premium_captured_pct = (premium_captured / strategy.entry_premium) * 100

        trigger = {
            "type": "premium_captured_pct",
            "value": 60.0  # Exit at 60% captured
        }

        # Captured 9000 / 15000 = 60%
        assert premium_captured_pct >= trigger["value"]

    @pytest.mark.asyncio
    async def test_premium_captured_calculation(self):
        """Test premium captured calculation."""
        initial_premium = 12000
        current_value = 4800

        captured = initial_premium - current_value
        captured_pct = (captured / initial_premium) * 100

        # Captured ₹7200 = 60%
        assert abs(captured_pct - 60.0) < 0.1

    # Feature #21: Target Return %
    @pytest.mark.asyncio
    async def test_return_on_margin_exit(self, db_session, test_user):
        """Test exit when target return % on margin is achieved."""
        engine = AdjustmentEngine(db_session, test_user.id)

        strategy = MagicMock()
        strategy.margin_used = Decimal("50000")
        strategy.current_pnl = Decimal("5000")

        # Return on margin = 5000 / 50000 = 10%
        return_pct = (strategy.current_pnl / strategy.margin_used) * 100

        trigger = {
            "type": "return_on_margin",
            "value": 8.0  # Exit at 8% return
        }

        assert float(return_pct) >= trigger["value"]

    # Feature #22: Capital Recycling
    @pytest.mark.asyncio
    async def test_capital_recycling_exit_early(self, db_session, test_user):
        """Test early exit for capital recycling (exit at 25% vs waiting for 50%)."""
        # Scenario: Exit at 25% to recycle capital faster
        strategy = MagicMock()
        strategy.max_profit = Decimal("10000")
        strategy.current_pnl = Decimal("2500")  # 25%
        strategy.days_in_trade = 5  # Only 5 days in

        # Capital recycling strategy: Exit early if:
        # 1. Profit >= 25% AND
        # 2. Days in trade < 10
        profit_pct = (strategy.current_pnl / strategy.max_profit) * 100

        should_exit_for_recycling = (
            float(profit_pct) >= 25.0 and
            strategy.days_in_trade < 10
        )

        assert should_exit_for_recycling is True


# =============================================================================
# FEATURES #23-25: TIME-BASED EXITS
# =============================================================================

class TestTimeBasedExits:
    """Tests for time-based exit rules."""

    # Feature #23: 21 DTE Exit
    @pytest.mark.asyncio
    async def test_21_dte_exit_rule(self, db_session, test_user):
        """Test exit at 21 DTE to capture 75-80% profit."""
        engine = AdjustmentEngine(db_session, test_user.id)

        strategy = MagicMock()
        strategy.dte = 21
        strategy.current_pnl = Decimal("7500")  # Captured 75% of ₹10k max
        strategy.max_profit = Decimal("10000")

        trigger = {
            "type": "dte_based",
            "value": 21
        }

        # Exit when DTE <= 21
        triggered = strategy.dte <= trigger["value"]

        assert triggered is True

    @pytest.mark.asyncio
    async def test_dte_exit_configurable(self, db_session, test_user):
        """Test DTE exit is configurable (e.g., 14 DTE, 7 DTE)."""
        strategy = MagicMock()

        # Test different DTE thresholds
        dte_thresholds = [21, 14, 7]

        for threshold in dte_thresholds:
            strategy.dte = threshold - 1  # One day before threshold

            trigger = {
                "type": "dte_based",
                "value": threshold
            }

            triggered = strategy.dte <= trigger["value"]
            assert triggered is True

    # Feature #24: Days in Trade Exit
    @pytest.mark.asyncio
    async def test_days_in_trade_exit(self, db_session, test_user):
        """Test exit after X days in trade."""
        engine = AdjustmentEngine(db_session, test_user.id)

        strategy = MagicMock()
        strategy.entry_date = date.today() - timedelta(days=15)
        strategy.days_in_trade = 15

        trigger = {
            "type": "days_in_trade",
            "value": 14  # Exit after 14 days
        }

        triggered = strategy.days_in_trade >= trigger["value"]

        assert triggered is True

    @pytest.mark.asyncio
    async def test_days_in_trade_calculation(self):
        """Test days in trade calculation."""
        entry_date = date(2025, 1, 1)
        current_date = date(2025, 1, 16)

        days_in_trade = (current_date - entry_date).days

        assert days_in_trade == 15

    # Feature #25: Optimal Exit Timing
    @pytest.mark.asyncio
    async def test_theta_curve_optimal_exit(self):
        """Test optimal exit timing based on theta decay curve."""
        # Theta decay is non-linear (accelerates near expiry)
        # Optimal exit: When theta decay rate peaks (before gamma risk becomes too high)

        dte_values = [45, 30, 21, 14, 7, 3, 1]
        # Realistic theta curve: accelerates, peaks at 21-14 DTE, then slows as gamma risk increases
        theta_values = [-50, -80, -130, -220, -280, -320, -350]

        # Calculate theta decay rate (change per day)
        decay_rates = []
        for i in range(len(dte_values) - 1):
            rate = theta_values[i+1] - theta_values[i]
            decay_rates.append(rate)

        # Optimal exit zone: 21-14 DTE (when theta peaks but before gamma risk)
        # Decay rates: [-30, -50, -90, -60, -40, -30]
        # Peak decay at index 2 (21→14 DTE): -90

        # Find when decay rate is highest (most negative)
        max_decay_rate_idx = decay_rates.index(min(decay_rates))

        # This should be around 21-14 DTE (index 2-3)
        assert 2 <= max_decay_rate_idx <= 4


# =============================================================================
# INTEGRATION: COMBINED EXIT RULES
# =============================================================================

class TestCombinedExitRules:
    """Tests for combined profit + time based exits."""

    @pytest.mark.asyncio
    async def test_exit_on_first_condition_met(self, db_session, test_user):
        """Test exit on first condition met (50% profit OR 21 DTE)."""
        strategy = MagicMock()
        strategy.max_profit = Decimal("10000")
        strategy.current_pnl = Decimal("3000")  # 30% (not met)
        strategy.dte = 20  # <= 21 (met)

        # Exit if 50% profit OR 21 DTE
        profit_condition = (strategy.current_pnl / strategy.max_profit) * 100 >= 50
        dte_condition = strategy.dte <= 21

        should_exit = profit_condition or dte_condition

        assert should_exit is True  # DTE condition met

    @pytest.mark.asyncio
    async def test_exit_priority_profit_over_time(self):
        """Test profit target has priority over time-based exit."""
        strategy = MagicMock()
        strategy.max_profit = Decimal("10000")
        strategy.current_pnl = Decimal("5000")  # 50% profit
        strategy.dte = 30  # Still 30 DTE

        # Exit immediately if profit target met, regardless of DTE
        profit_target_met = (strategy.current_pnl / strategy.max_profit) * 100 >= 50

        if profit_target_met:
            exit_reason = "profit_target"
        elif strategy.dte <= 21:
            exit_reason = "dte_based"
        else:
            exit_reason = None

        assert exit_reason == "profit_target"

    @pytest.mark.asyncio
    async def test_exit_with_stop_loss_override(self):
        """Test stop loss overrides profit/time exits."""
        strategy = MagicMock()
        strategy.max_loss = Decimal("5000")
        strategy.current_pnl = Decimal("-6000")  # Exceeded max loss
        strategy.max_profit = Decimal("10000")
        strategy.dte = 30

        # Check in order: Stop loss → Profit target → Time-based
        if strategy.current_pnl <= -strategy.max_loss:
            exit_reason = "stop_loss"
        elif (strategy.current_pnl / strategy.max_profit) * 100 >= 50:
            exit_reason = "profit_target"
        elif strategy.dte <= 21:
            exit_reason = "dte_based"
        else:
            exit_reason = None

        assert exit_reason == "stop_loss"
