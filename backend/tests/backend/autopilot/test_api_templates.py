"""
Test suite for AutoPilot Phase 4 Template API endpoints.

Tests cover:
- GET /autopilot/templates - List templates with filters
- GET /autopilot/templates/categories - Get category counts
- GET /autopilot/templates/popular - Get popular templates
- GET /autopilot/templates/{id} - Get template details
- POST /autopilot/templates - Create template
- PUT /autopilot/templates/{id} - Update template
- DELETE /autopilot/templates/{id} - Delete template
- POST /autopilot/templates/{id}/deploy - Deploy template as strategy
- POST /autopilot/templates/{id}/rate - Rate template
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.autopilot import (
    AutoPilotTemplate, AutoPilotTemplateRating, AutoPilotStrategy,
    TemplateCategory
)
from app.models.users import User


# ============================================================================
# TEST CLASS: Template Listing
# ============================================================================

class TestTemplateList:
    """Tests for GET /autopilot/templates endpoint."""

    @pytest.mark.asyncio
    async def test_list_templates_empty(self, db_session, test_user):
        """Test listing templates when none exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["data"] == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_templates_with_data(self, db_session, test_user, test_multiple_templates):
        """Test listing templates returns all available templates."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 2
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_category(self, db_session, test_user, test_multiple_templates):
        """Test filtering templates by category."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates?category=neutral")

            assert response.status_code == 200
            data = response.json()
            # All returned templates should be in the neutral category
            for template in data["data"]:
                assert template.get("category") == "neutral"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_underlying(self, db_session, test_user, test_multiple_templates):
        """Test filtering templates by underlying."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates?underlying=NIFTY")

            assert response.status_code == 200
            data = response.json()
            for template in data["data"]:
                assert template.get("underlying") == "NIFTY"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_risk_level(self, db_session, test_user, test_multiple_templates):
        """Test filtering templates by risk level."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates?risk_level=low")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_templates_search(self, db_session, test_user, test_template_in_db):
        """Test searching templates by name."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates?search=Iron")

            assert response.status_code == 200
            data = response.json()
            # Results should contain "Iron" in name
            for template in data["data"]:
                assert "Iron" in template.get("name", "").lower() or "iron" in template.get("name", "").lower()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_templates_pagination(self, db_session, test_user, test_multiple_templates):
        """Test pagination of templates."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates?page=1&page_size=1")

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 1
            assert len(data["data"]) <= 1
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_templates_pagination_invalid_page(self, db_session, test_user):
        """Test invalid pagination parameters."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates?page=0")

            # FastAPI should return 422 for invalid query params
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Template Categories
# ============================================================================

class TestTemplateCategories:
    """Tests for GET /autopilot/templates/categories endpoint."""

    @pytest.mark.asyncio
    async def test_get_categories(self, db_session, test_user, test_multiple_templates):
        """Test getting category counts."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates/categories")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_categories_empty(self, db_session, test_user):
        """Test getting categories when no templates exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates/categories")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Popular Templates
# ============================================================================

class TestPopularTemplates:
    """Tests for GET /autopilot/templates/popular endpoint."""

    @pytest.mark.asyncio
    async def test_get_popular_templates(self, db_session, test_user, test_multiple_templates):
        """Test getting popular templates."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates/popular")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_popular_templates_limit(self, db_session, test_user, test_multiple_templates):
        """Test getting popular templates with custom limit."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates/popular?limit=5")

            assert response.status_code == 200
            data = response.json()
            assert len(data.get("data", [])) <= 5
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Get Template Details
# ============================================================================

class TestGetTemplate:
    """Tests for GET /autopilot/templates/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_template_success(self, db_session, test_user, test_template_in_db):
        """Test getting template details."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/templates/{test_template_in_db.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["id"] == test_template_in_db.id
            assert data["data"]["name"] == test_template_in_db.name
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, db_session, test_user):
        """Test getting non-existent template returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates/99999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_system_template(self, db_session, test_user, test_template_in_db):
        """Test getting a system template."""
        # Update template to be a system template
        test_template_in_db.is_system = True
        await db_session.commit()
        await db_session.refresh(test_template_in_db)

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/templates/{test_template_in_db.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["is_system"] is True
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Create Template
# ============================================================================

class TestCreateTemplate:
    """Tests for POST /autopilot/templates endpoint."""

    @pytest.mark.asyncio
    async def test_create_template_success(self, db_session, test_user, get_iron_condor_legs_config):
        """Test creating a new template."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        template_data = {
            "name": "My Custom Iron Condor",
            "description": "A custom iron condor strategy",
            "category": "neutral",
            "underlying": "NIFTY",
            "legs_config": get_iron_condor_legs_config,
            "entry_conditions": {
                "time_condition": {"start_time": "09:30", "end_time": "15:00"},
                "vix_condition": {"min_vix": 12, "max_vix": 20}
            },
            "risk_level": "medium",
            "market_outlook": "range_bound"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/templates",
                    json=template_data
                )

            assert response.status_code == 201
            data = response.json()
            assert data["data"]["name"] == "My Custom Iron Condor"
            assert data["data"]["created_by_id"] == test_user.id
            assert data["data"]["is_system"] is False
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_template_missing_required_fields(self, db_session, test_user):
        """Test creating template without required fields fails."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        template_data = {
            "description": "Missing name and other required fields"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/templates",
                    json=template_data
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_template_with_educational_content(self, db_session, test_user, get_iron_condor_legs_config):
        """Test creating template with educational content."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        template_data = {
            "name": "Educational Iron Condor",
            "description": "An iron condor with educational content",
            "category": "neutral",
            "underlying": "NIFTY",
            "legs_config": get_iron_condor_legs_config,
            "entry_conditions": {
                "time_condition": {"start_time": "09:30", "end_time": "15:00"}
            },
            "educational_content": {
                "when_to_use": "Use when you expect low volatility",
                "pros": ["Limited risk", "High probability of profit"],
                "cons": ["Limited profit potential"],
                "common_mistakes": ["Selling too close to the money"],
                "exit_rules": ["Exit at 50% of max profit"]
            }
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/templates",
                    json=template_data
                )

            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Update Template
# ============================================================================

class TestUpdateTemplate:
    """Tests for PUT /autopilot/templates/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_own_template(self, db_session, test_user, test_template_in_db):
        """Test updating a user's own template."""
        # Ensure template belongs to test user
        test_template_in_db.created_by_id = test_user.id
        test_template_in_db.is_system = False
        await db_session.commit()
        await db_session.refresh(test_template_in_db)

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {
            "name": "Updated Template Name",
            "description": "Updated description"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}",
                    json=update_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["name"] == "Updated Template Name"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_system_template_forbidden(self, db_session, test_user, test_template_in_db):
        """Test that updating a system template is forbidden."""
        test_template_in_db.is_system = True
        test_template_in_db.created_by_id = None
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {
            "name": "Try to Update System Template"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}",
                    json=update_data
                )

            # Should be 404 or 403 depending on implementation
            assert response.status_code in [403, 404]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_other_user_template_forbidden(self, db_session, test_user, test_template_in_db):
        """Test that updating another user's template is forbidden."""
        # Set template to belong to a different user
        test_template_in_db.created_by_id = test_user.id + 100  # Different user
        test_template_in_db.is_system = False
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {
            "name": "Trying to steal"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}",
                    json=update_data
                )

            assert response.status_code in [403, 404]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Delete Template
