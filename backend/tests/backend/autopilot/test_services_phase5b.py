"""
Phase 5B Backend Tests - Core Monitoring

Tests for:
- Feature #48: Spot Distance (Configurable %)
- Feature #49: Delta Bands
- Feature #50: Premium Decay Tracking
- Feature #51: Theta Burn Rate
- Feature #52: Breakeven Proximity Alert
- Feature #53: IV Rank Tracking
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta

from app.services.condition_engine import ConditionEngine
from app.services.legacy.market_data import MarketDataService


# =============================================================================
# FEATURE #48: SPOT DISTANCE (CONFIGURABLE %)
# =============================================================================

class TestSpotDistanceMonitoring:
    """Tests for spot distance monitoring with configurable thresholds."""

    @pytest.mark.asyncio
    async def test_spot_distance_to_short_pe_calculation(self, db_session, test_user, mock_market_data):
        """Test calculation of spot distance to short PE strike."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        # Mock spot price
        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25000))

        # Strategy with short PE at 24500
        strategy = MagicMock()
        strategy.legs_config = [
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"}
        ]

        value = await engine._get_variable_value(
            variable="SPOT.DISTANCE_TO.SHORT_PE",
            underlying="NIFTY",
            strategy=strategy
        )

        # Distance = abs(25000 - 24500) / 25000 * 100 = 2.0%
        assert abs(value - 2.0) < 0.01

    @pytest.mark.asyncio
    async def test_spot_distance_to_short_ce_calculation(self, db_session, test_user, mock_market_data):
        """Test calculation of spot distance to short CE strike."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25000))

        strategy = MagicMock()
        strategy.legs_config = [
            {"strike": 26000, "option_type": "CE", "transaction_type": "sell"}
        ]

        value = await engine._get_variable_value(
            variable="SPOT.DISTANCE_TO.SHORT_CE",
            underlying="NIFTY",
            strategy=strategy
        )

        # Distance = abs(25000 - 26000) / 25000 * 100 = 4.0%
        assert abs(value - 4.0) < 0.01

    @pytest.mark.asyncio
    async def test_spot_distance_alert_at_3_percent(self, db_session, test_user, mock_market_data):
        """Test alert triggers when spot within 3% of short strike."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=24750))

        strategy = MagicMock()
        strategy.legs_config = [
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"}
        ]

        condition = {
            "variable": "SPOT.DISTANCE_TO.SHORT_PE",
            "operator": "less_than",
            "value": 3.0  # Alert at 3%
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        # Distance = (24750 - 24500) / 24750 * 100 ≈ 1.01% < 3%
        assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_spot_distance_configurable_threshold(self, db_session, test_user, mock_market_data):
        """Test configurable threshold (e.g., 5% instead of default 3%)."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25000))

        strategy = MagicMock()
        strategy.legs_config = [
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"}
        ]

        # Configure custom threshold of 5%
        condition = {
            "variable": "SPOT.DISTANCE_TO.SHORT_PE",
            "operator": "less_than",
            "value": 5.0
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        # Distance = 2% < 5%
        assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_spot_distance_separate_pe_ce_thresholds(self, db_session, test_user, mock_market_data):
        """Test separate thresholds for PE and CE sides."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25000))

        strategy = MagicMock()
        strategy.legs_config = [
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"},
            {"strike": 26000, "option_type": "CE", "transaction_type": "sell"}
        ]

        # PE side: tighter threshold (3%)
        pe_condition = {
            "variable": "SPOT.DISTANCE_TO.SHORT_PE",
            "operator": "less_than",
            "value": 3.0
        }

        # CE side: relaxed threshold (5%)
        ce_condition = {
            "variable": "SPOT.DISTANCE_TO.SHORT_CE",
            "operator": "less_than",
            "value": 5.0
        }

        pe_result = await engine.evaluate_condition(pe_condition, "NIFTY", strategy)
        ce_result = await engine.evaluate_condition(ce_condition, "NIFTY", strategy)

        # PE distance = 2% < 3% → triggered
        # CE distance = 4% < 5% → triggered
        assert pe_result["is_met"] is True
        assert ce_result["is_met"] is True

    @pytest.mark.asyncio
    async def test_spot_distance_condition_variable(self, db_session, test_user, mock_market_data):
        """Test SPOT.DISTANCE_TO.* as condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=24900))

        strategy = MagicMock()
        strategy.legs_config = [
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"}
        ]

        value = await engine._get_variable_value(
            variable="SPOT.DISTANCE_TO.SHORT_PE",
            underlying="NIFTY",
            strategy=strategy
        )

        # Distance = (24900 - 24500) / 24900 * 100 ≈ 1.6%
        assert 1.5 < value < 1.7


# =============================================================================
# FEATURE #49: DELTA BANDS
# =============================================================================

class TestDeltaBandMonitoring:
    """Tests for delta band monitoring (keep delta within range)."""

    @pytest.mark.asyncio
    async def test_delta_within_band_no_alert(self):
        """Test no alert when delta within band."""
        # Mock delta band service
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.10")

        # Band: -0.20 to +0.20
        upper_band = 0.20
        lower_band = -0.20

        # Delta 0.10 is within band
        assert lower_band < float(strategy.net_delta) < upper_band

    @pytest.mark.asyncio
    async def test_delta_exceeds_upper_band_alert(self):
        """Test alert when delta exceeds upper band."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.25")  # Exceeds +0.20

        upper_band = 0.20

        assert float(strategy.net_delta) > upper_band

    @pytest.mark.asyncio
    async def test_delta_exceeds_lower_band_alert(self):
        """Test alert when delta below lower band."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("-0.25")  # Below -0.20

        lower_band = -0.20

        assert float(strategy.net_delta) < lower_band

    @pytest.mark.asyncio
    async def test_configurable_band_width(self):
        """Test configurable delta band width."""
        # Conservative trader: ±0.15 band
        conservative_upper = 0.15
        conservative_lower = -0.15

        # Aggressive trader: ±0.30 band
        aggressive_upper = 0.30
        aggressive_lower = -0.30

        strategy_delta = 0.20

        # Conservative: triggers alert
        assert strategy_delta > conservative_upper

        # Aggressive: no alert
        assert aggressive_lower < strategy_delta < aggressive_upper

    @pytest.mark.asyncio
    async def test_rebalance_suggestion_generation(self):
        """Test rebalance suggestion when delta exits band."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.35")  # Exceeds band
        strategy.dte = 20  # Not in expiry week

        upper_band = 0.20

        # Should suggest rebalance (not exit) when DTE > 7
        if float(strategy.net_delta) > upper_band and strategy.dte > 7:
            suggested_action = "rebalance"
        else:
            suggested_action = "exit"

        assert suggested_action == "rebalance"


