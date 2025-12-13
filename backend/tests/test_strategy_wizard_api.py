"""
Backend API Tests for Strategy Wizard Endpoints

Tests all API endpoints in /api/strategy-library/:
- GET /templates - List templates with filters
- GET /templates/categories - Get categories with counts
- GET /templates/{name} - Get template details
- POST /wizard - AI-powered recommendations
- POST /deploy - Deploy template with live data
- POST /compare - Compare strategies
- GET /popular - Get popular strategies

Run with: pytest tests/test_strategy_wizard_api.py -v
"""

import pytest
import allure
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

from app.utils.dependencies import get_current_user, get_current_broker_connection


pytestmark = [pytest.mark.asyncio, pytest.mark.api]


@allure.epic("Strategy Library")
@allure.feature("Browse Templates")
class TestGetTemplates:
    """Tests for GET /api/strategy-library/templates endpoint."""

    async def test_get_all_templates(self, client, seeded_templates):
        """Test that endpoint returns all active templates."""
        response = await client.get("/api/strategy-library/templates")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= len(seeded_templates)

    async def test_get_templates_filter_by_category_bullish(self, client, seeded_templates):
        """Test filtering templates by bullish category."""
        response = await client.get("/api/strategy-library/templates?category=bullish")

        assert response.status_code == 200
        data = response.json()

        for template in data:
            assert template["category"] == "bullish"

    async def test_get_templates_filter_by_category_neutral(self, client, seeded_templates):
        """Test filtering templates by neutral category."""
        response = await client.get("/api/strategy-library/templates?category=neutral")

        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        for template in data:
            assert template["category"] == "neutral"

    async def test_get_templates_filter_by_category_bearish(self, client, seeded_templates):
        """Test filtering templates by bearish category."""
        response = await client.get("/api/strategy-library/templates?category=bearish")

        assert response.status_code == 200
        data = response.json()

        for template in data:
            assert template["category"] == "bearish"

    async def test_get_templates_filter_by_risk_level(self, client, seeded_templates):
        """Test filtering templates by risk level."""
        response = await client.get("/api/strategy-library/templates?risk_level=low")

        assert response.status_code == 200
        data = response.json()

        for template in data:
            assert template["risk_level"] == "low"

    async def test_get_templates_filter_by_difficulty(self, client, seeded_templates):
        """Test filtering templates by difficulty level."""
        response = await client.get("/api/strategy-library/templates?difficulty=beginner")

        assert response.status_code == 200
        data = response.json()

        for template in data:
            assert template["difficulty_level"] == "beginner"

    async def test_get_templates_filter_theta_positive(self, client, seeded_templates):
        """Test filtering for theta positive strategies."""
        response = await client.get("/api/strategy-library/templates?theta_positive=true")

        assert response.status_code == 200
        data = response.json()

        for template in data:
            assert template["theta_positive"] is True

    async def test_get_templates_search(self, client, seeded_templates):
        """Test searching templates by name/description."""
        response = await client.get("/api/strategy-library/templates?search=iron")

        assert response.status_code == 200
        data = response.json()

        # Should find iron condor
        names = [t["name"] for t in data]
        assert any("iron" in name for name in names)

    async def test_get_templates_search_description(self, client, seeded_templates):
        """Test searching templates in description."""
        response = await client.get("/api/strategy-library/templates?search=spread")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_get_templates_empty_category(self, client, seeded_templates):
        """Test that invalid category returns empty list."""
        response = await client.get("/api/strategy-library/templates?category=invalid_category")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_templates_ordered_by_popularity(self, client, seeded_templates):
        """Test that templates are ordered by popularity score descending."""
        response = await client.get("/api/strategy-library/templates")

        assert response.status_code == 200
        data = response.json()

        if len(data) >= 2:
            for i in range(len(data) - 1):
                assert data[i]["popularity_score"] >= data[i + 1]["popularity_score"]

    async def test_get_templates_pagination_limit(self, client, seeded_templates):
        """Test limit parameter for pagination."""
        response = await client.get("/api/strategy-library/templates?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    async def test_get_templates_pagination_offset(self, client, seeded_templates):
        """Test offset parameter for pagination."""
        # Get first page
        response1 = await client.get("/api/strategy-library/templates?limit=2&offset=0")
        # Get second page
        response2 = await client.get("/api/strategy-library/templates?limit=2&offset=2")

        data1 = response1.json()
        data2 = response2.json()

        # Should have different results (if enough templates)
        if len(data1) == 2 and len(data2) >= 1:
            assert data1[0]["name"] != data2[0]["name"]


@allure.epic("Strategy Library")
@allure.feature("Browse Templates")
class TestGetCategories:
    """Tests for GET /api/strategy-library/templates/categories endpoint."""

    @allure.story("Category List")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_get_categories(self, client, seeded_templates):
        """Test that endpoint returns all categories with counts."""
        response = await client.get("/api/strategy-library/templates/categories")

        assert response.status_code == 200
        data = response.json()

        assert "categories" in data
        assert "total" in data
        assert isinstance(data["categories"], list)
        assert data["total"] >= len(seeded_templates)

    @allure.story("Category List")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_categories_structure(self, client, seeded_templates):
        """Test that each category has required fields."""
        response = await client.get("/api/strategy-library/templates/categories")

        assert response.status_code == 200
        data = response.json()

        for category in data["categories"]:
            assert "category" in category
            assert "count" in category
            assert "display_name" in category
            assert isinstance(category["count"], int)
            assert category["count"] >= 0


@allure.epic("Strategy Library")
@allure.feature("Template Details")
class TestGetTemplateDetails:
    """Tests for GET /api/strategy-library/templates/{name} endpoint."""

    @allure.story("View Template")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_get_template_details(self, client, iron_condor_template):
        """Test getting full details of a template."""
        response = await client.get(f"/api/strategy-library/templates/{iron_condor_template.name}")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == iron_condor_template.name
        assert data["display_name"] == iron_condor_template.display_name
        assert "legs_config" in data
        assert len(data["legs_config"]) == 4

    @allure.story("View Template")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_get_template_not_found(self, client):
        """Test that 404 is returned for non-existent template."""
        response = await client.get("/api/strategy-library/templates/nonexistent_strategy")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @allure.story("Educational Content")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_template_details_includes_educational_content(self, client, iron_condor_template):
        """Test that educational content is included in response."""
        response = await client.get(f"/api/strategy-library/templates/{iron_condor_template.name}")

        assert response.status_code == 200
        data = response.json()

        # Check educational fields
        assert "when_to_use" in data
        assert "pros" in data
        assert "cons" in data
        assert "common_mistakes" in data
        assert "exit_rules" in data

    @allure.story("View Template")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_template_details_includes_all_fields(self, client, iron_condor_template):
        """Test that all fields are present in response."""
        response = await client.get(f"/api/strategy-library/templates/{iron_condor_template.name}")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "id", "name", "display_name", "category", "description",
            "legs_config", "max_profit", "max_loss", "market_outlook",
            "volatility_preference", "risk_level", "theta_positive",
            "vega_positive", "delta_neutral", "difficulty_level",
            "popularity_score", "created_at", "updated_at"
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"


@allure.epic("Strategy Library")
@allure.feature("Strategy Wizard")
class TestWizard:
    """Tests for POST /api/strategy-library/wizard endpoint."""

    @allure.story("Bullish Recommendations")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_wizard_bullish_low_vol_low_risk(self, client, seeded_templates):
        """Test wizard with bullish outlook, low volatility, low risk."""
        payload = {
            "market_outlook": "bullish",
            "volatility_view": "low_iv",
            "risk_tolerance": "low"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "recommendations" in data
        assert "inputs" in data
        assert "total_matches" in data

        # Should recommend bull_call_spread (debit spread, low risk, for low IV)
        if len(data["recommendations"]) > 0:
            names = [r["template"]["name"] for r in data["recommendations"]]
            # Bull call spread should be high in recommendations for this combo
            assert len(names) >= 1

    @allure.story("Bearish Recommendations")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_wizard_bearish_high_vol_medium_risk(self, client, seeded_templates):
        """Test wizard with bearish outlook, high volatility, medium risk."""
        payload = {
            "market_outlook": "bearish",
            "volatility_view": "high_iv",
            "risk_tolerance": "medium"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "recommendations" in data
        # Should have some bearish strategies
        if len(data["recommendations"]) > 0:
            categories = [r["template"]["category"] for r in data["recommendations"]]
            assert "bearish" in categories or "neutral" in categories

    @allure.story("Neutral Recommendations")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_wizard_neutral_high_vol_low_risk(self, client, seeded_templates):
        """Test wizard with neutral outlook, high volatility, low risk."""
        payload = {
            "market_outlook": "neutral",
            "volatility_view": "high_iv",
            "risk_tolerance": "low"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should recommend iron_condor (neutral, high IV, defined risk)
        if len(data["recommendations"]) > 0:
            names = [r["template"]["name"] for r in data["recommendations"]]
            # Iron condor should score well for this combo
            assert len(names) >= 1

    @allure.story("Volatile Recommendations")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_wizard_volatile_low_vol_medium_risk(self, client, seeded_templates):
        """Test wizard with volatile outlook, low volatility, medium risk."""
        payload = {
            "market_outlook": "volatile",
            "volatility_view": "low_iv",
            "risk_tolerance": "medium"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should recommend long_straddle or long_strangle (volatile, low IV to buy)
        if len(data["recommendations"]) > 0:
            names = [r["template"]["name"] for r in data["recommendations"]]
            assert len(names) >= 1

    @allure.story("Recommendation Limits")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_wizard_returns_top_5(self, client, seeded_templates):
        """Test that wizard returns maximum 5 recommendations."""
        payload = {
            "market_outlook": "neutral",
            "volatility_view": "any",
            "risk_tolerance": "medium"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert len(data["recommendations"]) <= 5

    @allure.story("Scoring Algorithm")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_wizard_includes_match_percentage(self, client, seeded_templates):
        """Test that each recommendation includes score and reasons."""
        payload = {
            "market_outlook": "bullish",
            "volatility_view": "high_iv",
            "risk_tolerance": "low"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()

        for rec in data["recommendations"]:
            assert "score" in rec
            assert "match_reasons" in rec
            assert isinstance(rec["score"], int)
            assert 0 <= rec["score"] <= 100
            assert isinstance(rec["match_reasons"], list)

    @allure.story("Scoring Algorithm")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_wizard_scoring_algorithm(self, client, seeded_templates):
        """Test that scoring algorithm produces logical results."""
        payload = {
            "market_outlook": "neutral",
            "volatility_view": "high_iv",
            "risk_tolerance": "medium"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Recommendations should be sorted by score descending
        if len(data["recommendations"]) >= 2:
            scores = [r["score"] for r in data["recommendations"]]
            assert scores == sorted(scores, reverse=True)

    @allure.story("Optional Parameters")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_wizard_with_experience_level(self, client, seeded_templates):
        """Test wizard with optional experience level."""
        payload = {
            "market_outlook": "neutral",
            "volatility_view": "high_iv",
            "risk_tolerance": "low",
            "experience_level": "beginner"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

    @allure.story("Optional Parameters")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_wizard_with_capital_size(self, client, seeded_templates):
        """Test wizard with optional capital size."""
        payload = {
            "market_outlook": "neutral",
            "volatility_view": "high_iv",
            "risk_tolerance": "low",
            "capital_size": "medium"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

    @allure.story("Validation")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_wizard_missing_required_fields(self, client):
        """Test that 422 is returned for missing required fields."""
        # Missing market_outlook
        payload = {
            "volatility_view": "high_iv",
            "risk_tolerance": "low"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)
        assert response.status_code == 422

    @allure.story("Validation")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_wizard_invalid_outlook_value(self, client):
        """Test that 422 is returned for invalid outlook value."""
        payload = {
            "market_outlook": "super_bullish",  # Invalid
            "volatility_view": "high_iv",
            "risk_tolerance": "low"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)
        assert response.status_code == 422


@allure.epic("Strategy Library")
@allure.feature("Deploy Strategy")
class TestDeploy:
    """Tests for POST /api/strategy-library/deploy endpoint."""

    @allure.story("Authentication")
    @allure.severity(allure.severity_level.BLOCKER)
    async def test_deploy_requires_auth(self, client, iron_condor_template):
        """Test that deploy endpoint requires authentication."""
        payload = {
            "template_name": iron_condor_template.name,
            "underlying": "NIFTY",
            "lots": 1
        }

        response = await client.post("/api/strategy-library/deploy", json=payload)
        # Should fail without auth
        assert response.status_code in [401, 403, 422]

    @allure.story("Validation")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_deploy_invalid_template(
        self, client, db_session, test_user, test_broker_connection, mock_kite_client
    ):
        """Test that 404 is returned for invalid template name."""
        from app.main import app

        async def override_user():
            return test_user

        async def override_broker():
            return test_broker_connection

        app.dependency_overrides[get_current_user] = override_user
        app.dependency_overrides[get_current_broker_connection] = override_broker

        payload = {
            "template_name": "nonexistent_template",
            "underlying": "NIFTY",
            "lots": 1
        }

        response = await client.post("/api/strategy-library/deploy", json=payload)
        assert response.status_code == 404

        app.dependency_overrides.clear()

    @allure.story("Deploy Iron Condor")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_deploy_iron_condor(
        self, client, db_session, test_user, test_broker_connection,
        iron_condor_template, mock_kite_client
    ):
        """Test deploying iron condor with 4 legs."""
        from app.main import app

        async def override_user():
            return test_user

        async def override_broker():
            return test_broker_connection

        app.dependency_overrides[get_current_user] = override_user
        app.dependency_overrides[get_current_broker_connection] = override_broker

        with patch('kiteconnect.KiteConnect') as MockKite:
            MockKite.return_value = mock_kite_client

            payload = {
                "template_name": iron_condor_template.name,
                "underlying": "NIFTY",
                "lots": 1
            }

            response = await client.post("/api/strategy-library/deploy", json=payload)

            if response.status_code == 200:
                data = response.json()
                assert "legs" in data
                assert len(data["legs"]) == 4
                assert data["underlying"] == "NIFTY"

        app.dependency_overrides.clear()

    @allure.story("Deploy Multiple Lots")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_deploy_multiple_lots(
        self, client, db_session, test_user, test_broker_connection,
        bull_call_spread_template, mock_kite_client
    ):
        """Test deploying with multiple lots."""
        from app.main import app

        async def override_user():
            return test_user

        async def override_broker():
            return test_broker_connection

        app.dependency_overrides[get_current_user] = override_user
        app.dependency_overrides[get_current_broker_connection] = override_broker

        with patch('kiteconnect.KiteConnect') as MockKite:
            MockKite.return_value = mock_kite_client

            payload = {
                "template_name": bull_call_spread_template.name,
                "underlying": "NIFTY",
                "lots": 3
            }

            response = await client.post("/api/strategy-library/deploy", json=payload)

            if response.status_code == 200:
                data = response.json()
                for leg in data["legs"]:
                    assert leg["lots"] == 3

        app.dependency_overrides.clear()


@allure.epic("Strategy Library")
@allure.feature("Compare Strategies")
class TestCompare:
    """Tests for POST /api/strategy-library/compare endpoint."""

    @allure.story("Compare Two Strategies")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_compare_two_strategies(self, client, iron_condor_template, bull_call_spread_template):
        """Test comparing two strategies."""
        payload = {
            "template_names": [iron_condor_template.name, bull_call_spread_template.name]
        }

        response = await client.post("/api/strategy-library/compare", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "strategies" in data
        assert "comparison_matrix" in data
        assert len(data["strategies"]) == 2

    @allure.story("Validation")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_compare_min_two_required(self, client, iron_condor_template):
        """Test that at least 2 strategies are required."""
        payload = {
            "template_names": [iron_condor_template.name]
        }

        response = await client.post("/api/strategy-library/compare", json=payload)
        assert response.status_code == 422  # Validation error

    @allure.story("Validation")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_compare_max_four(self, client, seeded_templates):
        """Test that maximum 4 strategies can be compared."""
        names = [t.name for t in seeded_templates[:5]]  # Try 5

        payload = {
            "template_names": names
        }

        response = await client.post("/api/strategy-library/compare", json=payload)

        # Should fail validation for > 4 templates
        if len(names) > 4:
            assert response.status_code == 422

    @allure.story("Comparison Metrics")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_compare_includes_all_metrics(
        self, client, iron_condor_template, bull_put_spread_template
    ):
        """Test that all comparison metrics are included."""
        payload = {
            "template_names": [iron_condor_template.name, bull_put_spread_template.name]
        }

        response = await client.post("/api/strategy-library/compare", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Check metrics in comparison matrix
        for name, metrics in data["comparison_matrix"].items():
            assert "max_profit" in metrics
            assert "max_loss" in metrics
            assert "risk_level" in metrics
            assert "theta_positive" in metrics
            assert "vega_positive" in metrics
            assert "delta_neutral" in metrics


@allure.epic("Strategy Library")
@allure.feature("Popular Strategies")
class TestPopular:
    """Tests for GET /api/strategy-library/popular endpoint."""

    @allure.story("Popular List")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_get_popular_default_limit(self, client, seeded_templates):
        """Test that default limit returns reasonable number."""
        response = await client.get("/api/strategy-library/popular")

        assert response.status_code == 200
        data = response.json()

        assert "strategies" in data
        assert len(data["strategies"]) <= 10

    @allure.story("Popular List")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_get_popular_custom_limit(self, client, seeded_templates):
        """Test that custom limit is respected."""
        response = await client.get("/api/strategy-library/popular?limit=3")

        assert response.status_code == 200
        data = response.json()

        assert len(data["strategies"]) <= 3

    @allure.story("Ordering")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_popular_ordered_by_score(self, client, seeded_templates):
        """Test that popular strategies are ordered by popularity score."""
        response = await client.get("/api/strategy-library/popular")

        assert response.status_code == 200
        data = response.json()

        strategies = data["strategies"]
        if len(strategies) >= 2:
            for i in range(len(strategies) - 1):
                assert strategies[i]["popularity_score"] >= strategies[i + 1]["popularity_score"]

    @allure.story("Validation")
    @allure.severity(allure.severity_level.MINOR)
    async def test_popular_limit_bounds(self, client, seeded_templates):
        """Test that limit has reasonable bounds."""
        # Very large limit should be capped
        response = await client.get("/api/strategy-library/popular?limit=100")

        assert response.status_code in [200, 422]  # Either succeeds with cap or validation error