# ============================================================================

class TestDeleteTemplate:
    """Tests for DELETE /autopilot/templates/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_own_template(self, db_session, test_user, test_template_in_db):
        """Test deleting a user's own template."""
        test_template_in_db.created_by_id = test_user.id
        test_template_in_db.is_system = False
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/autopilot/templates/{test_template_in_db.id}")

            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_system_template_forbidden(self, db_session, test_user, test_template_in_db):
        """Test that deleting a system template is forbidden."""
        test_template_in_db.is_system = True
        test_template_in_db.created_by_id = None
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/autopilot/templates/{test_template_in_db.id}")

            assert response.status_code in [403, 404]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_template(self, db_session, test_user):
        """Test deleting a non-existent template returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete("/api/v1/autopilot/templates/99999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Deploy Template
# ============================================================================

class TestDeployTemplate:
    """Tests for POST /autopilot/templates/{id}/deploy endpoint."""

    @pytest.mark.asyncio
    async def test_deploy_template_success(self, db_session, test_user, test_template_in_db):
        """Test deploying a template as a new strategy."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        deploy_data = {
            "strategy_name": "My Deployed Strategy",
            "lots": 2,
            "expiry_date": "2025-01-30"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/deploy",
                    json=deploy_data
                )

            assert response.status_code == 201
            data = response.json()
            assert data["data"]["name"] == "My Deployed Strategy"
            assert data["data"]["lots"] == 2
            assert data["data"]["status"] == "draft"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_deploy_template_default_name(self, db_session, test_user, test_template_in_db):
        """Test deploying a template with default name."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        deploy_data = {
            "lots": 1
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/deploy",
                    json=deploy_data
                )

            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_deploy_nonexistent_template(self, db_session, test_user):
        """Test deploying a non-existent template returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        deploy_data = {
            "strategy_name": "Test",
            "lots": 1
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/templates/99999/deploy",
                    json=deploy_data
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_deploy_template_increments_usage_count(self, db_session, test_user, test_template_in_db):
        """Test that deploying a template increments usage_count."""
        initial_count = test_template_in_db.usage_count or 0

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        deploy_data = {"lots": 1}

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/deploy",
                    json=deploy_data
                )

            assert response.status_code == 201

            # Verify usage count incremented
            await db_session.refresh(test_template_in_db)
            assert test_template_in_db.usage_count == initial_count + 1
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Rate Template
# ============================================================================

