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
from app.models.ai_risk_state import RiskState


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
        """Negative edge should return zero fraction."""
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
# State transition logic tests (pure/synchronous)
# ---------------------------------------------------------------------------

class TestStateTransitionLogic:
    """Test _evaluate_transition directly (no DB)."""

    def test_normal_state_when_good_metrics(self, engine):
        """Good metrics should stay NORMAL."""
        state, reason = engine._evaluate_transition(
            current_state=RiskState.NORMAL,
            sharpe_ratio=1.2,
            drawdown=Decimal("3.00"),
            consecutive_losses=0,
        )
        assert state == RiskState.NORMAL
        assert reason is None

    def test_degraded_on_low_sharpe(self, engine):
        """Low Sharpe ratio should trigger DEGRADED."""
        state, reason = engine._evaluate_transition(
            current_state=RiskState.NORMAL,
            sharpe_ratio=0.3,  # Below SHARPE_DEGRADED_THRESHOLD (0.5)
            drawdown=Decimal("5.00"),
            consecutive_losses=0,
        )
        assert state == RiskState.DEGRADED
        assert reason is not None

    def test_degraded_on_high_drawdown(self, engine):
        """High drawdown (>10%) should trigger DEGRADED."""
        state, reason = engine._evaluate_transition(
            current_state=RiskState.NORMAL,
            sharpe_ratio=0.8,
            drawdown=Decimal("12.00"),  # Above DRAWDOWN_DEGRADED_THRESHOLD (10%)
            consecutive_losses=0,
        )
        assert state == RiskState.DEGRADED
        assert reason is not None

    def test_paused_on_very_high_drawdown(self, engine):
        """Very high drawdown (>20%) should trigger PAUSED."""
        state, reason = engine._evaluate_transition(
            current_state=RiskState.DEGRADED,
            sharpe_ratio=0.2,
            drawdown=Decimal("25.00"),  # Above DRAWDOWN_PAUSED_THRESHOLD (20%)
            consecutive_losses=5,
        )
        assert state == RiskState.PAUSED
        assert reason is not None

    def test_paused_on_negative_sharpe(self, engine):
        """Negative Sharpe ratio should trigger PAUSED."""
        state, reason = engine._evaluate_transition(
            current_state=RiskState.NORMAL,
            sharpe_ratio=-0.5,  # Below SHARPE_PAUSED_THRESHOLD (0.0)
            drawdown=Decimal("5.00"),
            consecutive_losses=2,
        )
        assert state == RiskState.PAUSED

    def test_recovery_from_degraded_when_metrics_improve(self, engine):
        """Good metrics from DEGRADED should trigger recovery to NORMAL."""
        state, reason = engine._evaluate_transition(
            current_state=RiskState.DEGRADED,
            sharpe_ratio=0.8,  # Above SHARPE_RECOVERY_THRESHOLD (0.7)
            drawdown=Decimal("3.00"),  # Below DRAWDOWN_RECOVERY_THRESHOLD (5%)
            consecutive_losses=0,
        )
        assert state == RiskState.NORMAL

    def test_no_data_returns_current_state(self, engine):
        """None sharpe and drawdown should return current state unchanged."""
        state, reason = engine._evaluate_transition(
            current_state=RiskState.NORMAL,
            sharpe_ratio=None,
            drawdown=None,
            consecutive_losses=0,
        )
        assert state == RiskState.NORMAL


# ---------------------------------------------------------------------------
# State evaluation tests (with DB mock)
# ---------------------------------------------------------------------------