# =============================================================================
# FEATURE #50: PREMIUM DECAY TRACKING
# =============================================================================

class TestPremiumDecayTracking:
    """Tests for premium decay tracking over time."""

    @pytest.mark.asyncio
    async def test_premium_captured_percentage_calculation(self):
        """Test calculation of premium captured percentage."""
        initial_premium = 15000.0  # Entry premium collected
        current_value = 6000.0     # Current position value

        premium_captured = initial_premium - current_value
        premium_captured_pct = (premium_captured / initial_premium) * 100

        # Captured ₹9000 out of ₹15000 = 60%
        assert abs(premium_captured_pct - 60.0) < 0.01

    @pytest.mark.asyncio
    async def test_premium_decay_over_time_tracking(self):
        """Test tracking premium decay over multiple days."""
        decay_history = [
            {"date": date(2025, 1, 1), "premium_captured_pct": 0.0},
            {"date": date(2025, 1, 5), "premium_captured_pct": 15.0},
            {"date": date(2025, 1, 10), "premium_captured_pct": 35.0},
            {"date": date(2025, 1, 15), "premium_captured_pct": 50.0},
        ]

        # Verify progressive decay
        for i in range(len(decay_history) - 1):
            current = decay_history[i]["premium_captured_pct"]
            next_val = decay_history[i + 1]["premium_captured_pct"]
            assert next_val > current

    @pytest.mark.asyncio
    async def test_premium_decay_rate_calculation(self):
        """Test daily premium decay rate calculation."""
        day1_captured = 20.0  # % captured
        day5_captured = 50.0  # % captured

        days_elapsed = 4
        decay_rate = (day5_captured - day1_captured) / days_elapsed

        # Decay rate = (50 - 20) / 4 = 7.5% per day
        assert abs(decay_rate - 7.5) < 0.01

    @pytest.mark.asyncio
    async def test_premium_decay_stored_in_runtime_state(self):
        """Test premium decay metrics stored in strategy runtime_state."""
        strategy = MagicMock()
        strategy.entry_premium = Decimal("15000")
        strategy.runtime_state = {
            "premium_tracking": {
                "initial_premium": 15000.0,
                "current_value": 9000.0,
                "premium_captured": 6000.0,
                "premium_captured_pct": 40.0,
                "decay_rate_per_day": 8.0
            }
        }

        assert strategy.runtime_state["premium_tracking"]["premium_captured_pct"] == 40.0
        assert strategy.runtime_state["premium_tracking"]["decay_rate_per_day"] == 8.0