class TestRateTemplate:
    """Tests for POST /autopilot/templates/{id}/rate endpoint."""

    @pytest.mark.asyncio
    async def test_rate_template_success(self, db_session, test_user, test_template_in_db):
        """Test rating a template."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        rating_data = {
            "rating": 5,
            "review": "Excellent strategy!"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/rate",
                    json=rating_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["rating"] == 5
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_rate_template_update_existing(self, db_session, test_user, test_template_in_db, test_template_rating):
        """Test updating an existing rating."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        rating_data = {
            "rating": 3,
            "review": "Changed my mind"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/rate",
                    json=rating_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["rating"] == 3
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_rate_template_invalid_rating(self, db_session, test_user, test_template_in_db):
        """Test rating with invalid value."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        rating_data = {
            "rating": 10,  # Invalid - should be 1-5
            "review": "Test"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/rate",
                    json=rating_data
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_rate_nonexistent_template(self, db_session, test_user):
        """Test rating a non-existent template."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        rating_data = {
            "rating": 5,
            "review": "Test"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/templates/99999/rate",
                    json=rating_data
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_rate_template_updates_average(self, db_session, test_user, test_template_in_db):
        """Test that rating updates the template's average rating."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        rating_data = {
            "rating": 4
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    f"/api/v1/autopilot/templates/{test_template_in_db.id}/rate",
                    json=rating_data
                )

            assert response.status_code == 200

            # Refresh and check average rating
            await db_session.refresh(test_template_in_db)
            assert test_template_in_db.average_rating is not None
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Authentication and Authorization
# ============================================================================

class TestTemplateAuthentication:
    """Tests for template endpoint authentication."""

    @pytest.mark.asyncio
    async def test_list_templates_requires_auth(self, db_session):
        """Test that listing templates requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db
        # Note: Not overriding get_current_user, so it should require auth

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/templates")

            # Should return 401 or similar auth error
            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_template_requires_auth(self, db_session, get_iron_condor_legs_config):
        """Test that creating a template requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        template_data = {
            "name": "Test",
            "category": "neutral",
            "underlying": "NIFTY",
            "legs_config": get_iron_condor_legs_config
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/templates",
                    json=template_data
                )

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Multiple Filters
# ============================================================================

class TestTemplateMultipleFilters:
    """Tests for combining multiple filters."""

    @pytest.mark.asyncio
    async def test_filter_category_and_underlying(self, db_session, test_user, test_multiple_templates):
        """Test filtering by both category and underlying."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/autopilot/templates?category=neutral&underlying=NIFTY"
                )

            assert response.status_code == 200
            data = response.json()
            for template in data["data"]:
                assert template.get("category") == "neutral"
                assert template.get("underlying") == "NIFTY"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_filter_with_search(self, db_session, test_user, test_multiple_templates):
        """Test combining category filter with search."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/autopilot/templates?category=neutral&search=Iron"
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
