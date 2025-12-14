"""
Unit tests for AdjustmentCostTracker service (Phase 5G #46)

Tests:
- Cost calculation
- Threshold detection
- Alert level determination
- Recommendation generation
- Projected cost impact
"""
import pytest
from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autopilot import AutoPilotStrategy, AutoPilotOrder
from app.services.adjustment_cost_tracker import AdjustmentCostTracker, AdjustmentCostSummary


@pytest.fixture
def sample_strategy():
    """Create a sample strategy with entry premium."""
    strategy = AutoPilotStrategy(
        id=1,
        user_id="user-123",
        name="Test Iron Condor",
        underlying="NIFTY",
        entry_premium=Decimal("5000"),  # Collected ₹5000 premium
        max_profit=Decimal("5000"),
        max_loss=Decimal("10000"),
        runtime_state={}
    )
    return strategy


@pytest.fixture
def sample_orders_low_cost():
    """Sample orders with low adjustment cost (20%)."""
    return [
        AutoPilotOrder(
            id=1,
            strategy_id=1,
            user_id="user-123",
            order_type="adjustment",
            action_type="roll_strike",
            status="completed",
            filled_quantity=1,
            average_price=Decimal("500"),  # Cost ₹500
            notes="Delta threshold triggered",
            created_at=datetime(2024, 12, 10, 10, 0)
        ),
        AutoPilotOrder(
            id=2,
            strategy_id=1,
            user_id="user-123",
            order_type="adjustment",
            action_type="add_hedge",
            status="completed",
            filled_quantity=1,
            average_price=Decimal("500"),  # Cost ₹500
            notes="Protective hedge",
            created_at=datetime(2024, 12, 11, 11, 0)
        )
    ]  # Total: ₹1000 = 20% of ₹5000


@pytest.fixture
def sample_orders_high_cost():
    """Sample orders with high adjustment cost (60%)."""
    return [
        AutoPilotOrder(
            id=1,
            strategy_id=1,
            user_id="user-123",
            order_type="adjustment",
            action_type="roll_strike",
            status="completed",
            filled_quantity=1,
            average_price=Decimal("1500"),  # Cost ₹1500
            notes="First adjustment",
            created_at=datetime(2024, 12, 10, 10, 0)
        ),
        AutoPilotOrder(
            id=2,
            strategy_id=1,
            user_id="user-123",
            order_type="adjustment",
            action_type="add_hedge",
            status="completed",
            filled_quantity=1,
            average_price=Decimal("1500"),  # Cost ₹1500
            notes="Second adjustment",
            created_at=datetime(2024, 12, 11, 11, 0)
        )
    ]  # Total: ₹3000 = 60% of ₹5000


