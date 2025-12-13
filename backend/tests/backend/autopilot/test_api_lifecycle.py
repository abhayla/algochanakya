"""
AutoPilot Strategy Lifecycle API Tests

Tests for strategy lifecycle endpoints:
- POST /strategies/{id}/activate - Activate strategy
- POST /strategies/{id}/pause - Pause strategy
- POST /strategies/{id}/resume - Resume strategy
- POST /strategies/{id}/clone - Clone strategy
- POST /strategies/{id}/exit - Exit strategy (placeholder)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.models.users import User
from app.models.autopilot import AutoPilotStrategy, AutoPilotUserSettings


# =============================================================================
# ACTIVATE STRATEGY TESTS
# =============================================================================

class TestActivateStrategy:
    """Tests for POST /api/v1/autopilot/strategies/{id}/activate endpoint."""

    @pytest.mark.asyncio
    async def test_activate_from_draft(
        self,
        client: AsyncClient,
        test_strategy  # draft status
    ):
        """Test activate draft → waiting."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy.id}/activate",
            json={"confirm": True, "paper_trading": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "activated" in data["message"].lower()

        strategy = data["data"]
        assert strategy["status"] == "waiting"
        assert strategy["runtime_state"]["paper_trading"] is False
        assert strategy["activated_at"] is not None

    @pytest.mark.asyncio
    async def test_activate_from_draft_paper_trading(
        self,
        client: AsyncClient,
        test_strategy
    ):
        """Test activate with paper_trading flag."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy.id}/activate",
            json={"confirm": True, "paper_trading": True}
        )

        assert response.status_code == 200
        strategy = response.json()["data"]
        assert strategy["status"] == "waiting"
        assert strategy["runtime_state"]["paper_trading"] is True

    @pytest.mark.asyncio
    async def test_activate_already_active(
        self,
        client: AsyncClient,
        test_strategy_active
    ):
        """Test 400 when trying to activate active strategy."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_active.id}/activate",
            json={"confirm": True}
        )

        assert response.status_code == 400
        assert "cannot activate" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_activate_already_waiting(
        self,
        client: AsyncClient,
        test_strategy_waiting
    ):
        """Test 400 when trying to activate waiting strategy."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_waiting.id}/activate",
            json={"confirm": True}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_activate_completed(
        self,
        client: AsyncClient,
        test_strategy_completed
    ):
        """Test can't activate completed strategy."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_completed.id}/activate",
            json={"confirm": True}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_activate_max_active_limit(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        test_settings: AutoPilotUserSettings
    ):
        """Test activate respects max_active_strategies limit."""
        # Create and activate 3 strategies (the default limit)
        for i in range(3):
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Active Strategy {i}",
                status="waiting",  # Already active
                underlying="NIFTY",
                expiry_type="current_week",
                legs_config=[],
                entry_conditions={}
            )
            db_session.add(strategy)
        await db_session.commit()

        # Create one more draft strategy
        new_strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="One More Strategy",
            status="draft",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={}
        )
        db_session.add(new_strategy)
        await db_session.commit()
        await db_session.refresh(new_strategy)

        # Try to activate it
        response = await client.post(
            f"/api/v1/autopilot/strategies/{new_strategy.id}/activate",
            json={"confirm": True}
        )

        assert response.status_code == 409  # Conflict
        assert "limit" in response.json()["detail"].lower()


# =============================================================================
# PAUSE STRATEGY TESTS
# =============================================================================

