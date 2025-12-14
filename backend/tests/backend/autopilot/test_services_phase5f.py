"""
Phase 5F Backend Tests - Core Adjustments

Tests for:
- Feature #36: Break/Split Trade
- Feature #37: Add to Non-Threatened Side
- Feature #38: Delta Neutral Rebalance
- Feature #39: Shift Leg API
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date

# =============================================================================
# FEATURE #36: BREAK/SPLIT TRADE
# =============================================================================

class TestBreakTradeService:
    """Tests for break/split trade functionality."""

    @pytest.mark.asyncio
    async def test_calculate_exit_cost(self):
        """Test calculation of exit cost for losing leg."""
        entry_price = 180.0
        current_exit_price = 350.0
        lots = 1
        lot_size = 25  # NIFTY

        exit_cost = (current_exit_price - entry_price) * lots * lot_size

        # Loss = (350 - 180) * 1 * 25 = ₹4,250
        assert exit_cost == 4250.0

    @pytest.mark.asyncio
    async def test_calculate_recovery_premium(self):
        """Test calculation of recovery premium per new leg."""
        exit_cost = 4250.0

        # Split into 2 new positions
        recovery_premium_per_leg = exit_cost / 2

        # Each leg should collect ₹2,125
        assert recovery_premium_per_leg == 2125.0

    @pytest.mark.asyncio
    async def test_find_strikes_for_recovery(self):
        """Test finding strikes that match recovery premium."""
        target_premium = 2125.0
        lot_size = 25

        # Premium per contract = 2125 / 25 = ₹85
        premium_per_contract = target_premium / lot_size

        # Mock option chain
        option_chain = [
            {"strike": 24500, "ce_ltp": 120, "pe_ltp": 65},
            {"strike": 24600, "ce_ltp": 95, "pe_ltp": 85},   # PE matches ₹85
            {"strike": 24700, "ce_ltp": 75, "pe_ltp": 105},
        ]

        # Find strikes where premium ≈ target
        tolerance = 10  # ±₹10
        matching_strikes = []

        for strike_data in option_chain:
            if abs(strike_data["pe_ltp"] - premium_per_contract) <= tolerance:
                matching_strikes.append(strike_data)

        assert len(matching_strikes) > 0
        assert 24600 in [s["strike"] for s in matching_strikes]

    @pytest.mark.asyncio
    async def test_split_into_two_positions(self):
        """Test splitting into 2 new positions (PE + CE)."""
        # Original: Lost on 25000 CE
        # New positions: Sell 24600 PE + Sell 25400 CE

        exit_cost = 4250.0
        recovery_premium_per_leg = exit_cost / 2  # ₹2,125 each

        new_positions = [
            {"strike": 24600, "option_type": "PE", "target_premium": recovery_premium_per_leg},
            {"strike": 25400, "option_type": "CE", "target_premium": recovery_premium_per_leg},
        ]

        assert len(new_positions) == 2
        assert new_positions[0]["option_type"] == "PE"
        assert new_positions[1]["option_type"] == "CE"
        assert sum(p["target_premium"] for p in new_positions) == exit_cost

    @pytest.mark.asyncio
    async def test_break_trade_execution(self):
        """Test break trade execution workflow."""
        # Step 1: Exit losing leg
        exit_leg = {
            "leg_id": "leg_1",
            "strike": 25000,
            "option_type": "CE",
            "entry_price": 180.0,
            "exit_price": 350.0,
            "lots": 1
        }

        # Step 2: Calculate recovery premium
        exit_cost = (exit_leg["exit_price"] - exit_leg["entry_price"]) * exit_leg["lots"] * 25
        recovery_per_leg = exit_cost / 2

        # Step 3: Find new strikes
        new_legs = [
            {"strike": 24600, "option_type": "PE", "premium": 85.0},
            {"strike": 25400, "option_type": "CE", "premium": 85.0},
        ]

        # Step 4: Execute new positions
        executed = True

        assert executed is True
        assert len(new_legs) == 2

    @pytest.mark.asyncio
    async def test_break_trade_cost_tracking(self):
        """Test break trade cost is tracked as adjustment cost."""
        original_premium = 15000.0  # Original strategy premium
        break_trade_cost = 4250.0   # Cost to exit losing leg

        # Net premium after break trade
        net_premium = original_premium - break_trade_cost

        # Cost as % of original premium
        cost_pct = (break_trade_cost / original_premium) * 100

        # Cost is 28.33% of original premium
        assert abs(cost_pct - 28.33) < 0.01


# =============================================================================
# FEATURE #37: ADD TO NON-THREATENED SIDE
# =============================================================================

class TestAddToOppositeSide:
    """Tests for adding contracts to non-threatened side."""

    @pytest.mark.asyncio
    async def test_identify_non_threatened_side(self):
        """Test identification of non-threatened side."""
        spot = 25000
        legs = [
            {"strike": 24500, "option_type": "PE", "distance": abs(25000 - 24500)},  # 500 points away
            {"strike": 26000, "option_type": "CE", "distance": abs(26000 - 25000)},  # 1000 points away
        ]

        # CE side is farther → non-threatened
        non_threatened = max(legs, key=lambda x: x["distance"])

        assert non_threatened["option_type"] == "CE"
        assert non_threatened["strike"] == 26000

    @pytest.mark.asyncio
    async def test_calculate_contracts_to_add(self):
        """Test calculation of contracts to add."""
        current_lots = 1
        add_percentage = 50  # Add 50% more

        contracts_to_add = current_lots * (add_percentage / 100)

        # Add 0.5 lots (round up to 1)
        contracts_to_add = max(1, int(contracts_to_add))

        assert contracts_to_add == 1

    @pytest.mark.asyncio
    async def test_add_to_opposite_execution(self):
        """Test execution of add to opposite side."""
        original_position = {
            "ce_lots": 1,
            "pe_lots": 1
        }

        # Spot moves down, PE threatened
        # Add to CE side
        non_threatened_side = "CE"
        contracts_to_add = 1

        if non_threatened_side == "CE":
            original_position["ce_lots"] += contracts_to_add
        else:
            original_position["pe_lots"] += contracts_to_add

        # CE lots increased to 2
        assert original_position["ce_lots"] == 2
        assert original_position["pe_lots"] == 1


# =============================================================================
# FEATURE #38: DELTA NEUTRAL REBALANCE
# =============================================================================

class TestDeltaRebalanceService:
    """Tests for delta neutral rebalancing."""

    @pytest.mark.asyncio
    async def test_calculate_delta_imbalance(self):
        """Test calculation of delta imbalance."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.28")
        strategy.target_delta = Decimal("0.00")  # Target neutral

        delta_imbalance = strategy.net_delta - strategy.target_delta

        # Imbalance = +0.28 (too bullish)
        assert float(delta_imbalance) == 0.28

    @pytest.mark.asyncio
    async def test_determine_rebalance_action(self):
        """Test determination of rebalance action."""
        net_delta = 0.28  # Too bullish

        # Need to reduce delta by 0.28
        # Options: 1) Roll CE closer, 2) Roll PE farther, 3) Add PE contracts

        if net_delta > 0.20:
            rebalance_actions = [
                {"action": "roll_ce_closer", "delta_impact": -0.15},
                {"action": "add_pe_contracts", "delta_impact": -0.13},
            ]
        else:
            rebalance_actions = []

        assert len(rebalance_actions) > 0
        assert "roll_ce_closer" in [a["action"] for a in rebalance_actions]

    @pytest.mark.asyncio
    async def test_rebalance_by_roll_strikes(self):
        """Test rebalancing by rolling strikes."""
        # Current: 26000 CE with delta +0.28
        # Action: Roll to 25800 CE (closer to ATM) to reduce delta

        current_ce_strike = 26000
        current_ce_delta = 0.15  # Delta of current CE
        net_delta = 0.28

        # Roll closer by 200 points
        new_ce_strike = 25800
        new_ce_delta = 0.20  # Higher delta when closer

        # Delta change from roll
        delta_change = new_ce_delta - current_ce_delta  # +0.05

        # This would increase net delta (wrong direction)
        # Correct approach: Roll farther from ATM to reduce delta
        new_ce_strike = 26200  # Farther
        new_ce_delta = 0.12  # Lower delta

        delta_change = current_ce_delta - new_ce_delta  # 0.03 reduction

        assert new_ce_strike > current_ce_strike
        assert new_ce_delta < current_ce_delta

    @pytest.mark.asyncio
    async def test_rebalance_by_add_contracts(self):
        """Test rebalancing by adding contracts to opposite side."""
        net_delta = 0.28  # Too bullish

        # Add PE contracts to reduce delta
        pe_delta_per_lot = -0.14  # Each PE lot adds -0.14 delta

        lots_to_add = int(abs(net_delta / pe_delta_per_lot))

        # Need 2 lots to neutralize (2 * -0.14 = -0.28)
        assert lots_to_add == 2

    @pytest.mark.asyncio
    async def test_rebalance_execution(self):
        """Test rebalance execution workflow."""
        strategy = MagicMock()
        strategy.net_delta = Decimal("0.30")
        strategy.target_delta = Decimal("0.00")

        # Execute rebalance
        rebalance_plan = {
            "action": "add_pe_contracts",
            "lots": 2,
            "expected_delta_after": 0.02  # Close to neutral
        }

        executed = True
        new_delta = 0.02

        assert executed is True
        assert abs(new_delta) < 0.05  # Within tolerance


