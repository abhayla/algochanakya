"""
Backend Unit Tests for StrategyTemplate Model

Tests the StrategyTemplate model and database operations.
Covers: CRUD operations, constraints, validations, and default values.

Run with: pytest tests/test_strategy_templates.py -v
"""

import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.strategy_templates import StrategyTemplate


pytestmark = pytest.mark.asyncio


class TestStrategyTemplateModel:
    """Test StrategyTemplate model operations."""

    async def test_create_strategy_template(self, db_session):
        """Test creating a template and verify all fields saved correctly."""
        template = StrategyTemplate(
            id=uuid4(),
            name="test_bull_spread",
            display_name="Test Bull Spread",
            category="bullish",
            description="A test bull spread strategy",
            legs_config=[
                {"type": "CE", "position": "BUY", "strike_offset": 0},
                {"type": "CE", "position": "SELL", "strike_offset": 200}
            ],
            max_profit="Limited",
            max_loss="Limited",
            breakeven="Lower strike + premium",
            market_outlook="bullish",
            volatility_preference="low_iv",
            ideal_iv_rank="<50%",
            risk_level="low",
            capital_requirement="low",
            margin_requirement="Low margin",
            theta_positive=False,
            vega_positive=True,
            delta_neutral=False,
            gamma_risk="low",
            win_probability="~45%",
            profit_target="50% of max profit",
            when_to_use="Moderate upward movement expected",
            pros=["Limited risk", "Lower cost than buying calls"],
            cons=["Limited profit", "Time decay works against you"],
            common_mistakes=["Setting strikes too wide"],
            exit_rules=["Exit at 50% profit"],
            popularity_score=85,
            difficulty_level="beginner",
            tags=["bullish", "debit"]
        )

        db_session.add(template)
        await db_session.commit()

        # Query the template back
        result = await db_session.execute(
            select(StrategyTemplate).where(StrategyTemplate.name == "test_bull_spread")
        )
        saved_template = result.scalar_one()

        # Verify all fields
        assert saved_template.name == "test_bull_spread"
        assert saved_template.display_name == "Test Bull Spread"
        assert saved_template.category == "bullish"
        assert saved_template.description == "A test bull spread strategy"
        assert len(saved_template.legs_config) == 2
        assert saved_template.legs_config[0]["type"] == "CE"
        assert saved_template.legs_config[0]["position"] == "BUY"
        assert saved_template.max_profit == "Limited"
        assert saved_template.max_loss == "Limited"
        assert saved_template.market_outlook == "bullish"
        assert saved_template.volatility_preference == "low_iv"
        assert saved_template.risk_level == "low"
        assert saved_template.theta_positive is False
        assert saved_template.vega_positive is True
        assert saved_template.delta_neutral is False
        assert saved_template.popularity_score == 85
        assert saved_template.difficulty_level == "beginner"
        assert "bullish" in saved_template.tags

    async def test_template_unique_name_constraint(self, db_session, sample_strategy_template):
        """Test that duplicate names raise an error."""
        duplicate_template = StrategyTemplate(
            id=uuid4(),
            name=sample_strategy_template.name,  # Same name as existing
            display_name="Duplicate Strategy",
            category="neutral",
            description="This should fail",
            legs_config=[{"type": "CE", "position": "SELL", "strike_offset": 0}],
            max_profit="Limited",
            max_loss="Limited",
            market_outlook="neutral",
            volatility_preference="high_iv",
            risk_level="medium",
            capital_requirement="medium"
        )

        db_session.add(duplicate_template)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_template_legs_config_json(self, db_session):
        """Test that JSON legs_config stores and retrieves correctly."""
        complex_legs = [
            {"type": "PE", "position": "BUY", "strike_offset": -400, "expiry_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": -200, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 200, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 400, "expiry_offset": 0}
        ]

        template = StrategyTemplate(
            id=uuid4(),
            name="test_iron_condor_json",
            display_name="Test Iron Condor JSON",
            category="neutral",
            description="Testing JSON storage",
            legs_config=complex_legs,
            max_profit="Limited",
            max_loss="Limited",
            market_outlook="neutral",
            volatility_preference="high_iv",
            risk_level="medium",
            capital_requirement="medium"
        )

        db_session.add(template)
        await db_session.commit()

        # Query and verify JSON structure preserved
        result = await db_session.execute(
            select(StrategyTemplate).where(StrategyTemplate.name == "test_iron_condor_json")
        )
        saved = result.scalar_one()

        assert len(saved.legs_config) == 4
        assert saved.legs_config[0]["type"] == "PE"
        assert saved.legs_config[0]["position"] == "BUY"
        assert saved.legs_config[0]["strike_offset"] == -400
        assert saved.legs_config[3]["type"] == "CE"
        assert saved.legs_config[3]["strike_offset"] == 400

    async def test_template_risk_level_values(self, db_session):
        """Test LOW, MEDIUM, HIGH risk level values."""
        risk_levels = ["low", "medium", "high"]

        for i, risk in enumerate(risk_levels):
            template = StrategyTemplate(
                id=uuid4(),
                name=f"test_risk_{risk}",
                display_name=f"Test Risk {risk.title()}",
                category="neutral",
                description=f"Testing {risk} risk level",
                legs_config=[{"type": "CE", "position": "SELL", "strike_offset": 0}],
                max_profit="Limited",
                max_loss="Limited",
                market_outlook="neutral",
                volatility_preference="high_iv",
                risk_level=risk,
                capital_requirement="medium"
            )
            db_session.add(template)

        await db_session.commit()

        # Verify each risk level
        for risk in risk_levels:
            result = await db_session.execute(
                select(StrategyTemplate).where(StrategyTemplate.name == f"test_risk_{risk}")
            )
            saved = result.scalar_one()
            assert saved.risk_level == risk

    async def test_template_default_values(self, db_session):
        """Test that default values are applied correctly."""
        template = StrategyTemplate(
            id=uuid4(),
            name="test_defaults",
            display_name="Test Defaults",
            category="neutral",
            description="Testing default values",
            legs_config=[{"type": "CE", "position": "SELL", "strike_offset": 0}],
            max_profit="Limited",
            max_loss="Limited",
            market_outlook="neutral",
            volatility_preference="any",
            risk_level="medium",
            capital_requirement="medium"
        )

        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Check default values
        assert template.popularity_score == 0  # Default
        assert template.difficulty_level == "intermediate"  # Default
        assert template.theta_positive is False  # Default
        assert template.vega_positive is False  # Default
        assert template.delta_neutral is False  # Default
        assert template.created_at is not None
        assert template.updated_at is not None

    async def test_update_template(self, db_session, sample_strategy_template):
        """Test updating template fields and verifying changes."""
        original_name = sample_strategy_template.display_name
        original_score = sample_strategy_template.popularity_score

        # Update fields
        sample_strategy_template.display_name = "Updated Strategy Name"
        sample_strategy_template.popularity_score = 99
        sample_strategy_template.theta_positive = False

        await db_session.commit()
        await db_session.refresh(sample_strategy_template)

        # Verify updates
        assert sample_strategy_template.display_name == "Updated Strategy Name"
        assert sample_strategy_template.display_name != original_name
        assert sample_strategy_template.popularity_score == 99
        assert sample_strategy_template.popularity_score != original_score
        assert sample_strategy_template.theta_positive is False

    async def test_template_timestamps(self, db_session):
        """Test that created_at and updated_at are set correctly."""
        from datetime import timedelta
        before_create = datetime.utcnow() - timedelta(seconds=1)  # Buffer for timing differences

        template = StrategyTemplate(
            id=uuid4(),
            name="test_timestamps",
            display_name="Test Timestamps",
            category="neutral",
            description="Testing timestamps",
            legs_config=[{"type": "CE", "position": "SELL", "strike_offset": 0}],
            max_profit="Limited",
            max_loss="Limited",
            market_outlook="neutral",
            volatility_preference="any",
            risk_level="medium",
            capital_requirement="medium"
        )

        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        after_create = datetime.utcnow() + timedelta(seconds=1)  # Buffer for timing differences

        # Verify created_at is set
        assert template.created_at is not None
        assert before_create <= template.created_at.replace(tzinfo=None) <= after_create

        # Verify updated_at is set
        assert template.updated_at is not None


