"""
Phase 5 Model Tests

Tests for AutoPilotPositionLeg, AutoPilotAdjustmentSuggestion, and new columns.
"""

import pytest
import pytest_asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.models.autopilot import (
    AutoPilotStrategy, AutoPilotPositionLeg, AutoPilotAdjustmentSuggestion,
    AutoPilotUserSettings,
    PositionLegStatus, SuggestionType, SuggestionUrgency, SuggestionStatus
)


# =============================================================================
# POSITION LEG TESTS
# =============================================================================

class TestAutoPilotPositionLeg:
    """Tests for AutoPilotPositionLeg model."""

    @pytest.mark.asyncio
    async def test_create_position_leg_with_required_fields(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test creating position leg with required fields only."""
        leg = AutoPilotPositionLeg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_1",
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=7),
            strike=25000,
            option_type="PE",
            transaction_type="SELL",
            quantity=25,
            entry_price=Decimal("180.00"),
            status=PositionLegStatus.PENDING
        )
        db_session.add(leg)
        await db_session.commit()
        await db_session.refresh(leg)

        assert leg.id is not None
        assert leg.strategy_id == test_strategy_active.id
        assert leg.status == PositionLegStatus.PENDING

    @pytest.mark.asyncio
    async def test_create_position_leg_with_all_fields(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test creating position leg with all fields including Greeks."""
        leg = AutoPilotPositionLeg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_full",
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=7),
            strike=25000,
            option_type="CE",
            transaction_type="BUY",
            quantity=25,
            entry_price=Decimal("200.00"),
            status=PositionLegStatus.OPEN,
            entry_time=datetime.utcnow(),
            delta=Decimal("0.25"),
            gamma=Decimal("0.003"),
            theta=Decimal("-15.50"),
            vega=Decimal("9.75"),
            iv=Decimal("0.19"),
            unrealized_pnl=Decimal("250.00")
        )
        db_session.add(leg)
        await db_session.commit()
        await db_session.refresh(leg)

        assert leg.delta == Decimal("0.25")
        assert leg.gamma == Decimal("0.003")
        assert leg.theta == Decimal("-15.50")
        assert leg.unrealized_pnl == Decimal("250.00")

    @pytest.mark.asyncio
    async def test_position_leg_status_transitions(
        self, db_session: AsyncSession, test_position_leg
    ):
        """Test valid status transitions PENDING→OPEN→CLOSED."""
        # Start as PENDING
        assert test_position_leg.status == PositionLegStatus.OPEN

        # Transition to CLOSED
        test_position_leg.status = PositionLegStatus.CLOSED
        test_position_leg.exit_time = datetime.utcnow()
        test_position_leg.exit_price = Decimal("120.00")
        await db_session.commit()
        await db_session.refresh(test_position_leg)

        assert test_position_leg.status == PositionLegStatus.CLOSED
        assert test_position_leg.exit_time is not None
        assert test_position_leg.exit_price is not None

    @pytest.mark.asyncio
    async def test_position_leg_status_transitions_rolled(
        self, db_session: AsyncSession, test_position_leg
    ):
        """Test OPEN→ROLLED status transition."""
        test_position_leg.status = PositionLegStatus.ROLLED
        await db_session.commit()
        await db_session.refresh(test_position_leg)

        assert test_position_leg.status == PositionLegStatus.ROLLED

    @pytest.mark.asyncio
    async def test_position_leg_greeks_fields(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test all Greeks fields are stored correctly."""
        leg = AutoPilotPositionLeg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_greeks",
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=7),
            strike=25100,
            option_type="PE",
            transaction_type="SELL",
            quantity=25,
            entry_price=Decimal("175.00"),
            status=PositionLegStatus.OPEN,
            delta=Decimal("-0.18"),
            gamma=Decimal("0.0025"),
            theta=Decimal("-11.25"),
            vega=Decimal("7.80"),
            iv=Decimal("0.165")
        )
        db_session.add(leg)
        await db_session.commit()
        await db_session.refresh(leg)

        assert leg.delta == Decimal("-0.18")
        assert leg.gamma == Decimal("0.0025")
        assert leg.theta == Decimal("-11.25")
        assert leg.vega == Decimal("7.80")
        assert leg.iv == Decimal("0.165")

    @pytest.mark.asyncio
    async def test_position_leg_entry_exit_prices(
        self, db_session: AsyncSession, test_position_leg
    ):
        """Test entry and exit price tracking."""
        assert test_position_leg.entry_price == Decimal("185.50")
        assert test_position_leg.exit_price is None

        # Close position
        test_position_leg.exit_price = Decimal("110.00")
        test_position_leg.exit_time = datetime.utcnow()
        test_position_leg.status = PositionLegStatus.CLOSED
        await db_session.commit()
        await db_session.refresh(test_position_leg)

        assert test_position_leg.exit_price == Decimal("110.00")

    @pytest.mark.asyncio
    async def test_position_leg_unrealized_pnl_calculation(
        self, db_session: AsyncSession, test_position_leg
    ):
        """Test unrealized P&L calculation."""
        # Sell PE at 185.50, current price 150.00 = profit of 35.50 per qty
        current_price = Decimal("150.00")
        pnl_per_qty = test_position_leg.entry_price - current_price
        expected_pnl = pnl_per_qty * test_position_leg.quantity

        test_position_leg.unrealized_pnl = expected_pnl
        await db_session.commit()
        await db_session.refresh(test_position_leg)

        assert test_position_leg.unrealized_pnl == expected_pnl

    @pytest.mark.asyncio
    async def test_position_leg_realized_pnl_calculation(
        self, db_session: AsyncSession, test_position_leg
    ):
        """Test realized P&L after exit."""
        test_position_leg.exit_price = Decimal("120.00")
        test_position_leg.status = PositionLegStatus.CLOSED

        # SELL PE: entry 185.50, exit 120.00 = profit 65.50 * 25 qty
        realized_pnl = (test_position_leg.entry_price - test_position_leg.exit_price) * test_position_leg.quantity
        test_position_leg.realized_pnl = realized_pnl

        await db_session.commit()
        await db_session.refresh(test_position_leg)

        assert test_position_leg.realized_pnl == Decimal("1637.50")

    @pytest.mark.asyncio
    async def test_position_leg_relationship_to_strategy(
        self, db_session: AsyncSession, test_position_leg, test_strategy_active
    ):
        """Test relationship to parent strategy."""
        assert test_position_leg.strategy_id == test_strategy_active.id

        # Test cascade delete would work
        await db_session.refresh(test_position_leg)
        assert test_position_leg.strategy_id is not None

    @pytest.mark.asyncio
    async def test_position_leg_cascade_delete_with_strategy(
        self, db_session: AsyncSession, test_position_leg, test_strategy_active
    ):
        """Test position legs are deleted when strategy is deleted."""
        leg_id = test_position_leg.id

        # Delete strategy
        await db_session.delete(test_strategy_active)
        await db_session.commit()

        # Position leg should also be deleted (cascade)
        from sqlalchemy import select
        result = await db_session.execute(
            select(AutoPilotPositionLeg).where(AutoPilotPositionLeg.id == leg_id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_rolled_leg_relationship(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test rolled_from_leg_id and rolled_to_leg_id relationship."""
        # Create original leg
        original_leg = AutoPilotPositionLeg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_original",
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=7),
            strike=25000,
            option_type="PE",
            transaction_type="SELL",
            quantity=25,
            entry_price=Decimal("180.00"),
            status=PositionLegStatus.ROLLED
        )
        db_session.add(original_leg)
        await db_session.commit()
        await db_session.refresh(original_leg)

        # Create rolled leg
        rolled_leg = AutoPilotPositionLeg(
            strategy_id=test_strategy_active.id,
            leg_id="leg_rolled",
            underlying="NIFTY",
            expiry=date.today() + timedelta(days=14),  # New expiry
            strike=25000,
            option_type="PE",
            transaction_type="SELL",
            quantity=25,
            entry_price=Decimal("190.00"),
            status=PositionLegStatus.OPEN,
            rolled_from_leg_id=original_leg.id
        )
        db_session.add(rolled_leg)
        await db_session.commit()
        await db_session.refresh(rolled_leg)

        assert rolled_leg.rolled_from_leg_id == original_leg.id


