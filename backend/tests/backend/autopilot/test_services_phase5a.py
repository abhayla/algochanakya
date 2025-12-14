"""
Phase 5A Backend Tests - Quick Wins

Tests for:
- Feature #1: Delta Range Strike Selection
- Feature #2: Premium Range Strike Selection
- Feature #3: Round Strike Preference
- Features #54-57: Greeks as Entry/Exit Conditions (DELTA.NET, GAMMA.NET, THETA.NET, VEGA.NET)
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date

from app.services.strike_finder_service import StrikeFinderService
from app.services.condition_engine import ConditionEngine
from app.services.market_data import MarketDataService


# =============================================================================
# FEATURE #1: DELTA RANGE STRIKE SELECTION
# =============================================================================

class TestDeltaRangeStrikeSelection:
    """Tests for delta range strike selection."""

    @pytest.mark.asyncio
    async def test_find_strike_in_delta_range_success(self, mock_kite, db_session):
        """Test finding strike within delta range."""
        service = StrikeFinderService(mock_kite, db_session)

        # Mock option chain with various deltas
        mock_options = [
            {"strike": 24500, "option_type": "CE", "delta": 0.45, "ltp": 150, "tradingsymbol": "NIFTY25JAN24500CE", "instrument_token": 1},
            {"strike": 24500, "option_type": "PE", "delta": -0.55, "ltp": 200, "tradingsymbol": "NIFTY25JAN24500PE", "instrument_token": 2},
            {"strike": 24600, "option_type": "CE", "delta": 0.35, "ltp": 120, "tradingsymbol": "NIFTY25JAN24600CE", "instrument_token": 3},
            {"strike": 24600, "option_type": "PE", "delta": -0.65, "ltp": 250, "tradingsymbol": "NIFTY25JAN24600PE", "instrument_token": 4},
            {"strike": 24700, "option_type": "CE", "delta": 0.25, "ltp": 90, "tradingsymbol": "NIFTY25JAN24700CE", "instrument_token": 5},
            {"strike": 24700, "option_type": "PE", "delta": -0.75, "ltp": 300, "tradingsymbol": "NIFTY25JAN24700PE", "instrument_token": 6},
            {"strike": 24800, "option_type": "CE", "delta": 0.15, "ltp": 60, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 7},
            {"strike": 24800, "option_type": "PE", "delta": -0.85, "ltp": 350, "tradingsymbol": "NIFTY25JAN24800PE", "instrument_token": 8},
            {"strike": 24900, "option_type": "CE", "delta": 0.08, "ltp": 40, "tradingsymbol": "NIFTY25JAN24900CE", "instrument_token": 9},
            {"strike": 24900, "option_type": "PE", "delta": -0.92, "ltp": 400, "tradingsymbol": "NIFTY25JAN24900PE", "instrument_token": 10},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta_range(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            min_delta=0.10,
            max_delta=0.20
        )

        assert result is not None
        assert result["strike"] == 24800
        assert 0.10 <= abs(result["ce_delta"]) <= 0.20

    @pytest.mark.asyncio
    async def test_find_strike_delta_range_no_match(self, mock_kite, db_session):
        """Test when no strike matches delta range."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24500, "option_type": "CE", "delta": 0.45, "ltp": 100, "tradingsymbol": "NIFTY25JAN24500CE", "instrument_token": 1},
            {"strike": 24500, "option_type": "PE", "delta": -0.55, "ltp": 150, "tradingsymbol": "NIFTY25JAN24500PE", "instrument_token": 2},
            {"strike": 24600, "option_type": "CE", "delta": 0.35, "ltp": 100, "tradingsymbol": "NIFTY25JAN24600CE", "instrument_token": 3},
            {"strike": 24600, "option_type": "PE", "delta": -0.65, "ltp": 150, "tradingsymbol": "NIFTY25JAN24600PE", "instrument_token": 4},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta_range(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            min_delta=0.05,
            max_delta=0.08
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_find_strike_delta_range_multiple_matches_picks_closest(self, mock_kite, db_session):
        """Test that when multiple strikes match, picks the one closest to midpoint."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24700, "option_type": "CE", "delta": 0.12, "ltp": 100, "tradingsymbol": "NIFTY25JAN24700CE", "instrument_token": 1},
            {"strike": 24700, "option_type": "PE", "delta": -0.88, "ltp": 150, "tradingsymbol": "NIFTY25JAN24700PE", "instrument_token": 2},
            {"strike": 24800, "option_type": "CE", "delta": 0.15, "ltp": 100, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 3},
            {"strike": 24800, "option_type": "PE", "delta": -0.85, "ltp": 150, "tradingsymbol": "NIFTY25JAN24800PE", "instrument_token": 4},
            {"strike": 24900, "option_type": "CE", "delta": 0.18, "ltp": 100, "tradingsymbol": "NIFTY25JAN24900CE", "instrument_token": 5},
            {"strike": 24900, "option_type": "PE", "delta": -0.82, "ltp": 150, "tradingsymbol": "NIFTY25JAN24900PE", "instrument_token": 6},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta_range(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            min_delta=0.10,
            max_delta=0.20
        )

        assert result["strike"] == 24800

    @pytest.mark.asyncio
    async def test_delta_range_validation_min_greater_than_max(self, mock_kite, db_session):
        """Test validation error when min_delta > max_delta."""
        service = StrikeFinderService(mock_kite, db_session)

        with pytest.raises(ValueError, match="min_delta must be less than max_delta"):
            await service.find_strike_by_delta_range(
                underlying="NIFTY",
                expiry=date(2025, 1, 30),
                option_type="CE",
                min_delta=0.20,
                max_delta=0.10
            )

    @pytest.mark.asyncio
    async def test_delta_range_with_round_strike_preference(self, mock_kite, db_session):
        """Test delta range with round strike preference enabled."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24750, "option_type": "CE", "delta": 0.15, "ltp": 100, "tradingsymbol": "NIFTY25JAN24750CE", "instrument_token": 1},
            {"strike": 24750, "option_type": "PE", "delta": -0.85, "ltp": 150, "tradingsymbol": "NIFTY25JAN24750PE", "instrument_token": 2},
            {"strike": 24800, "option_type": "CE", "delta": 0.17, "ltp": 100, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 3},
            {"strike": 24800, "option_type": "PE", "delta": -0.83, "ltp": 150, "tradingsymbol": "NIFTY25JAN24800PE", "instrument_token": 4},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta_range(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            min_delta=0.10,
            max_delta=0.20,
            prefer_round_strike=True
        )

        # Should prefer 24800 (round strike) over 24750
        assert result["strike"] == 24800


# =============================================================================
# FEATURE #2: PREMIUM RANGE STRIKE SELECTION
# =============================================================================

class TestPremiumRangeStrikeSelection:
    """Tests for premium range strike selection."""

    @pytest.mark.asyncio
    async def test_find_strike_in_premium_range_success(self, mock_kite, db_session):
        """Test finding strike within premium range."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24700, "option_type": "CE", "ltp": 150.25, "delta": 0.25, "tradingsymbol": "NIFTY25JAN24700CE", "instrument_token": 1},
            {"strike": 24800, "option_type": "CE", "ltp": 120.50, "delta": 0.15, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 2},
            {"strike": 24900, "option_type": "CE", "ltp": 90.75, "delta": 0.08, "tradingsymbol": "NIFTY25JAN24900CE", "instrument_token": 3},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_premium_range(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            min_premium=100.0,
            max_premium=130.0
        )

        assert result is not None
        assert result["strike"] == 24800
        assert result["ce_ltp"] == 120.50

    @pytest.mark.asyncio
    async def test_find_strike_premium_range_no_match(self, mock_kite, db_session):
        """Test when no strike matches premium range."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24700, "option_type": "CE", "ltp": 150.25, "delta": 0.25, "tradingsymbol": "NIFTY25JAN24700CE", "instrument_token": 1},
            {"strike": 24800, "option_type": "CE", "ltp": 120.50, "delta": 0.15, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 2},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_premium_range(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            min_premium=50.0,
            max_premium=70.0
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_premium_range_with_delta_constraint(self, mock_kite, db_session):
        """Test premium range with additional delta constraint."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24700, "option_type": "CE", "ltp": 150.25, "delta": 0.25, "tradingsymbol": "NIFTY25JAN24700CE", "instrument_token": 1},
            {"strike": 24800, "option_type": "CE", "ltp": 120.50, "delta": 0.15, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 2},
            {"strike": 24900, "option_type": "CE", "ltp": 100.75, "delta": 0.08, "tradingsymbol": "NIFTY25JAN24900CE", "instrument_token": 3},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_premium_range(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            min_premium=100.0,
            max_premium=160.0,
            delta_constraint={"min": 0.10, "max": 0.20}
        )

        # Should match 24800 (delta 0.15 within constraint)
        assert result["strike"] == 24800

    @pytest.mark.asyncio
    async def test_premium_range_validation(self, mock_kite, db_session):
        """Test validation error when min_premium > max_premium."""
        service = StrikeFinderService(mock_kite, db_session)

        with pytest.raises(ValueError, match="min_premium must be less than max_premium"):
            await service.find_strike_by_premium_range(
                underlying="NIFTY",
                expiry=date(2025, 1, 30),
                option_type="CE",
                min_premium=200.0,
                max_premium=100.0
            )


# =============================================================================
# FEATURE #3: ROUND STRIKE PREFERENCE
# =============================================================================

class TestRoundStrikePreference:
    """Tests for round strike preference feature."""

    @pytest.mark.asyncio
    async def test_prefers_strike_divisible_by_100(self, mock_kite, db_session):
        """Test that round strike preference selects strikes divisible by 100."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24750, "option_type": "CE", "delta": 0.15, "ltp": 100, "tradingsymbol": "NIFTY25JAN24750CE", "instrument_token": 1},
            {"strike": 24750, "option_type": "PE", "delta": -0.85, "ltp": 150, "tradingsymbol": "NIFTY25JAN24750PE", "instrument_token": 2},
            {"strike": 24800, "option_type": "CE", "delta": 0.16, "ltp": 100, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 3},
            {"strike": 24800, "option_type": "PE", "delta": -0.84, "ltp": 150, "tradingsymbol": "NIFTY25JAN24800PE", "instrument_token": 4},
            {"strike": 24850, "option_type": "CE", "delta": 0.14, "ltp": 100, "tradingsymbol": "NIFTY25JAN24850CE", "instrument_token": 5},
            {"strike": 24850, "option_type": "PE", "delta": -0.86, "ltp": 150, "tradingsymbol": "NIFTY25JAN24850PE", "instrument_token": 6},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            target_delta=0.15,
            prefer_round_strike=True,
            round_strike_divisor=100
        )

        assert result["strike"] % 100 == 0
        assert result["strike"] == 24800

    @pytest.mark.asyncio
    async def test_prefers_strike_divisible_by_50_if_no_100(self, mock_kite, db_session):
        """Test fallback to divisible by 50 if no strike divisible by 100."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24725, "option_type": "CE", "delta": 0.15, "ltp": 100, "tradingsymbol": "NIFTY25JAN24725CE", "instrument_token": 1},
            {"strike": 24725, "option_type": "PE", "delta": -0.85, "ltp": 150, "tradingsymbol": "NIFTY25JAN24725PE", "instrument_token": 2},
            {"strike": 24750, "option_type": "CE", "delta": 0.16, "ltp": 100, "tradingsymbol": "NIFTY25JAN24750CE", "instrument_token": 3},
            {"strike": 24750, "option_type": "PE", "delta": -0.84, "ltp": 150, "tradingsymbol": "NIFTY25JAN24750PE", "instrument_token": 4},
            {"strike": 24775, "option_type": "CE", "delta": 0.14, "ltp": 100, "tradingsymbol": "NIFTY25JAN24775CE", "instrument_token": 5},
            {"strike": 24775, "option_type": "PE", "delta": -0.86, "ltp": 150, "tradingsymbol": "NIFTY25JAN24775PE", "instrument_token": 6},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            target_delta=0.15,
            prefer_round_strike=True,
            round_strike_divisor=50
        )

        assert result["strike"] % 50 == 0
        assert result["strike"] == 24750

    @pytest.mark.asyncio
    async def test_round_strike_with_delta_constraint(self, mock_kite, db_session):
        """Test round strike preference maintains delta accuracy."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24700, "option_type": "CE", "delta": 0.25, "ltp": 100, "tradingsymbol": "NIFTY25JAN24700CE", "instrument_token": 1},
            {"strike": 24700, "option_type": "PE", "delta": -0.75, "ltp": 150, "tradingsymbol": "NIFTY25JAN24700PE", "instrument_token": 2},
            {"strike": 24750, "option_type": "CE", "delta": 0.16, "ltp": 100, "tradingsymbol": "NIFTY25JAN24750CE", "instrument_token": 3},
            {"strike": 24750, "option_type": "PE", "delta": -0.84, "ltp": 150, "tradingsymbol": "NIFTY25JAN24750PE", "instrument_token": 4},
            {"strike": 24800, "option_type": "CE", "delta": 0.15, "ltp": 100, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 5},
            {"strike": 24800, "option_type": "PE", "delta": -0.85, "ltp": 150, "tradingsymbol": "NIFTY25JAN24800PE", "instrument_token": 6},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            target_delta=0.15,
            prefer_round_strike=True,
            delta_tolerance=0.02
        )

        # Should pick 24800 (round and within delta tolerance)
        assert result["strike"] == 24800

    @pytest.mark.asyncio
    async def test_round_strike_disabled_returns_exact_match(self, mock_kite, db_session):
        """Test that with round strike disabled, returns exact delta match."""
        service = StrikeFinderService(mock_kite, db_session)

        mock_options = [
            {"strike": 24750, "option_type": "CE", "delta": 0.150, "ltp": 100, "tradingsymbol": "NIFTY25JAN24750CE", "instrument_token": 1},
            {"strike": 24750, "option_type": "PE", "delta": -0.850, "ltp": 150, "tradingsymbol": "NIFTY25JAN24750PE", "instrument_token": 2},
            {"strike": 24800, "option_type": "CE", "delta": 0.160, "ltp": 100, "tradingsymbol": "NIFTY25JAN24800CE", "instrument_token": 3},
            {"strike": 24800, "option_type": "PE", "delta": -0.840, "ltp": 150, "tradingsymbol": "NIFTY25JAN24800PE", "instrument_token": 4},
        ]

        service.option_chain_service.get_option_chain = AsyncMock(return_value={"options": mock_options})

        result = await service.find_strike_by_delta(
            underlying="NIFTY",
            expiry=date(2025, 1, 30),
            option_type="CE",
            target_delta=0.150,
            prefer_round_strike=False
        )

        assert result["strike"] == 24750


