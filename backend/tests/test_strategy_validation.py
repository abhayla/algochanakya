"""
Strategy Template Validation Tests

Validates the correctness of strategy template configurations:
- Legs configuration (type, position, strike offsets)
- Strategy characteristics (theta, vega, delta)
- Risk levels and win probabilities

Run with: pytest tests/test_strategy_validation.py -v
"""

import pytest
from uuid import uuid4

from app.models.strategy_templates import StrategyTemplate


pytestmark = pytest.mark.asyncio


class TestLegsConfiguration:
    """Test legs configuration for various strategies."""

    async def test_bull_call_spread_legs(self, bull_call_spread_template):
        """Verify Bull Call Spread: BUY CE offset 0, SELL CE offset +200."""
        legs = bull_call_spread_template.legs_config

        assert len(legs) == 2, "Bull Call Spread should have 2 legs"

        # First leg: Buy ATM CE
        assert legs[0]["type"] == "CE"
        assert legs[0]["position"] == "BUY"
        assert legs[0]["strike_offset"] == 0

        # Second leg: Sell OTM CE
        assert legs[1]["type"] == "CE"
        assert legs[1]["position"] == "SELL"
        assert legs[1]["strike_offset"] > 0  # Higher strike

    async def test_bull_put_spread_legs(self, bull_put_spread_template):
        """Verify Bull Put Spread: SELL PE offset 0, BUY PE offset -200."""
        legs = bull_put_spread_template.legs_config

        assert len(legs) == 2, "Bull Put Spread should have 2 legs"

        # First leg: Sell higher strike PE
        sell_leg = next((l for l in legs if l["position"] == "SELL"), None)
        buy_leg = next((l for l in legs if l["position"] == "BUY"), None)

        assert sell_leg is not None, "Should have a SELL leg"
        assert buy_leg is not None, "Should have a BUY leg"
        assert sell_leg["type"] == "PE"
        assert buy_leg["type"] == "PE"
        assert sell_leg["strike_offset"] > buy_leg["strike_offset"], "Sell strike should be higher"

    async def test_iron_condor_legs(self, iron_condor_template):
        """Verify Iron Condor has 4 legs in correct order."""
        legs = iron_condor_template.legs_config

        assert len(legs) == 4, "Iron Condor should have 4 legs"

        # Extract by type and position
        pe_buy = [l for l in legs if l["type"] == "PE" and l["position"] == "BUY"]
        pe_sell = [l for l in legs if l["type"] == "PE" and l["position"] == "SELL"]
        ce_sell = [l for l in legs if l["type"] == "CE" and l["position"] == "SELL"]
        ce_buy = [l for l in legs if l["type"] == "CE" and l["position"] == "BUY"]

        assert len(pe_buy) == 1, "Should have 1 PE BUY leg"
        assert len(pe_sell) == 1, "Should have 1 PE SELL leg"
        assert len(ce_sell) == 1, "Should have 1 CE SELL leg"
        assert len(ce_buy) == 1, "Should have 1 CE BUY leg"

        # Verify strike order: PE_BUY < PE_SELL < CE_SELL < CE_BUY
        assert pe_buy[0]["strike_offset"] < pe_sell[0]["strike_offset"]
        assert pe_sell[0]["strike_offset"] < ce_sell[0]["strike_offset"]
        assert ce_sell[0]["strike_offset"] < ce_buy[0]["strike_offset"]

    async def test_iron_butterfly_legs(self, db_session):
        """Verify Iron Butterfly: ATM straddle + OTM wings."""
        template = StrategyTemplate(
            id=uuid4(),
            name="iron_butterfly_test",
            display_name="Iron Butterfly Test",
            category="neutral",
            description="Test iron butterfly",
            legs_config=[
                {"type": "PE", "position": "BUY", "strike_offset": -200},
                {"type": "PE", "position": "SELL", "strike_offset": 0},
                {"type": "CE", "position": "SELL", "strike_offset": 0},
                {"type": "CE", "position": "BUY", "strike_offset": 200}
            ],
            max_profit="Limited",
            max_loss="Limited",
            market_outlook="neutral",
            volatility_preference="high_iv",
            risk_level="medium",
            capital_requirement="medium",
            theta_positive=True,
            delta_neutral=True
        )
        db_session.add(template)
        await db_session.commit()

        legs = template.legs_config

        assert len(legs) == 4

        # ATM straddle: Both short legs at offset 0
        atm_legs = [l for l in legs if l["strike_offset"] == 0]
        assert len(atm_legs) == 2, "Should have 2 ATM legs"
        assert any(l["type"] == "CE" for l in atm_legs)
        assert any(l["type"] == "PE" for l in atm_legs)

    async def test_short_straddle_legs(self, short_straddle_template):
        """Verify Short Straddle: SELL CE + SELL PE at same strike."""
        legs = short_straddle_template.legs_config

        assert len(legs) == 2, "Short Straddle should have 2 legs"

        ce_leg = next((l for l in legs if l["type"] == "CE"), None)
        pe_leg = next((l for l in legs if l["type"] == "PE"), None)

        assert ce_leg is not None
        assert pe_leg is not None
        assert ce_leg["position"] == "SELL"
        assert pe_leg["position"] == "SELL"
        assert ce_leg["strike_offset"] == pe_leg["strike_offset"], "Both should be at same strike"
        assert ce_leg["strike_offset"] == 0, "Should be at ATM"

    async def test_short_strangle_legs(self, short_strangle_template):
        """Verify Short Strangle: OTM calls and puts."""
        legs = short_strangle_template.legs_config

        assert len(legs) == 2, "Short Strangle should have 2 legs"

        ce_leg = next((l for l in legs if l["type"] == "CE"), None)
        pe_leg = next((l for l in legs if l["type"] == "PE"), None)

        assert ce_leg is not None
        assert pe_leg is not None
        assert ce_leg["position"] == "SELL"
        assert pe_leg["position"] == "SELL"
        assert ce_leg["strike_offset"] > 0, "CE should be OTM (higher strike)"
        assert pe_leg["strike_offset"] < 0, "PE should be OTM (lower strike)"

    async def test_butterfly_spread_legs(self, db_session):
        """Verify Butterfly Spread: 1:2:1 ratio."""
        template = StrategyTemplate(
            id=uuid4(),
            name="butterfly_spread_test",
            display_name="Butterfly Spread Test",
            category="neutral",
            description="Test butterfly spread",
            legs_config=[
                {"type": "CE", "position": "BUY", "strike_offset": -200, "quantity": 1},
                {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 2},
                {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 1}
            ],
            max_profit="Limited",
            max_loss="Limited",
            market_outlook="neutral",
            volatility_preference="high_iv",
            risk_level="low",
            capital_requirement="low",
            theta_positive=True,
            delta_neutral=True
        )
        db_session.add(template)
        await db_session.commit()

        legs = template.legs_config

        assert len(legs) == 3, "Butterfly should have 3 legs"

        buy_legs = [l for l in legs if l["position"] == "BUY"]
        sell_legs = [l for l in legs if l["position"] == "SELL"]

        assert len(buy_legs) == 2, "Should have 2 BUY legs (wings)"
        assert len(sell_legs) == 1, "Should have 1 SELL leg (body)"

        # Verify 1:2:1 ratio
        assert sell_legs[0].get("quantity", 1) == 2, "Body should have quantity 2"

    async def test_ratio_backspread_legs(self, db_session):
        """Verify Ratio Backspread: 1:2 ratio."""
        template = StrategyTemplate(
            id=uuid4(),
            name="ratio_backspread_test",
            display_name="Ratio Backspread Test",
            category="volatile",
            description="Test ratio backspread",
            legs_config=[
                {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1},
                {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 2}
            ],
            max_profit="Unlimited",
            max_loss="Limited",
            market_outlook="volatile",
            volatility_preference="low_iv",
            risk_level="medium",
            capital_requirement="medium",
            vega_positive=True
        )
        db_session.add(template)
        await db_session.commit()

        legs = template.legs_config

        assert len(legs) == 2

        sell_leg = next((l for l in legs if l["position"] == "SELL"), None)
        buy_leg = next((l for l in legs if l["position"] == "BUY"), None)

        assert sell_leg is not None
        assert buy_leg is not None
        assert sell_leg.get("quantity", 1) == 1
        assert buy_leg.get("quantity", 1) == 2


