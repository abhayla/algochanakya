"""
Position Legs API Tests

Tests for /api/v1/autopilot/legs endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from decimal import Decimal

from app.models.users import User
from .conftest import assert_position_leg_response


class TestGetLegs:
    """Tests for GET legs endpoints."""

    @pytest.mark.asyncio
    async def test_get_all_strategy_legs(self, client: AsyncClient, test_user: User, test_strategy_active, test_position_legs_multiple):
        """Test getting all legs for a strategy."""
        response = await client.get(f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    @pytest.mark.asyncio
    async def test_get_legs_empty_list(self, client: AsyncClient, test_strategy_active):
        """Test empty legs list."""
        response = await client.get(f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_legs_filter_by_status(self, client: AsyncClient, test_strategy_active, test_position_legs_multiple):
        """Test filtering legs by status."""
        response = await client.get(f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs?status=open")

        assert response.status_code == 200
        data = response.json()
        assert all(leg["status"] == "open" for leg in data)

    @pytest.mark.asyncio
    async def test_get_single_leg(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test getting single leg by ID."""
        response = await client.get(f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}")

        assert response.status_code == 200
        data = response.json()
        assert_position_leg_response(data)
        assert data["id"] == test_position_leg.id

    @pytest.mark.asyncio
    async def test_get_leg_not_found(self, client: AsyncClient, test_strategy_active):
        """Test 404 for non-existent leg."""
        response = await client.get(f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_legs_unauthorized_strategy(self, client: AsyncClient, another_user):
        """Test unauthorized access to another user's strategy."""
        response = await client.get("/api/v1/autopilot/legs/strategies/99999/legs")

        assert response.status_code in [403, 404]


class TestExitLeg:
    """Tests for exiting legs."""

    @pytest.mark.asyncio
    async def test_exit_leg_market_order(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test exiting leg with market order."""
        payload = {"execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/exit",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

    @pytest.mark.asyncio
    async def test_exit_leg_limit_order(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test exiting leg with limit order."""
        payload = {"execution_mode": "limit", "limit_price": 125.00}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/exit",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_exit_leg_already_closed(self, client: AsyncClient, test_strategy_active, test_position_leg, db_session):
        """Test cannot exit already closed leg."""
        from app.models.autopilot import PositionLegStatus
        test_position_leg.status = PositionLegStatus.CLOSED
        await db_session.commit()

        payload = {"execution_mode": "market"}
        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/exit",
            json=payload
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_exit_leg_strategy_not_active(self, client: AsyncClient, test_strategy, test_position_leg):
        """Test cannot exit leg when strategy not active."""
        payload = {"execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy.id}/legs/{test_position_leg.id}/exit",
            json=payload
        )

        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_exit_leg_not_found(self, client: AsyncClient, test_strategy_active):
        """Test 404 for non-existent leg."""
        payload = {"execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/99999/exit",
            json=payload
        )

        assert response.status_code == 404


class TestShiftLeg:
    """Tests for shifting legs."""

    @pytest.mark.asyncio
    async def test_shift_leg_by_target_strike(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test shifting leg to specific strike."""
        payload = {"target_strike": 24900, "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/shift",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_shift_leg_by_target_delta(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test shifting leg by target delta."""
        payload = {"target_delta": 0.18, "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/shift",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_shift_leg_by_direction_amount(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test shifting by direction and amount."""
        payload = {"shift_direction": "closer", "shift_amount": 100, "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/shift",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_shift_leg_same_strike_rejected(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test shifting to same strike is rejected."""
        payload = {"target_strike": test_position_leg.strike, "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/shift",
            json=payload
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_shift_leg_invalid_strike(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test invalid strike is rejected."""
        payload = {"target_strike": 99999, "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/shift",
            json=payload
        )

        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_shift_leg_dry_run_mode(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test dry run mode for shift."""
        payload = {"target_strike": 24900, "execution_mode": "dry_run"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/shift",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert "preview" in data or "cost" in data


class TestRollLeg:
    """Tests for rolling legs."""

    @pytest.mark.asyncio
    async def test_roll_leg_to_new_expiry(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test rolling leg to new expiry."""
        from datetime import date, timedelta
        new_expiry = (date.today() + timedelta(days=14)).isoformat()
        payload = {"target_expiry": new_expiry, "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/roll",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_roll_leg_with_strike_change(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test rolling with strike change."""
        from datetime import date, timedelta
        new_expiry = (date.today() + timedelta(days=14)).isoformat()
        payload = {"target_expiry": new_expiry, "target_strike": 25100, "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/roll",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_roll_leg_same_expiry_rejected(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test rolling to same expiry is rejected."""
        payload = {"target_expiry": test_position_leg.expiry.isoformat(), "execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/roll",
            json=payload
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_roll_leg_dry_run_mode(self, client: AsyncClient, test_strategy_active, test_position_leg):
        """Test dry run mode for roll."""
        from datetime import date, timedelta
        new_expiry = (date.today() + timedelta(days=14)).isoformat()
        payload = {"target_expiry": new_expiry, "execution_mode": "dry_run"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/roll",
            json=payload
        )

        assert response.status_code == 200


class TestBreakTrade:
    """Tests for break trade."""

    @pytest.mark.asyncio
    async def test_break_trade_execution(self, client: AsyncClient, test_break_trade_scenario):
        """Test break trade execution."""
        strategy, losing_leg = test_break_trade_scenario
        payload = {"execution_mode": "market", "premium_split": "equal"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{strategy.id}/legs/{losing_leg.id}/break",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_break_trade_with_custom_strikes(self, client: AsyncClient, test_break_trade_scenario):
        """Test break trade with custom strikes."""
        strategy, losing_leg = test_break_trade_scenario
        payload = {
            "execution_mode": "market",
            "new_put_strike": 24800,
            "new_call_strike": 25700
        }

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{strategy.id}/legs/{losing_leg.id}/break",
            json=payload
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_break_trade_invalid_leg(self, client: AsyncClient, test_strategy_active):
        """Test break trade with invalid leg."""
        payload = {"execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/99999/break",
            json=payload
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_break_trade_closed_leg_rejected(self, client: AsyncClient, test_strategy_active, test_position_leg, db_session):
        """Test cannot break trade on closed leg."""
        from app.models.autopilot import PositionLegStatus
        test_position_leg.status = PositionLegStatus.CLOSED
        await db_session.commit()

        payload = {"execution_mode": "market"}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/{test_position_leg.id}/break",
            json=payload
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_simulate_break_trade(self, client: AsyncClient, test_break_trade_scenario):
        """Test simulating break trade."""
        strategy, losing_leg = test_break_trade_scenario
        payload = {"premium_split": "equal", "prefer_round_strikes": True}

        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{strategy.id}/legs/{losing_leg.id}/break/simulate",
            json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert "exit_cost" in data
        assert "new_put_strike" in data
        assert "new_call_strike" in data


class TestUpdateGreeks:
    """Tests for updating Greeks."""

    @pytest.mark.asyncio
    async def test_update_all_legs_greeks(self, client: AsyncClient, test_strategy_active, test_position_legs_multiple):
        """Test updating Greeks for all strategy legs."""
        response = await client.post(
            f"/api/v1/autopilot/legs/strategies/{test_strategy_active.id}/legs/update-greeks"
        )

        assert response.status_code == 200
        data = response.json()
        assert "updated_count" in data or isinstance(data, list)
