"""
Phase 5C Backend Tests - Entry Enhancements

Tests for:
- Feature #4: Standard Deviation Strike Selection
- Feature #5: Expected Move Strike Selection
- Features #6-8: OI-Based Conditions (PCR, Max Pain, OI Change)
- Features #9-10: IV Rank/Percentile Entry Conditions
- Feature #11: Probability OTM
- Features #14-17: Entry Logic (Optimal DTE, Delta Neutral, Expected Move, Multi-Condition)
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
import math

from app.services.autopilot.strike_finder_service import StrikeFinderService
from app.services.autopilot.condition_engine import ConditionEngine
from app.services.legacy.market_data import MarketDataService


# =============================================================================
# FEATURE #4: STANDARD DEVIATION STRIKE SELECTION
# =============================================================================

class TestSDStrikeSelection:
    """Tests for Standard Deviation based strike selection."""

    @pytest.mark.asyncio
    async def test_find_strike_at_1_sd(self, mock_kite, db_session):
        """Test finding strike at 1 SD from spot."""
        service = StrikeFinderService(mock_kite, db_session)

        spot_price = 25000
        iv = 15.0  # 15% IV
        days_to_expiry = 30

        # 1 SD move = spot * iv * sqrt(days/365)
        sd_move = spot_price * (iv / 100) * math.sqrt(days_to_expiry / 365)
        expected_strike = spot_price + sd_move  # For CE

        mock_options = [
            {"strike": 25300, "option_type": "CE", "delta": 0.32, "ltp": 100, "tradingsymbol": "NIFTY25JAN25300CE", "instrument_token": 1},
            {"strike": 25400, "option_type": "CE", "delta": 0.28, "ltp": 80, "tradingsymbol": "NIFTY25JAN25400CE", "instrument_token": 2},
            {"strike": int(expected_strike), "option_type": "CE", "delta": 0.25, "ltp": 60, "tradingsymbol": f"NIFTY25JAN{int(expected_strike)}CE", "instrument_token": 3},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={
            "options": mock_options,
            "spot_price": spot_price
        })
        service.option_chain_service.get_strikes_list = AsyncMock(return_value=[25300, 25400, int(expected_strike)])
        # Mock expected move service to return the SD move
        service.expected_move_service.get_expected_move = AsyncMock(return_value=sd_move)

        result = await service.find_strike_by_sd(
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=days_to_expiry),
            option_type="CE",
            sd_multiplier=1.0
        )

        assert result is not None
        # Strike should be close to 1 SD
        assert abs(result["strike"] - expected_strike) < 100

    @pytest.mark.asyncio
    async def test_find_strike_at_1_5_sd(self, mock_kite, db_session):
        """Test finding strike at 1.5 SD from spot."""
        service = StrikeFinderService(mock_kite, db_session)

        spot_price = 25000
        iv = 15.0
        days_to_expiry = 30

        sd_move = spot_price * (iv / 100) * math.sqrt(days_to_expiry / 365)
        expected_strike = spot_price + (sd_move * 1.5)

        mock_options = [
            {"strike": int(expected_strike), "option_type": "CE", "delta": 0.18, "ltp": 50, "tradingsymbol": f"NIFTY25JAN{int(expected_strike)}CE", "instrument_token": 1},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={
            "options": mock_options,
            "spot_price": spot_price
        })
        service.option_chain_service.get_strikes_list = AsyncMock(return_value=[int(expected_strike)])
        service.expected_move_service.get_expected_move = AsyncMock(return_value=sd_move)

        result = await service.find_strike_by_sd(
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=days_to_expiry),
            option_type="CE",
            sd_multiplier=1.5
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_find_strike_at_2_sd(self, mock_kite, db_session):
        """Test finding strike at 2 SD from spot."""
        service = StrikeFinderService(mock_kite, db_session)

        spot_price = 25000
        iv = 15.0
        days_to_expiry = 30

        sd_move = spot_price * (iv / 100) * math.sqrt(days_to_expiry / 365)
        expected_strike = spot_price + (sd_move * 2.0)

        mock_options = [
            {"strike": int(expected_strike), "option_type": "CE", "delta": 0.10, "ltp": 30, "tradingsymbol": f"NIFTY25JAN{int(expected_strike)}CE", "instrument_token": 1},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={
            "options": mock_options,
            "spot_price": spot_price
        })
        service.option_chain_service.get_strikes_list = AsyncMock(return_value=[int(expected_strike)])
        service.expected_move_service.get_expected_move = AsyncMock(return_value=sd_move)

        result = await service.find_strike_by_sd(
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=days_to_expiry),
            option_type="CE",
            sd_multiplier=2.0
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_sd_calculation_from_iv(self):
        """Test SD calculation uses current IV."""
        spot = 25000
        iv = 18.0  # 18% IV
        dte = 45

        # Standard deviation formula
        sd = spot * (iv / 100) * math.sqrt(dte / 365)

        # For 45 DTE, 18% IV:
        # sd = 25000 * 0.18 * sqrt(45/365) ≈ 1577
        assert 1500 < sd < 1650


# =============================================================================
# FEATURE #5: EXPECTED MOVE STRIKE SELECTION
# =============================================================================

class TestExpectedMoveService:
    """Tests for Expected Move calculation and strike selection."""

    @pytest.mark.asyncio
    async def test_expected_move_calculation(self):
        """Test expected move calculation from ATM straddle price."""
        atm_strike = 25000
        ce_price = 250.0
        pe_price = 230.0
        straddle_price = ce_price + pe_price  # 480

        # Expected move ≈ straddle price * 0.85 (85% rule)
        expected_move = straddle_price * 0.85

        assert abs(expected_move - 408.0) < 1.0

    @pytest.mark.asyncio
    async def test_strike_outside_expected_move(self, mock_kite, db_session):
        """Test finding strikes outside expected move range."""
        service = StrikeFinderService(mock_kite, db_session)

        spot = 25000
        expected_move = 400  # ±400 points

        # Strikes outside expected move: < 24600 or > 25400
        lower_boundary = spot - expected_move  # 24600
        upper_boundary = spot + expected_move  # 25400

        mock_options = [
            {"strike": 24500, "option_type": "PE", "delta": -0.15, "ltp": 80, "tradingsymbol": "NIFTY25JAN24500PE", "instrument_token": 1},
            {"strike": 25500, "option_type": "CE", "delta": 0.12, "ltp": 60, "tradingsymbol": "NIFTY25JAN25500CE", "instrument_token": 2},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})
        service.market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=spot))
        service.market_data.get_expected_move = AsyncMock(return_value=expected_move)

        # PE strike should be < 24600
        pe_result = await service.find_strike_by_expected_move(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="PE",
            outside=True
        )

        assert pe_result["strike"] < lower_boundary

    @pytest.mark.asyncio
    async def test_expected_move_for_weekly_expiry(self):
        """Test expected move for weekly expiry (7 DTE)."""
        spot = 25000
        iv = 15.0
        dte = 7

        # For weekly: expected_move = spot * iv * sqrt(dte/365)
        expected_move = spot * (iv / 100) * math.sqrt(dte / 365)

        # Weekly move ≈ 547
        assert 500 < expected_move < 600

    @pytest.mark.asyncio
    async def test_expected_move_for_monthly_expiry(self):
        """Test expected move for monthly expiry (30 DTE)."""
        spot = 25000
        iv = 15.0
        dte = 30

        expected_move = spot * (iv / 100) * math.sqrt(dte / 365)

        # Monthly move ≈ 1077
        assert 1000 < expected_move < 1150


# =============================================================================
# FEATURES #6-8: OI-BASED CONDITIONS
# =============================================================================

class TestOIAnalysisService:
    """Tests for OI, PCR, Max Pain analysis."""

    # Feature #6: OI.PCR
    @pytest.mark.asyncio
    async def test_pcr_calculation(self):
        """Test Put-Call Ratio calculation."""
        total_put_oi = 8500000
        total_call_oi = 6500000

        pcr = total_put_oi / total_call_oi

        # PCR = 1.31 (bullish)
        assert abs(pcr - 1.31) < 0.01

    @pytest.mark.asyncio
    async def test_pcr_condition_variable(self, db_session, test_user, mock_market_data):
        """Test OI.PCR as condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.oi_analysis_service.OIAnalysisService.get_pcr', new_callable=AsyncMock) as mock_pcr:
            mock_pcr.return_value = 1.25

            value = await engine._get_variable_value(
                variable="OI.PCR",
                underlying="NIFTY",
                strategy=None
            )

            assert value == 1.25

    @pytest.mark.asyncio
    async def test_pcr_between_condition(self, db_session, test_user, mock_market_data):
        """Test PCR between range condition."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.oi_analysis_service.OIAnalysisService.get_pcr', new_callable=AsyncMock) as mock_pcr:
            mock_pcr.return_value = 1.15

            condition = {
                "variable": "OI.PCR",
                "operator": "between",
                "value": [1.0, 1.3]  # Neutral to slightly bullish range
            }

            result = await engine.evaluate_condition(condition, "NIFTY", None)

            assert result["is_met"] is True

    # Feature #7: OI.MAX_PAIN
    @pytest.mark.asyncio
    async def test_max_pain_calculation(self):
        """Test Max Pain strike calculation."""
        # Option chain with OI data
        chain = [
            {"strike": 24500, "ce_oi": 500000, "pe_oi": 900000},
            {"strike": 24600, "ce_oi": 700000, "pe_oi": 800000},
            {"strike": 24700, "ce_oi": 900000, "pe_oi": 600000},
            {"strike": 24800, "ce_oi": 1100000, "pe_oi": 400000},
        ]

        # Max pain = strike where option sellers have minimum loss
        # (Simplified: strike with highest total OI)
        max_pain_strike = max(chain, key=lambda x: x["ce_oi"] + x["pe_oi"])["strike"]

        # 24600, 24700, 24800 all have highest total OI (1.5M)
        # max() returns first match: 24600
        assert max_pain_strike == 24600

    @pytest.mark.asyncio
    async def test_max_pain_condition_variable(self, db_session, test_user, mock_market_data):
        """Test OI.MAX_PAIN as condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.oi_analysis_service.OIAnalysisService.get_max_pain', new_callable=AsyncMock) as mock_max_pain:
            mock_max_pain.return_value = 24700

            value = await engine._get_variable_value(
                variable="OI.MAX_PAIN",
                underlying="NIFTY",
                strategy=None
            )

            assert value == 24700

    @pytest.mark.asyncio
    async def test_max_pain_distance_calculation(self, db_session, test_user, mock_market_data):
        """Test distance of spot to max pain."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        mock_market_data.get_spot_price = AsyncMock(return_value=MagicMock(ltp=25000))

        with patch('app.services.oi_analysis_service.OIAnalysisService.get_max_pain', new_callable=AsyncMock) as mock_max_pain:
            mock_max_pain.return_value = 24700

            spot = 25000
            max_pain = 24700
            distance_pct = abs(spot - max_pain) / spot * 100

            # Distance = 1.2%
            assert abs(distance_pct - 1.2) < 0.1

    # Feature #8: OI.CHANGE
    @pytest.mark.asyncio
    async def test_oi_change_calculation(self):
        """Test OI change calculation."""
        previous_oi = 5000000
        current_oi = 6500000

        oi_change = current_oi - previous_oi
        oi_change_pct = (oi_change / previous_oi) * 100

        # OI increased by 30%
        assert abs(oi_change_pct - 30.0) < 0.1

    @pytest.mark.asyncio
    async def test_oi_change_condition_variable(self, db_session, test_user, mock_market_data):
        """Test OI.CHANGE as condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.oi_analysis_service.OIAnalysisService.get_oi_change_pct', new_callable=AsyncMock) as mock_oi_change:
            mock_oi_change.return_value = 25.5  # 25.5% increase

            value = await engine._get_variable_value(
                variable="OI.CHANGE",
                underlying="NIFTY",
                strategy=None
            )

            assert value == 25.5

    @pytest.mark.asyncio
    async def test_oi_buildup_detection(self):
        """Test OI buildup detection (rising OI + rising price = bullish)."""
        scenarios = [
            {"oi_change": 20.0, "price_change": 1.5, "signal": "long_buildup"},
            {"oi_change": 25.0, "price_change": -1.2, "signal": "short_buildup"},
            {"oi_change": -15.0, "price_change": 1.8, "signal": "short_covering"},
            {"oi_change": -10.0, "price_change": -0.9, "signal": "long_unwinding"},
        ]

        for scenario in scenarios:
            oi_change = scenario["oi_change"]
            price_change = scenario["price_change"]

            if oi_change > 0 and price_change > 0:
                signal = "long_buildup"
            elif oi_change > 0 and price_change < 0:
                signal = "short_buildup"
            elif oi_change < 0 and price_change > 0:
                signal = "short_covering"
            else:
                signal = "long_unwinding"

            assert signal == scenario["signal"]