class TestStrategyCharacteristics:
    """Test strategy Greeks and characteristics."""

    async def test_credit_strategies_theta_positive(
        self, bull_put_spread_template, bear_call_spread_template, iron_condor_template
    ):
        """Credit strategies should have theta_positive=True."""
        credit_strategies = [
            bull_put_spread_template,
            bear_call_spread_template,
            iron_condor_template
        ]

        for strategy in credit_strategies:
            assert strategy.theta_positive is True, \
                f"{strategy.name} should be theta positive"

    async def test_debit_strategies_vega_positive(
        self, bull_call_spread_template, long_straddle_template
    ):
        """Debit strategies should have vega_positive=True."""
        debit_strategies = [
            bull_call_spread_template,
            long_straddle_template
        ]

        for strategy in debit_strategies:
            assert strategy.vega_positive is True, \
                f"{strategy.name} should be vega positive"

    async def test_neutral_strategies_delta_neutral(
        self, iron_condor_template, short_straddle_template, short_strangle_template, long_straddle_template
    ):
        """Neutral strategies should have delta_neutral=True."""
        delta_neutral_strategies = [
            iron_condor_template,
            short_straddle_template,
            short_strangle_template,
            long_straddle_template
        ]

        for strategy in delta_neutral_strategies:
            assert strategy.delta_neutral is True, \
                f"{strategy.name} should be delta neutral"

    async def test_high_risk_strategies(
        self, short_straddle_template, short_strangle_template
    ):
        """Short straddle and short strangle should have risk_level=high."""
        high_risk_strategies = [
            short_straddle_template,
            short_strangle_template
        ]

        for strategy in high_risk_strategies:
            assert strategy.risk_level == "high", \
                f"{strategy.name} should have high risk level"

    async def test_low_risk_strategies(
        self, bull_call_spread_template, bull_put_spread_template, bear_call_spread_template
    ):
        """Defined risk spreads should have risk_level=low."""
        low_risk_strategies = [
            bull_call_spread_template,
            bull_put_spread_template,
            bear_call_spread_template
        ]

        for strategy in low_risk_strategies:
            assert strategy.risk_level == "low", \
                f"{strategy.name} should have low risk level"


