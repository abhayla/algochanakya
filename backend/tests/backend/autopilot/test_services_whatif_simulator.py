"""
WhatIfSimulator Service Tests

Tests for simulation of proposed adjustments and scenario comparisons.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta
from decimal import Decimal

from app.services.autopilot.whatif_simulator import WhatIfSimulator
from app.models.autopilot import PositionLegStatus


class TestWhatIfSimulator:
    """Test WhatIfSimulator functionality."""

    @pytest.mark.asyncio
    async def test_simulate_shift_by_strike(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test simulating shift to specific strike."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.delta = Decimal("0.40")
        test_position_leg.tradingsymbol = "NIFTY24JAN25000PE"
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.40")
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        # Mock strike finder
        with patch.object(service.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_finder:
            mock_finder.return_value = {
                "strike": 24900,
                "ltp": 120.00,
                "delta": 0.25
            }

            result = await service.simulate_shift(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.leg_id,
                target_strike=Decimal("24900")
            )

            assert result["simulation_type"] == "shift"
            assert result["new_strike"] == 24900
            assert "before" in result
            assert "after" in result
            assert "impact" in result

    @pytest.mark.asyncio
    async def test_simulate_shift_by_delta(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test simulating shift by target delta."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.delta = Decimal("0.40")
        test_position_leg.tradingsymbol = "NIFTY24JAN25000PE"
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.40")
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        # Mock strike finder
        with patch.object(service.strike_finder, 'find_strike_by_delta', new_callable=AsyncMock) as mock_delta_finder, \
             patch.object(service.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_premium_finder:

            mock_delta_finder.return_value = {"strike": 24900}
            mock_premium_finder.return_value = {
                "strike": 24900,
                "ltp": 120.00,
                "delta": 0.18
            }

            result = await service.simulate_shift(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.leg_id,
                target_delta=Decimal("0.18")
            )

            assert result["simulation_type"] == "shift"
            assert "new_strike" in result
            assert result["impact"]["delta_change"] < 0  # Delta should reduce

    @pytest.mark.asyncio
    async def test_simulate_roll_to_new_expiry(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test simulating roll to new expiry."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.expiry = date.today() + timedelta(days=5)
        await db_session.commit()

        test_strategy_active.status = "active"
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        new_expiry = date.today() + timedelta(days=14)

        result = await service.simulate_roll(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            target_expiry=new_expiry
        )

        assert result["simulation_type"] == "roll"
        assert result["new_expiry"] == new_expiry.isoformat()
        assert result["new_dte"] == 14
        assert "roll_cost" in result
        assert "before" in result
        assert "after" in result

    @pytest.mark.asyncio
    async def test_simulate_break_trade_shows_recovery(
        self, db_session, test_break_trade_scenario
    ):
        """Test break trade simulation shows recovery plan."""
        strategy, losing_leg = test_break_trade_scenario

        losing_leg.tradingsymbol = "NIFTY24JAN25000PE"
        losing_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_ltp = AsyncMock(return_value={"NFO:NIFTY24JAN25000PE": 320.00})

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        # Mock strike finder
        with patch.object(service.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_finder:
            # Return PUT and CALL strikes
            mock_finder.side_effect = [
                {"strike": 24800, "ltp": 160.00, "delta": 0.20},  # PUT
                {"strike": 25700, "ltp": 160.00, "delta": 0.20}   # CALL
            ]

            result = await service.simulate_break_trade(
                strategy_id=strategy.id,
                leg_id=losing_leg.leg_id,
                premium_split="equal"
            )

            assert result["simulation_type"] == "break_trade"
            assert "exit_cost" in result
            assert "recovery_plan" in result
            assert "put_strike" in result["recovery_plan"]
            assert "call_strike" in result["recovery_plan"]
            assert "net_cost" in result

    @pytest.mark.asyncio
    async def test_simulate_exit_full_position(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test simulating full position exit."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.tradingsymbol = "NIFTY24JAN25000PE"
        await db_session.commit()

        test_strategy_active.runtime_state = {"current_pnl": -500}
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_ltp = AsyncMock(return_value={"NFO:NIFTY24JAN25000PE": 150.00})

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        result = await service.simulate_exit(
            strategy_id=test_strategy_active.id,
            exit_type="full"
        )

        assert result["simulation_type"] == "exit"
        assert result["exit_type"] == "full"
        assert "before" in result
        assert "after" in result
        assert result["after"]["num_positions"] == 0
        assert result["after"]["net_delta"] == 0

    @pytest.mark.asyncio
    async def test_compare_multiple_scenarios(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test comparing multiple adjustment scenarios."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.tradingsymbol = "NIFTY24JAN25000PE"
        test_position_leg.delta = Decimal("0.40")
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.40")
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_ltp = AsyncMock(return_value={"NFO:NIFTY24JAN25000PE": 150.00})

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        # Mock strike finder
        with patch.object(service.strike_finder, 'find_strike_by_delta', new_callable=AsyncMock) as mock_delta_finder, \
             patch.object(service.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_premium_finder:

            mock_delta_finder.return_value = {"strike": 24900}
            mock_premium_finder.return_value = {"strike": 24900, "ltp": 120.00, "delta": 0.18}

            scenarios = [
                {"type": "shift", "leg_id": test_position_leg.leg_id, "target_delta": Decimal("0.18")},
                {"type": "exit"}
            ]

            result = await service.compare_scenarios(
                strategy_id=test_strategy_active.id,
                scenarios=scenarios
            )

            assert result["scenarios_compared"] == 2
            assert "results" in result
            assert "ranked" in result
            assert "best_option" in result
            assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_calculate_impact_metrics(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test impact calculation between before/after states."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.delta = Decimal("0.40")
        test_position_leg.tradingsymbol = "NIFTY24JAN25000PE"
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.40")
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        # Mock strike finder
        with patch.object(service.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_finder:
            mock_finder.return_value = {
                "strike": 24900,
                "ltp": 120.00,
                "delta": 0.18
            }

            result = await service.simulate_shift(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.leg_id,
                target_strike=Decimal("24900")
            )

            impact = result["impact"]
            assert "delta_change" in impact
            assert "theta_change" in impact
            assert "pnl_change" in impact
            assert "cost" in impact

    @pytest.mark.asyncio
    async def test_rank_scenarios_by_effectiveness(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test scenarios are ranked correctly."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.tradingsymbol = "NIFTY24JAN25000PE"
        test_position_leg.delta = Decimal("0.40")
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.40")
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_ltp = AsyncMock(return_value={"NFO:NIFTY24JAN25000PE": 150.00})

        service = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        # Mock strike finder
        with patch.object(service.strike_finder, 'find_strike_by_delta', new_callable=AsyncMock) as mock_delta_finder, \
             patch.object(service.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_premium_finder:

            mock_delta_finder.return_value = {"strike": 24900}
            mock_premium_finder.return_value = {"strike": 24900, "ltp": 120.00, "delta": 0.18}

            scenarios = [
                {"type": "shift", "leg_id": test_position_leg.leg_id, "target_delta": Decimal("0.18")},
                {"type": "exit"}
            ]

            result = await service.compare_scenarios(
                strategy_id=test_strategy_active.id,
                scenarios=scenarios
            )

            # Best option should be ranked first
            assert result["best_option"] is not None
            assert result["best_option"] == result["ranked"][0]