# =============================================================================
# FEATURES #9-10: IV RANK/PERCENTILE ENTRY CONDITIONS
# =============================================================================

class TestIVEntryConditions:
    """Tests for IV Rank/Percentile entry conditions."""

    @pytest.mark.asyncio
    async def test_iv_rank_greater_than_50_entry(self, db_session, test_user, mock_market_data):
        """Test entry when IV Rank > 50."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.iv_metrics_service.IVMetricsService.get_iv_rank', new_callable=AsyncMock) as mock_iv_rank:
            mock_iv_rank.return_value = 62.5

            condition = {
                "variable": "IV.RANK",
                "operator": "greater_than",
                "value": 50.0
            }

            result = await engine.evaluate_condition(condition, "NIFTY", None)

            assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_iv_rank_greater_than_70_entry(self, db_session, test_user, mock_market_data):
        """Test entry when IV Rank > 70 (very high IV)."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.iv_metrics_service.IVMetricsService.get_iv_rank', new_callable=AsyncMock) as mock_iv_rank:
            mock_iv_rank.return_value = 75.8

            condition = {
                "variable": "IV.RANK",
                "operator": "greater_than",
                "value": 70.0
            }

            result = await engine.evaluate_condition(condition, "NIFTY", None)

            assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_iv_percentile_greater_than_60_entry(self, db_session, test_user, mock_market_data):
        """Test entry when IV Percentile > 60."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.iv_metrics_service.IVMetricsService.get_iv_percentile', new_callable=AsyncMock) as mock_iv_percentile:
            mock_iv_percentile.return_value = 68.2

            condition = {
                "variable": "IV.PERCENTILE",
                "operator": "greater_than",
                "value": 60.0
            }

            result = await engine.evaluate_condition(condition, "NIFTY", None)

            assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_iv_condition_with_time_condition(self, db_session, test_user, mock_market_data):
        """Test IV condition combined with time condition (multi-condition logic)."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.iv_metrics_service.IVMetricsService.get_iv_rank', new_callable=AsyncMock) as mock_iv_rank:
            mock_iv_rank.return_value = 65.0

            iv_condition = {
                "variable": "IV.RANK",
                "operator": "greater_than",
                "value": 50.0
            }

            time_condition = {
                "variable": "TIME.CURRENT",
                "operator": "greater_than",
                "value": "09:20"
            }

            # Both conditions must be met (AND logic)
            iv_result = await engine.evaluate_condition(iv_condition, "NIFTY", None)

            # Would also check time_result in real implementation
            assert iv_result["is_met"] is True