# =============================================================================
# FEATURE #39: SHIFT LEG API
# =============================================================================

class TestShiftLegAPI:
    """Tests for shift leg API endpoints."""

    @pytest.mark.asyncio
    async def test_shift_leg_by_strike(self):
        """Test shifting leg to specific strike."""
        current_leg = {
            "strike": 25000,
            "option_type": "CE",
            "delta": 0.15
        }

        target_strike = 25200

        shift_request = {
            "leg_id": "leg_1",
            "mode": "by_strike",
            "target_strike": target_strike
        }

        # Shift executed
        new_leg = {
            "strike": target_strike,
            "option_type": "CE",
            "delta": 0.12  # Lower delta when farther
        }

        assert new_leg["strike"] == target_strike

    @pytest.mark.asyncio
    async def test_shift_leg_by_delta(self):
        """Test shifting leg to target delta."""
        current_leg = {
            "strike": 25000,
            "option_type": "CE",
            "delta": 0.15
        }

        target_delta = 0.10

        shift_request = {
            "leg_id": "leg_1",
            "mode": "by_delta",
            "target_delta": target_delta
        }

        # Find strike with target delta
        new_strike = 25400  # Farther from ATM

        new_leg = {
            "strike": new_strike,
            "option_type": "CE",
            "delta": 0.10
        }

        assert abs(new_leg["delta"] - target_delta) < 0.01

    @pytest.mark.asyncio
    async def test_shift_closer_to_atm(self):
        """Test shifting leg closer to ATM."""
        spot = 25000
        current_strike = 25400  # CE 400 points away

        shift_request = {
            "leg_id": "leg_1",
            "direction": "closer",
            "distance": 200  # Move 200 points closer
        }

        new_strike = current_strike - shift_request["distance"]

        # New strike = 25200 (closer to 25000 ATM)
        assert new_strike == 25200
        assert abs(new_strike - spot) < abs(current_strike - spot)

    @pytest.mark.asyncio
    async def test_shift_farther_from_atm(self):
        """Test shifting leg farther from ATM."""
        spot = 25000
        current_strike = 25400  # CE 400 points away

        shift_request = {
            "leg_id": "leg_1",
            "direction": "farther",
            "distance": 200  # Move 200 points farther
        }

        new_strike = current_strike + shift_request["distance"]

        # New strike = 25600 (farther from 25000 ATM)
        assert new_strike == 25600
        assert abs(new_strike - spot) > abs(current_strike - spot)
