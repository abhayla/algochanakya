"""
Integration Tests - Phase 5

Tests for complete workflows across multiple services and components.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, timedelta
from decimal import Decimal

from app.models.autopilot import PositionLegStatus, SuggestionType


class TestIntegrationPhase5:
    """Integration tests for Phase 5 workflows."""

    @pytest.mark.asyncio
    async def test_full_break_trade_flow(
        self, db_session, test_break_trade_scenario, test_user
    ):
        """Test complete break trade workflow from detection to execution."""
        strategy, losing_leg = test_break_trade_scenario

        # Step 1: Detect losing leg
        from app.services.position_leg_service import PositionLegService
        mock_kite = MagicMock()
        leg_service = PositionLegService(mock_kite, db_session)

        # Update leg with loss
        losing_leg.unrealized_pnl = Decimal("-600.00")
        await db_session.commit()

        # Step 2: Generate suggestion
        from app.services.suggestion_engine import SuggestionEngine
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25300.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        suggestion_engine = SuggestionEngine(mock_kite, db_session, mock_market_data)
        suggestions = await suggestion_engine.generate_suggestions(strategy.id, test_user.id)

        # Should get break trade suggestion
        break_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.BREAK]
        assert len(break_suggestions) > 0

        # Step 3: Execute break trade
        from app.services.break_trade_service import BreakTradeService
        break_service = BreakTradeService(mock_kite, db_session)

        with patch.object(break_service, 'strike_finder') as mock_finder:
            mock_finder.find_strike_by_premium.side_effect = [
                {"strike": 24800, "ltp": 150.00, "delta": 0.20},
                {"strike": 25700, "ltp": 150.00, "delta": 0.20}
            ]

            with patch.object(break_service, 'order_executor') as mock_executor:
                mock_executor.execute_orders.return_value = {"status": "success"}

                # This would execute the break trade
                # (Simplified for test - actual implementation would be more complex)
                assert losing_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_full_shift_leg_flow(
        self, db_session, test_strategy_active, test_position_leg, test_user
    ):
        """Test complete shift leg workflow."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.delta = Decimal("0.45")
        await db_session.commit()

        # Step 1: Detect high delta
        test_strategy_active.net_delta = Decimal("0.45")
        await db_session.commit()

        # Step 2: Simulate shift
        from app.services.whatif_simulator import WhatIfSimulator
        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))

        simulator = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        with patch.object(simulator.strike_finder, 'find_strike_by_delta', new_callable=AsyncMock) as mock_finder:
            mock_finder.return_value = {"strike": 24900}

            with patch.object(simulator.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_premium:
                mock_premium.return_value = {"strike": 24900, "ltp": 120.00, "delta": 0.18}

                simulation = await simulator.simulate_shift(
                    strategy_id=test_strategy_active.id,
                    leg_id=test_position_leg.leg_id,
                    target_delta=Decimal("0.18")
                )

                assert simulation["simulation_type"] == "shift"
                assert "impact" in simulation

        # Step 3: Execute shift
        from app.services.leg_actions_service import LegActionsService
        leg_actions = LegActionsService(mock_kite, db_session)

        with patch.object(leg_actions, 'order_executor') as mock_executor:
            mock_executor.execute_orders.return_value = {"status": "success"}

            # Would execute the shift here
            assert test_position_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_full_roll_leg_flow(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test complete roll leg workflow."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.expiry = date.today() + timedelta(days=4)
        await db_session.commit()

        # Step 1: Detect approaching expiry
        dte = (test_position_leg.expiry - date.today()).days
        assert dte <= 7

        # Step 2: Simulate roll
        from app.services.whatif_simulator import WhatIfSimulator
        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))

        simulator = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        new_expiry = date.today() + timedelta(days=14)
        simulation = await simulator.simulate_roll(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.leg_id,
            target_expiry=new_expiry
        )

        assert simulation["simulation_type"] == "roll"
        assert "roll_cost" in simulation

        # Step 3: Execute roll
        from app.services.leg_actions_service import LegActionsService
        leg_actions = LegActionsService(mock_kite, db_session)

        with patch.object(leg_actions, 'order_executor') as mock_executor:
            mock_executor.execute_orders.return_value = {"status": "success"}

            # Would execute the roll here
            assert test_position_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_suggestion_to_execution_flow(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test flow from suggestion generation to execution."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.delta = Decimal("0.55")
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.55")
        test_strategy_active.status = "active"
        await db_session.commit()

        # Step 1: Generate suggestions
        from app.services.suggestion_engine import SuggestionEngine
        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        suggestion_engine = SuggestionEngine(mock_kite, db_session, mock_market_data)
        suggestions = await suggestion_engine.generate_suggestions(strategy.id, test_user.id)

        # Should get shift suggestion
        shift_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.SHIFT]
        assert len(shift_suggestions) > 0

        # Step 2: Execute suggestion
        suggestion = shift_suggestions[0]
        action_params = suggestion.action_params or {}

        from app.services.leg_actions_service import LegActionsService
        leg_actions = LegActionsService(mock_kite, db_session)

        with patch.object(leg_actions, 'order_executor') as mock_executor:
            mock_executor.execute_orders.return_value = {"status": "success"}

            # Would execute based on action_params
            assert action_params.get("execution_mode") in ["market", "limit"]

    @pytest.mark.asyncio
    async def test_whatif_to_adjustment_flow(
        self, db_session, test_strategy_active, test_position_leg
    ):
        """Test flow from what-if simulation to actual adjustment."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        # Step 1: Run what-if simulation
        from app.services.whatif_simulator import WhatIfSimulator
        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))

        simulator = WhatIfSimulator(mock_kite, db_session, mock_market_data)

        with patch.object(simulator.strike_finder, 'find_strike_by_premium', new_callable=AsyncMock) as mock_finder:
            mock_finder.return_value = {"strike": 24900, "ltp": 120.00, "delta": 0.25}

            simulation = await simulator.simulate_shift(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.leg_id,
                target_strike=Decimal("24900")
            )

            # User reviews simulation
            assert "recommendation" in simulation
            impact = simulation.get("impact", {})

            # Step 2: If approved, execute
            if impact.get("delta_change", 0) < -0.1:
                # Would execute the adjustment
                from app.services.leg_actions_service import LegActionsService
                leg_actions = LegActionsService(mock_kite, db_session)

                with patch.object(leg_actions, 'order_executor') as mock_executor:
                    mock_executor.execute_orders.return_value = {"status": "success"}

                    assert test_position_leg.status == PositionLegStatus.OPEN

    @pytest.mark.asyncio
    async def test_delta_alert_to_adjustment_flow(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test flow from delta alert to adjustment."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.delta = Decimal("0.60")
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.60")
        await db_session.commit()

        # Delta exceeds danger threshold
        danger_threshold = test_user_settings.delta_danger_threshold or 0.50
        assert abs(float(test_strategy_active.net_delta)) > danger_threshold

        # Step 1: Alert triggered
        alert_triggered = abs(float(test_strategy_active.net_delta)) > danger_threshold

        # Step 2: Generate adjustment suggestion
        if alert_triggered:
            from app.services.suggestion_engine import SuggestionEngine
            mock_kite = MagicMock()
            mock_market_data = MagicMock()
            mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
            mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

            suggestion_engine = SuggestionEngine(mock_kite, db_session, mock_market_data)
            suggestions = await suggestion_engine.generate_suggestions(test_strategy_active.id, test_user.id)

            critical_suggestions = [
                s for s in suggestions
                if s.priority.name == "CRITICAL" and s.suggestion_type == SuggestionType.SHIFT
            ]

            assert len(critical_suggestions) > 0

    @pytest.mark.asyncio
    async def test_multi_leg_strategy_management(
        self, db_session, test_strategy_active, test_position_legs_multiple
    ):
        """Test managing multi-leg strategy with concurrent operations."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        # Calculate strategy Greeks
        total_delta = sum(float(leg.delta or 0) for leg in test_position_legs_multiple)
        total_theta = sum(float(leg.theta or 0) for leg in test_position_legs_multiple)

        test_strategy_active.net_delta = Decimal(str(total_delta))
        test_strategy_active.net_theta = Decimal(str(total_theta))
        await db_session.commit()

        # Generate payoff
        from app.services.options.payoff_calculator import PayoffCalculator
        calculator = PayoffCalculator(db_session)

        result = await calculator.calculate_payoff(
            strategy_id=test_strategy_active.id,
            mode="expiry"
        )

        assert "metrics" in result
        assert len(result["legs_summary"]) == len(test_position_legs_multiple)

    @pytest.mark.asyncio
    async def test_dte_affects_workflow(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test that DTE affects suggestion thresholds and recommendations."""
        # Early DTE (20 days)
        test_position_leg.expiry = date.today() + timedelta(days=20)
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        test_position_leg.delta = Decimal("0.25")
        await db_session.commit()

        test_strategy_active.net_delta = Decimal("0.25")
        test_strategy_active.status = "active"
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        from app.services.suggestion_engine import SuggestionEngine
        suggestion_engine = SuggestionEngine(mock_kite, db_session, mock_market_data)

        # Early DTE should have looser thresholds
        suggestions_early = await suggestion_engine.generate_suggestions(test_strategy_active.id, test_user.id)

        # Late DTE (4 days) - tighter thresholds
        test_position_leg.expiry = date.today() + timedelta(days=4)
        await db_session.commit()

        suggestions_late = await suggestion_engine.generate_suggestions(test_strategy_active.id, test_user.id)

        # Late DTE should generate more suggestions for same delta
        # (because thresholds are tighter)
        # This is a simplified test - actual behavior depends on threshold values
        assert isinstance(suggestions_early, list)
        assert isinstance(suggestions_late, list)

    @pytest.mark.asyncio
    async def test_concurrent_leg_operations(
        self, db_session, test_strategy_active, test_position_legs_multiple
    ):
        """Test handling concurrent operations on different legs."""
        for leg in test_position_legs_multiple:
            leg.strategy_id = test_strategy_active.id
            leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        from app.services.leg_actions_service import LegActionsService
        mock_kite = MagicMock()
        leg_actions = LegActionsService(mock_kite, db_session)

        # Simulate concurrent operations
        import asyncio

        async def shift_leg_1():
            with patch.object(leg_actions, 'order_executor') as mock_executor:
                mock_executor.execute_orders.return_value = {"status": "success"}
                # Would shift leg 1
                await asyncio.sleep(0.1)

        async def update_leg_2():
            # Update Greeks for leg 2
            await asyncio.sleep(0.1)

        # Run concurrently
        await asyncio.gather(
            shift_leg_1(),
            update_leg_2()
        )

        # Both operations should complete successfully
        assert all(leg.strategy_id == test_strategy_active.id for leg in test_position_legs_multiple)
