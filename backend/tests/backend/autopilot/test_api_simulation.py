"""
Simulation API Tests

Tests for /api/v1/autopilot/simulate endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from datetime import date, timedelta

from app.models.users import User
from app.models.autopilot import PositionLegStatus


class TestSimulateShift:
    """Tests for simulate shift endpoint."""

    @pytest.mark.asyncio
    async def test_simulate_shift_by_strike(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating shift to specific strike."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {
            "leg_id": test_position_leg.leg_id,
            "target_strike": 24900
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "shift",
                "new_strike": 24900,
                "before": {"net_delta": 0.40},
                "after": {"net_delta": 0.25},
                "impact": {"delta_change": -0.15}
            }
            MockSimulator.return_value.simulate_shift = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/shift",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["simulation_type"] == "shift"
            assert data["new_strike"] == 24900

    @pytest.mark.asyncio
    async def test_simulate_shift_by_delta(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating shift by target delta."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {
            "leg_id": test_position_leg.leg_id,
            "target_delta": 0.18
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "shift",
                "new_strike": 24900,
                "impact": {"delta_change": -0.22}
            }
            MockSimulator.return_value.simulate_shift = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/shift",
                json=payload
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_simulate_shift_by_amount(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating shift by specific amount."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {
            "leg_id": test_position_leg.leg_id,
            "shift_amount": -100
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "shift",
                "current_strike": 25000,
                "new_strike": 24900
            }
            MockSimulator.return_value.simulate_shift = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/shift",
                json=payload
            )

            assert response.status_code == 200


class TestSimulateRoll:
    """Tests for simulate roll endpoint."""

    @pytest.mark.asyncio
    async def test_simulate_roll_to_new_expiry(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating roll to new expiry."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        new_expiry = (date.today() + timedelta(days=14)).isoformat()
        payload = {
            "leg_id": test_position_leg.leg_id,
            "target_expiry": new_expiry
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "roll",
                "new_expiry": new_expiry,
                "roll_cost": 50.0
            }
            MockSimulator.return_value.simulate_roll = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/roll",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["simulation_type"] == "roll"

    @pytest.mark.asyncio
    async def test_simulate_roll_with_strike_change(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating roll with strike change."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        new_expiry = (date.today() + timedelta(days=14)).isoformat()
        payload = {
            "leg_id": test_position_leg.leg_id,
            "target_expiry": new_expiry,
            "target_strike": 25100
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "roll",
                "new_expiry": new_expiry,
                "new_strike": 25100
            }
            MockSimulator.return_value.simulate_roll = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/roll",
                json=payload
            )

            assert response.status_code == 200


class TestSimulateBreak:
    """Tests for simulate break trade endpoint."""

    @pytest.mark.asyncio
    async def test_simulate_break_trade(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating break trade."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {
            "leg_id": test_position_leg.leg_id,
            "premium_split": "equal"
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "break_trade",
                "exit_cost": 320.0,
                "recovery_plan": {
                    "put_strike": 24800,
                    "call_strike": 25700
                }
            }
            MockSimulator.return_value.simulate_break_trade = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/break",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["simulation_type"] == "break_trade"
            assert "recovery_plan" in data

    @pytest.mark.asyncio
    async def test_simulate_break_shows_recovery(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test break trade simulation shows recovery details."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {
            "leg_id": test_position_leg.leg_id,
            "premium_split": "equal",
            "max_delta": 0.25
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "break_trade",
                "exit_cost": 500.0,
                "recovery_plan": {
                    "put_strike": 24800,
                    "put_premium": 250.0,
                    "call_strike": 25700,
                    "call_premium": 250.0,
                    "total_recovery": 500.0
                },
                "net_cost": 0.0
            }
            MockSimulator.return_value.simulate_break_trade = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/break",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert "exit_cost" in data
            assert "net_cost" in data


class TestSimulateExit:
    """Tests for simulate exit endpoint."""

    @pytest.mark.asyncio
    async def test_simulate_exit_full(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating full exit."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {"exit_type": "full"}

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "exit",
                "exit_type": "full",
                "before": {"num_positions": 2},
                "after": {"num_positions": 0}
            }
            MockSimulator.return_value.simulate_exit = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/exit",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["simulation_type"] == "exit"

    @pytest.mark.asyncio
    async def test_simulate_exit_partial(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test simulating partial exit."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {"exit_type": "partial"}

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "simulation_type": "exit",
                "exit_type": "partial"
            }
            MockSimulator.return_value.simulate_exit = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/exit",
                json=payload
            )

            assert response.status_code == 200


class TestCompareScenarios:
    """Tests for compare scenarios endpoint."""

    @pytest.mark.asyncio
    async def test_compare_multiple_scenarios(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test comparing multiple scenarios."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {
            "scenarios": [
                {"type": "shift", "leg_id": test_position_leg.leg_id, "target_delta": 0.18},
                {"type": "exit"}
            ]
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "scenarios_compared": 2,
                "results": [
                    {"simulation_type": "shift"},
                    {"simulation_type": "exit"}
                ],
                "ranked": [
                    {"simulation_type": "shift"},
                    {"simulation_type": "exit"}
                ],
                "best_option": {"simulation_type": "shift"}
            }
            MockSimulator.return_value.compare_scenarios = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/compare",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["scenarios_compared"] == 2
            assert "ranked" in data
            assert "best_option" in data

    @pytest.mark.asyncio
    async def test_compare_scenarios_ranking(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test scenarios are ranked correctly."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        payload = {
            "scenarios": [
                {"type": "shift", "leg_id": test_position_leg.leg_id, "target_strike": 24900},
                {"type": "break", "leg_id": test_position_leg.leg_id},
                {"type": "exit"}
            ]
        }

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            mock_result = {
                "scenarios_compared": 3,
                "results": [{}, {}, {}],
                "ranked": [{}, {}, {}],
                "best_option": {}
            }
            MockSimulator.return_value.compare_scenarios = AsyncMock(return_value=mock_result)

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/compare",
                json=payload
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["ranked"]) == 3

    @pytest.mark.asyncio
    async def test_compare_scenarios_empty_rejected(
        self, client: AsyncClient, test_strategy_active
    ):
        """Test empty scenarios list is rejected."""
        payload = {"scenarios": []}

        response = await client.post(
            f"/api/v1/autopilot/simulate/{test_strategy_active.id}/compare",
            json=payload
        )

        # Should fail validation or return error
        assert response.status_code in [400, 422]


class TestSimulationErrors:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_simulation_unauthorized_strategy(
        self, client: AsyncClient
    ):
        """Test unauthorized access to another user's strategy."""
        payload = {"leg_id": "leg1", "target_strike": 24900}

        response = await client.post(
            "/api/v1/autopilot/simulate/99999/shift",
            json=payload
        )

        assert response.status_code in [400, 404, 500]

    @pytest.mark.asyncio
    async def test_simulation_invalid_leg(
        self, client: AsyncClient, test_strategy_active
    ):
        """Test simulation with invalid leg ID."""
        payload = {"leg_id": "invalid_leg", "target_strike": 24900}

        with patch('app.api.v1.autopilot.simulation.WhatIfSimulator') as MockSimulator:
            MockSimulator.return_value.simulate_shift = AsyncMock(
                side_effect=ValueError("Leg not found")
            )

            response = await client.post(
                f"/api/v1/autopilot/simulate/{test_strategy_active.id}/shift",
                json=payload
            )

            assert response.status_code == 400
