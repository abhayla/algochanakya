"""
AutoPilot Strategies CRUD API Tests

Tests for /api/v1/autopilot/strategies endpoints:
- GET /strategies - List strategies with pagination and filters
- POST /strategies - Create strategy
- GET /strategies/{id} - Get single strategy
- PUT /strategies/{id} - Update strategy
- DELETE /strategies/{id} - Delete strategy
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient
from uuid import uuid4

from app.models.users import User
from app.models.autopilot import AutoPilotStrategy, AutoPilotUserSettings
from .conftest import (
    create_strategy_request, assert_strategy_response,
    get_sample_legs_config, get_sample_entry_conditions
)


# =============================================================================
# LIST STRATEGIES TESTS
# =============================================================================

class TestListStrategies:
    """Tests for GET /api/v1/autopilot/strategies endpoint."""

    @pytest.mark.asyncio
    async def test_list_strategies_empty(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test empty list returns correctly."""
        response = await client.get("/api/v1/autopilot/strategies")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["has_next"] is False
        assert data["has_prev"] is False

    @pytest.mark.asyncio
    async def test_list_strategies_returns_all(
        self,
        client: AsyncClient,
        test_user: User,
        test_strategy,
        test_strategy_active,
        test_strategy_waiting
    ):
        """Test returns all user strategies."""
        response = await client.get("/api/v1/autopilot/strategies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["data"]) >= 3

        # Check structure of returned items
        for item in data["data"]:
            assert "id" in item
            assert "name" in item
            assert "status" in item
            assert "underlying" in item
            assert "lots" in item
            assert "leg_count" in item

    @pytest.mark.asyncio
    async def test_list_strategies_filter_status(
        self,
        client: AsyncClient,
        test_strategy,  # draft
        test_strategy_active,  # active
        test_strategy_waiting  # waiting
    ):
        """Test filter by status works."""
        # Filter by draft
        response = await client.get("/api/v1/autopilot/strategies?status=draft")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["status"] == "draft"

        # Filter by active
        response = await client.get("/api/v1/autopilot/strategies?status=active")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["status"] == "active"

    @pytest.mark.asyncio
    async def test_list_strategies_filter_underlying(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_strategy  # NIFTY
    ):
        """Test filter by underlying works."""
        # Create BANKNIFTY strategy
        banknifty_strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="BANKNIFTY Strategy",
            status="draft",
            underlying="BANKNIFTY",
            expiry_type="current_week",
            legs_config=[],
            entry_conditions={}
        )
        db_session.add(banknifty_strategy)
        await db_session.commit()

        # Filter by NIFTY
        response = await client.get("/api/v1/autopilot/strategies?underlying=NIFTY")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["underlying"] == "NIFTY"

        # Filter by BANKNIFTY
        response = await client.get("/api/v1/autopilot/strategies?underlying=BANKNIFTY")
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]:
            assert item["underlying"] == "BANKNIFTY"

    @pytest.mark.asyncio
    async def test_list_strategies_pagination(
        self,
        client: AsyncClient,
        db_session,
        test_user: User
    ):
        """Test pagination works."""
        # Create 25 strategies
        for i in range(25):
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Strategy {i}",
                status="draft",
                underlying="NIFTY",
                expiry_type="current_week",
                legs_config=[],
                entry_conditions={}
            )
            db_session.add(strategy)
        await db_session.commit()

        # Page 1 with default page_size (20)
        response = await client.get("/api/v1/autopilot/strategies?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert data["total"] == 25
        assert data["total_pages"] == 3
        assert data["has_next"] is True
        assert data["has_prev"] is False

        # Page 2
        response = await client.get("/api/v1/autopilot/strategies?page=2&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 10
        assert data["page"] == 2
        assert data["has_next"] is True
        assert data["has_prev"] is True

        # Page 3
        response = await client.get("/api/v1/autopilot/strategies?page=3&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5  # Remaining strategies
        assert data["page"] == 3
        assert data["has_next"] is False
        assert data["has_prev"] is True

    @pytest.mark.asyncio
    async def test_list_strategies_sorting(
        self,
        client: AsyncClient,
        db_session,
        test_user: User
    ):
        """Test sorting by different fields."""
        # Create strategies with different priorities
        for i, priority in enumerate([50, 100, 75]):
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Priority {priority} Strategy",
                status="draft",
                underlying="NIFTY",
                expiry_type="current_week",
                legs_config=[],
                entry_conditions={},
                priority=priority
            )
            db_session.add(strategy)
        await db_session.commit()

        # Sort by priority descending
        response = await client.get("/api/v1/autopilot/strategies?sort_by=priority&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        priorities = [item["priority"] for item in data["data"]]
        assert priorities == sorted(priorities, reverse=True)

        # Sort by priority ascending
        response = await client.get("/api/v1/autopilot/strategies?sort_by=priority&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        priorities = [item["priority"] for item in data["data"]]
        assert priorities == sorted(priorities)


# =============================================================================
# CREATE STRATEGY TESTS
# =============================================================================

class TestCreateStrategy:
    """Tests for POST /api/v1/autopilot/strategies endpoint."""

    @pytest.mark.asyncio
    async def test_create_strategy_minimal(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test create with minimum required fields."""
        request_data = {
            "name": "Minimal Strategy",
            "underlying": "NIFTY",
            "legs_config": [
                {
                    "id": "leg_1",
                    "contract_type": "CE",
                    "transaction_type": "SELL",
                    "strike_selection": {"mode": "atm_offset", "offset": 0}
                }
            ],
            "entry_conditions": {"logic": "AND", "conditions": []}
        }

        response = await client.post("/api/v1/autopilot/strategies", json=request_data)

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "created" in data["message"].lower()

        strategy = data["data"]
        assert strategy["name"] == "Minimal Strategy"
        assert strategy["underlying"] == "NIFTY"
        assert strategy["status"] == "draft"
        assert len(strategy["legs_config"]) == 1

    @pytest.mark.asyncio
    async def test_create_strategy_full(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test create with all fields."""
        request_data = create_strategy_request(
            name="Full Iron Condor",
            description="Complete Iron Condor setup",
            underlying="NIFTY",
            lots=2,
            position_type="intraday",
            legs_config=get_sample_legs_config(),
            entry_conditions=get_sample_entry_conditions(),
            order_settings={
                "order_type": "MARKET",
                "execution_style": "sequential",
                "delay_between_legs": 3
            },
            risk_settings={
                "max_loss": 5000,
                "trailing_stop": {"enabled": True, "trigger_profit": 3000, "trail_amount": 1000}
            },
            schedule_config={
                "active_days": ["MON", "TUE", "WED", "THU", "FRI"],
                "start_time": "09:20",
                "end_time": "15:00"
            },
            priority=75
        )

        response = await client.post("/api/v1/autopilot/strategies", json=request_data)

        assert response.status_code == 201
        data = response.json()

        strategy = data["data"]
        assert_strategy_response(strategy, expected_status="draft")
        assert strategy["name"] == "Full Iron Condor"
        assert strategy["description"] == "Complete Iron Condor setup"
        assert strategy["lots"] == 2
        assert len(strategy["legs_config"]) == 4
        assert strategy["entry_conditions"]["logic"] == "AND"
        assert strategy["priority"] == 75

    @pytest.mark.asyncio
    async def test_create_strategy_validation_error(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test invalid data rejected."""
        request_data = {
            "name": "Invalid Strategy",
            # Missing required fields
        }

        response = await client.post("/api/v1/autopilot/strategies", json=request_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_strategy_invalid_underlying(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test invalid underlying rejected."""
        request_data = {
            "name": "Invalid Underlying",
            "underlying": "INVALID",
            "legs_config": [{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            "entry_conditions": {"logic": "AND", "conditions": []}
        }

        response = await client.post("/api/v1/autopilot/strategies", json=request_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_strategy_max_limit(
        self,
        client: AsyncClient,
        db_session,
        test_user: User
    ):
        """Test reject if max strategies reached."""
        # Create 50 strategies (the limit)
        for i in range(50):
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Strategy {i}",
                status="draft",
                underlying="NIFTY",
                expiry_type="current_week",
                legs_config=[],
                entry_conditions={}
            )
            db_session.add(strategy)
        await db_session.commit()

        # Try to create one more
        request_data = create_strategy_request(name="One Too Many")
        response = await client.post("/api/v1/autopilot/strategies", json=request_data)

        assert response.status_code == 400
        assert "50" in response.json()["detail"].lower() or "maximum" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_strategy_duplicate_leg_ids(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test duplicate leg IDs rejected."""
        request_data = {
            "name": "Duplicate Legs",
            "underlying": "NIFTY",
            "legs_config": [
                {"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}},
                {"id": "leg_1", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}}  # Duplicate
            ],
            "entry_conditions": {"logic": "AND", "conditions": []}
        }

        response = await client.post("/api/v1/autopilot/strategies", json=request_data)

        assert response.status_code == 422


# =============================================================================
# GET SINGLE STRATEGY TESTS
# =============================================================================

class TestGetStrategy:
    """Tests for GET /api/v1/autopilot/strategies/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_strategy_found(
        self,
        client: AsyncClient,
        test_strategy
    ):
        """Test get existing strategy."""
        response = await client.get(f"/api/v1/autopilot/strategies/{test_strategy.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        strategy = data["data"]
        assert strategy["id"] == test_strategy.id
        assert strategy["name"] == test_strategy.name
        assert_strategy_response(strategy)

    @pytest.mark.asyncio
    async def test_get_strategy_not_found(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test 404 for non-existent strategy."""
        response = await client.get("/api/v1/autopilot/strategies/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_strategy_wrong_user(
        self,
        client: AsyncClient,
        db_session,
        another_user: User,
        test_strategy
    ):
        """Test can't access other user's strategy."""
        # Create strategy for another user
        other_strategy = AutoPilotStrategy(
            user_id=another_user.id,
            name="Other User Strategy",
            status="draft",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[],
            entry_conditions={}
        )
        db_session.add(other_strategy)
        await db_session.commit()
        await db_session.refresh(other_strategy)

        # Try to access it
        response = await client.get(f"/api/v1/autopilot/strategies/{other_strategy.id}")

        assert response.status_code == 404  # Returns 404 (not 403) to avoid leaking info


# =============================================================================
# UPDATE STRATEGY TESTS
# =============================================================================

class TestUpdateStrategy:
    """Tests for PUT /api/v1/autopilot/strategies/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_strategy_draft(
        self,
        client: AsyncClient,
        test_strategy  # draft status
    ):
        """Test update draft strategy."""
        update_data = {
            "name": "Updated Strategy Name",
            "description": "New description",
            "lots": 3,
            "priority": 150
        }

        response = await client.put(
            f"/api/v1/autopilot/strategies/{test_strategy.id}",
            json=update_data
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        strategy = data["data"]
        assert strategy["name"] == "Updated Strategy Name"
        assert strategy["description"] == "New description"
        assert strategy["lots"] == 3
        assert strategy["priority"] == 150

    @pytest.mark.asyncio
    async def test_update_strategy_not_draft(
        self,
        client: AsyncClient,
        test_strategy_active  # active status
    ):
        """Test can't update non-draft strategy."""
        update_data = {
            "name": "Try to Update Active"
        }

        response = await client.put(
            f"/api/v1/autopilot/strategies/{test_strategy_active.id}",
            json=update_data
        )

        assert response.status_code == 400
        assert "cannot update" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_strategy_paused(
        self,
        client: AsyncClient,
        test_strategy_paused
    ):
        """Test can update paused strategy."""
        update_data = {
            "name": "Updated Paused Strategy"
        }

        response = await client.put(
            f"/api/v1/autopilot/strategies/{test_strategy_paused.id}",
            json=update_data
        )

        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Paused Strategy"

    @pytest.mark.asyncio
    async def test_update_strategy_partial(
        self,
        client: AsyncClient,
        test_strategy
    ):
        """Test partial update works."""
        original_name = test_strategy.name
        update_data = {
            "description": "Only updating description"
        }

        response = await client.put(
            f"/api/v1/autopilot/strategies/{test_strategy.id}",
            json=update_data
        )

        assert response.status_code == 200
        strategy = response.json()["data"]
        assert strategy["description"] == "Only updating description"
        # Name should remain unchanged
        assert strategy["name"] == original_name

    @pytest.mark.asyncio
    async def test_update_strategy_legs_config(
        self,
        client: AsyncClient,
        test_strategy
    ):
        """Test updating legs_config."""
        new_legs = [
            {
                "id": "new_leg_1",
                "contract_type": "CE",
                "transaction_type": "BUY",
                "strike_selection": {"mode": "atm_offset", "offset": 0}
            }
        ]
        update_data = {
            "legs_config": new_legs
        }

        response = await client.put(
            f"/api/v1/autopilot/strategies/{test_strategy.id}",
            json=update_data
        )

        assert response.status_code == 200
        strategy = response.json()["data"]
        assert len(strategy["legs_config"]) == 1
        assert strategy["legs_config"][0]["id"] == "new_leg_1"

    @pytest.mark.asyncio
    async def test_update_strategy_not_found(
        self,
        client: AsyncClient
    ):
        """Test 404 for non-existent strategy."""
        update_data = {"name": "Update Non-existent"}

        response = await client.put(
            "/api/v1/autopilot/strategies/99999",
            json=update_data
        )

        assert response.status_code == 404


# =============================================================================
# DELETE STRATEGY TESTS
# =============================================================================

class TestDeleteStrategy:
    """Tests for DELETE /api/v1/autopilot/strategies/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_strategy_draft(
        self,
        client: AsyncClient,
        test_strategy  # draft status
    ):
        """Test delete draft strategy."""
        response = await client.delete(f"/api/v1/autopilot/strategies/{test_strategy.id}")

        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/api/v1/autopilot/strategies/{test_strategy.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_strategy_active(
        self,
        client: AsyncClient,
        test_strategy_active
    ):
        """Test can't delete active strategy."""
        response = await client.delete(f"/api/v1/autopilot/strategies/{test_strategy_active.id}")

        assert response.status_code == 400
        assert "cannot delete" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_strategy_waiting(
        self,
        client: AsyncClient,
        test_strategy_waiting
    ):
        """Test can't delete waiting strategy."""
        response = await client.delete(f"/api/v1/autopilot/strategies/{test_strategy_waiting.id}")

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_strategy_completed(
        self,
        client: AsyncClient,
        test_strategy_completed
    ):
        """Test can delete completed strategy."""
        response = await client.delete(f"/api/v1/autopilot/strategies/{test_strategy_completed.id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_strategy_not_found(
        self,
        client: AsyncClient
    ):
        """Test 404 for non-existent strategy."""
        response = await client.delete("/api/v1/autopilot/strategies/99999")

        assert response.status_code == 404