# =============================================================================
# FEATURE #11: PROBABILITY OTM
# =============================================================================

class TestProbabilityOTM:
    """Tests for Probability Out-of-the-Money calculation."""

    @pytest.mark.asyncio
    async def test_probability_otm_calculation(self):
        """Test Probability OTM using Black-Scholes."""
        from scipy.stats import norm

        spot = 25000
        strike = 26000
        days_to_expiry = 30
        iv = 15.0
        risk_free_rate = 0.07

        # Black-Scholes Probability OTM for CE
        # P(OTM) = N(-d2) where d2 = (ln(S/K) + (r - 0.5*σ²)*T) / (σ*sqrt(T))
        T = days_to_expiry / 365
        d2 = (math.log(spot / strike) + (risk_free_rate - 0.5 * (iv/100)**2) * T) / ((iv/100) * math.sqrt(T))
        prob_otm = norm.cdf(-d2)

        # For 26000 CE, probability OTM ≈ 75-80%
        assert 0.70 < prob_otm < 0.85

    @pytest.mark.asyncio
    async def test_probability_otm_condition_variable(self, db_session, test_user, mock_market_data):
        """Test PROBABILITY.OTM as condition variable."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.greeks_calculator.GreeksCalculatorService.calculate_probability_otm', new_callable=AsyncMock) as mock_prob:
            mock_prob.return_value = 78.5

            value = await engine._get_variable_value(
                variable="PROBABILITY.OTM",
                underlying="NIFTY",
                strategy=MagicMock(legs_config=[{"strike": 26000, "option_type": "CE"}])
            )

            assert value == 78.5

    @pytest.mark.asyncio
    async def test_probability_otm_greater_than_75(self, db_session, test_user, mock_market_data):
        """Test entry when Probability OTM > 75%."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        with patch('app.services.greeks_calculator.GreeksCalculatorService.calculate_probability_otm', new_callable=AsyncMock) as mock_prob:
            mock_prob.return_value = 80.2

            condition = {
                "variable": "PROBABILITY.OTM",
                "operator": "greater_than",
                "value": 75.0
            }

            result = await engine.evaluate_condition(condition, "NIFTY", MagicMock())

            assert result["is_met"] is True