# =============================================================================
# FEATURES #54-57: GREEKS AS ENTRY/EXIT CONDITIONS
# =============================================================================

class TestGreeksConditionVariables:
    """Tests for Greeks (Delta, Gamma, Theta, Vega) as condition variables."""

    # -------------------------------------------------------------------------
    # FEATURE #54: DELTA.NET CONDITION
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_strategy_delta_variable_resolution(self, mock_market_data):
        """Test STRATEGY.DELTA variable resolves to net delta."""
        engine = ConditionEngine(mock_market_data)

        # Mock strategy with net delta
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.25")
        strategy.runtime_state = {
            "greeks": {
                "net_delta": 0.25,
                "net_gamma": 0.02,
                "net_theta": -150.0,
                "net_vega": 200.0
            }
        }

        value = await engine._get_variable_value(
            variable="STRATEGY.DELTA",
            underlying="NIFTY",
            strategy=strategy
        )

        assert value == 0.25

    @pytest.mark.asyncio
    async def test_delta_greater_than_condition(self, mock_market_data):
        """Test delta > threshold condition."""
        engine = ConditionEngine(mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_delta": 0.30}}

        condition = {
            "variable": "STRATEGY.DELTA",
            "operator": "greater_than",
            "value": 0.20
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_delta_between_condition(self, mock_market_data):
        """Test delta between range condition."""
        engine = ConditionEngine(mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_delta": 0.15}}

        condition = {
            "variable": "STRATEGY.DELTA",
            "operator": "between",
            "value": [0.10, 0.20]
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_delta_crosses_above_condition(self, mock_market_data):
        """Test delta crosses above threshold."""
        engine = ConditionEngine(mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {
            "greeks": {"net_delta": 0.25},
            "previous_greeks": {"net_delta": 0.18}
        }

        condition = {
            "variable": "STRATEGY.DELTA",
            "operator": "crosses_above",
            "value": 0.20
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        assert result["is_met"] is True

    # -------------------------------------------------------------------------
    # FEATURE #55: GAMMA.NET CONDITION
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_strategy_gamma_variable_resolution(self, mock_market_data):
        """Test STRATEGY.GAMMA variable resolves to net gamma."""
        engine = ConditionEngine(mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_gamma": 0.03}}

        value = await engine._get_variable_value(
            variable="STRATEGY.GAMMA",
            underlying="NIFTY",
            strategy=strategy
        )

        assert value == 0.03

    @pytest.mark.asyncio
    async def test_gamma_greater_than_threshold(self, db_session, test_user, mock_market_data):
        """Test gamma > threshold (expiry week warning)."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_gamma": 0.06}}

        condition = {
            "variable": "STRATEGY.GAMMA",
            "operator": "greater_than",
            "value": 0.05  # Gamma explosion threshold
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        assert result["is_met"] is True

    @pytest.mark.asyncio
    async def test_gamma_expiry_week_warning(self, db_session, test_user, mock_market_data):
        """Test gamma warning in expiry week (DTE < 7)."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        strategy = MagicMock()
        strategy.dte = 5  # Expiry week
        strategy.runtime_state = {"greeks": {"net_gamma": 0.08}}

        condition = {
            "variable": "STRATEGY.GAMMA",
            "operator": "greater_than",
            "value": 0.05
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        assert result["is_met"] is True
        # In real implementation, would trigger expiry week warning

    # -------------------------------------------------------------------------
    # FEATURE #56: THETA.NET CONDITION
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_strategy_theta_variable_resolution(self, mock_market_data):
        """Test STRATEGY.THETA variable resolves to net theta."""
        engine = ConditionEngine(mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_theta": -250.5}}

        value = await engine._get_variable_value(
            variable="STRATEGY.THETA",
            underlying="NIFTY",
            strategy=strategy
        )

        assert value == -250.5

    @pytest.mark.asyncio
    async def test_theta_decay_threshold(self, db_session, test_user, mock_market_data):
        """Test exit when theta decay exceeds threshold."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_theta": -600.0}}

        # Exit when earning more than 500/day in theta
        condition = {
            "variable": "STRATEGY.THETA",
            "operator": "less_than",
            "value": -500.0
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        assert result["is_met"] is True

    # -------------------------------------------------------------------------
    # FEATURE #57: VEGA.NET CONDITION
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_strategy_vega_variable_resolution(self, mock_market_data):
        """Test STRATEGY.VEGA variable resolves to net vega."""
        engine = ConditionEngine(mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_vega": 350.75}}

        value = await engine._get_variable_value(
            variable="STRATEGY.VEGA",
            underlying="NIFTY",
            strategy=strategy
        )

        assert value == 350.75

    @pytest.mark.asyncio
    async def test_vega_exposure_threshold(self, db_session, test_user, mock_market_data):
        """Test alert when vega exposure too high."""
        engine = ConditionEngine(db_session, test_user.id, mock_market_data)

        strategy = MagicMock()
        strategy.runtime_state = {"greeks": {"net_vega": 1200.0}}

        # Alert when vega > 1000 (₹1000 per 1% IV change)
        condition = {
            "variable": "STRATEGY.VEGA",
            "operator": "greater_than",
            "value": 1000.0
        }

        result = await engine.evaluate_condition(condition, "NIFTY", strategy)

        assert result["is_met"] is True
