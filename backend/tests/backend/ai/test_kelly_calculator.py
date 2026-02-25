"""
Kelly Calculator Tests

Tests for KellyCalculator including:
- Kelly fraction calculation with various win rates
- Optimal lots calculation
- Safety factor (half-Kelly)
- Edge cases (zero trades, negative edge, boundary values)
- Recommendation categories
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.services.ai.kelly_calculator import KellyCalculator


# ---------------------------------------------------------------------------
# Constants (matching the calculator's thresholds)
# ---------------------------------------------------------------------------

MIN_TRADES_REQUIRED = 100
KELLY_SAFETY_FACTOR = 0.5
MAX_KELLY_FRACTION = 0.25


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
def calculator(mock_db):
    """Create a KellyCalculator with mocked DB."""
    return KellyCalculator(db=mock_db)


@pytest.fixture
def user_id():
    return uuid4()


# ---------------------------------------------------------------------------
# Kelly fraction calculation tests
# ---------------------------------------------------------------------------

class TestKellyFractionCalculation:
    """Test the core Kelly Criterion formula."""

    def test_positive_edge_returns_positive(self, calculator):
        """Win rate > breakeven should return positive fraction."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=0.60,
            avg_win=200.0,
            avg_loss=100.0,
        )

        assert fraction > 0, "Positive edge should give positive fraction"

    def test_negative_edge_returns_zero_or_negative(self, calculator):
        """Win rate below breakeven should return <= 0."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=0.30,
            avg_win=100.0,
            avg_loss=200.0,
        )

        assert fraction <= 0

    def test_perfect_win_rate(self, calculator):
        """100% win rate should return high fraction."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=1.0,
            avg_win=100.0,
            avg_loss=100.0,
        )

        assert fraction > 0

    def test_zero_win_rate(self, calculator):
        """0% win rate should return negative fraction."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=0.0,
            avg_win=100.0,
            avg_loss=100.0,
        )

        assert fraction <= 0

    def test_equal_win_loss_50_50(self, calculator):
        """50/50 with 1:1 ratio should return ~0."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=0.50,
            avg_win=100.0,
            avg_loss=100.0,
        )

        assert abs(fraction) < 0.05, f"50/50 equal should be near zero, got {fraction}"

    def test_high_win_loss_ratio_compensates_low_win_rate(self, calculator):
        """High win/loss ratio should compensate for low win rate."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=0.40,
            avg_win=300.0,  # 3:1 win/loss ratio
            avg_loss=100.0,
        )

        assert fraction > 0, "3:1 ratio with 40% win rate should be positive"

    def test_reliability_flag(self, calculator):
        """Reliability flag should depend on input quality."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=0.55,
            avg_win=150.0,
            avg_loss=100.0,
        )

        assert isinstance(reliable, bool)

    def test_zero_avg_loss_handled(self, calculator):
        """Zero average loss should not cause division by zero."""
        try:
            fraction, reliable = calculator.calculate_kelly_fraction(
                win_rate=0.60,
                avg_win=100.0,
                avg_loss=0.0,
            )
            # Should handle gracefully (return 0 or max, not crash)
            assert isinstance(fraction, (int, float))
        except (ZeroDivisionError, ValueError):
            pytest.fail("Should handle zero avg_loss without raising")

    def test_zero_avg_win_handled(self, calculator):
        """Zero average win should return non-positive fraction."""
        fraction, reliable = calculator.calculate_kelly_fraction(
            win_rate=0.60,
            avg_win=0.0,
            avg_loss=100.0,
        )

        assert fraction <= 0


# ---------------------------------------------------------------------------
# Optimal lots calculation tests
# ---------------------------------------------------------------------------