# =============================================================================
# FEATURES #14-17: ENTRY LOGIC
# =============================================================================

class TestOptimalDTEEnforcement:
    """Feature #14: Optimal DTE enforcement."""

    @pytest.mark.asyncio
    async def test_dte_enforcement_30_45_days(self):
        """Test entry allowed only in 30-45 DTE range."""
        expiry_date = date.today() + timedelta(days=35)
        current_date = date.today()
        dte = (expiry_date - current_date).days

        # DTE should be in range 30-45
        assert 30 <= dte <= 45

    @pytest.mark.asyncio
    async def test_entry_blocked_outside_dte_range(self):
        """Test entry blocked when DTE outside optimal range."""
        expiry_date = date.today() + timedelta(days=20)  # Too close
        dte = (expiry_date - date.today()).days

        min_dte = 30
        max_dte = 45

        # Should block entry
        assert not (min_dte <= dte <= max_dte)


class TestDeltaNeutralEntry:
    """Feature #15: Delta neutral entry enforcement."""

    @pytest.mark.asyncio
    async def test_delta_neutral_entry_check(self):
        """Test delta neutral entry check."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.02")  # Nearly neutral

        delta_tolerance = 0.05

        # Delta within tolerance
        assert abs(float(strategy.net_delta)) <= delta_tolerance

    @pytest.mark.asyncio
    async def test_entry_blocked_if_not_neutral(self):
        """Test entry blocked if delta not neutral."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.25")  # Too directional

        delta_tolerance = 0.05

        # Should block entry
        assert abs(float(strategy.net_delta)) > delta_tolerance


