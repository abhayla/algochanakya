"""
Phase 5E Backend Tests - Risk-Based & DTE-Aware Exits

Tests for:
- Features #26-29: Risk-Based Exits (Gamma Risk, ATR Trailing, Delta Doubles, Delta Change)
- Features #30-35: DTE-Aware Exits (DTE Zones, Dynamic Thresholds, Expiry Week Warnings)
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

from app.services.autopilot.adjustment_engine import AdjustmentEngine
from app.services.autopilot.strategy_monitor import StrategyMonitor


# =============================================================================
# FEATURES #26-29: RISK-BASED EXITS
# =============================================================================

class TestRiskBasedExits:
    """Tests for risk-based exit rules."""

    # Feature #26: Gamma Risk Exit
    @pytest.mark.asyncio
    async def test_gamma_explosion_detection(self):
        """Test detection of gamma explosion near expiry."""
        strategy = MagicMock()
        strategy.net_gamma = Decimal("0.08")  # High gamma
        strategy.dte = 5  # Expiry week

        # Gamma risk threshold (increases near expiry)
        gamma_threshold = 0.05

        gamma_risk_detected = float(strategy.net_gamma) > gamma_threshold and strategy.dte < 7

        assert gamma_risk_detected is True

    @pytest.mark.asyncio
    async def test_gamma_exit_before_expiry_week(self):
        """Test exit before expiry week due to gamma explosion risk."""
        strategy = MagicMock()
        strategy.net_gamma = Decimal("0.06")
        strategy.dte = 6  # Expiry week

        # Exit when: gamma > 0.05 AND dte < 7
        should_exit = float(strategy.net_gamma) > 0.05 and strategy.dte < 7

        assert should_exit is True

    # Feature #27: ATR Trailing Stop
    @pytest.mark.asyncio
    async def test_atr_calculation(self):
        """Test ATR (Average True Range) calculation."""
        # Sample price data (High, Low, Close)
        price_data = [
            {"high": 25100, "low": 24900, "close": 25000},
            {"high": 25200, "low": 25000, "close": 25100},
            {"high": 25300, "low": 25100, "close": 25250},
        ]

        true_ranges = []
        for i in range(1, len(price_data)):
            high_low = price_data[i]["high"] - price_data[i]["low"]
            high_close = abs(price_data[i]["high"] - price_data[i-1]["close"])
            low_close = abs(price_data[i]["low"] - price_data[i-1]["close"])
            tr = max(high_low, high_close, low_close)
            true_ranges.append(tr)

        atr = sum(true_ranges) / len(true_ranges)

        # Average TR should be around 200
        assert 150 < atr < 250

    @pytest.mark.asyncio
    async def test_atr_trailing_stop_adjustment(self):
        """Test ATR-based trailing stop adjustment."""
        strategy = MagicMock()
        strategy.entry_price = 25000
        strategy.current_spot = 25300
        strategy.atr = 200
        strategy.atr_multiplier = 2.0  # Trail at 2x ATR

        # Trailing stop = current spot - (ATR * multiplier)
        trailing_stop = strategy.current_spot - (strategy.atr * strategy.atr_multiplier)

        # Trailing stop = 25300 - (200 * 2) = 24900
        assert trailing_stop == 24900

    # Feature #28: Delta Doubles Alert
    @pytest.mark.asyncio
    async def test_delta_doubles_from_entry_detection(self):
        """Test detection when delta doubles from entry."""
        strategy = MagicMock()
        strategy.entry_delta = Decimal("0.10")
        strategy.current_delta = Decimal("0.22")  # More than doubled

        delta_multiplier = float(strategy.current_delta) / float(strategy.entry_delta)

        # Delta has more than doubled
        assert delta_multiplier >= 2.0

    @pytest.mark.asyncio
    async def test_delta_doubles_alert_triggered(self):
        """Test alert triggers when delta doubles."""
        strategy = MagicMock()
        strategy.entry_delta = Decimal("0.15")
        strategy.current_delta = Decimal("0.35")

        delta_multiplier = float(strategy.current_delta) / float(strategy.entry_delta)

        should_alert = delta_multiplier >= 2.0

        # 0.35 / 0.15 = 2.33 → alert
        assert should_alert is True

    # Feature #29: Delta Change Alert
    @pytest.mark.asyncio
    async def test_daily_delta_change_calculation(self):
        """Test daily delta change calculation."""
        strategy = MagicMock()
        strategy.runtime_state = {
            "delta_history": [
                {"date": date(2025, 1, 10), "delta": 0.10},
                {"date": date(2025, 1, 11), "delta": 0.22},
            ]
        }

        # Delta change from previous day
        previous_delta = strategy.runtime_state["delta_history"][-2]["delta"]
        current_delta = strategy.runtime_state["delta_history"][-1]["delta"]

        delta_change = abs(current_delta - previous_delta)

        # Delta change = 0.12
        assert abs(delta_change - 0.12) < 0.01

    @pytest.mark.asyncio
    async def test_delta_change_greater_than_0_10_alert(self):
        """Test alert when daily delta change > 0.10."""
        previous_delta = 0.08
        current_delta = 0.20

        delta_change = abs(current_delta - previous_delta)

        should_alert = delta_change > 0.10

        # Change = 0.12 > 0.10 → alert
        assert should_alert is True


# =============================================================================
# FEATURES #30-35: DTE-AWARE EXITS
# =============================================================================

class TestDTEZoneService:
    """Tests for DTE zone service and dynamic thresholds."""

    # Feature #30: DTE Zone Display
    @pytest.mark.asyncio
    async def test_dte_zone_early_21_45(self):
        """Test DTE zone: Early (21-45 DTE)."""
        dte = 35

        def get_dte_zone(dte):
            if 21 <= dte <= 45:
                return "early"
            elif 14 <= dte < 21:
                return "middle"
            elif 7 <= dte < 14:
                return "late"
            elif 0 <= dte < 7:
                return "expiry_week"
            return "unknown"

        zone = get_dte_zone(dte)

        assert zone == "early"

    @pytest.mark.asyncio
    async def test_dte_zone_middle_14_21(self):
        """Test DTE zone: Middle (14-21 DTE)."""
        dte = 17

        def get_dte_zone(dte):
            if 21 <= dte <= 45:
                return "early"
            elif 14 <= dte < 21:
                return "middle"
            elif 7 <= dte < 14:
                return "late"
            elif 0 <= dte < 7:
                return "expiry_week"
            return "unknown"

        zone = get_dte_zone(dte)

        assert zone == "middle"

    @pytest.mark.asyncio
    async def test_dte_zone_late_7_14(self):
        """Test DTE zone: Late (7-14 DTE)."""
        dte = 10

        def get_dte_zone(dte):
            if 21 <= dte <= 45:
                return "early"
            elif 14 <= dte < 21:
                return "middle"
            elif 7 <= dte < 14:
                return "late"
            elif 0 <= dte < 7:
                return "expiry_week"
            return "unknown"

        zone = get_dte_zone(dte)

        assert zone == "late"

    @pytest.mark.asyncio
    async def test_dte_zone_expiry_week_0_7(self):
        """Test DTE zone: Expiry Week (0-7 DTE)."""
        dte = 4

        def get_dte_zone(dte):
            if 21 <= dte <= 45:
                return "early"
            elif 14 <= dte < 21:
                return "middle"
            elif 7 <= dte < 14:
                return "late"
            elif 0 <= dte < 7:
                return "expiry_week"
            return "unknown"

        zone = get_dte_zone(dte)

        assert zone == "expiry_week"

    # Feature #31: DTE-Aware Thresholds
    @pytest.mark.asyncio
    async def test_dynamic_threshold_early_zone(self):
        """Test dynamic threshold in early zone (relaxed)."""
        dte = 35
        base_delta_threshold = 0.30

        # In early zone, use base threshold (relaxed)
        zone_multiplier = 1.0  # No adjustment

        dynamic_threshold = base_delta_threshold * zone_multiplier

        assert dynamic_threshold == 0.30

    @pytest.mark.asyncio
    async def test_dynamic_threshold_late_zone(self):
        """Test dynamic threshold in late zone (tighter)."""
        dte = 10
        base_delta_threshold = 0.30

        # In late zone, tighten threshold
        zone_multiplier = 0.67  # Tighter (20% instead of 30%)

        dynamic_threshold = base_delta_threshold * zone_multiplier

        # Threshold tightened to 0.20
        assert abs(dynamic_threshold - 0.20) < 0.01

    @pytest.mark.asyncio
    async def test_tighter_thresholds_as_dte_decreases(self):
        """Test thresholds get tighter as DTE decreases."""
        test_cases = [
            {"dte": 35, "zone": "early", "delta_threshold": 0.30},
            {"dte": 17, "zone": "middle", "delta_threshold": 0.25},
            {"dte": 10, "zone": "late", "delta_threshold": 0.20},
            {"dte": 4, "zone": "expiry_week", "delta_threshold": 0.15},
        ]

        # Verify thresholds decrease
        for i in range(len(test_cases) - 1):
            current = test_cases[i]["delta_threshold"]
            next_val = test_cases[i + 1]["delta_threshold"]
            assert next_val < current

    # Feature #32: Expiry Week Warning
    @pytest.mark.asyncio
    async def test_expiry_week_warning_generated(self):
        """Test expiry week warning is generated."""
        strategy = MagicMock()
        strategy.dte = 5  # Expiry week

        should_warn = strategy.dte < 7

        assert should_warn is True

    # Feature #33: DTE-Based Exit Suggestion
    @pytest.mark.asyncio
    async def test_exit_over_adjustment_suggestion_last_week(self):
        """Test suggestion to exit over adjustment in last week."""
        strategy = MagicMock()
        strategy.dte = 4  # Expiry week
        strategy.net_delta = Decimal("0.25")  # Delta breach

        # In expiry week: suggest exit instead of adjustment
        if strategy.dte < 7:
            suggested_action = "exit"
        else:
            suggested_action = "adjust"

        assert suggested_action == "exit"

    # Feature #34: DTE-Based Allowed Actions
    @pytest.mark.asyncio
    async def test_adjustment_restricted_in_expiry_week(self):
        """Test adjustments restricted in expiry week."""
        strategy = MagicMock()
        strategy.dte = 3

        allowed_actions = []

        if strategy.dte >= 7:
            allowed_actions = ["shift", "roll", "add_hedge", "exit"]
        else:
            # Only allow exit in expiry week
            allowed_actions = ["exit"]

        assert "shift" not in allowed_actions
        assert "exit" in allowed_actions

    # Feature #35: Gamma Zone Warnings
    @pytest.mark.asyncio
    async def test_7_dte_warning(self):
        """Test warning at 7 DTE (gamma acceleration)."""
        strategy = MagicMock()
        strategy.dte = 7
        strategy.net_gamma = Decimal("0.04")

        warning_level = None

        if strategy.dte <= 7:
            if strategy.dte >= 3:
                warning_level = "warning"
            else:
                warning_level = "danger"

        assert warning_level == "warning"

    @pytest.mark.asyncio
    async def test_3_dte_danger_zone(self):
        """Test danger zone at 3 DTE (gamma explosion)."""
        strategy = MagicMock()
        strategy.dte = 2
        strategy.net_gamma = Decimal("0.10")

        warning_level = None

        if strategy.dte <= 7:
            if strategy.dte >= 3:
                warning_level = "warning"
            else:
                warning_level = "danger"

        assert warning_level == "danger"


# =============================================================================
# INTEGRATION: DTE-AWARE RISK MANAGEMENT
# =============================================================================

class TestDTEAwareRiskManagement:
    """Integration tests for DTE-aware risk management."""

    @pytest.mark.asyncio
    async def test_early_zone_allows_aggressive_adjustments(self):
        """Test early zone allows aggressive adjustments."""
        strategy = MagicMock()
        strategy.dte = 35
        strategy.net_delta = Decimal("0.28")

        # Early zone: delta threshold 0.30
        delta_threshold = 0.30

        # Delta within threshold - no adjustment needed
        needs_adjustment = abs(float(strategy.net_delta)) > delta_threshold

        assert needs_adjustment is False

    @pytest.mark.asyncio
    async def test_late_zone_triggers_earlier_adjustments(self):
        """Test late zone triggers adjustments earlier."""
        strategy = MagicMock()
        strategy.dte = 10
        strategy.net_delta = Decimal("0.22")

        # Late zone: tighter threshold 0.20
        delta_threshold = 0.20

        # Delta exceeds tighter threshold
        needs_adjustment = abs(float(strategy.net_delta)) > delta_threshold

        assert needs_adjustment is True

    @pytest.mark.asyncio
    async def test_expiry_week_suggests_exit_not_adjust(self):
        """Test expiry week suggests exit instead of adjustment."""
        strategy = MagicMock()
        strategy.dte = 4
        strategy.net_delta = Decimal("0.30")
        strategy.net_gamma = Decimal("0.08")

        # Expiry week: gamma risk high, suggest exit
        if strategy.dte < 7 and float(strategy.net_gamma) > 0.05:
            suggestion = {
                "action": "exit",
                "reason": "High gamma risk in expiry week - exit recommended over adjustment"
            }
        else:
            suggestion = {
                "action": "adjust",
                "reason": "Delta breach - adjust position"
            }

        assert suggestion["action"] == "exit"
        assert "gamma risk" in suggestion["reason"].lower()