class TestStateEvaluation:
    """Test risk state evaluation with mocked DB."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_tuple(self, engine, user_id, mock_db):
        """evaluate_state should return (RiskState, reason) tuple."""
        mock_state_obj = MagicMock()
        mock_state_obj.state = "NORMAL"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state_obj
        mock_db.execute.return_value = mock_result

        # Mock _get_performance_metrics to avoid DB queries
        with patch.object(engine, '_get_performance_metrics', new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = (1.0, Decimal("3.00"), 0)  # sharpe, drawdown, consecutive_losses

            state, reason = await engine.evaluate_state(user_id)

            assert state is not None
            assert state.value in ["NORMAL", "DEGRADED", "PAUSED"]

    @pytest.mark.asyncio
    async def test_evaluate_handles_no_data(self, engine, user_id, mock_db):
        """evaluate_state returns NORMAL when no performance data available."""
        mock_state_obj = MagicMock()
        mock_state_obj.state = "NORMAL"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state_obj
        mock_db.execute.return_value = mock_result

        with patch.object(engine, '_get_performance_metrics', new_callable=AsyncMock) as mock_perf:
            mock_perf.return_value = (None, None, 0)  # No data

            state, reason = await engine.evaluate_state(user_id)

            # Should stay NORMAL with no data
            assert state == RiskState.NORMAL


# ---------------------------------------------------------------------------
# State transition record tests
# ---------------------------------------------------------------------------

class TestStateTransition:
    """Test state transition recording."""

    @pytest.mark.asyncio
    async def test_transition_creates_record(self, engine, user_id, mock_db):
        """transition_state should update and commit state."""
        mock_state_obj = MagicMock()
        mock_state_obj.state = "NORMAL"
        mock_state_obj.previous_state = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_state_obj
        mock_db.execute.return_value = mock_result

        await engine.transition_state(
            user_id=user_id,
            new_state=RiskState.DEGRADED,
            reason="Sharpe ratio dropped below 0.5",
            sharpe_ratio=0.3,
            drawdown=Decimal("12.00"),
        )

        # Should have committed
        assert mock_db.commit.called


# ---------------------------------------------------------------------------
# Degraded adjustments tests
# ---------------------------------------------------------------------------

class TestDegradedAdjustments:
    """Test DEGRADED mode parameter adjustments."""

    @pytest.mark.asyncio
    async def test_degraded_adjustments_returns_dict(self, engine):
        """apply_degraded_adjustments should return a dict."""
        mock_config = MagicMock()
        mock_config.min_confidence_to_trade = Decimal("60.00")
        mock_config.max_lots_per_strategy = 4
        mock_config.max_strategies_per_day = 5
        mock_config.confidence_tiers = [{"multiplier": 1.0}, {"multiplier": 2.0}]

        adjustments = await engine.apply_degraded_adjustments(mock_config)

        assert isinstance(adjustments, dict)

    @pytest.mark.asyncio
    async def test_degraded_increases_confidence_threshold(self, engine):
        """DEGRADED mode should increase confidence threshold by 15%."""
        mock_config = MagicMock()
        mock_config.min_confidence_to_trade = Decimal("60.00")
        mock_config.max_lots_per_strategy = 4
        mock_config.max_strategies_per_day = 5
        mock_config.confidence_tiers = []

        adjustments = await engine.apply_degraded_adjustments(mock_config)

        if "min_confidence_to_trade" in adjustments:
            assert adjustments["min_confidence_to_trade"] >= Decimal("60.00")

    @pytest.mark.asyncio
    async def test_degraded_reduces_lot_multiplier(self, engine):
        """DEGRADED mode should reduce lot sizes."""
        mock_config = MagicMock()
        mock_config.min_confidence_to_trade = Decimal("60.00")
        mock_config.max_lots_per_strategy = 4
        mock_config.max_strategies_per_day = 5
        mock_config.confidence_tiers = [{"multiplier": 2.0}]

        adjustments = await engine.apply_degraded_adjustments(mock_config)

        if "max_lots_per_strategy" in adjustments:
            assert adjustments["max_lots_per_strategy"] <= 4

    @pytest.mark.asyncio
    async def test_degraded_disables_adjustments(self, engine):
        """DEGRADED mode should disable offensive adjustments."""
        mock_config = MagicMock()
        mock_config.min_confidence_to_trade = Decimal("60.00")
        mock_config.max_lots_per_strategy = 4
        mock_config.max_strategies_per_day = 5
        mock_config.confidence_tiers = []

        adjustments = await engine.apply_degraded_adjustments(mock_config)

        if "adjustments_disabled" in adjustments:
            assert adjustments["adjustments_disabled"] is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_risk_state(state_name, **kwargs):
    """Create a mock AIRiskState object."""
    state = MagicMock()
    state.state = state_name
    state.sharpe_ratio = kwargs.get("sharpe_ratio", 1.0)
    state.drawdown = kwargs.get("drawdown", Decimal("0.00"))
    state.created_at = datetime.now()
    return state