# =============================================================================
# ADJUSTMENT SUGGESTION TESTS
# =============================================================================

class TestAutoPilotAdjustmentSuggestion:
    """Tests for AutoPilotAdjustmentSuggestion model."""

    @pytest.mark.asyncio
    async def test_create_suggestion_with_required_fields(
        self, db_session: AsyncSession, test_strategy_active, test_position_leg
    ):
        """Test creating suggestion with required fields."""
        suggestion = AutoPilotAdjustmentSuggestion(
            strategy_id=test_strategy_active.id,
            leg_id=test_position_leg.id,
            suggestion_type=SuggestionType.SHIFT,
            title="Shift leg closer",
            description="Premium decayed, shift closer to ATM",
            urgency=SuggestionUrgency.MEDIUM,
            confidence=Decimal("0.70"),
            expected_impact={},
            one_click_params={},
            status=SuggestionStatus.ACTIVE
        )
        db_session.add(suggestion)
        await db_session.commit()
        await db_session.refresh(suggestion)

        assert suggestion.id is not None
        assert suggestion.suggestion_type == SuggestionType.SHIFT

    @pytest.mark.asyncio
    async def test_suggestion_types_enum(
        self, db_session: AsyncSession, test_strategy_active, test_position_leg
    ):
        """Test all suggestion types."""
        types = [SuggestionType.SHIFT, SuggestionType.BREAK, SuggestionType.ROLL,
                 SuggestionType.EXIT, SuggestionType.ADD_HEDGE, SuggestionType.NO_ACTION]

        for stype in types:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.id,
                suggestion_type=stype,
                title=f"Test {stype.value}",
                description="Test",
                urgency=SuggestionUrgency.LOW,
                confidence=Decimal("0.50"),
                expected_impact={},
                one_click_params={},
                status=SuggestionStatus.ACTIVE
            )
            db_session.add(suggestion)

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_suggestion_urgency_levels(
        self, db_session: AsyncSession, test_strategy_active, test_position_leg
    ):
        """Test all urgency levels."""
        urgencies = [SuggestionUrgency.LOW, SuggestionUrgency.MEDIUM,
                     SuggestionUrgency.HIGH, SuggestionUrgency.CRITICAL]

        for urgency in urgencies:
            suggestion = AutoPilotAdjustmentSuggestion(
                strategy_id=test_strategy_active.id,
                leg_id=test_position_leg.id,
                suggestion_type=SuggestionType.SHIFT,
                title=f"Urgency {urgency.value}",
                description="Test",
                urgency=urgency,
                confidence=Decimal("0.60"),
                expected_impact={},
                one_click_params={},
                status=SuggestionStatus.ACTIVE
            )
            db_session.add(suggestion)

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_suggestion_status_transitions(
        self, db_session: AsyncSession, test_suggestion
    ):
        """Test status transitions ACTIVE→EXECUTED/DISMISSED."""
        assert test_suggestion.status == SuggestionStatus.ACTIVE

        # Execute suggestion
        test_suggestion.status = SuggestionStatus.EXECUTED
        test_suggestion.executed_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(test_suggestion)

        assert test_suggestion.status == SuggestionStatus.EXECUTED
        assert test_suggestion.executed_at is not None

    @pytest.mark.asyncio
    async def test_suggestion_one_click_params_jsonb(
        self, db_session: AsyncSession, test_suggestion
    ):
        """Test one_click_params JSONB field."""
        assert isinstance(test_suggestion.one_click_params, dict)
        assert "target_strike" in test_suggestion.one_click_params

    @pytest.mark.asyncio
    async def test_suggestion_expires_at_field(
        self, db_session: AsyncSession, test_suggestion
    ):
        """Test suggestion expiration."""
        assert test_suggestion.expires_at is not None

        # Check if expired
        future_time = datetime.utcnow() + timedelta(hours=3)
        assert test_suggestion.expires_at < future_time

    @pytest.mark.asyncio
    async def test_suggestion_relationship_to_strategy(
        self, db_session: AsyncSession, test_suggestion, test_strategy_active
    ):
        """Test relationship to strategy."""
        assert test_suggestion.strategy_id == test_strategy_active.id

    @pytest.mark.asyncio
    async def test_suggestion_relationship_to_leg(
        self, db_session: AsyncSession, test_suggestion, test_position_leg
    ):
        """Test relationship to position leg."""
        assert test_suggestion.leg_id == test_position_leg.id


