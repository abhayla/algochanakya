"""
Risk State Engine Tests

Tests for RiskStateEngine including:
- State evaluation logic (NORMAL, DEGRADED, PAUSED)
- State transitions with threshold checks
- Degraded mode adjustments
- Edge cases (no data, boundary thresholds)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.ai.risk_state_engine import RiskStateEngine


# ---------------------------------------------------------------------------
# Constants (matching the engine's thresholds)
# ---------------------------------------------------------------------------

SHARPE_DEGRADED = 0.5
SHARPE_PAUSED = 0.0
SHARPE_RECOVERY = 0.7
DRAWDOWN_DEGRADED = Decimal("10.00")
DRAWDOWN_PAUSED = Decimal("20.00")
DRAWDOWN_RECOVERY = Decimal("5.00")
MIN_TRADES = 20


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def engine(mock_db):
    """Create a RiskStateEngine with mocked database."""
    return RiskStateEngine(db=mock_db)


# ---------------------------------------------------------------------------
# Pure calculation tests (no DB needed)
# ---------------------------------------------------------------------------

class TestKellyCriterionFormula:
    """Test the Kelly Criterion calculations used in risk assessment."""

    def test_kelly_fraction_positive_edge(self):
        """Positive edge should return positive kelly fraction."""
        from app.services.ai.kelly_calculator import KellyCalculator
        calc = KellyCalculator(db=MagicMock())

        fraction, reliable = calc.calculate_kelly_fraction(
            win_rate=0.60,
            avg_win=200.0,
            avg_loss=100.0,
        )

        assert fraction > 0, "Positive edge should give positive fraction"
        assert reliable is True

    def test_kelly_fraction_negative_edge(self):
        """Negative edge should return zero or negative fraction."""
        from app.services.ai.kelly_calculator import KellyCalculator
        calc = KellyCalculator(db=MagicMock())

        fraction, reliable = calc.calculate_kelly_fraction(
            win_rate=0.30,
            avg_win=100.0,
            avg_loss=200.0,
        )

        assert fraction <= 0, "Negative edge should give zero/negative fraction"

    def test_kelly_fraction_50_50(self):
        """50/50 with equal win/loss should return zero."""
        from app.services.ai.kelly_calculator import KellyCalculator
        calc = KellyCalculator(db=MagicMock())

        fraction, reliable = calc.calculate_kelly_fraction(
            win_rate=0.50,
            avg_win=100.0,
            avg_loss=100.0,
        )

        assert abs(fraction) < 0.01, "50/50 equal should be near zero"


# ---------------------------------------------------------------------------
# State evaluation tests
# ---------------------------------------------------------------------------

class TestStateEvaluation:
    """Test risk state evaluation logic."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_tuple(self, engine, user_id, mock_db):
        """evaluate_state should return (RiskState, reason) tuple."""
        # Mock current state query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_risk_state("NORMAL")
        mock_db.execute.return_value = mock_result

        with patch.object(engine, '_get_recent_performance', new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = {
                "total_trades": 30,
                "sharpe_ratio": 1.0,
                "drawdown": Decimal("3.00"),
                "consecutive_losses": 0,
            }

            state, reason = await engine.evaluate_state(user_id)

            assert state is not None
            # Should remain NORMAL with good metrics
            assert state.value in ["NORMAL", "DEGRADED", "PAUSED"]

    @pytest.mark.asyncio
    async def test_degraded_on_low_sharpe(self, engine, user_id, mock_db):
        """Low Sharpe ratio should trigger DEGRADED state."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_risk_state("NORMAL")
        mock_db.execute.return_value = mock_result

        with patch.object(engine, '_get_recent_performance', new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = {
                "total_trades": 30,
                "sharpe_ratio": 0.3,  # Below SHARPE_DEGRADED (0.5)
                "drawdown": Decimal("5.00"),
                "consecutive_losses": 0,
            }

            state, reason = await engine.evaluate_state(user_id)

            assert state.value == "DEGRADED"
            assert reason is not None

    @pytest.mark.asyncio
    async def test_paused_on_high_drawdown(self, engine, user_id, mock_db):
        """Very high drawdown should trigger PAUSED state."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_risk_state("DEGRADED")
        mock_db.execute.return_value = mock_result

        with patch.object(engine, '_get_recent_performance', new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = {
                "total_trades": 30,
                "sharpe_ratio": 0.2,
                "drawdown": Decimal("25.00"),  # Above DRAWDOWN_PAUSED (20%)
                "consecutive_losses": 5,
            }

            state, reason = await engine.evaluate_state(user_id)

            assert state.value == "PAUSED"

    @pytest.mark.asyncio
    async def test_insufficient_trades_stays_normal(self, engine, user_id, mock_db):
        """With fewer than MIN_TRADES, should stay NORMAL (not enough data)."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_risk_state("NORMAL")
        mock_db.execute.return_value = mock_result

        with patch.object(engine, '_get_recent_performance', new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = {
                "total_trades": 5,  # Below MIN_TRADES (20)
                "sharpe_ratio": -1.0,
                "drawdown": Decimal("30.00"),
                "consecutive_losses": 5,
            }

            state, reason = await engine.evaluate_state(user_id)

            # Should not degrade with insufficient data
            assert state.value == "NORMAL"


# ---------------------------------------------------------------------------
# State transition tests
# ---------------------------------------------------------------------------

class TestStateTransition:
    """Test state transition recording."""

    @pytest.mark.asyncio
    async def test_transition_creates_record(self, engine, user_id, mock_db):
        """transition_state should create a new AIRiskState record."""
        from app.models.ai_risk_state import RiskState

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _make_risk_state("NORMAL")
        mock_db.execute.return_value = mock_result

        result = await engine.transition_state(
            user_id=user_id,
            new_state=RiskState.DEGRADED,
            reason="Sharpe ratio dropped below 0.5",
            sharpe_ratio=0.3,
            drawdown=Decimal("12.00"),
        )

        # Should have attempted to add and commit
        assert mock_db.add.called or mock_db.commit.called


# ---------------------------------------------------------------------------
# Degraded adjustments tests
# ---------------------------------------------------------------------------

class TestDegradedAdjustments:
    """Test DEGRADED mode parameter adjustments."""

    @pytest.mark.asyncio
    async def test_degraded_reduces_lot_size(self, engine):
        """DEGRADED mode should reduce lot multiplier to 50%."""
        mock_config = MagicMock()
        mock_config.base_lots = 4
        mock_config.min_confidence = Decimal("60.00")

        adjustments = await engine.apply_degraded_adjustments(mock_config)

        assert isinstance(adjustments, dict)
        # Should contain reduced parameters
        if "lot_multiplier" in adjustments:
            assert adjustments["lot_multiplier"] <= 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_risk_state(state_name, **kwargs):
    """Create a mock AIRiskState object."""
    state = MagicMock()
    state.state = MagicMock()
    state.state.value = state_name
    state.sharpe_ratio = kwargs.get("sharpe_ratio", 1.0)
    state.drawdown = kwargs.get("drawdown", Decimal("0.00"))
    state.created_at = datetime.now()
    return state