class TestStrategyTemplateQueries:
    """Test querying StrategyTemplate records."""

    async def test_query_by_category(self, db_session, seeded_templates):
        """Test filtering templates by category."""
        result = await db_session.execute(
            select(StrategyTemplate).where(StrategyTemplate.category == "neutral")
        )
        neutral_templates = result.scalars().all()

        assert len(neutral_templates) >= 1
        for template in neutral_templates:
            assert template.category == "neutral"

    async def test_query_by_risk_level(self, db_session, seeded_templates):
        """Test filtering templates by risk level."""
        result = await db_session.execute(
            select(StrategyTemplate).where(StrategyTemplate.risk_level == "low")
        )
        low_risk_templates = result.scalars().all()

        for template in low_risk_templates:
            assert template.risk_level == "low"

    async def test_query_theta_positive(self, db_session, seeded_templates):
        """Test filtering for theta positive strategies."""
        result = await db_session.execute(
            select(StrategyTemplate).where(StrategyTemplate.theta_positive == True)
        )
        theta_positive_templates = result.scalars().all()

        assert len(theta_positive_templates) >= 1
        for template in theta_positive_templates:
            assert template.theta_positive is True

    async def test_query_order_by_popularity(self, db_session, seeded_templates):
        """Test ordering templates by popularity score."""
        result = await db_session.execute(
            select(StrategyTemplate).order_by(StrategyTemplate.popularity_score.desc())
        )
        templates = result.scalars().all()

        # Verify ordering
        for i in range(len(templates) - 1):
            assert templates[i].popularity_score >= templates[i + 1].popularity_score

    async def test_query_by_difficulty(self, db_session, seeded_templates):
        """Test filtering templates by difficulty level."""
        result = await db_session.execute(
            select(StrategyTemplate).where(StrategyTemplate.difficulty_level == "beginner")
        )
        beginner_templates = result.scalars().all()

        for template in beginner_templates:
            assert template.difficulty_level == "beginner"