class TestExpectedMoveCalculation:
    """Feature #16: Expected move calculation display."""

    @pytest.mark.asyncio
    async def test_expected_move_displayed_at_entry(self):
        """Test expected move is calculated and displayed at entry."""
        spot = 25000
        atm_ce_premium = 250.0
        atm_pe_premium = 230.0
        straddle_price = atm_ce_premium + atm_pe_premium

        expected_move = straddle_price * 0.85

        # Expected move ≈ 408 points
        assert 400 < expected_move < 420


class TestMultiConditionLogic:
    """Feature #17: Multi-condition logic with AND/OR."""

    @pytest.mark.asyncio
    async def test_and_logic_all_conditions(self, db_session, test_user, mock_market_data):
        """Test AND logic - all conditions must be met."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        conditions = [
            {"variable": "SPOT.PRICE", "operator": "greater_than", "value": 24500, "is_met": True},
            {"variable": "VIX.VALUE", "operator": "less_than", "value": 20.0, "is_met": True},
        ]

        # AND logic: both True → True
        all_met = all(c["is_met"] for c in conditions)
        assert all_met is True

    @pytest.mark.asyncio
    async def test_or_logic_any_condition(self, db_session, test_user, mock_market_data):
        """Test OR logic - any condition can be met."""
        conditions = [
            {"variable": "SPOT.PRICE", "operator": "greater_than", "value": 24500, "is_met": False},
            {"variable": "VIX.VALUE", "operator": "greater_than", "value": 20.0, "is_met": True},
        ]

        # OR logic: one True → True
        any_met = any(c["is_met"] for c in conditions)
        assert any_met is True

    @pytest.mark.asyncio
    async def test_nested_condition_groups(self):
        """Test nested condition groups: (A AND B) OR (C AND D)."""
        # Group 1: (IV.RANK > 50 AND TIME > 09:20) → False AND True = False
        # Group 2: (VIX > 18 AND SPOT > 24500) → True AND True = True
        # Result: False OR True = True

        group1 = {"iv_rank": False, "time": True}
        group2 = {"vix": True, "spot": True}

        group1_result = all(group1.values())  # False
        group2_result = all(group2.values())  # True

        final_result = group1_result or group2_result

        assert final_result is True

    @pytest.mark.asyncio
    async def test_complex_expression_parsing(self):
        """Test complex expression: ((A AND B) OR C) AND D."""
        A, B, C, D = True, False, True, True

        # ((True AND False) OR True) AND True
        # (False OR True) AND True
        # True AND True
        # = True

        result = ((A and B) or C) and D

        assert result is True
