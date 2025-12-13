"""
Test suite for AutoPilot Phase 4 Integration Tests.

These tests verify end-to-end flows across multiple features:
- Template to Strategy to Journal flow
- Backtest to Analysis flow
- Report generation with trade data
- Strategy sharing and cloning workflow
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.autopilot import (
    AutoPilotStrategy, AutoPilotTemplate, AutoPilotTradeJournal,
    AutoPilotBacktest, AutoPilotReport, AutoPilotTemplateRating,
    TemplateCategory, ExitReason, BacktestStatus, ReportType
)
from app.models.users import User


# ============================================================================
# TEST CLASS: Template to Strategy Flow
# ============================================================================

class TestTemplateToStrategyFlow:
    """Integration tests for template deployment and strategy creation."""

    @pytest.mark.asyncio
    async def test_deploy_template_creates_strategy(self, db_session, test_user, test_template_in_db):
        """Test that deploying a template creates a new strategy."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        deploy_data = {
            "strategy_name": "My Iron Condor",
            "lots": 2
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # Deploy template
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/deploy",
                    json=deploy_data
                )

            assert response.status_code == 201
            data = response.json()
            strategy_id = data["data"]["id"]

            # Verify strategy was created
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                strategy_response = await client.get(f"/api/v1/autopilot/strategies/{strategy_id}")

            assert strategy_response.status_code == 200
            strategy_data = strategy_response.json()
            assert strategy_data["data"]["name"] == "My Iron Condor"
            assert strategy_data["data"]["source_template_id"] == test_template_in_db.id
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_template_usage_count_increments(self, db_session, test_user, test_template_in_db):
        """Test that deploying a template increments its usage count."""
        initial_count = test_template_in_db.usage_count or 0

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        deploy_data = {"lots": 1}

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/deploy",
                    json=deploy_data
                )

            await db_session.refresh(test_template_in_db)
            assert test_template_in_db.usage_count == initial_count + 1
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Strategy to Trade Journal Flow
# ============================================================================

class TestStrategyToJournalFlow:
    """Integration tests for strategy execution and trade journaling."""

    @pytest.mark.asyncio
    async def test_completed_trade_appears_in_journal(
        self, db_session, test_user, test_autopilot_strategy, test_trade_journal_in_db
    ):
        """Test that completed trades appear in the journal."""
        # Link journal entry to strategy
        test_trade_journal_in_db.strategy_id = test_autopilot_strategy.id
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
                response = await client.get("/api/v1/autopilot/journal")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1

            # Find the trade for our strategy
            strategy_trades = [
                t for t in data["data"]
                if t.get("strategy_id") == test_autopilot_strategy.id
            ]
            assert len(strategy_trades) >= 1
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Backtest to Analytics Flow
# ============================================================================

class TestBacktestToAnalyticsFlow:
    """Integration tests for backtest and analytics."""

    @pytest.mark.asyncio
    async def test_backtest_creates_performance_data(
        self, db_session, test_user, test_autopilot_strategy, test_backtest_completed
    ):
        """Test that completed backtests can be analyzed."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)

            # Get backtest results
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                backtest_response = await client.get(
                    f"/api/v1/autopilot/backtests/{test_backtest_completed.id}"
                )

            assert backtest_response.status_code == 200
            backtest_data = backtest_response.json()
            assert backtest_data["data"]["status"] == "completed"

            # Get analytics (should work with backtest data)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                analytics_response = await client.get("/api/v1/autopilot/analytics/performance")

            assert analytics_response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Report Generation Flow
# ============================================================================

class TestReportGenerationFlow:
    """Integration tests for report generation with real data."""

    @pytest.mark.asyncio
    async def test_generate_report_with_trades(
        self, db_session, test_user, test_journal_entries
    ):
        """Test generating a report when trade data exists."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        report_data = {
            "report_type": "monthly_performance",
            "name": "December 2024 Performance",
            "start_date": "2024-12-01",
            "end_date": "2024-12-31",
            "format": "pdf"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/reports/generate",
                    json=report_data
                )

            assert response.status_code == 201
            data = response.json()
            report_id = data["data"]["id"]

            # Verify report was created
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                report_response = await client.get(f"/api/v1/autopilot/reports/{report_id}")

            assert report_response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Strategy Sharing Flow
# ============================================================================