class TestStrategyTemplateLegConfigs:
    """Test different leg configurations."""

    async def test_two_leg_spread(self, db_session, bull_call_spread_template):
        """Test 2-leg vertical spread configuration."""
        assert len(bull_call_spread_template.legs_config) == 2
        assert bull_call_spread_template.legs_config[0]["position"] == "BUY"
        assert bull_call_spread_template.legs_config[1]["position"] == "SELL"

    async def test_four_leg_iron_condor(self, db_session, iron_condor_template):
        """Test 4-leg iron condor configuration."""
        legs = iron_condor_template.legs_config
        assert len(legs) == 4

        # Verify structure: BUY PE (lower), SELL PE, SELL CE, BUY CE (higher)
        assert legs[0]["type"] == "PE" and legs[0]["position"] == "BUY"
        assert legs[1]["type"] == "PE" and legs[1]["position"] == "SELL"
        assert legs[2]["type"] == "CE" and legs[2]["position"] == "SELL"
        assert legs[3]["type"] == "CE" and legs[3]["position"] == "BUY"

    async def test_straddle_same_strikes(self, db_session, short_straddle_template):
        """Test straddle with same strike for both legs."""
        legs = short_straddle_template.legs_config
        assert len(legs) == 2

        # Both legs should have same strike offset (ATM)
        assert legs[0]["strike_offset"] == 0
        assert legs[1]["strike_offset"] == 0
        assert legs[0]["type"] != legs[1]["type"]  # CE and PE


class TestStrategyTemplateRepr:
    """Test string representation."""

    async def test_repr(self, sample_strategy_template):
        """Test __repr__ method."""
        repr_str = repr(sample_strategy_template)
        assert "StrategyTemplate" in repr_str
        assert sample_strategy_template.name in repr_str
        assert sample_strategy_template.category in repr_str
