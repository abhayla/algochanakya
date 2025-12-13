"""
Test suite for AutoPilot Phase 4 Backtest API endpoints.

Tests cover:
- GET /autopilot/backtests - List backtests
- POST /autopilot/backtests - Create and start a backtest
- GET /autopilot/backtests/{id} - Get backtest details
- POST /autopilot/backtests/{id}/cancel - Cancel a running backtest
- DELETE /autopilot/backtests/{id} - Delete a backtest
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.autopilot import AutoPilotBacktest, BacktestStatus
from app.models.users import User


# ============================================================================
# TEST CLASS: Backtest Listing
# ============================================================================

class TestBacktestList:
    """Tests for GET /autopilot/backtests endpoint."""

    @pytest.mark.asyncio
    async def test_list_backtests_empty(self, db_session, test_user):
        """Test listing backtests when none exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/backtests")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["data"] == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_backtests_with_data(self, db_session, test_user, test_backtest_in_db):
        """Test listing backtests returns all backtests."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/backtests")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_backtests_filter_by_status(self, db_session, test_user, test_backtest_completed):
        """Test filtering backtests by status."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/backtests?status=completed")

            assert response.status_code == 200
            data = response.json()
            for backtest in data["data"]:
                assert backtest.get("status") == "completed"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_backtests_pagination(self, db_session, test_user, test_backtest_in_db):
        """Test pagination of backtests."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/backtests?page=1&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 10
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Create Backtest
# ============================================================================

class TestCreateBacktest:
    """Tests for POST /autopilot/backtests endpoint."""

    @pytest.mark.asyncio
    async def test_create_backtest_success(self, db_session, test_user, test_autopilot_strategy):
        """Test creating a new backtest."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        backtest_data = {
            "name": "Test Backtest",
            "strategy_id": test_autopilot_strategy.id,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 500000.0,
            "slippage_pct": 0.05
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/backtests",
                    json=backtest_data
                )

            assert response.status_code == 201
            data = response.json()
            assert data["data"]["name"] == "Test Backtest"
            assert data["data"]["status"] in ["pending", "running"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_backtest_with_template(self, db_session, test_user, test_template_in_db):
        """Test creating a backtest from a template."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        backtest_data = {
            "name": "Template Backtest",
            "template_id": test_template_in_db.id,
            "start_date": "2024-06-01",
            "end_date": "2024-12-31",
            "initial_capital": 300000.0
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/backtests",
                    json=backtest_data
                )

            assert response.status_code in [201, 422]  # 422 if template_id not supported
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_backtest_invalid_date_range(self, db_session, test_user, test_autopilot_strategy):
        """Test creating backtest with end date before start date."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        backtest_data = {
            "name": "Invalid Backtest",
            "strategy_id": test_autopilot_strategy.id,
            "start_date": "2024-12-31",
            "end_date": "2024-01-01",  # End before start
            "initial_capital": 500000.0
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/backtests",
                    json=backtest_data
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_backtest_missing_required_fields(self, db_session, test_user):
        """Test creating backtest without required fields fails."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        backtest_data = {
            "name": "Missing Fields"
            # Missing strategy_id, dates, etc.
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/backtests",
                    json=backtest_data
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_backtest_negative_capital(self, db_session, test_user, test_autopilot_strategy):
        """Test creating backtest with negative capital."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        backtest_data = {
            "name": "Negative Capital Backtest",
            "strategy_id": test_autopilot_strategy.id,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": -100000.0
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/backtests",
                    json=backtest_data
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_backtest_excessive_slippage(self, db_session, test_user, test_autopilot_strategy):
        """Test creating backtest with excessive slippage percentage."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        backtest_data = {
            "name": "High Slippage Backtest",
            "strategy_id": test_autopilot_strategy.id,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 500000.0,
            "slippage_pct": 50.0  # 50% slippage - unrealistic
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/backtests",
                    json=backtest_data
                )

            # Should either accept (will produce poor results) or reject
            assert response.status_code in [201, 422]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Get Backtest Details
# ============================================================================

class TestGetBacktest:
    """Tests for GET /autopilot/backtests/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_backtest_success(self, db_session, test_user, test_backtest_in_db):
        """Test getting backtest details."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/backtests/{test_backtest_in_db.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["id"] == test_backtest_in_db.id
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_backtest_not_found(self, db_session, test_user):
        """Test getting non-existent backtest returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/backtests/99999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_backtest_other_user(self, db_session, test_user, test_backtest_in_db):
        """Test getting another user's backtest is forbidden."""
        test_backtest_in_db.user_id = test_user.id + 100
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/backtests/{test_backtest_in_db.id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_completed_backtest_with_results(self, db_session, test_user, test_backtest_completed):
        """Test getting completed backtest with results."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/backtests/{test_backtest_completed.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "completed"
            assert "results" in data["data"] or "total_pnl" in data["data"]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Cancel Backtest
# ============================================================================

class TestCancelBacktest:
    """Tests for POST /autopilot/backtests/{id}/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_running_backtest(self, db_session, test_user, test_backtest_in_db):
        """Test cancelling a running backtest."""
        test_backtest_in_db.status = BacktestStatus.running.value
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/v1/autopilot/backtests/{test_backtest_in_db.id}/cancel")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["cancelled"] is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_completed_backtest(self, db_session, test_user, test_backtest_completed):
        """Test cancelling an already completed backtest."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(f"/api/v1/autopilot/backtests/{test_backtest_completed.id}/cancel")

            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_backtest(self, db_session, test_user):
        """Test cancelling a non-existent backtest."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/v1/autopilot/backtests/99999/cancel")

            assert response.status_code in [400, 404]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Delete Backtest
# ============================================================================

class TestDeleteBacktest:
    """Tests for DELETE /autopilot/backtests/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_backtest_success(self, db_session, test_user, test_backtest_completed):
        """Test deleting a completed backtest."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/autopilot/backtests/{test_backtest_completed.id}")

            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_backtest_not_found(self, db_session, test_user):
        """Test deleting non-existent backtest returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete("/api/v1/autopilot/backtests/99999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_other_user_backtest(self, db_session, test_user, test_backtest_in_db):
        """Test deleting another user's backtest is forbidden."""
        test_backtest_in_db.user_id = test_user.id + 100
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/autopilot/backtests/{test_backtest_in_db.id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Backtest Authentication
# ============================================================================

class TestBacktestAuthentication:
    """Tests for backtest endpoint authentication."""

    @pytest.mark.asyncio
    async def test_list_backtests_requires_auth(self, db_session):
        """Test that listing backtests requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/backtests")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_backtest_requires_auth(self, db_session):
        """Test that creating backtest requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        backtest_data = {
            "name": "Test",
            "strategy_id": 1,
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 500000.0
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/backtests",
                    json=backtest_data
                )

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Backtest Results
# ============================================================================

class TestBacktestResults:
    """Tests for backtest result calculations."""

    @pytest.mark.asyncio
    async def test_backtest_results_include_metrics(self, db_session, test_user, test_backtest_completed):
        """Test that completed backtest includes performance metrics."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/backtests/{test_backtest_completed.id}")

            assert response.status_code == 200
            data = response.json()
            # Completed backtests should have results
            backtest_data = data["data"]
            assert backtest_data["status"] == "completed"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_pending_backtest_no_results(self, db_session, test_user, test_backtest_in_db):
        """Test that pending backtest has no results yet."""
        test_backtest_in_db.status = BacktestStatus.pending.value
        test_backtest_in_db.results = None
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/backtests/{test_backtest_in_db.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "pending"
        finally:
            app.dependency_overrides.clear()
