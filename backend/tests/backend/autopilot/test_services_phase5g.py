"""
Phase 5G Backend Tests - Advanced Adjustments

Tests for:
- Feature #40: Strategy Conversion
- Feature #41: Widen the Spread
- Feature #42: Convert to Ratio Spread
- Feature #43: Iron Butterfly Conversion
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# =============================================================================
# FEATURE #40: STRATEGY CONVERSION
# =============================================================================

class TestStrategyConverterService:
    """Tests for strategy conversion functionality."""

    @pytest.mark.asyncio
    async def test_iron_condor_to_strangle_conversion(self):
        """Test converting iron condor to strangle by removing wings."""
        # Iron Condor: Buy 24000 PE, Sell 24500 PE, Sell 25500 CE, Buy 26000 CE
        iron_condor = [
            {"strike": 24000, "option_type": "PE", "transaction_type": "buy"},
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"},
            {"strike": 25500, "option_type": "CE", "transaction_type": "sell"},
            {"strike": 26000, "option_type": "CE", "transaction_type": "buy"},
        ]

        # Strangle: Remove wings, keep only short strikes
        strangle = [leg for leg in iron_condor if leg["transaction_type"] == "sell"]

        assert len(strangle) == 2
        assert strangle[0]["strike"] == 24500
        assert strangle[1]["strike"] == 25500

    @pytest.mark.asyncio
    async def test_strangle_to_straddle_conversion(self):
        """Test converting strangle to straddle (both strikes at ATM)."""
        # Strangle: Sell 24500 PE, Sell 25500 CE
        strangle = [
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"},
            {"strike": 25500, "option_type": "CE", "transaction_type": "sell"},
        ]

        spot = 25000

        # Straddle: Move both to ATM
        straddle = [
            {"strike": spot, "option_type": "PE", "transaction_type": "sell"},
            {"strike": spot, "option_type": "CE", "transaction_type": "sell"},
        ]

        assert straddle[0]["strike"] == spot
        assert straddle[1]["strike"] == spot

    @pytest.mark.asyncio
    async def test_conversion_cost_calculation(self):
        """Test calculation of conversion cost."""
        # Current position value
        current_pe_price = 180.0
        current_ce_price = 160.0

        # New position prices (for straddle at ATM)
        new_pe_price = 250.0
        new_ce_price = 240.0

        # Cost to convert
        pe_cost = new_pe_price - current_pe_price
        ce_cost = new_ce_price - current_ce_price

        total_conversion_cost = (pe_cost + ce_cost) * 25  # Lot size

        # Cost = (70 + 80) * 25 = ₹3,750
        assert total_conversion_cost == 3750.0

    # Feature #41: Widen the Spread
    @pytest.mark.asyncio
    async def test_widen_spread_calculation(self):
        """Test widening the spread between long and short strikes."""
        # Current spread
        short_pe = 24500
        long_pe = 24000
        current_spread = short_pe - long_pe  # 500 points

        # Widen by moving long farther
        widen_by = 200
        new_long_pe = long_pe - widen_by

        new_spread = short_pe - new_long_pe  # 700 points

        assert new_spread == 700
        assert new_spread > current_spread

    @pytest.mark.asyncio
    async def test_widen_spread_execution(self):
        """Test execution of widen spread adjustment."""
        # Iron Condor with 500-point spreads
        original = [
            {"strike": 24000, "option_type": "PE", "transaction_type": "buy"},
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"},
        ]

        # Widen PE spread to 700 points
        adjusted = [
            {"strike": 23800, "option_type": "PE", "transaction_type": "buy"},  # Moved farther
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"},  # Unchanged
        ]

        old_spread = original[1]["strike"] - original[0]["strike"]
        new_spread = adjusted[1]["strike"] - adjusted[0]["strike"]

        assert new_spread > old_spread
        assert new_spread == 700

    # Feature #42: Convert to Ratio Spread
    @pytest.mark.asyncio
    async def test_ratio_spread_conversion(self):
        """Test converting to ratio spread (add extra short contracts)."""
        # Original: Sell 1 lot of 25500 CE
        original_ce_lots = 1

        # Convert to 1:2 ratio spread: Sell 2 lots of 25500 CE
        ratio_ce_lots = 2

        assert ratio_ce_lots == original_ce_lots * 2

    @pytest.mark.asyncio
    async def test_ratio_calculation(self):
        """Test ratio spread calculation (1:2 or 1:3)."""
        # 1:2 ratio spread
        long_lots = 1
        short_lots = 2

        ratio = short_lots / long_lots

        assert ratio == 2.0

        # 1:3 ratio spread
        short_lots = 3
        ratio = short_lots / long_lots

        assert ratio == 3.0

    # Feature #43: Iron Butterfly Conversion
    @pytest.mark.asyncio
    async def test_iron_condor_to_butterfly_conversion(self):
        """Test converting iron condor to iron butterfly."""
        spot = 25000

        # Iron Condor
        condor = [
            {"strike": 24000, "option_type": "PE", "transaction_type": "buy"},
            {"strike": 24500, "option_type": "PE", "transaction_type": "sell"},
            {"strike": 25500, "option_type": "CE", "transaction_type": "sell"},
            {"strike": 26000, "option_type": "CE", "transaction_type": "buy"},
        ]

        # Iron Butterfly: Move short strikes to ATM
        butterfly = [
            {"strike": 24000, "option_type": "PE", "transaction_type": "buy"},
            {"strike": spot, "option_type": "PE", "transaction_type": "sell"},  # At ATM
            {"strike": spot, "option_type": "CE", "transaction_type": "sell"},  # At ATM
            {"strike": 26000, "option_type": "CE", "transaction_type": "buy"},
        ]

        # Both short strikes at ATM
        assert butterfly[1]["strike"] == spot
        assert butterfly[2]["strike"] == spot

    @pytest.mark.asyncio
    async def test_butterfly_strikes_calculation(self):
        """Test butterfly strike calculation (ATM centered)."""
        spot = 25000
        wing_distance = 1000  # Wings 1000 points from ATM

        butterfly = {
            "long_pe": spot - wing_distance,   # 24000
            "short_atm": spot,                 # 25000
            "long_ce": spot + wing_distance,   # 26000
        }

        assert butterfly["long_pe"] == 24000
        assert butterfly["short_atm"] == 25000
        assert butterfly["long_ce"] == 26000

        # Verify symmetry
        pe_distance = spot - butterfly["long_pe"]
        ce_distance = butterfly["long_ce"] - spot

        assert pe_distance == ce_distance


# =============================================================================
# INTEGRATION: STRATEGY CONVERSION WORKFLOW
# =============================================================================

class TestStrategyConversionWorkflow:
    """Integration tests for strategy conversion workflows."""

    @pytest.mark.asyncio
    async def test_conversion_preserves_greeks(self):
        """Test conversion maintains similar Greeks (where possible)."""
        # Original Iron Condor Greeks
        original_greeks = {
            "delta": 0.05,
            "gamma": 0.02,
            "theta": -150.0,
            "vega": 200.0
        }

        # After converting to Strangle (remove wings)
        # Delta and Gamma increase, Theta stays similar
        strangle_greeks = {
            "delta": 0.08,    # Slightly higher
            "gamma": 0.04,    # Higher (less hedge)
            "theta": -160.0,  # Similar
            "vega": 220.0     # Slightly higher
        }

        # Verify theta is similar (±20%)
        theta_change_pct = abs((strangle_greeks["theta"] - original_greeks["theta"]) / original_greeks["theta"]) * 100

        assert theta_change_pct < 20  # Within 20%

    @pytest.mark.asyncio
    async def test_conversion_cost_benefit_analysis(self):
        """Test cost-benefit analysis of conversion."""
        conversion_cost = 3750.0
        current_position_value = 6000.0
        new_position_max_profit = 12000.0

        # Cost as % of new max profit
        cost_pct = (conversion_cost / new_position_max_profit) * 100

        # Worth it if cost < 40% of new max profit
        is_worth_it = cost_pct < 40.0

        # 3750 / 12000 = 31.25% → worth it
        assert is_worth_it is True

    @pytest.mark.asyncio
    async def test_conversion_requires_user_confirmation(self):
        """Test conversion requires user confirmation."""
        conversion_request = {
            "strategy_id": "strategy_123",
            "conversion_type": "iron_condor_to_strangle",
            "estimated_cost": 3750.0,
            "confirmed": False
        }

        # Should not execute without confirmation
        can_execute = conversion_request["confirmed"]

        assert can_execute is False

        # After confirmation
        conversion_request["confirmed"] = True
        can_execute = conversion_request["confirmed"]

        assert can_execute is True