class TestAdjustmentCostTracker:
    """Test suite for AdjustmentCostTracker."""

    async def test_low_cost_returns_success_alert(self, sample_strategy, sample_orders_low_cost):
        """Test that low adjustment costs (< 25%) return success alert."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)  # Mock db

        # Mock the _get_adjustment_orders method
        async def mock_get_orders(strategy_id):
            return sample_orders_low_cost

        tracker._get_adjustment_orders = mock_get_orders

        # Act
        summary = await tracker.get_summary(sample_strategy, warning_threshold_pct=50.0)

        # Assert
        assert summary.original_premium == Decimal("5000")
        assert summary.total_adjustment_cost == Decimal("1000")
        assert summary.adjustment_cost_pct == 20.0
        assert summary.net_potential_profit == Decimal("4000")
        assert summary.alert_level == "success"
        assert "20.0%" in summary.alert_message
        assert len(summary.adjustments) == 2

    async def test_moderate_cost_returns_info_alert(self, sample_strategy):
        """Test that moderate costs (25-50%) return info alert."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)

        orders = [
            AutoPilotOrder(
                id=1,
                strategy_id=1,
                user_id="user-123",
                order_type="adjustment",
                action_type="roll_strike",
                status="completed",
                filled_quantity=1,
                average_price=Decimal("1800"),  # 36% of 5000
                notes="Adjustment",
                created_at=datetime(2024, 12, 10, 10, 0)
            )
        ]

        async def mock_get_orders(strategy_id):
            return orders

        tracker._get_adjustment_orders = mock_get_orders

        # Act
        summary = await tracker.get_summary(sample_strategy, warning_threshold_pct=50.0)

        # Assert
        assert summary.adjustment_cost_pct == 36.0
        assert summary.alert_level == "info"
        assert "36.0%" in summary.alert_message

    async def test_high_cost_returns_warning_alert(self, sample_strategy, sample_orders_high_cost):
        """Test that high costs (50-75%) return warning alert."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)

        async def mock_get_orders(strategy_id):
            return sample_orders_high_cost

        tracker._get_adjustment_orders = mock_get_orders

        # Act
        summary = await tracker.get_summary(sample_strategy, warning_threshold_pct=50.0)

        # Assert
        assert summary.adjustment_cost_pct == 60.0
        assert summary.alert_level == "warning"
        assert "60.0%" in summary.alert_message
        assert summary.warning_threshold_pct == 50.0

    async def test_excessive_cost_returns_danger_alert(self, sample_strategy):
        """Test that excessive costs (>= 75%) return danger alert."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)

        orders = [
            AutoPilotOrder(
                id=1,
                strategy_id=1,
                user_id="user-123",
                order_type="adjustment",
                action_type="roll_strike",
                status="completed",
                filled_quantity=1,
                average_price=Decimal("4000"),  # 80% of 5000
                notes="Expensive adjustment",
                created_at=datetime(2024, 12, 10, 10, 0)
            )
        ]

        async def mock_get_orders(strategy_id):
            return orders

        tracker._get_adjustment_orders = mock_get_orders

        # Act
        summary = await tracker.get_summary(sample_strategy, warning_threshold_pct=50.0)

        # Assert
        assert summary.adjustment_cost_pct == 80.0
        assert summary.alert_level == "danger"
        assert "80.0%" in summary.alert_message
        assert "75%" in summary.alert_message

    async def test_threshold_check_not_exceeded(self, sample_strategy, sample_orders_low_cost):
        """Test threshold check when costs are below threshold."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)

        async def mock_get_orders(strategy_id):
            return sample_orders_low_cost

        tracker._get_adjustment_orders = mock_get_orders

        # Act
        result = await tracker.check_cost_threshold(sample_strategy, threshold_pct=50.0)

        # Assert
        assert result["threshold_exceeded"] == False
        assert result["current_pct"] == 20.0
        assert result["threshold_pct"] == 50.0
        assert "recommendation" in result

    async def test_threshold_check_exceeded(self, sample_strategy, sample_orders_high_cost):
        """Test threshold check when costs exceed threshold."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)

        async def mock_get_orders(strategy_id):
            return sample_orders_high_cost

        tracker._get_adjustment_orders = mock_get_orders

        # Act
        result = await tracker.check_cost_threshold(sample_strategy, threshold_pct=50.0)

        # Assert
        assert result["threshold_exceeded"] == True
        assert result["current_pct"] == 60.0
        assert result["threshold_pct"] == 50.0
        assert "avoid further adjustments" in result["recommendation"].lower()

    async def test_project_cost_under_threshold(self, sample_strategy, sample_orders_low_cost):
        """Test projecting a new adjustment that keeps costs under threshold."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)

        async def mock_get_orders(strategy_id):
            return sample_orders_low_cost

        tracker._get_adjustment_orders = mock_get_orders

        # Act - Project adding ₹500 more (would be 30% total)
        projection = await tracker.track_new_adjustment(
            strategy=sample_strategy,
            action_type="roll_strike",
            estimated_cost=Decimal("500"),
            notes="Proposed adjustment"
        )

        # Assert
        assert projection["current_cost"] == 1000.0
        assert projection["current_pct"] == 20.0
        assert projection["estimated_new_cost"] == 500.0
        assert projection["projected_total_cost"] == 1500.0
        assert projection["projected_cost_pct"] == 30.0
        assert projection["recommendation"] == "proceed"

    async def test_project_cost_over_threshold(self, sample_strategy, sample_orders_high_cost):
        """Test projecting a new adjustment that exceeds threshold."""
        # Arrange
        tracker = AdjustmentCostTracker(db=None)

        async def mock_get_orders(strategy_id):
            return sample_orders_high_cost

        tracker._get_adjustment_orders = mock_get_orders

        # Act - Project adding ₹1000 more (would be 80% total)
        projection = await tracker.track_new_adjustment(
            strategy=sample_strategy,
            action_type="add_hedge",
            estimated_cost=Decimal("1000"),
            notes="Expensive hedge"
        )

        # Assert
        assert projection["current_pct"] == 60.0
        assert projection["projected_cost_pct"] == 80.0
        assert projection["recommendation"] == "do_not_adjust"

    async def test_recommendation_logic(self):
        """Test recommendation messages at different cost levels."""
        # This can be expanded with specific test cases for each recommendation tier
        # For now, we verify the recommendations are included in responses
        pass

    async def test_no_entry_premium_returns_zero_summary(self):
        """Test that strategy with no entry premium returns all zeros."""
        # Arrange
        strategy = AutoPilotStrategy(
            id=1,
            user_id="user-123",
            name="Test Strategy",
            underlying="NIFTY",
            entry_premium=None,  # No premium
            runtime_state={}
        )

        tracker = AdjustmentCostTracker(db=None)

        # Act
        summary = await tracker.get_summary(strategy)

        # Assert
        assert summary.original_premium == Decimal("0")
        assert summary.total_adjustment_cost == Decimal("0")
        assert summary.adjustment_cost_pct == 0.0
        assert len(summary.adjustments) == 0


@pytest.mark.asyncio
class TestAdjustmentCostSummary:
    """Test the AdjustmentCostSummary dataclass."""

    def test_to_dict_conversion(self):
        """Test that summary converts to dict correctly."""
        # Arrange
        summary = AdjustmentCostSummary(
            original_premium=Decimal("5000"),
            total_adjustment_cost=Decimal("2000"),
            adjustment_cost_pct=40.0,
            net_potential_profit=Decimal("3000"),
            adjustments=[],
            warning_threshold_pct=50.0
        )

        # Act
        result = summary.to_dict()

        # Assert
        assert result["original_premium"] == 5000.0
        assert result["total_adjustment_cost"] == 2000.0
        assert result["adjustment_cost_pct"] == 40.0
        assert result["net_potential_profit"] == 3000.0
        assert result["alert_level"] == "info"
        assert "alert_message" in result
