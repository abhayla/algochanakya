"""
AutoPilot Settings API Tests

Tests for /api/v1/autopilot/settings endpoints:
- GET /settings - Get user settings
- PUT /settings - Update user settings
"""

import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import AsyncClient

from app.models.users import User
from app.models.autopilot import AutoPilotUserSettings
from .conftest import assert_settings_response


# =============================================================================
# GET SETTINGS TESTS
# =============================================================================

class TestGetSettings:
    """Tests for GET /api/v1/autopilot/settings endpoint."""

    @pytest.mark.asyncio
    async def test_get_settings_returns_existing(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test GET returns existing settings."""
        response = await client.get("/api/v1/autopilot/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data

        settings = data["data"]
        assert_settings_response(settings)
        assert float(settings["daily_loss_limit"]) == 20000.00
        assert float(settings["per_strategy_loss_limit"]) == 10000.00
        assert settings["max_active_strategies"] == 3
        assert settings["paper_trading_mode"] is False

    @pytest.mark.asyncio
    async def test_get_settings_creates_default(
        self,
        client: AsyncClient,
        test_user: User
    ):
        """Test GET creates default settings if not exists."""
        # Don't create settings fixture - should create automatically
        response = await client.get("/api/v1/autopilot/settings")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        settings = data["data"]
        assert_settings_response(settings)

        # Verify defaults
        assert float(settings["daily_loss_limit"]) == 20000.00
        assert float(settings["per_strategy_loss_limit"]) == 10000.00
        assert float(settings["max_capital_deployed"]) == 500000.00
        assert settings["max_active_strategies"] == 3
        assert settings["no_trade_first_minutes"] == 5
        assert settings["no_trade_last_minutes"] == 5
        assert settings["cooldown_after_loss"] is False
        assert settings["cooldown_minutes"] == 30
        assert float(settings["cooldown_threshold"]) == 5000.00
        assert settings["paper_trading_mode"] is False
        assert settings["show_advanced_features"] is False

    @pytest.mark.asyncio
    async def test_get_settings_with_custom_values(
        self,
        client: AsyncClient,
        db_session,
        test_user: User
    ):
        """Test GET returns custom settings values."""
        # Create custom settings
        settings = AutoPilotUserSettings(
            user_id=test_user.id,
            daily_loss_limit=Decimal("50000.00"),
            per_strategy_loss_limit=Decimal("25000.00"),
            max_capital_deployed=Decimal("1000000.00"),
            max_active_strategies=5,
            no_trade_first_minutes=15,
            no_trade_last_minutes=15,
            cooldown_after_loss=True,
            cooldown_minutes=60,
            cooldown_threshold=Decimal("10000.00"),
            paper_trading_mode=True,
            show_advanced_features=True,
            default_order_settings={"order_type": "LIMIT"},
            notification_prefs={"email": True}
        )
        db_session.add(settings)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/settings")

        assert response.status_code == 200
        data = response.json()["data"]

        assert float(data["daily_loss_limit"]) == 50000.00
        assert float(data["per_strategy_loss_limit"]) == 25000.00
        assert float(data["max_capital_deployed"]) == 1000000.00
        assert data["max_active_strategies"] == 5
        assert data["no_trade_first_minutes"] == 15
        assert data["cooldown_after_loss"] is True
        assert data["paper_trading_mode"] is True
        assert data["default_order_settings"]["order_type"] == "LIMIT"


# =============================================================================
# UPDATE SETTINGS TESTS
# =============================================================================

class TestUpdateSettings:
    """Tests for PUT /api/v1/autopilot/settings endpoint."""

    @pytest.mark.asyncio
    async def test_update_settings_all_fields(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test PUT updates all fields."""
        update_data = {
            "daily_loss_limit": 30000.00,
            "per_strategy_loss_limit": 15000.00,
            "max_capital_deployed": 750000.00,
            "max_active_strategies": 5,
            "no_trade_first_minutes": 10,
            "no_trade_last_minutes": 10,
            "cooldown_after_loss": True,
            "cooldown_minutes": 45,
            "cooldown_threshold": 7500.00,
            "paper_trading_mode": True,
            "show_advanced_features": True,
            "default_order_settings": {"order_type": "LIMIT", "delay": 5},
            "notification_prefs": {"email": True, "sms": True},
            "failure_handling": {"on_error": "pause", "max_retries": 5}
        }

        response = await client.put("/api/v1/autopilot/settings", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "updated" in data["message"].lower()

        settings = data["data"]
        assert float(settings["daily_loss_limit"]) == 30000.00
        assert float(settings["per_strategy_loss_limit"]) == 15000.00
        assert float(settings["max_capital_deployed"]) == 750000.00
        assert settings["max_active_strategies"] == 5
        assert settings["no_trade_first_minutes"] == 10
        assert settings["no_trade_last_minutes"] == 10
        assert settings["cooldown_after_loss"] is True
        assert settings["cooldown_minutes"] == 45
        assert float(settings["cooldown_threshold"]) == 7500.00
        assert settings["paper_trading_mode"] is True
        assert settings["show_advanced_features"] is True
        assert settings["default_order_settings"]["order_type"] == "LIMIT"
        assert settings["notification_prefs"]["email"] is True

    @pytest.mark.asyncio
    async def test_update_settings_partial(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test PUT with partial update."""
        # Update only a few fields
        update_data = {
            "daily_loss_limit": 25000.00,
            "paper_trading_mode": True
        }

        response = await client.put("/api/v1/autopilot/settings", json=update_data)

        assert response.status_code == 200
        data = response.json()["data"]

        # Updated fields
        assert float(data["daily_loss_limit"]) == 25000.00
        assert data["paper_trading_mode"] is True

        # Unchanged fields (should retain original values)
        assert float(data["per_strategy_loss_limit"]) == 10000.00
        assert data["max_active_strategies"] == 3

    @pytest.mark.asyncio
    async def test_update_settings_validation_error(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test PUT with invalid values rejected."""
        # Invalid max_active_strategies (exceeds max of 10)
        update_data = {
            "max_active_strategies": 15
        }

        response = await client.put("/api/v1/autopilot/settings", json=update_data)

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_update_settings_invalid_cooldown_minutes(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test invalid cooldown_minutes validation."""
        # cooldown_minutes max is 240
        update_data = {
            "cooldown_minutes": 300
        }

        response = await client.put("/api/v1/autopilot/settings", json=update_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_settings_invalid_no_trade_minutes(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test invalid no_trade minutes validation."""
        # no_trade_first_minutes max is 60
        update_data = {
            "no_trade_first_minutes": 65
        }

        response = await client.put("/api/v1/autopilot/settings", json=update_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_settings_per_strategy_exceeds_daily(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test per_strategy_loss_limit cannot exceed daily_loss_limit."""
        update_data = {
            "daily_loss_limit": 10000.00,
            "per_strategy_loss_limit": 15000.00  # Exceeds daily
        }

        response = await client.put("/api/v1/autopilot/settings", json=update_data)

        # Should return 400 Bad Request
        assert response.status_code == 400
        assert "per_strategy_loss_limit" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_settings_jsonb_fields(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test updating JSONB fields."""
        update_data = {
            "default_order_settings": {
                "order_type": "LIMIT",
                "execution_style": "simultaneous",
                "delay_between_legs": 0,
                "slippage_protection": {
                    "enabled": True,
                    "max_pct": 2.0
                }
            },
            "notification_prefs": {
                "enabled": True,
                "channels": ["in_app", "email", "push"],
                "events": ["entry", "exit", "alert"]
            },
            "failure_handling": {
                "on_network_error": "retry",
                "on_broker_error": "pause",
                "max_retries": 5,
                "retry_delay_ms": 1000
            }
        }

        response = await client.put("/api/v1/autopilot/settings", json=update_data)

        assert response.status_code == 200
        data = response.json()["data"]

        assert data["default_order_settings"]["order_type"] == "LIMIT"
        assert data["default_order_settings"]["execution_style"] == "simultaneous"
        assert data["notification_prefs"]["channels"] == ["in_app", "email", "push"]
        assert data["failure_handling"]["max_retries"] == 5


# =============================================================================
# UNAUTHORIZED ACCESS TESTS
# =============================================================================

class TestSettingsUnauthorized:
    """Tests for unauthorized access to settings endpoints."""

    @pytest.mark.asyncio
    async def test_settings_unauthorized(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test 401 without auth token."""
        response = await unauthenticated_client.get("/api/v1/autopilot/settings")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_settings_unauthorized(
        self,
        unauthenticated_client: AsyncClient
    ):
        """Test PUT 401 without auth token."""
        update_data = {"daily_loss_limit": 25000.00}
        response = await unauthenticated_client.put(
            "/api/v1/autopilot/settings",
            json=update_data
        )

        assert response.status_code == 401


# =============================================================================
# SETTINGS RESPONSE STRUCTURE TESTS
# =============================================================================

class TestSettingsResponseStructure:
    """Tests for settings response structure."""

    @pytest.mark.asyncio
    async def test_settings_response_has_all_fields(
        self,
        client: AsyncClient,
        test_settings: AutoPilotUserSettings
    ):
        """Test response contains all expected fields."""
        response = await client.get("/api/v1/autopilot/settings")

        assert response.status_code == 200
        data = response.json()

        # Check wrapper structure
        assert "status" in data
        assert "data" in data
        assert "timestamp" in data

        # Check settings fields
        settings = data["data"]
        expected_fields = [
            "daily_loss_limit",
            "per_strategy_loss_limit",
            "max_capital_deployed",
            "max_active_strategies",
            "no_trade_first_minutes",
            "no_trade_last_minutes",
            "cooldown_after_loss",
            "cooldown_minutes",
            "cooldown_threshold",
            "default_order_settings",
            "notification_prefs",
            "failure_handling",
            "paper_trading_mode",
            "show_advanced_features"
        ]

        for field in expected_fields:
            assert field in settings, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_settings_response_decimal_precision(
        self,
        client: AsyncClient,
        db_session,
        test_user: User
    ):
        """Test decimal fields maintain precision."""
        settings = AutoPilotUserSettings(
            user_id=test_user.id,
            daily_loss_limit=Decimal("12345.67"),
            per_strategy_loss_limit=Decimal("5432.10"),
            max_capital_deployed=Decimal("987654.32"),
            cooldown_threshold=Decimal("1234.56")
        )
        db_session.add(settings)
        await db_session.commit()

        response = await client.get("/api/v1/autopilot/settings")

        assert response.status_code == 200
        data = response.json()["data"]

        # Decimals should be returned as strings or floats with proper precision
        assert float(data["daily_loss_limit"]) == 12345.67
        assert float(data["per_strategy_loss_limit"]) == 5432.10
        assert float(data["max_capital_deployed"]) == 987654.32
        assert float(data["cooldown_threshold"]) == 1234.56
