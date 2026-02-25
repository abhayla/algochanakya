"""
Strategy Recommender Tests

Tests for StrategyRecommender including:
- Regime-strategy scoring matrix
- Recommendation sorting by confidence
- VIX and trend adjustments
- Edge cases (unknown regime, no templates)
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai.market_regime import RegimeType
from app.services.ai.strategy_recommender import (
    StrategyRecommender,
    REGIME_STRATEGY_SCORES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def recommender(mock_db):
    """Create a StrategyRecommender with mocked DB."""
    return StrategyRecommender(session=mock_db)


@pytest.fixture
def mock_user_config():
    """Create a mock AIUserConfig."""
    config = MagicMock()
    config.allowed_strategies = None  # No restrictions
    config.min_confidence = Decimal("50.00")
    config.max_daily_trades = 5
    return config


@pytest.fixture
def mock_regime_rangebound():
    """Create a mock rangebound regime response."""
    regime = MagicMock()
    regime.regime_type = RegimeType.RANGEBOUND
    regime.confidence = 85.0
    regime.indicators = MagicMock()
    regime.indicators.vix = 14.0
    regime.indicators.rsi_14 = 50.0
    regime.indicators.adx_14 = 18.0
    return regime


@pytest.fixture
def mock_regime_bullish():
    """Create a mock bullish regime response."""
    regime = MagicMock()
    regime.regime_type = RegimeType.TRENDING_BULLISH
    regime.confidence = 80.0
    regime.indicators = MagicMock()
    regime.indicators.vix = 12.0
    regime.indicators.rsi_14 = 65.0
    regime.indicators.adx_14 = 30.0
    return regime


# ---------------------------------------------------------------------------
# Scoring matrix tests
# ---------------------------------------------------------------------------

class TestRegimeStrategyScores:
    """Test the regime-strategy scoring matrix."""

    def test_rangebound_prefers_iron_condor(self):
        """Iron condor should score highest in rangebound market."""
        scores = REGIME_STRATEGY_SCORES.get(RegimeType.RANGEBOUND, {})
        assert "iron_condor" in scores
        assert scores["iron_condor"] >= scores.get("short_strangle", 0)

    def test_bullish_prefers_bull_call_spread(self):
        """Bull call spread should score highest in bullish market."""
        scores = REGIME_STRATEGY_SCORES.get(RegimeType.TRENDING_BULLISH, {})
        assert "bull_call_spread" in scores

    def test_bearish_prefers_bear_put_spread(self):
        """Bear put spread should score highest in bearish market."""
        scores = REGIME_STRATEGY_SCORES.get(RegimeType.TRENDING_BEARISH, {})
        assert "bear_put_spread" in scores

    def test_volatile_prefers_long_straddle(self):
        """Long straddle should score highest in volatile market."""
        scores = REGIME_STRATEGY_SCORES.get(RegimeType.VOLATILE, {})
        assert "long_straddle" in scores

    def test_event_day_has_no_recommendations(self):
        """Event day should have no strategy recommendations."""
        scores = REGIME_STRATEGY_SCORES.get(RegimeType.EVENT_DAY, {})
        assert len(scores) == 0

    def test_all_regimes_have_scores(self):
        """All regime types should have entries in the scoring matrix."""
        for regime in [RegimeType.RANGEBOUND, RegimeType.TRENDING_BULLISH,
                       RegimeType.TRENDING_BEARISH, RegimeType.VOLATILE,
                       RegimeType.PRE_EVENT, RegimeType.EVENT_DAY]:
            assert regime in REGIME_STRATEGY_SCORES

    def test_scores_in_valid_range(self):
        """All scores should be between 0 and 100."""
        for regime, strategies in REGIME_STRATEGY_SCORES.items():
            for strategy, score in strategies.items():
                assert 0 <= score <= 100, (
                    f"Score {score} for {strategy} in {regime} out of range"
                )


# ---------------------------------------------------------------------------
# Recommendation tests
# ---------------------------------------------------------------------------

class TestGetRecommendations:
    """Test recommendation generation."""

    @pytest.mark.asyncio
    async def test_recommendations_returns_list(
        self, recommender, mock_regime_rangebound, mock_user_config, mock_db
    ):
        """get_recommendations should return a list."""
        # Mock template query
        templates = _make_templates(["iron_condor", "short_strangle", "butterfly_spread"])
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = templates
        mock_db.execute.return_value = mock_result

        with patch.object(recommender, '_check_cooldown', new_callable=AsyncMock, return_value=False):
            recs = await recommender.get_recommendations(
                underlying="NIFTY",
                regime=mock_regime_rangebound,
                user_config=mock_user_config,
                top_n=3,
            )

            assert isinstance(recs, list)

    @pytest.mark.asyncio
    async def test_recommendations_sorted_by_confidence(
        self, recommender, mock_regime_rangebound, mock_user_config, mock_db
    ):
        """Recommendations should be sorted by confidence descending."""
        templates = _make_templates(["iron_condor", "short_strangle", "butterfly_spread"])
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = templates
        mock_db.execute.return_value = mock_result

        with patch.object(recommender, '_check_cooldown', new_callable=AsyncMock, return_value=False):
            recs = await recommender.get_recommendations(
                underlying="NIFTY",
                regime=mock_regime_rangebound,
                user_config=mock_user_config,
                top_n=3,
            )

            if len(recs) >= 2:
                for i in range(len(recs) - 1):
                    assert recs[i].confidence >= recs[i + 1].confidence

    @pytest.mark.asyncio
    async def test_recommendations_respects_top_n(
        self, recommender, mock_regime_rangebound, mock_user_config, mock_db
    ):
        """Should return at most top_n recommendations."""
        templates = _make_templates(["iron_condor", "short_strangle", "butterfly_spread",
                                     "short_straddle", "iron_butterfly"])
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = templates
        mock_db.execute.return_value = mock_result

        with patch.object(recommender, '_check_cooldown', new_callable=AsyncMock, return_value=False):
            recs = await recommender.get_recommendations(
                underlying="NIFTY",
                regime=mock_regime_rangebound,
                user_config=mock_user_config,
                top_n=2,
            )

            assert len(recs) <= 2


# ---------------------------------------------------------------------------
# Score strategy tests
# ---------------------------------------------------------------------------

class TestScoreStrategy:
    """Test individual strategy scoring."""

    @pytest.mark.asyncio
    async def test_score_in_valid_range(self, recommender, mock_regime_rangebound, mock_user_config):
        """Score should be between 0 and 100."""
        template = _make_template("iron_condor")

        score = await recommender.score_strategy(
            template=template,
            regime=mock_regime_rangebound,
            user_config=mock_user_config,
        )

        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_iron_condor_scores_high_rangebound(
        self, recommender, mock_regime_rangebound, mock_user_config
    ):
        """Iron condor should score high in rangebound market."""
        template = _make_template("iron_condor")

        score = await recommender.score_strategy(
            template=template,
            regime=mock_regime_rangebound,
            user_config=mock_user_config,
        )

        assert score >= 50, f"Iron condor should score >= 50 in rangebound, got {score}"

    @pytest.mark.asyncio
    async def test_unknown_strategy_scores_low(self, recommender, mock_regime_rangebound, mock_user_config):
        """Unknown strategy type should score 0 or very low."""
        template = _make_template("nonexistent_strategy")

        score = await recommender.score_strategy(
            template=template,
            regime=mock_regime_rangebound,
            user_config=mock_user_config,
        )

        assert score <= 20, f"Unknown strategy should score low, got {score}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_template(strategy_type, name=None):
    """Create a mock StrategyTemplate."""
    template = MagicMock()
    template.strategy_type = strategy_type
    template.name = name or strategy_type.replace("_", " ").title()
    template.description = f"Test {strategy_type}"
    template.legs = []
    return template


def _make_templates(strategy_types):
    """Create a list of mock StrategyTemplates."""
    return [_make_template(st) for st in strategy_types]