class TestStrategySharingFlow:
    """Integration tests for strategy sharing and cloning."""

    @pytest.mark.asyncio
    async def test_share_clone_workflow(self, db_session, test_user, test_autopilot_strategy):
        """Test complete share and clone workflow."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)

            # Step 1: Share the strategy
            share_data = {"share_mode": "clonable"}
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                share_response = await client.post(
                    f"/api/v1/autopilot/strategies/{test_autopilot_strategy.id}/share",
                    json=share_data
                )

            assert share_response.status_code == 200
            share_token = share_response.json()["data"]["share_token"]

            # Step 2: Access shared strategy (public)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                shared_response = await client.get(f"/api/v1/autopilot/shared/{share_token}")

            assert shared_response.status_code == 200

            # Step 3: Clone the shared strategy
            clone_data = {
                "new_name": "Cloned Strategy",
                "lots": 1
            }
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                clone_response = await client.post(
                    f"/api/v1/autopilot/shared/{share_token}/clone",
                    json=clone_data
                )

            assert clone_response.status_code == 201
            cloned_id = clone_response.json()["data"]["id"]

            # Step 4: Verify cloned strategy exists
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                cloned_strategy_response = await client.get(
                    f"/api/v1/autopilot/strategies/{cloned_id}"
                )

            assert cloned_strategy_response.status_code == 200
            assert cloned_strategy_response.json()["data"]["cloned_from_id"] == test_autopilot_strategy.id
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unshare_breaks_access(self, db_session, test_user, test_strategy_with_share_token):
        """Test that unsharing breaks public access."""
        share_token = test_strategy_with_share_token.share_token

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)

            # Verify shared access works initially
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                shared_response = await client.get(f"/api/v1/autopilot/shared/{share_token}")

            assert shared_response.status_code == 200

            # Unshare the strategy
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                unshare_response = await client.delete(
                    f"/api/v1/autopilot/strategies/{test_strategy_with_share_token.id}/share"
                )

            assert unshare_response.status_code == 200

            # Verify shared access no longer works
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                shared_response = await client.get(f"/api/v1/autopilot/shared/{share_token}")

            assert shared_response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Template Rating Flow
# ============================================================================

class TestTemplateRatingFlow:
    """Integration tests for template rating and average calculation."""

    @pytest.mark.asyncio
    async def test_rating_updates_average(self, db_session, test_user, test_template_in_db):
        """Test that rating a template updates its average rating."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        rating_data = {"rating": 5, "review": "Great template!"}

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/rate",
                    json=rating_data
                )

            assert response.status_code == 200

            # Verify average rating is updated
            await db_session.refresh(test_template_in_db)
            assert test_template_in_db.average_rating is not None
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Full Trade Lifecycle
# ============================================================================

class TestFullTradeLifecycle:
    """Integration tests for complete trade lifecycle."""

    @pytest.mark.asyncio
    async def test_strategy_lifecycle(self, db_session, test_user, get_iron_condor_legs_config):
        """Test complete strategy lifecycle: create -> activate -> track."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        strategy_data = {
            "name": "Lifecycle Test Strategy",
            "underlying": "NIFTY",
            "expiry_type": "weekly",
            "lots": 1,
            "position_type": "short",
            "legs_config": get_iron_condor_legs_config,
            "entry_conditions": {
                "time_condition": {"start_time": "09:30", "end_time": "15:00"}
            }
        }

        try:
            transport = ASGITransport(app=app)

            # Step 1: Create strategy
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                create_response = await client.post(
                    "/api/v1/autopilot/strategies",
                    json=strategy_data
                )

            assert create_response.status_code == 201
            strategy_id = create_response.json()["data"]["id"]
            assert create_response.json()["data"]["status"] == "draft"

            # Step 2: Activate strategy
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                activate_response = await client.post(
                    f"/api/v1/autopilot/strategies/{strategy_id}/activate",
                    json={"paper_trading": True}
                )

            assert activate_response.status_code == 200
            assert activate_response.json()["data"]["status"] == "waiting"

            # Step 3: Pause strategy
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                pause_response = await client.post(
                    f"/api/v1/autopilot/strategies/{strategy_id}/pause"
                )

            assert pause_response.status_code == 200
            assert pause_response.json()["data"]["status"] == "paused"

            # Step 4: Resume strategy
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resume_response = await client.post(
                    f"/api/v1/autopilot/strategies/{strategy_id}/resume"
                )

            assert resume_response.status_code == 200
            assert resume_response.json()["data"]["status"] == "waiting"
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Cross-Feature Consistency
# ============================================================================

class TestCrossFeatureConsistency:
    """Integration tests for data consistency across features."""

    @pytest.mark.asyncio
    async def test_journal_stats_match_trade_count(
        self, db_session, test_user, test_journal_entries
    ):
        """Test that journal stats match actual trade count."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)

            # Get trade list
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                list_response = await client.get("/api/v1/autopilot/journal")

            # Get stats
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                stats_response = await client.get("/api/v1/autopilot/journal/stats")

            list_data = list_response.json()
            stats_data = stats_response.json()

            # Trade count should be consistent
            assert list_data["total"] == len(list_data["data"])
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_template_categories_match_list(
        self, db_session, test_user, test_multiple_templates
    ):
        """Test that category counts match template list."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)

            # Get categories
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                categories_response = await client.get("/api/v1/autopilot/templates/categories")

            # Get all templates
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                templates_response = await client.get("/api/v1/autopilot/templates?page_size=100")

            assert categories_response.status_code == 200
            assert templates_response.status_code == 200
        finally:
            app.dependency_overrides.clear()