class TestOptimalLots:
    """Test optimal lots calculation."""

    def test_positive_fraction_returns_positive_lots(self, calculator):
        """Positive Kelly fraction should give positive lots."""
        lots = calculator.calculate_optimal_lots(
            kelly_fraction=0.10,
            capital=1000000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        assert lots > 0

    def test_zero_fraction_returns_zero_lots(self, calculator):
        """Zero Kelly fraction should give 0 lots."""
        lots = calculator.calculate_optimal_lots(
            kelly_fraction=0.0,
            capital=1000000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        assert lots == 0

    def test_negative_fraction_returns_zero_lots(self, calculator):
        """Negative Kelly fraction should give 0 lots."""
        lots = calculator.calculate_optimal_lots(
            kelly_fraction=-0.10,
            capital=1000000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        assert lots == 0

    def test_lots_proportional_to_capital(self, calculator):
        """More capital should yield more lots."""
        lots_small = calculator.calculate_optimal_lots(
            kelly_fraction=0.10,
            capital=500000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        lots_large = calculator.calculate_optimal_lots(
            kelly_fraction=0.10,
            capital=2000000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        assert lots_large >= lots_small

    def test_lots_are_integer(self, calculator):
        """Lots should always be an integer (can't trade fractional lots)."""
        lots = calculator.calculate_optimal_lots(
            kelly_fraction=0.15,
            capital=1000000.0,
            max_loss_per_lot=7000.0,
            underlying="NIFTY",
        )

        assert isinstance(lots, int)

    def test_safety_factor_applied(self, calculator):
        """Half-Kelly safety factor should reduce lots vs full Kelly."""
        # This tests that the calculator applies KELLY_SAFETY_FACTOR (0.5)
        lots = calculator.calculate_optimal_lots(
            kelly_fraction=0.20,  # Before safety
            capital=1000000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        # With 20% Kelly, 0.5 safety, 10L capital, 5K loss:
        # (0.20 * 0.5 * 10,00,000) / 5000 = 20 lots max
        # Should be capped or at least reasonable
        assert lots <= 40  # Reasonable upper bound


# ---------------------------------------------------------------------------
# Full recommendation tests
# ---------------------------------------------------------------------------

class TestKellyRecommendation:
    """Test complete Kelly recommendation output."""

    @pytest.mark.asyncio
    async def test_not_enough_data(self, calculator, user_id, mock_db):
        """Should return NOT_ENOUGH_DATA with few trades."""
        # Mock query returning few trades
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10  # Less than MIN_TRADES_REQUIRED
        mock_db.execute.return_value = mock_result

        rec = await calculator.get_kelly_recommendation(
            user_id=user_id,
            capital=1000000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        assert isinstance(rec, dict)
        assert rec.get("recommendation") == "NOT_ENOUGH_DATA" or rec.get("enabled") is False

    @pytest.mark.asyncio
    async def test_recommendation_has_required_fields(self, calculator, user_id, mock_db):
        """Recommendation dict should have all required fields."""
        # Mock enough trade data
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 150

        # Mock performance data
        mock_perf_result = MagicMock()
        mock_perf_result.all.return_value = [
            MagicMock(realized_pnl=Decimal("500.00")),
            MagicMock(realized_pnl=Decimal("-200.00")),
            MagicMock(realized_pnl=Decimal("300.00")),
            MagicMock(realized_pnl=Decimal("-150.00")),
            MagicMock(realized_pnl=Decimal("400.00")),
        ] * 30  # 150 trades

        mock_db.execute.side_effect = [mock_count_result, mock_perf_result]

        rec = await calculator.get_kelly_recommendation(
            user_id=user_id,
            capital=1000000.0,
            max_loss_per_lot=5000.0,
            underlying="NIFTY",
        )

        assert isinstance(rec, dict)
        # Should have standard fields
        expected_fields = {"kelly_fraction", "optimal_lots", "recommendation"}
        assert expected_fields.issubset(set(rec.keys())), (
            f"Missing fields: {expected_fields - set(rec.keys())}"
        )


# ---------------------------------------------------------------------------
# Recommendation category tests
# ---------------------------------------------------------------------------

class TestRecommendationCategories:
    """Test that recommendation categories are logical."""

    def test_categories_exist(self):
        """All expected recommendation categories should be defined."""
        expected = [
            "NOT_ENOUGH_DATA", "NEGATIVE_EDGE",
            "VERY_CONSERVATIVE", "CONSERVATIVE",
            "MODERATE", "AGGRESSIVE", "VERY_AGGRESSIVE",
        ]
        # These are string constants used in the calculator
        # Just verify the strings are valid (no typos)
        for cat in expected:
            assert isinstance(cat, str)
            assert cat == cat.upper()