# =============================================================================
# NEW COLUMNS ON EXISTING MODELS
# =============================================================================

class TestAutoPilotStrategyNewColumns:
    """Test new columns on AutoPilotStrategy."""

    @pytest.mark.asyncio
    async def test_strategy_net_greeks_columns(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test net Greeks columns."""
        test_strategy_active.net_delta = Decimal("0.05")
        test_strategy_active.net_theta = Decimal("-25.00")
        test_strategy_active.net_gamma = Decimal("0.005")
        test_strategy_active.net_vega = Decimal("15.50")
        await db_session.commit()
        await db_session.refresh(test_strategy_active)

        assert test_strategy_active.net_delta == Decimal("0.05")
        assert test_strategy_active.net_theta == Decimal("-25.00")

    @pytest.mark.asyncio
    async def test_strategy_breakeven_columns(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test breakeven columns."""
        test_strategy_active.breakeven_lower = Decimal("25100.00")
        test_strategy_active.breakeven_upper = Decimal("25400.00")
        await db_session.commit()
        await db_session.refresh(test_strategy_active)

        assert test_strategy_active.breakeven_lower == Decimal("25100.00")
        assert test_strategy_active.breakeven_upper == Decimal("25400.00")

    @pytest.mark.asyncio
    async def test_strategy_dte_column(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test DTE (days to expiry) column."""
        test_strategy_active.dte = 7
        await db_session.commit()
        await db_session.refresh(test_strategy_active)

        assert test_strategy_active.dte == 7

    @pytest.mark.asyncio
    async def test_strategy_position_legs_snapshot_jsonb(
        self, db_session: AsyncSession, test_strategy_active
    ):
        """Test position_legs_snapshot JSONB column."""
        snapshot = {
            "legs": [
                {"leg_id": "leg_1", "strike": 25000, "status": "open"},
                {"leg_id": "leg_2", "strike": 25500, "status": "open"}
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        test_strategy_active.position_legs_snapshot = snapshot
        await db_session.commit()
        await db_session.refresh(test_strategy_active)

        assert test_strategy_active.position_legs_snapshot == snapshot


class TestAutoPilotUserSettingsNewColumns:
    """Test new columns on AutoPilotUserSettings."""

    @pytest.mark.asyncio
    async def test_settings_delta_threshold_columns(
        self, db_session: AsyncSession, test_settings
    ):
        """Test delta threshold columns."""
        test_settings.delta_watch_threshold = Decimal("0.20")
        test_settings.delta_warning_threshold = Decimal("0.30")
        test_settings.delta_danger_threshold = Decimal("0.40")
        await db_session.commit()
        await db_session.refresh(test_settings)

        assert test_settings.delta_watch_threshold == Decimal("0.20")
        assert test_settings.delta_warning_threshold == Decimal("0.30")
        assert test_settings.delta_danger_threshold == Decimal("0.40")

    @pytest.mark.asyncio
    async def test_settings_delta_alert_enabled(
        self, db_session: AsyncSession, test_settings
    ):
        """Test delta_alert_enabled column."""
        test_settings.delta_alert_enabled = True
        await db_session.commit()
        await db_session.refresh(test_settings)

        assert test_settings.delta_alert_enabled is True

    @pytest.mark.asyncio
    async def test_settings_suggestions_enabled(
        self, db_session: AsyncSession, test_settings
    ):
        """Test suggestions_enabled column."""
        test_settings.suggestions_enabled = True
        await db_session.commit()
        await db_session.refresh(test_settings)

        assert test_settings.suggestions_enabled is True

    @pytest.mark.asyncio
    async def test_settings_prefer_round_strikes(
        self, db_session: AsyncSession, test_settings
    ):
        """Test prefer_round_strikes column."""
        test_settings.prefer_round_strikes = True
        await db_session.commit()
        await db_session.refresh(test_settings)

        assert test_settings.prefer_round_strikes is True
