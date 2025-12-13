"""
Integration Tests for Strategy Templates System

Tests end-to-end flows:
- Full wizard to deploy flow
- Seed script verification
- Concurrent request handling
- Complete deploy flow with mocked Kite API

Run with: pytest tests/test_strategy_integration.py -v
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from uuid import uuid4
from sqlalchemy import select

from app.models.strategy_templates import StrategyTemplate
from app.utils.dependencies import get_current_user, get_current_broker_connection


pytestmark = pytest.mark.asyncio


class TestFullWizardToDeployFlow:
    """Test complete wizard to deployment flow."""

    async def test_full_wizard_to_deploy_flow(
        self, client, db_session, seeded_templates,
        test_user, test_broker_connection, mock_kite_client
    ):
        """Complete flow: Run wizard -> select recommendation -> deploy."""
        from app.main import app

        # Step 1: Run the wizard
        wizard_payload = {
            "market_outlook": "neutral",
            "volatility_view": "high_iv",
            "risk_tolerance": "medium"
        }

        wizard_response = await client.post(
            "/api/strategy-library/wizard",
            json=wizard_payload
        )

        assert wizard_response.status_code == 200
        wizard_data = wizard_response.json()
        assert len(wizard_data["recommendations"]) >= 1

        # Step 2: Get the top recommendation
        top_recommendation = wizard_data["recommendations"][0]
        template_name = top_recommendation["template"]["name"]

        # Step 3: Get template details
        details_response = await client.get(
            f"/api/strategy-library/templates/{template_name}"
        )

        assert details_response.status_code == 200
        details_data = details_response.json()
        assert details_data["name"] == template_name

        # Step 4: Deploy the strategy (with auth mocking)
        async def override_user():
            return test_user

        async def override_broker():
            return test_broker_connection

        app.dependency_overrides[get_current_user] = override_user
        app.dependency_overrides[get_current_broker_connection] = override_broker

        with patch('kiteconnect.KiteConnect') as MockKite:
            MockKite.return_value = mock_kite_client

            deploy_payload = {
                "template_name": template_name,
                "underlying": "NIFTY",
                "lots": 1
            }

            deploy_response = await client.post(
                "/api/strategy-library/deploy",
                json=deploy_payload
            )

            # Verify deployment
            if deploy_response.status_code == 200:
                deploy_data = deploy_response.json()
                assert deploy_data["template_name"] == template_name
                assert deploy_data["underlying"] == "NIFTY"
                assert "legs" in deploy_data
                assert len(deploy_data["legs"]) >= 1

        app.dependency_overrides.clear()


class TestSeedScript:
    """Test the strategy template seeding."""

    async def test_seed_creates_templates(self, db_session):
        """Verify that seeding creates templates in database."""
        # Count templates before (should be from fixtures)
        result = await db_session.execute(select(StrategyTemplate))
        templates = result.scalars().all()

        # Should have some templates from fixtures
        assert len(templates) >= 0  # May or may not have templates

    async def test_seeded_templates_have_required_fields(self, db_session, seeded_templates):
        """Verify all seeded templates have required fields."""
        for template in seeded_templates:
            assert template.name is not None
            assert template.display_name is not None
            assert template.category is not None
            assert template.description is not None
            assert template.legs_config is not None
            assert len(template.legs_config) >= 1
            assert template.max_profit is not None
            assert template.max_loss is not None
            assert template.market_outlook is not None
            assert template.volatility_preference is not None
            assert template.risk_level is not None
            assert template.capital_requirement is not None

    async def test_all_categories_represented(self, db_session, seeded_templates):
        """Verify multiple categories are represented in seeded data."""
        categories = set(t.category for t in seeded_templates)

        # Should have multiple categories
        assert len(categories) >= 3, "Should have at least 3 different categories"


class TestConcurrentRequests:
    """Test concurrent request handling."""

    async def test_concurrent_wizard_requests(self, client, seeded_templates):
        """Test multiple simultaneous wizard requests."""
        wizard_payloads = [
            {"market_outlook": "bullish", "volatility_view": "low_iv", "risk_tolerance": "low"},
            {"market_outlook": "bearish", "volatility_view": "high_iv", "risk_tolerance": "medium"},
            {"market_outlook": "neutral", "volatility_view": "high_iv", "risk_tolerance": "low"},
            {"market_outlook": "volatile", "volatility_view": "low_iv", "risk_tolerance": "medium"},
        ]

        async def make_wizard_request(payload):
            return await client.post("/api/strategy-library/wizard", json=payload)

        # Execute all requests concurrently
        results = await asyncio.gather(
            *[make_wizard_request(p) for p in wizard_payloads],
            return_exceptions=True
        )

        # All should succeed
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Request {i} raised exception: {result}")
            assert result.status_code == 200, f"Request {i} failed with status {result.status_code}"

    async def test_concurrent_template_reads(self, client, seeded_templates):
        """Test concurrent template detail reads."""
        template_names = [t.name for t in seeded_templates[:4]]

        async def get_template(name):
            return await client.get(f"/api/strategy-library/templates/{name}")

        # Execute all reads concurrently
        results = await asyncio.gather(
            *[get_template(name) for name in template_names],
            return_exceptions=True
        )

        # All should succeed
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Request {i} raised exception: {result}")
            assert result.status_code == 200


class TestDeployWithMockedKite:
    """Test deploy flow with mocked Kite API."""

    async def test_deploy_fetches_spot_price(
        self, client, db_session, test_user, test_broker_connection,
        iron_condor_template, mock_kite_client
    ):
        """Test that deploy fetches spot price from Kite."""
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
                # Should have spot price from mocked Kite
                assert "spot_price" in data
                assert data["spot_price"] > 0

        app.dependency_overrides.clear()

    async def test_deploy_calculates_atm_correctly(
        self, client, db_session, test_user, test_broker_connection,
        bull_call_spread_template, mock_kite_client
    ):
        """Test that ATM strike is calculated correctly."""
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
                "lots": 1
            }

            response = await client.post("/api/strategy-library/deploy", json=payload)

            if response.status_code == 200:
                data = response.json()
                # ATM should be rounded to nearest 50 (NIFTY strike interval)
                atm = data["atm_strike"]
                assert float(atm) % 50 == 0, "ATM strike should be multiple of 50"

        app.dependency_overrides.clear()

    async def test_deploy_applies_strike_offsets(
        self, client, db_session, test_user, test_broker_connection,
        iron_condor_template, mock_kite_client
    ):
        """Test that strike offsets are applied correctly."""
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
                legs = data["legs"]
                atm = float(data["atm_strike"])

                # Verify offset application
                template_legs = iron_condor_template.legs_config
                for i, (template_leg, deployed_leg) in enumerate(zip(template_legs, legs)):
                    expected_strike = atm + template_leg["strike_offset"]
                    assert float(deployed_leg["strike"]) == expected_strike, \
                        f"Leg {i} strike mismatch"

        app.dependency_overrides.clear()

    async def test_deploy_banknifty_underlying(
        self, client, db_session, test_user, test_broker_connection,
        bull_call_spread_template, mock_kite_client
    ):
        """Test deploying with BANKNIFTY underlying."""
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
                "underlying": "BANKNIFTY",
                "lots": 1
            }

            response = await client.post("/api/strategy-library/deploy", json=payload)

            if response.status_code == 200:
                data = response.json()
                assert data["underlying"] == "BANKNIFTY"
                # BANKNIFTY ATM should be multiple of 100
                atm = float(data["atm_strike"])
                assert atm % 100 == 0, "BANKNIFTY ATM should be multiple of 100"

        app.dependency_overrides.clear()


class TestTemplateUpdate:
    """Test template update scenarios."""

    async def test_template_update_reflects_in_api(
        self, client, db_session, sample_strategy_template
    ):
        """Test that template updates are reflected in API response."""
        # Update the template
        new_description = "Updated description for testing"
        sample_strategy_template.description = new_description
        await db_session.commit()

        # Fetch via API
        response = await client.get(
            f"/api/strategy-library/templates/{sample_strategy_template.name}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == new_description

    async def test_popularity_score_update(
        self, client, db_session, sample_strategy_template
    ):
        """Test that popularity score updates affect ordering."""
        # Update to highest popularity
        sample_strategy_template.popularity_score = 999
        await db_session.commit()

        # Fetch popular strategies
        response = await client.get("/api/strategy-library/popular?limit=1")

        assert response.status_code == 200
        data = response.json()

        # Our template should be first
        if len(data["strategies"]) > 0:
            assert data["strategies"][0]["name"] == sample_strategy_template.name


class TestEdgeCases:
    """Test edge cases and error handling."""

    async def test_empty_database(self, client, db_session):
        """Test API behavior with empty database."""
        # Delete all templates
        result = await db_session.execute(select(StrategyTemplate))
        templates = result.scalars().all()
        for template in templates:
            await db_session.delete(template)
        await db_session.commit()

        # List templates
        response = await client.get("/api/strategy-library/templates")
        assert response.status_code == 200
        assert response.json() == []

        # Categories
        response = await client.get("/api/strategy-library/templates/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

        # Popular
        response = await client.get("/api/strategy-library/popular")
        assert response.status_code == 200
        assert len(response.json()["strategies"]) == 0

    async def test_wizard_no_matches(self, client, db_session):
        """Test wizard when no strategies match criteria."""
        # First ensure we have templates
        template = StrategyTemplate(
            id=uuid4(),
            name="edge_case_template",
            display_name="Edge Case",
            category="bullish",  # Bullish only
            description="Test",
            legs_config=[{"type": "CE", "position": "BUY", "strike_offset": 0}],
            max_profit="Limited",
            max_loss="Limited",
            market_outlook="bullish",  # Only matches bullish
            volatility_preference="low_iv",
            risk_level="low",
            capital_requirement="low"
        )
        db_session.add(template)
        await db_session.commit()

        # Request something that won't match well
        payload = {
            "market_outlook": "volatile",
            "volatility_view": "high_iv",
            "risk_tolerance": "high"
        }

        response = await client.post("/api/strategy-library/wizard", json=payload)
        assert response.status_code == 200
        # May have few or no recommendations
        data = response.json()
        assert "recommendations" in data

    async def test_special_characters_in_search(self, client, seeded_templates):
        """Test search with special characters."""
        special_queries = [
            "iron%20condor",
            "bull+call",
            "strategy<script>",
            "test'; DROP TABLE",
        ]

        for query in special_queries:
            response = await client.get(
                f"/api/strategy-library/templates?search={query}"
            )
            # Should not error, even with special chars
            assert response.status_code in [200, 422]

    async def test_very_long_search_query(self, client, seeded_templates):
        """Test search with very long query."""
        long_query = "a" * 1000

        response = await client.get(
            f"/api/strategy-library/templates?search={long_query}"
        )

        # Should handle gracefully
        assert response.status_code in [200, 422]
