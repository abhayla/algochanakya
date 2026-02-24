"""
SuggestionEngine Service Tests

Tests for AI-powered adjustment suggestions based on position analysis.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
from decimal import Decimal

from app.services.autopilot.suggestion_engine import SuggestionEngine, DTEZone
from app.models.autopilot import (
    AutoPilotStrategy,
    AutoPilotPositionLeg,
    AutoPilotUserSettings,
    PositionLegStatus,
    SuggestionType,
    SuggestionPriority
)


class TestSuggestionEngine:
    """Test SuggestionEngine functionality."""

    @pytest.mark.asyncio
    async def test_generate_suggestions_returns_list(
        self, db_session, test_strategy_active, test_position_legs_multiple, test_user, test_user_settings
    ):
        """Test generate_suggestions returns a list."""
        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        assert isinstance(suggestions, list)

    @pytest.mark.asyncio
    async def test_suggest_for_high_delta_critical(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test critical delta suggestion when net delta exceeds danger threshold."""
        # Set high delta on strategy
        test_strategy_active.net_delta = Decimal("0.60")
        test_strategy_active.status = "active"
        await db_session.commit()

        # Set high delta on leg
        test_position_leg.delta = Decimal("0.60")
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # Should get critical delta suggestion
        delta_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.SHIFT]
        assert len(delta_suggestions) > 0
        assert delta_suggestions[0].urgency == SuggestionPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_suggest_for_moderate_delta_warning(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test warning delta suggestion when net delta exceeds warning threshold."""
        # Set moderate delta on strategy
        test_strategy_active.net_delta = Decimal("0.35")
        test_strategy_active.status = "active"
        await db_session.commit()

        # Set moderate delta on leg
        test_position_leg.delta = Decimal("0.35")
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # Should get high priority delta suggestion
        delta_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.SHIFT]
        assert len(delta_suggestions) > 0
        assert delta_suggestions[0].urgency == SuggestionPriority.HIGH

    @pytest.mark.asyncio
    async def test_suggest_break_trade_for_losing_leg(
        self, db_session, test_break_trade_scenario, test_user, test_user_settings
    ):
        """Test break trade suggestion for losing leg."""
        strategy, losing_leg = test_break_trade_scenario

        # Set large unrealized loss
        losing_leg.unrealized_pnl = Decimal("-600.00")
        losing_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25300.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(strategy.id, test_user.id)

        # Should get break trade suggestion
        break_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.BREAK]
        assert len(break_suggestions) > 0
        assert break_suggestions[0].urgency == SuggestionPriority.CRITICAL
        assert "break trade" in break_suggestions[0].title.lower()

    @pytest.mark.asyncio
    async def test_suggest_exit_approaching_max_loss(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test exit suggestion when P&L approaches max loss."""
        # Set max loss limit
        test_strategy_active.risk_settings = {"max_loss": 1000}
        test_strategy_active.runtime_state = {"current_pnl": -750}  # 75% of max loss
        test_strategy_active.status = "active"
        await db_session.commit()

        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # Should get exit suggestion
        exit_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.EXIT]
        assert len(exit_suggestions) > 0
        assert "exit" in exit_suggestions[0].title.lower()

    @pytest.mark.asyncio
    async def test_suggest_roll_near_expiry(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test roll suggestion near expiry."""
        # Set expiry in 5 days (LATE zone)
        test_position_leg.expiry = date.today() + timedelta(days=5)
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        test_strategy_active.status = "active"
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # Should get roll suggestion
        roll_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.ROLL]
        assert len(roll_suggestions) > 0
        assert "roll" in roll_suggestions[0].title.lower()
        assert roll_suggestions[0].urgency == SuggestionPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_suggest_exit_expiry_day(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test critical exit suggestion on expiry day."""
        # Set expiry today (EXPIRY zone)
        test_position_leg.expiry = date.today()
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        test_strategy_active.status = "active"
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # Should get critical exit suggestion
        exit_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.EXIT]
        assert len(exit_suggestions) > 0
        expiry_exit = [s for s in exit_suggestions if "expiry" in s.title.lower()]
        assert len(expiry_exit) > 0
        assert expiry_exit[0].urgency == SuggestionPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_no_suggestion_when_healthy(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test no critical suggestions when position is healthy."""
        # Set healthy metrics
        test_strategy_active.net_delta = Decimal("0.05")  # Low delta
        test_strategy_active.runtime_state = {"current_pnl": 100}  # Profitable
        test_strategy_active.status = "active"
        await db_session.commit()

        # Set expiry far away
        test_position_leg.expiry = date.today() + timedelta(days=20)
        test_position_leg.delta = Decimal("0.05")
        test_position_leg.unrealized_pnl = Decimal("50.00")  # Profitable
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # Should have no critical or high priority suggestions
        critical_suggestions = [s for s in suggestions if s.urgency == SuggestionPriority.CRITICAL]
        high_suggestions = [s for s in suggestions if s.urgency == SuggestionPriority.HIGH]
        assert len(critical_suggestions) == 0
        assert len(high_suggestions) == 0

    @pytest.mark.asyncio
    async def test_dte_zone_affects_thresholds(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test DTE zone affects delta thresholds."""
        # Set moderate delta that should trigger warning in LATE zone
        test_strategy_active.net_delta = Decimal("0.25")
        test_strategy_active.status = "active"
        await db_session.commit()

        # Set expiry in 4 days (LATE zone)
        test_position_leg.expiry = date.today() + timedelta(days=4)
        test_position_leg.delta = Decimal("0.25")
        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # LATE zone should have tighter thresholds, so 0.25 delta should trigger suggestion
        # (0.30 warning threshold * 0.7 = 0.21)
        delta_suggestions = [s for s in suggestions if s.suggestion_type == SuggestionType.SHIFT]
        assert len(delta_suggestions) > 0  # Should trigger due to tighter threshold

    @pytest.mark.asyncio
    async def test_suggestions_disabled_returns_empty(
        self, db_session, test_strategy_active, test_position_leg, test_user, test_user_settings
    ):
        """Test no suggestions when suggestions_enabled is False."""
        # Disable suggestions
        test_user_settings.suggestions_enabled = False
        await db_session.commit()

        test_strategy_active.status = "active"
        test_strategy_active.net_delta = Decimal("0.80")  # High delta
        await db_session.commit()

        test_position_leg.strategy_id = test_strategy_active.id
        test_position_leg.status = PositionLegStatus.OPEN
        await db_session.commit()

        mock_kite = MagicMock()
        mock_market_data = MagicMock()
        mock_market_data.get_spot_price = AsyncMock(return_value=Decimal("25000.00"))
        mock_market_data.get_vix = AsyncMock(return_value=Decimal("15.00"))

        service = SuggestionEngine(mock_kite, db_session, mock_market_data)

        suggestions = await service.generate_suggestions(test_strategy_active.id, test_user.id)

        # Should return empty list
        assert suggestions == []