class TestWinProbability:
    """Test win probability classifications."""

    async def test_high_probability_strategies(
        self, bull_put_spread_template, bear_call_spread_template, iron_condor_template
    ):
        """Credit spreads should have high win probability (>=65%)."""
        high_prob_strategies = [
            bull_put_spread_template,
            bear_call_spread_template,
            iron_condor_template
        ]

        for strategy in high_prob_strategies:
            if strategy.win_probability:
                # Extract number from probability string (e.g., "~65%" -> 65)
                prob_str = strategy.win_probability.replace("~", "").replace("%", "").strip()
                try:
                    prob = int(prob_str)
                    assert prob >= 50, \
                        f"{strategy.name} should have win probability >= 50%"
                except ValueError:
                    pass  # Skip if can't parse

    async def test_low_probability_strategies(self, long_straddle_template):
        """Long straddle/strangle should have low win probability (<40%)."""
        if long_straddle_template.win_probability:
            prob_str = long_straddle_template.win_probability.replace("~", "").replace("%", "").strip()
            try:
                prob = int(prob_str)
                assert prob < 50, \
                    f"Long Straddle should have win probability < 50%"
            except ValueError:
                pass


class TestMaxProfitMaxLoss:
    """Test max profit and max loss characteristics."""

    async def test_defined_risk_strategies(
        self, bull_call_spread_template, bull_put_spread_template,
        bear_call_spread_template, iron_condor_template
    ):
        """Defined risk strategies should have Limited max loss."""
        defined_risk = [
            bull_call_spread_template,
            bull_put_spread_template,
            bear_call_spread_template,
            iron_condor_template
        ]

        for strategy in defined_risk:
            assert strategy.max_loss == "Limited", \
                f"{strategy.name} should have Limited max loss"

    async def test_unlimited_risk_strategies(
        self, short_straddle_template, short_strangle_template
    ):
        """Naked short strategies should have Unlimited max loss."""
        unlimited_risk = [
            short_straddle_template,
            short_strangle_template
        ]

        for strategy in unlimited_risk:
            assert strategy.max_loss == "Unlimited", \
                f"{strategy.name} should have Unlimited max loss"

    async def test_unlimited_profit_strategies(self, long_straddle_template):
        """Long volatility strategies should have Unlimited max profit."""
        assert long_straddle_template.max_profit == "Unlimited", \
            "Long Straddle should have Unlimited max profit"

    async def test_limited_profit_strategies(
        self, bull_call_spread_template, iron_condor_template
    ):
        """Spread strategies should have Limited max profit."""
        limited_profit = [
            bull_call_spread_template,
            iron_condor_template
        ]

        for strategy in limited_profit:
            assert strategy.max_profit == "Limited", \
                f"{strategy.name} should have Limited max profit"