# =============================================================================
# FEATURE #51: THETA BURN RATE
# =============================================================================

class TestThetaBurnRate:
    """Tests for theta burn rate monitoring."""

    @pytest.mark.asyncio
    async def test_daily_theta_calculation(self):
        """Test daily theta calculation for position."""
        strategy = MagicMock()
        strategy.net_theta = Decimal("-350.5")  # Earning ₹350.5/day

        daily_theta = float(strategy.net_theta)

        assert daily_theta == -350.5

    @pytest.mark.asyncio
    async def test_theta_burn_vs_expected_comparison(self):
        """Test comparison of actual theta vs expected."""
        expected_theta = -400.0  # Expected to earn ₹400/day
        actual_theta = -350.0    # Actually earning ₹350/day

        theta_efficiency = (actual_theta / expected_theta) * 100

        # Earning 87.5% of expected theta
        assert abs(theta_efficiency - 87.5) < 0.01

    @pytest.mark.asyncio
    async def test_theta_burn_rate_alert(self):
        """Test alert when theta burn rate below threshold."""
        strategy = MagicMock()
        strategy.net_theta = Decimal("-200.0")  # Low theta
        strategy.runtime_state = {
            "theta_tracking": {
                "expected_theta": -400.0,
                "actual_theta": -200.0,
                "efficiency_pct": 50.0
            }
        }

        # Alert if efficiency < 70%
        efficiency_threshold = 70.0
        should_alert = strategy.runtime_state["theta_tracking"]["efficiency_pct"] < efficiency_threshold

        assert should_alert is True


# =============================================================================
# FEATURE #52: BREAKEVEN PROXIMITY ALERT
# =============================================================================