class TestPauseStrategy:
    """Tests for POST /api/v1/autopilot/strategies/{id}/pause endpoint."""

    @pytest.mark.asyncio
    async def test_pause_from_active(
        self,
        client: AsyncClient,
        test_strategy_active
    ):
        """Test pause active → paused."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_active.id}/pause"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "paused" in data["message"].lower()

        strategy = data["data"]
        assert strategy["status"] == "paused"

    @pytest.mark.asyncio
    async def test_pause_from_waiting(
        self,
        client: AsyncClient,
        test_strategy_waiting
    ):
        """Test pause waiting → paused."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_waiting.id}/pause"
        )

        assert response.status_code == 200
        strategy = response.json()["data"]
        assert strategy["status"] == "paused"

    @pytest.mark.asyncio
    async def test_pause_from_draft(
        self,
        client: AsyncClient,
        test_strategy  # draft
    ):
        """Test 400 can't pause draft strategy."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy.id}/pause"
        )

        assert response.status_code == 400
        assert "cannot pause" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_pause_already_paused(
        self,
        client: AsyncClient,
        test_strategy_paused
    ):
        """Test 400 when already paused."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_paused.id}/pause"
        )

        assert response.status_code == 400


# =============================================================================
# RESUME STRATEGY TESTS
# =============================================================================