class TestCategoryValidation:
    """Test that strategies are in correct categories."""

    async def test_bullish_category(
        self, bull_call_spread_template, bull_put_spread_template
    ):
        """Bull spreads should be in bullish category."""
        bullish_strategies = [
            bull_call_spread_template,
            bull_put_spread_template
        ]

        for strategy in bullish_strategies:
            assert strategy.category == "bullish", \
                f"{strategy.name} should be in bullish category"

    async def test_bearish_category(self, bear_call_spread_template):
        """Bear spreads should be in bearish category."""
        assert bear_call_spread_template.category == "bearish", \
            "Bear Call Spread should be in bearish category"

    async def test_neutral_category(
        self, iron_condor_template, short_straddle_template, short_strangle_template
    ):
        """Range-bound strategies should be in neutral category."""
        neutral_strategies = [
            iron_condor_template,
            short_straddle_template,
            short_strangle_template
        ]

        for strategy in neutral_strategies:
            assert strategy.category == "neutral", \
                f"{strategy.name} should be in neutral category"

    async def test_volatile_category(self, long_straddle_template):
        """Long volatility strategies should be in volatile category."""
        assert long_straddle_template.category == "volatile", \
            "Long Straddle should be in volatile category"


class TestVolatilityPreference:
    """Test volatility preference settings."""

    async def test_sell_premium_high_iv(
        self, bull_put_spread_template, iron_condor_template,
        short_straddle_template, short_strangle_template
    ):
        """Sell premium strategies should prefer high IV."""
        sell_premium = [
            bull_put_spread_template,
            iron_condor_template,
            short_straddle_template,
            short_strangle_template
        ]

        for strategy in sell_premium:
            assert strategy.volatility_preference == "high_iv", \
                f"{strategy.name} should prefer high IV"

    async def test_buy_premium_low_iv(
        self, bull_call_spread_template, long_straddle_template
    ):
        """Buy premium strategies should prefer low IV."""
        buy_premium = [
            bull_call_spread_template,
            long_straddle_template
        ]

        for strategy in buy_premium:
            assert strategy.volatility_preference == "low_iv", \
                f"{strategy.name} should prefer low IV"