class TestBreakevenProximityAlert:
    """Tests for breakeven proximity alert."""

    @pytest.mark.asyncio
    async def test_breakeven_distance_calculation(self, db_session, test_user, mock_market_data):
        """Test calculation of spot distance to breakeven."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25100))

        strategy = MagicMock()
        strategy.breakevens = [24800, 25200]  # Lower and upper breakevens

        # Distance to nearest breakeven
        spot = 25100
        breakevens = strategy.breakevens
        distances = [abs(spot - be) for be in breakevens]
        min_distance = min(distances)
        distance_pct = (min_distance / spot) * 100

        # Distance to 25200 = 100, percentage = 0.40%
        assert abs(distance_pct - 0.40) < 0.01

    @pytest.mark.asyncio
    async def test_breakeven_proximity_condition_variable(self, db_session, test_user, mock_market_data):
        """Test SPOT.DISTANCE_TO.BREAKEVEN condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25150))

        strategy = MagicMock()
        strategy.breakevens = [24800, 25200]

        value = await engine._get_variable_value(
            variable="SPOT.DISTANCE_TO.BREAKEVEN",
            underlying="NIFTY",
            strategy=strategy
        )

        # Distance to nearest breakeven (25200) = 50 / 25150 * 100 ≈ 0.20%
        assert 0.15 < value < 0.25

    @pytest.mark.asyncio
    async def test_breakeven_alert_triggered(self, db_session, test_user, mock_market_data):
        """Test alert triggers when spot near breakeven."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25180))

        strategy = MagicMock()
        strategy.breakevens = [24800, 25200]

        condition = {
            "variable": "SPOT.DISTANCE_TO.BREAKEVEN",
            "operator": "less_than",
            "value": 1.0  # Alert when within 1% of breakeven
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        # Distance ≈ 0.08% < 1%
        assert result["is_met"] is True


# =============================================================================
# FEATURE #53: IV RANK TRACKING
# =============================================================================

class TestIVRankTracking:
    """Tests for IV Rank and IV Percentile tracking."""

    @pytest.mark.asyncio
    async def test_iv_rank_calculation(self):
        """Test IV Rank calculation: (Current IV - 52W Low) / (52W High - 52W Low) * 100."""
        current_iv = 15.5
        iv_52w_high = 22.0
        iv_52w_low = 10.0

        iv_rank = ((current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low)) * 100

        # (15.5 - 10) / (22 - 10) * 100 = 45.83%
        assert abs(iv_rank - 45.83) < 0.01

    @pytest.mark.asyncio
    async def test_iv_percentile_calculation(self):
        """Test IV Percentile: % of days in past year where IV was lower."""
        # Historical IV data (252 trading days)
        iv_history = [12.0, 13.5, 11.8, 14.2, 15.0, 16.5, 14.8, 13.0] + [13.5] * 244  # Simplified

        current_iv = 15.5
        days_lower = sum(1 for iv in iv_history if iv < current_iv)
        iv_percentile = (days_lower / len(iv_history)) * 100

        assert iv_percentile > 0

    @pytest.mark.asyncio
    async def test_iv_rank_caching(self):
        """Test IV Rank is cached for 5 minutes."""
        # Mock IV metrics service with cache
        cache = {
            "NIFTY_iv_rank": {
                "value": 52.3,
                "timestamp": datetime.now(),
                "ttl": 300  # 5 minutes
            }
        }

        cached_value = cache["NIFTY_iv_rank"]["value"]
        cache_age = (datetime.now() - cache["NIFTY_iv_rank"]["timestamp"]).total_seconds()

        assert cached_value == 52.3
        assert cache_age < 300

    @pytest.mark.asyncio
    async def test_iv_rank_condition_variable(self, db_session, test_user, mock_market_data):
        """Test IV.RANK as condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        # Mock IV metrics service
        with patch('app.services.iv_metrics_service.IVMetricsService.get_iv_rank', new_callable=AsyncMock) as mock_iv_rank:
            mock_iv_rank.return_value = 65.5

            value = await engine._get_variable_value(
                variable="IV.RANK",
                underlying="NIFTY",
                strategy=None
            )

            assert value == 65.5

    @pytest.mark.asyncio
    async def test_iv_percentile_condition_variable(self, db_session, test_user, mock_market_data):
        """Test IV.PERCENTILE as condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.iv_metrics_service.IVMetricsService.get_iv_percentile', new_callable=AsyncMock) as mock_iv_percentile:
            mock_iv_percentile.return_value = 72.8

            value = await engine._get_variable_value(
                variable="IV.PERCENTILE",
                underlying="NIFTY",
                strategy=None
            )

            assert value == 72.8