class TestResumeStrategy:
    """Tests for POST /api/v1/autopilot/strategies/{id}/resume endpoint."""

    @pytest.mark.asyncio
    async def test_resume_from_paused(
        self,
        client: AsyncClient,
        test_strategy_paused
    ):
        """Test resume paused → waiting."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_paused.id}/resume"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "resumed" in data["message"].lower()

        strategy = data["data"]
        assert strategy["status"] == "waiting"

    @pytest.mark.asyncio
    async def test_resume_not_paused(
        self,
        client: AsyncClient,
        test_strategy  # draft
    ):
        """Test 400 can't resume non-paused strategy."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy.id}/resume"
        )

        assert response.status_code == 400
        assert "cannot resume" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_resume_active(
        self,
        client: AsyncClient,
        test_strategy_active
    ):
        """Test 400 can't resume active strategy."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_active.id}/resume"
        )

        assert response.status_code == 400


# =============================================================================
# CLONE STRATEGY TESTS
# =============================================================================

class TestCloneStrategy:
    """Tests for POST /api/v1/autopilot/strategies/{id}/clone endpoint."""

    @pytest.mark.asyncio
    async def test_clone_strategy(
        self,
        client: AsyncClient,
        test_strategy
    ):
        """Test clone creates copy with '(Copy)' suffix."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy.id}/clone",
            json={}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert "cloned" in data["message"].lower()

        clone = data["data"]
        assert clone["id"] != test_strategy.id  # Different ID
        assert "(Copy)" in clone["name"]
        assert clone["status"] == "draft"  # Always draft

    @pytest.mark.asyncio
    async def test_clone_strategy_custom_name(
        self,
        client: AsyncClient,
        test_strategy
    ):
        """Test clone with custom name."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy.id}/clone",
            json={"new_name": "My Cloned Strategy"}
        )

        assert response.status_code == 201
        clone = response.json()["data"]
        assert clone["name"] == "My Cloned Strategy"

    @pytest.mark.asyncio
    async def test_clone_preserves_config(
        self,
        client: AsyncClient,
        test_strategy
    ):
        """Test clone preserves legs and conditions."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy.id}/clone",
            json={}
        )

        assert response.status_code == 201
        clone = response.json()["data"]

        # Should have same configuration
        assert clone["underlying"] == test_strategy.underlying
        assert clone["lots"] == test_strategy.lots
        assert len(clone["legs_config"]) == len(test_strategy.legs_config)
        assert clone["entry_conditions"]["logic"] == test_strategy.entry_conditions["logic"]

    @pytest.mark.asyncio
    async def test_clone_resets_status(
        self,
        client: AsyncClient,
        test_strategy_active  # Clone from active
    ):
        """Test clone is always in draft status."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_active.id}/clone",
            json={}
        )

        assert response.status_code == 201
        clone = response.json()["data"]
        assert clone["status"] == "draft"  # Not active
        assert clone["runtime_state"] is None or clone["runtime_state"] == {}

    @pytest.mark.asyncio
    async def test_clone_reset_schedule(
        self,
        client: AsyncClient,
        db_session,
        test_user: User
    ):
        """Test clone with reset_schedule option."""
        # Create strategy with expiry_date
        from datetime import date
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Strategy with Expiry",
            status="draft",
            underlying="NIFTY",
            expiry_type="custom",
            expiry_date=date(2024, 12, 26),
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={}
        )
        db_session.add(strategy)
        await db_session.commit()
        await db_session.refresh(strategy)

        # Clone with reset_schedule=True (default)
        response = await client.post(
            f"/api/v1/autopilot/strategies/{strategy.id}/clone",
            json={"reset_schedule": True}
        )

        assert response.status_code == 201
        clone = response.json()["data"]
        assert clone["expiry_date"] is None  # Reset

        # Clone with reset_schedule=False
        response = await client.post(
            f"/api/v1/autopilot/strategies/{strategy.id}/clone",
            json={"reset_schedule": False}
        )

        assert response.status_code == 201
        clone = response.json()["data"]
        assert clone["expiry_date"] == "2024-12-26"  # Preserved


# =============================================================================
# STATUS TRANSITION TESTS (PARAMETRIZED)
# =============================================================================

class TestStatusTransitions:
    """Parametrized tests for all status transitions."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("initial,action,expected,success", [
        ("draft", "activate", "waiting", True),
        ("draft", "pause", None, False),
        ("draft", "resume", None, False),
        ("waiting", "pause", "paused", True),
        ("waiting", "activate", None, False),
        ("active", "pause", "paused", True),
        ("active", "activate", None, False),
        ("paused", "resume", "waiting", True),
        ("paused", "pause", None, False),
        ("completed", "activate", None, False),
        ("completed", "resume", None, False),
        ("error", "activate", None, False),
    ])
    async def test_status_transition(
        self,
        client: AsyncClient,
        db_session,
        test_user: User,
        initial: str,
        action: str,
        expected: str,
        success: bool
    ):
        """Test various status transitions."""
        # Create strategy with initial status
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name=f"Transition Test {initial} -> {action}",
            status=initial,
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[{"id": "leg_1", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}}],
            entry_conditions={}
        )
        db_session.add(strategy)
        await db_session.commit()
        await db_session.refresh(strategy)

        # Perform action
        if action == "activate":
            response = await client.post(
                f"/api/v1/autopilot/strategies/{strategy.id}/activate",
                json={"confirm": True}
            )
        elif action == "pause":
            response = await client.post(
                f"/api/v1/autopilot/strategies/{strategy.id}/pause"
            )
        elif action == "resume":
            response = await client.post(
                f"/api/v1/autopilot/strategies/{strategy.id}/resume"
            )
        else:
            pytest.fail(f"Unknown action: {action}")

        if success:
            assert response.status_code == 200, f"Expected 200 for {initial} -> {action}"
            result_status = response.json()["data"]["status"]
            assert result_status == expected, f"Expected {expected}, got {result_status}"
        else:
            assert response.status_code == 400, f"Expected 400 for {initial} -> {action}"


# =============================================================================
# EXIT STRATEGY TESTS (PLACEHOLDER)
# =============================================================================

class TestExitStrategy:
    """Tests for POST /api/v1/autopilot/strategies/{id}/exit endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Exit endpoint may require additional implementation")
    async def test_exit_strategy(
        self,
        client: AsyncClient,
        test_strategy_active
    ):
        """Test exit active strategy (placeholder)."""
        response = await client.post(
            f"/api/v1/autopilot/strategies/{test_strategy_active.id}/exit",
            json={"confirm": True, "exit_type": "market", "reason": "Manual exit"}
        )

        # This endpoint may not be implemented yet
        # Update test when implemented
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Exit endpoint may require additional implementation")
    async def test_exit_not_active(
        self,
        client: AsyncClient,
        test_strategy  # draft
    ):
        """Test 400 can't exit non-active strategy."""
        pass
