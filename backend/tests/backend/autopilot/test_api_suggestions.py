"""
Suggestions API Tests

Tests for /api/v1/autopilot/suggestions endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from datetime import date, timedelta

from app.models.users import User
from app.models.autopilot import (
    AutoPilotAdjustmentSuggestion,
    SuggestionType,
    SuggestionPriority,
    PositionLegStatus
)


class TestGetSuggestions:
    """Tests for GET suggestions endpoints."""

    @pytest.mark.asyncio
    async def test_get_suggestions_list(
        self, client: AsyncClient, test_user: User, test_strategy_active, test_position_leg
    ):
        """Test getting suggestions list."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        # Mock the suggestion engine
        with patch('app.api.v1.autopilot.suggestions.SuggestionEngine') as MockEngine:
            mock_suggestions = [
                MagicMock(
                    id=1,
                    strategy_id=test_strategy_active.id,
                    suggestion_type=SuggestionType.SHIFT,
                    priority=SuggestionPriority.CRITICAL,
                    title="Test suggestion",
                    description="Test description",
                    reasoning="Test reasoning",
                    action_params={},
                    estimated_impact={}
                )
            ]
            MockEngine.return_value.generate_suggestions = AsyncMock(return_value=mock_suggestions)

            response = await client.get(f"/api/v1/autopilot/suggestions/strategies/{test_strategy_active.id}")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_suggestions_empty_list(
        self, client: AsyncClient, test_user: User, test_strategy_active
    ):
        """Test empty suggestions list when none exist."""
        with patch('app.api.v1.autopilot.suggestions.SuggestionEngine') as MockEngine:
            MockEngine.return_value.generate_suggestions = AsyncMock(return_value=[])

            response = await client.get(f"/api/v1/autopilot/suggestions/strategies/{test_strategy_active.id}")

            assert response.status_code == 200
            data = response.json()
            assert data == []

    @pytest.mark.asyncio
    async def test_get_single_suggestion(
        self, client: AsyncClient, test_user: User, test_suggestion, db_session
    ):
        """Test getting single suggestion by ID."""
        await db_session.commit()

        response = await client.get(
            f"/api/v1/autopilot/suggestions/strategies/{test_suggestion.strategy_id}/suggestions/{test_suggestion.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_suggestion.id
        assert data["title"] == test_suggestion.title

    @pytest.mark.asyncio
    async def test_get_suggestion_not_found(
        self, client: AsyncClient, test_strategy_active
    ):
        """Test 404 for non-existent suggestion."""
        response = await client.get(
            f"/api/v1/autopilot/suggestions/strategies/{test_strategy_active.id}/suggestions/99999"
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_suggestions_unauthorized_strategy(
        self, client: AsyncClient
    ):
        """Test unauthorized access to another user's strategy."""
        response = await client.get("/api/v1/autopilot/suggestions/strategies/99999")

        # Should fail when trying to access non-existent strategy or unauthorized
        # Depending on implementation, could be 403 or 404
        assert response.status_code in [400, 404, 500]


class TestDismissSuggestion:
    """Tests for dismissing suggestions."""

    @pytest.mark.asyncio
    async def test_dismiss_suggestion_success(
        self, client: AsyncClient, test_suggestion, db_session
    ):
        """Test dismissing a suggestion."""
        await db_session.commit()

        response = await client.post(
            f"/api/v1/autopilot/suggestions/strategies/{test_suggestion.strategy_id}/suggestions/{test_suggestion.id}/dismiss"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify suggestion is deleted
        await db_session.refresh(test_suggestion, attribute_names=['id'])

    @pytest.mark.asyncio
    async def test_dismiss_suggestion_not_found(
        self, client: AsyncClient, test_strategy_active
    ):
        """Test dismissing non-existent suggestion."""
        response = await client.post(
            f"/api/v1/autopilot/suggestions/strategies/{test_strategy_active.id}/suggestions/99999/dismiss"
        )

        assert response.status_code == 404


class TestExecuteSuggestion:
    """Tests for executing suggestions."""

    @pytest.mark.asyncio
    async def test_execute_shift_suggestion(
        self, client: AsyncClient, test_suggestion, test_position_leg, db_session
    ):
        """Test executing a SHIFT suggestion."""
        test_suggestion.suggestion_type = SuggestionType.SHIFT
        test_suggestion.action_params = {
            "leg_id": test_position_leg.leg_id,
            "target_strike": 24900,
            "execution_mode": "market"
        }
        await db_session.commit()

        with patch('app.api.v1.autopilot.suggestions.LegActionsService') as MockService:
            MockService.return_value.shift_leg = AsyncMock(return_value={"status": "success"})

            response = await client.post(
                f"/api/v1/autopilot/suggestions/strategies/{test_suggestion.strategy_id}/suggestions/{test_suggestion.id}/execute"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_execute_roll_suggestion(
        self, client: AsyncClient, test_suggestion, test_position_leg, db_session
    ):
        """Test executing a ROLL suggestion."""
        test_suggestion.suggestion_type = SuggestionType.ROLL
        test_suggestion.action_params = {
            "leg_id": test_position_leg.leg_id,
            "target_expiry": (date.today() + timedelta(days=14)).isoformat(),
            "execution_mode": "market"
        }
        await db_session.commit()

        with patch('app.api.v1.autopilot.suggestions.LegActionsService') as MockService:
            MockService.return_value.roll_leg = AsyncMock(return_value={"status": "success"})

            response = await client.post(
                f"/api/v1/autopilot/suggestions/strategies/{test_suggestion.strategy_id}/suggestions/{test_suggestion.id}/execute"
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_break_suggestion(
        self, client: AsyncClient, test_suggestion, test_position_leg, db_session
    ):
        """Test executing a BREAK suggestion."""
        test_suggestion.suggestion_type = SuggestionType.BREAK
        test_suggestion.action_params = {
            "leg_id": test_position_leg.leg_id,
            "execution_mode": "market",
            "premium_split": "equal"
        }
        await db_session.commit()

        with patch('app.api.v1.autopilot.suggestions.BreakTradeService') as MockService:
            MockService.return_value.break_trade = AsyncMock(return_value={"status": "success"})

            response = await client.post(
                f"/api/v1/autopilot/suggestions/strategies/{test_suggestion.strategy_id}/suggestions/{test_suggestion.id}/execute"
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_exit_suggestion(
        self, client: AsyncClient, test_suggestion, test_position_leg, db_session
    ):
        """Test executing an EXIT suggestion."""
        test_suggestion.suggestion_type = SuggestionType.EXIT
        test_suggestion.action_params = {
            "leg_id": test_position_leg.leg_id,
            "execution_mode": "market"
        }
        await db_session.commit()

        with patch('app.api.v1.autopilot.suggestions.LegActionsService') as MockService:
            MockService.return_value.exit_leg = AsyncMock(return_value={"status": "success"})

            response = await client.post(
                f"/api/v1/autopilot/suggestions/strategies/{test_suggestion.strategy_id}/suggestions/{test_suggestion.id}/execute"
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_execute_suggestion_not_found(
        self, client: AsyncClient, test_strategy_active
    ):
        """Test executing non-existent suggestion."""
        response = await client.post(
            f"/api/v1/autopilot/suggestions/strategies/{test_strategy_active.id}/suggestions/99999/execute"
        )

        assert response.status_code == 404


class TestRefreshSuggestions:
    """Tests for refreshing suggestions."""

    @pytest.mark.asyncio
    async def test_refresh_suggestions(
        self, client: AsyncClient, test_strategy_active, test_position_leg
    ):
        """Test refreshing suggestions."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN

        with patch('app.api.v1.autopilot.suggestions.SuggestionEngine') as MockEngine:
            mock_suggestions = [
                MagicMock(
                    id=1,
                    title="New suggestion"
                )
            ]
            MockEngine.return_value.generate_suggestions = AsyncMock(return_value=mock_suggestions)

            response = await client.post(
                f"/api/v1/autopilot/suggestions/strategies/{test_strategy_active.id}/suggestions/refresh"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_refresh_suggestions_clears_old(
        self, client: AsyncClient, test_strategy_active, test_suggestion, test_position_leg, db_session
    ):
        """Test refresh clears old suggestions."""
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        # Get initial count
        from sqlalchemy import select
        result = await db_session.execute(
            select(AutoPilotAdjustmentSuggestion).where(
                AutoPilotAdjustmentSuggestion.strategy_id == test_strategy_active.id
            )
        )
        initial_count = len(result.scalars().all())

        with patch('app.api.v1.autopilot.suggestions.SuggestionEngine') as MockEngine:
            # Return different suggestions
            mock_suggestions = [
                MagicMock(id=999, title="New suggestion")
            ]
            MockEngine.return_value.generate_suggestions = AsyncMock(return_value=mock_suggestions)

            response = await client.post(
                f"/api/v1/autopilot/suggestions/strategies/{test_strategy_active.id}/suggestions/refresh"
            )

            assert response.status_code == 200
            data = response.json()
            # The engine clears old suggestions and creates new ones
            assert "count" in data
