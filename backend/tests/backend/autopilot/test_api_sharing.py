"""
Test suite for AutoPilot Phase 4 Strategy Sharing API endpoints.

Tests cover:
- POST /autopilot/strategies/{id}/share - Share a strategy
- DELETE /autopilot/strategies/{id}/share - Unshare a strategy
- GET /autopilot/shared/{token} - Get shared strategy (public)
- POST /autopilot/shared/{token}/clone - Clone a shared strategy
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.autopilot import AutoPilotStrategy, ShareMode
from app.models.users import User


# ============================================================================
# TEST CLASS: Share Strategy
# ============================================================================

class TestShareStrategy:
    """Tests for POST /autopilot/strategies/{id}/share endpoint."""

    @pytest.mark.asyncio
    async def test_share_strategy_view_only(self, db_session, test_user, test_autopilot_strategy):
        """Test sharing a strategy with view_only mode."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        share_data = {
            "share_mode": "view_only"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/strategies/{test_autopilot_strategy.id}/share",
                    json=share_data
                )

            assert response.status_code == 200
            data = response.json()
            assert "share_token" in data["data"]
            assert "share_url" in data["data"]
            assert data["data"]["share_mode"] == "view_only"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_share_strategy_clonable(self, db_session, test_user, test_autopilot_strategy):
        """Test sharing a strategy with clonable mode."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        share_data = {
            "share_mode": "clonable"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/strategies/{test_autopilot_strategy.id}/share",
                    json=share_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["share_mode"] == "clonable"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_share_strategy_not_found(self, db_session, test_user):
        """Test sharing a non-existent strategy returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        share_data = {
            "share_mode": "view_only"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/strategies/99999/share",
                    json=share_data
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_share_other_user_strategy(self, db_session, test_user, test_autopilot_strategy):
        """Test sharing another user's strategy is forbidden."""
        test_autopilot_strategy.user_id = test_user.id + 100
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        share_data = {
            "share_mode": "view_only"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/strategies/{test_autopilot_strategy.id}/share",
                    json=share_data
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_share_strategy_generates_unique_token(self, db_session, test_user, test_autopilot_strategy):
        """Test that sharing generates a unique token."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        share_data = {
            "share_mode": "view_only"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/strategies/{test_autopilot_strategy.id}/share",
                    json=share_data
                )

            assert response.status_code == 200
            data = response.json()
            token = data["data"]["share_token"]
            assert len(token) > 10  # Token should be reasonably long
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Unshare Strategy
# ============================================================================

class TestUnshareStrategy:
    """Tests for DELETE /autopilot/strategies/{id}/share endpoint."""

    @pytest.mark.asyncio
    async def test_unshare_strategy_success(self, db_session, test_user, test_strategy_with_share_token):
        """Test unsharing a strategy."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(
                    f"/api/v1/autopilot/strategies/{test_strategy_with_share_token.id}/share"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["unshared"] is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unshare_strategy_not_found(self, db_session, test_user):
        """Test unsharing a non-existent strategy returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete("/api/v1/autopilot/strategies/99999/share")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unshare_clears_token(self, db_session, test_user, test_strategy_with_share_token):
        """Test that unsharing clears the share token."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(
                    f"/api/v1/autopilot/strategies/{test_strategy_with_share_token.id}/share"
                )

            assert response.status_code == 200

            # Verify token is cleared
            await db_session.refresh(test_strategy_with_share_token)
            assert test_strategy_with_share_token.share_token is None
            assert test_strategy_with_share_token.share_mode == "private"
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Get Shared Strategy (Public)
# ============================================================================

class TestGetSharedStrategy:
    """Tests for GET /autopilot/shared/{token} endpoint."""

    @pytest.mark.asyncio
    async def test_get_shared_strategy_success(self, db_session, test_strategy_with_share_token):
        """Test getting a shared strategy by token (no auth required)."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/autopilot/shared/{test_strategy_with_share_token.share_token}"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["name"] == test_strategy_with_share_token.name
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_shared_strategy_invalid_token(self, db_session):
        """Test getting shared strategy with invalid token returns 404."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/shared/invalid_token_123")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_shared_strategy_private_fails(self, db_session, test_autopilot_strategy):
        """Test getting a private strategy's token fails."""
        # Ensure strategy is private
        test_autopilot_strategy.share_mode = "private"
        test_autopilot_strategy.share_token = "private_token_123"
        await db_session.commit()

        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/shared/private_token_123")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_shared_strategy_excludes_sensitive_data(self, db_session, test_strategy_with_share_token):
        """Test that shared strategy response excludes sensitive data."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/autopilot/shared/{test_strategy_with_share_token.share_token}"
                )

            assert response.status_code == 200
            data = response.json()
            # Should not include user_id or other sensitive data
            assert "user_id" not in data["data"]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Clone Shared Strategy
# ============================================================================

class TestCloneSharedStrategy:
    """Tests for POST /autopilot/shared/{token}/clone endpoint."""

    @pytest.mark.asyncio
    async def test_clone_shared_strategy_success(self, db_session, test_user, test_strategy_public):
        """Test cloning a shared strategy."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        clone_data = {
            "new_name": "My Cloned Strategy",
            "lots": 2
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/shared/{test_strategy_public.share_token}/clone",
                    json=clone_data
                )

            assert response.status_code == 201
            data = response.json()
            assert data["data"]["name"] == "My Cloned Strategy"
            assert data["data"]["lots"] == 2
            assert data["data"]["status"] == "draft"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clone_shared_strategy_default_name(self, db_session, test_user, test_strategy_public):
        """Test cloning with default name."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        clone_data = {
            "lots": 1
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/shared/{test_strategy_public.share_token}/clone",
                    json=clone_data
                )

            assert response.status_code == 201
            data = response.json()
            # Name should include "(Cloned)" or similar
            assert "clone" in data["data"]["name"].lower() or test_strategy_public.name in data["data"]["name"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clone_shared_strategy_invalid_token(self, db_session, test_user):
        """Test cloning with invalid token returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        clone_data = {
            "lots": 1
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/shared/invalid_token_123/clone",
                    json=clone_data
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clone_view_only_strategy_fails(self, db_session, test_user, test_strategy_with_share_token):
        """Test cloning a view_only strategy fails."""
        # Ensure strategy is view_only (not clonable)
        test_strategy_with_share_token.share_mode = "view_only"
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        clone_data = {
            "lots": 1
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/shared/{test_strategy_with_share_token.share_token}/clone",
                    json=clone_data
                )

            # Should fail - view_only strategies cannot be cloned
            assert response.status_code in [403, 404]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_clone_requires_auth(self, db_session, test_strategy_public):
        """Test that cloning requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        clone_data = {
            "lots": 1
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/shared/{test_strategy_public.share_token}/clone",
                    json=clone_data
                )

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Sharing Authentication
# ============================================================================

class TestSharingAuthentication:
    """Tests for sharing endpoint authentication."""

    @pytest.mark.asyncio
    async def test_share_requires_auth(self, db_session):
        """Test that sharing requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        share_data = {
            "share_mode": "view_only"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/strategies/1/share",
                    json=share_data
                )

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_unshare_requires_auth(self, db_session):
        """Test that unsharing requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete("/api/v1/autopilot/strategies/1/share")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_shared_is_public(self, db_session, test_strategy_with_share_token):
        """Test that getting shared strategy does not require auth."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/autopilot/shared/{test_strategy_with_share_token.share_token}"
                )

            # Should succeed without auth (it's a public endpoint)
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
