"""
AutoPilot Dashboard API Tests

Tests for /api/v1/autopilot/dashboard endpoints:
- GET /dashboard/summary - Get dashboard summary
"""

import pytest
import pytest_asyncio
from datetime import datetime
from decimal import Decimal
from httpx import AsyncClient

from app.models.users import User
from app.models.autopilot import AutoPilotStrategy, AutoPilotUserSettings
from .conftest import assert_dashboard_response


# =============================================================================
# GET DASHBOARD SUMMARY TESTS
# =============================================================================

class TestDashboardSummary:
    """Tests for GET /api/v1/autopilot/dashboard/summary endpoint."""

    @pytest.mark.asyncio
    async def test_dashboard_summary_empty(
        self,
        client: AsyncClient,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test dashboard summary with no strategies."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

        summary = data["data"]
        assert_dashboard_response(summary)

        # All counts should be zero
        assert summary["active_strategies"] == 0
        assert summary["waiting_strategies"] == 0
        assert summary["pending_confirmations"] == 0

        # P&L should be zero
        assert summary["today_realized_pnl"] == 0
        assert summary["today_unrealized_pnl"] == 0
        assert summary["today_total_pnl"] == 0

        # Strategies list should be empty
        assert summary["strategies"] == []

    @pytest.mark.asyncio
    async def test_dashboard_summary_with_strategies(
        self,
        client: AsyncClient,
        test_strategy_active,
        test_strategy_waiting,
        test_settings: AutoPilotUserSettings
    ):
        """Test dashboard summary returns correct strategy counts."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        data = response.json()
        summary = data["data"]

        assert_dashboard_response(summary)

        # Check strategy counts
        assert summary["active_strategies"] == 1
        assert summary["waiting_strategies"] == 1
        assert summary["pending_confirmations"] == 0

        # Check strategies list includes active and waiting
        assert len(summary["strategies"]) >= 2

        # Verify strategies have correct structure
        for strategy in summary["strategies"]:
            assert "id" in strategy
            assert "name" in strategy
            assert "status" in strategy
            assert strategy["status"] in ["active", "waiting", "pending", "paused"]

    @pytest.mark.asyncio
    async def test_dashboard_summary_includes_paused(
        self,
        client: AsyncClient,
        test_strategy_paused,
        test_settings: AutoPilotUserSettings
    ):
        """Test dashboard includes paused strategies in list."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        # Paused should be in strategies list
        paused_strategies = [s for s in summary["strategies"] if s["status"] == "paused"]
        assert len(paused_strategies) == 1
        assert paused_strategies[0]["name"] == "Paused Strategy"

    @pytest.mark.asyncio
    async def test_dashboard_summary_excludes_draft_completed(
        self,
        client: AsyncClient,
        test_strategy,  # draft
        test_strategy_completed,
        test_settings: AutoPilotUserSettings
    ):
        """Test dashboard excludes draft and completed strategies from list."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        # Draft and completed should NOT be in strategies list
        strategy_statuses = [s["status"] for s in summary["strategies"]]
        assert "draft" not in strategy_statuses
        assert "completed" not in strategy_statuses

    @pytest.mark.asyncio
    async def test_dashboard_summary_pnl_calculation(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test today's P&L is calculated correctly."""
        # Create strategy with P&L data
        strategy1 = AutoPilotStrategy(
            user_id=test_user.id,
            name="Strategy with P&L 1",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                "current_pnl": 2500.0,
                "realized_pnl": 1000.0
            }
        )

        strategy2 = AutoPilotStrategy(
            user_id=test_user.id,
            name="Strategy with P&L 2",
            status="waiting",
            underlying="BANKNIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "PE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                "current_pnl": 1500.0,
                "realized_pnl": 500.0
            }
        )

        db_session.add(strategy1)
        db_session.add(strategy2)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        # realized_pnl: 1000 + 500 = 1500
        assert summary["today_realized_pnl"] == 1500.0

        # unrealized_pnl from active+waiting: 2500 + 1500 = 4000
        assert summary["today_unrealized_pnl"] == 4000.0

        # total = realized + unrealized
        assert summary["today_total_pnl"] == 5500.0

    @pytest.mark.asyncio
    async def test_dashboard_summary_pnl_with_losses(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test P&L calculation handles negative values correctly."""
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Losing Strategy",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                "current_pnl": -3000.0,
                "realized_pnl": -2000.0
            }
        )

        db_session.add(strategy)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        assert summary["today_realized_pnl"] == -2000.0
        assert summary["today_unrealized_pnl"] == -3000.0
        assert summary["today_total_pnl"] == -5000.0


# =============================================================================
# RISK METRICS TESTS
# =============================================================================

class TestDashboardRiskMetrics:
    """Tests for risk metrics in dashboard summary."""

    @pytest.mark.asyncio
    async def test_dashboard_risk_metrics_structure(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test risk metrics has all expected fields."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        expected_fields = [
            "daily_loss_limit",
            "daily_loss_used",
            "daily_loss_pct",
            "max_capital",
            "capital_used",
            "capital_pct",
            "max_active_strategies",
            "active_strategies_count",
            "status"
        ]

        for field in expected_fields:
            assert field in risk_metrics, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_dashboard_risk_metrics_from_settings(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test risk metrics use values from user settings."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # Should match test_settings fixture values
        assert risk_metrics["daily_loss_limit"] == 20000.0
        assert risk_metrics["max_capital"] == 500000.0
        assert risk_metrics["max_active_strategies"] == 3

    @pytest.mark.asyncio
    async def test_dashboard_daily_loss_percentage(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test daily loss percentage calculation."""
        # Create strategy with losses to trigger loss calculation
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Loss Strategy",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                "current_pnl": -5000.0,
                "realized_pnl": -5000.0
            }
        )

        db_session.add(strategy)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # Loss: 5000 + 5000 = 10000 (total loss)
        # Daily limit: 20000
        # Loss %: 10000 / 20000 * 100 = 50%
        assert risk_metrics["daily_loss_used"] == 10000.0
        assert risk_metrics["daily_loss_pct"] == 50.0

    @pytest.mark.asyncio
    async def test_dashboard_risk_status_safe(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test risk status is 'safe' when below 70% loss."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # No losses = 0% = safe
        assert risk_metrics["status"] == "safe"

    @pytest.mark.asyncio
    async def test_dashboard_risk_status_warning(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test risk status is 'warning' when 70-89% of daily loss used."""
        # Create strategy with 75% of daily loss limit
        # Daily limit is 20000, so we need -15000 loss
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Warning Level Strategy",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                "current_pnl": -10000.0,
                "realized_pnl": -5000.0
            }
        )

        db_session.add(strategy)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # 15000 / 20000 * 100 = 75%
        assert risk_metrics["daily_loss_pct"] == 75.0
        assert risk_metrics["status"] == "warning"

    @pytest.mark.asyncio
    async def test_dashboard_risk_status_critical(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test risk status is 'critical' when >= 90% of daily loss used."""
        # Create strategy with 95% of daily loss limit
        # Daily limit is 20000, so we need -19000 loss
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Critical Level Strategy",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                "current_pnl": -10000.0,
                "realized_pnl": -9000.0
            }
        )

        db_session.add(strategy)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # 19000 / 20000 * 100 = 95%
        assert risk_metrics["daily_loss_pct"] == 95.0
        assert risk_metrics["status"] == "critical"

    @pytest.mark.asyncio
    async def test_dashboard_capital_used_calculation(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test capital used is sum of margin_used from active strategies."""
        strategy1 = AutoPilotStrategy(
            user_id=test_user.id,
            name="Strategy 1",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={"margin_used": 50000.0}
        )

        strategy2 = AutoPilotStrategy(
            user_id=test_user.id,
            name="Strategy 2",
            status="waiting",
            underlying="BANKNIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "PE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={"margin_used": 75000.0}
        )

        db_session.add(strategy1)
        db_session.add(strategy2)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        assert risk_metrics["capital_used"] == 125000.0
        # 125000 / 500000 * 100 = 25%
        assert risk_metrics["capital_pct"] == 25.0

    @pytest.mark.asyncio
    async def test_dashboard_active_strategies_count(
        self,
        client: AsyncClient,
        test_strategy_active,
        test_strategy_waiting,
        test_settings: AutoPilotUserSettings
    ):
        """Test active strategies count includes active, waiting, and pending."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # 1 active + 1 waiting = 2
        assert risk_metrics["active_strategies_count"] == 2


# =============================================================================
# BROKER STATUS TESTS
# =============================================================================

class TestDashboardBrokerStatus:
    """Tests for broker/connection status in dashboard."""

    @pytest.mark.asyncio
    async def test_dashboard_broker_connection_status(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test broker connection status is included."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        # These are currently hardcoded as True in the API
        # TODO: Update when actual connection checking is implemented
        assert "kite_connected" in summary
        assert "websocket_connected" in summary

    @pytest.mark.asyncio
    async def test_dashboard_last_update_timestamp(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test last_update timestamp is present and recent."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        assert "last_update" in summary
        assert summary["last_update"] is not None

        # Verify it's a valid ISO format timestamp
        last_update = datetime.fromisoformat(summary["last_update"].replace("Z", "+00:00"))
        assert last_update is not None


# =============================================================================
# DEFAULT SETTINGS TESTS
# =============================================================================

class TestDashboardDefaultSettings:
    """Tests for dashboard when user has no settings configured."""

    @pytest.mark.asyncio
    async def test_dashboard_without_settings(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test dashboard uses defaults when no settings exist."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # Default values should be used
        assert risk_metrics["daily_loss_limit"] == 20000.0
        assert risk_metrics["max_capital"] == 500000.0
        assert risk_metrics["max_active_strategies"] == 3


# =============================================================================
# UNAUTHORIZED ACCESS TESTS
# =============================================================================

class TestDashboardUnauthorized:
    """Tests for unauthorized access to dashboard endpoints."""

    @pytest.mark.asyncio
    async def test_dashboard_unauthorized(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test 401 without auth token."""
        response = await unauthenticated_client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 401


# =============================================================================
# DASHBOARD RESPONSE STRUCTURE TESTS
# =============================================================================

class TestDashboardResponseStructure:
    """Tests for dashboard response structure."""

    @pytest.mark.asyncio
    async def test_dashboard_response_wrapper(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test response has proper wrapper structure."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        data = response.json()

        # Check wrapper structure
        assert "status" in data
        assert data["status"] == "success"
        assert "data" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_dashboard_strategy_list_item_structure(
        self,
        client: AsyncClient,
        test_strategy_active,
        test_settings: AutoPilotUserSettings
    ):
        """Test strategy items in list have correct structure."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        strategies = response.json()["data"]["strategies"]

        assert len(strategies) > 0

        strategy = strategies[0]
        expected_fields = [
            "id", "name", "status", "underlying", "lots",
            "leg_count", "current_pnl", "margin_used",
            "priority", "created_at", "updated_at"
        ]

        for field in expected_fields:
            assert field in strategy, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_dashboard_strategy_pnl_in_list(
        self,
        client: AsyncClient,
        test_strategy_active,
        test_settings: AutoPilotUserSettings
    ):
        """Test strategy list items include current P&L."""
        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        strategies = response.json()["data"]["strategies"]

        active_strategy = next(
            (s for s in strategies if s["name"] == "Active Strategy"),
            None
        )
        assert active_strategy is not None

        # test_strategy_active has current_pnl: 1500.0
        assert active_strategy["current_pnl"] == 1500.0
        assert active_strategy["margin_used"] == 50000.0


# =============================================================================
# EDGE CASES
# =============================================================================

class TestDashboardEdgeCases:
    """Edge case tests for dashboard."""

    @pytest.mark.asyncio
    async def test_dashboard_with_null_runtime_state(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test dashboard handles strategies with null runtime_state."""
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="No Runtime State",
            status="waiting",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state=None  # Explicitly null
        )

        db_session.add(strategy)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        # Should not raise an error
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_dashboard_with_missing_pnl_fields(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test dashboard handles missing P&L fields gracefully."""
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Partial Runtime State",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                # Missing current_pnl and realized_pnl
                "paper_trading": False
            }
        )

        db_session.add(strategy)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        # Should default to 0
        assert summary["today_realized_pnl"] == 0
        assert summary["today_unrealized_pnl"] == 0

    @pytest.mark.asyncio
    async def test_dashboard_many_strategies(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test dashboard handles many strategies efficiently."""
        # Create 20 strategies with various statuses
        for i in range(20):
            status = ["draft", "waiting", "active", "paused", "completed"][i % 5]
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Strategy {i}",
                status=status,
                underlying="NIFTY" if i % 2 == 0 else "BANKNIFTY",
                expiry_type="current_week",
                legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                             "strike_selection": {"mode": "atm_offset", "offset": 0}}],
                entry_conditions={"logic": "AND", "conditions": []},
                runtime_state={
                    "current_pnl": float(i * 100),
                    "margin_used": float(i * 1000)
                } if status in ["waiting", "active", "pending"] else None
            )
            db_session.add(strategy)

        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        summary = response.json()["data"]

        # Only active, waiting, pending, paused should be in list
        # From 20 strategies: 4 waiting, 4 active, 4 paused = 12
        assert len(summary["strategies"]) == 12

        # Counts
        assert summary["active_strategies"] == 4
        assert summary["waiting_strategies"] == 4

    @pytest.mark.asyncio
    async def test_dashboard_profit_no_loss_tracking(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test that profits don't count toward daily loss used."""
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Profitable Strategy",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL",
                         "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={"logic": "AND", "conditions": []},
            runtime_state={
                "current_pnl": 5000.0,  # Profit
                "realized_pnl": 3000.0  # Profit
            }
        )

        db_session.add(strategy)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/dashboard/summary")

        assert response.status_code == 200
        risk_metrics = response.json()["data"]["risk_metrics"]

        # Profit shouldn't affect daily loss used
        assert risk_metrics["daily_loss_used"] == 0
        assert risk_metrics["daily_loss_pct"] == 0
        assert risk_metrics["status"] == "safe"
