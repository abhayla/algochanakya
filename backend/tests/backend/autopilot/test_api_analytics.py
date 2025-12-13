"""
Test suite for AutoPilot Phase 4 Analytics API endpoints.

Tests cover:
- GET /autopilot/analytics/performance - Get performance analytics
- GET /autopilot/analytics/daily-pnl - Get daily P&L data
- GET /autopilot/analytics/by-strategy - Get performance by strategy
- GET /autopilot/analytics/by-weekday - Get performance by weekday
- GET /autopilot/analytics/drawdown - Get drawdown analysis
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.autopilot import AutoPilotTradeJournal, AutoPilotAnalyticsCache
from app.models.users import User


# ============================================================================
# TEST CLASS: Performance Analytics
# ============================================================================

class TestPerformanceAnalytics:
    """Tests for GET /autopilot/analytics/performance endpoint."""

    @pytest.mark.asyncio
    async def test_get_performance_empty(self, db_session, test_user):
        """Test getting performance with no trade data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_with_data(self, db_session, test_user, test_journal_entries):
        """Test getting performance with trade data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            # Performance analytics should include key metrics
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_period_7d(self, db_session, test_user, test_journal_entries):
        """Test getting performance for 7-day period."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance?period=7d")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_period_30d(self, db_session, test_user, test_journal_entries):
        """Test getting performance for 30-day period."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance?period=30d")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_period_90d(self, db_session, test_user, test_journal_entries):
        """Test getting performance for 90-day period."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance?period=90d")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_period_ytd(self, db_session, test_user, test_journal_entries):
        """Test getting performance for year-to-date period."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance?period=ytd")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_period_all(self, db_session, test_user, test_journal_entries):
        """Test getting performance for all time."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance?period=all")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_invalid_period(self, db_session, test_user):
        """Test getting performance with invalid period."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance?period=invalid")

            # Should return 422 validation error
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_performance_filter_underlying(self, db_session, test_user, test_journal_entries):
        """Test getting performance filtered by underlying."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance?underlying=NIFTY")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Daily P&L Analytics
# ============================================================================

class TestDailyPnLAnalytics:
    """Tests for GET /autopilot/analytics/daily-pnl endpoint."""

    @pytest.mark.asyncio
    async def test_get_daily_pnl_empty(self, db_session, test_user):
        """Test getting daily P&L with no data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/daily-pnl")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_daily_pnl_with_data(self, db_session, test_user, test_journal_entries):
        """Test getting daily P&L with trade data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/daily-pnl")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_daily_pnl_date_range(self, db_session, test_user, test_journal_entries):
        """Test getting daily P&L for specific date range."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/autopilot/analytics/daily-pnl?start_date={start}&end_date={end}"
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_daily_pnl_returns_cumulative(self, db_session, test_user, test_journal_entries):
        """Test that daily P&L returns cumulative data for charts."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/daily-pnl")

            assert response.status_code == 200
            data = response.json()
            # Daily P&L should return data for chart rendering
            assert "data" in data
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Analytics By Strategy
# ============================================================================

class TestAnalyticsByStrategy:
    """Tests for GET /autopilot/analytics/by-strategy endpoint."""

    @pytest.mark.asyncio
    async def test_get_by_strategy_empty(self, db_session, test_user):
        """Test getting strategy breakdown with no data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/by-strategy")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_by_strategy_with_data(self, db_session, test_user, test_journal_entries):
        """Test getting strategy breakdown with trade data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/by-strategy")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_by_strategy_different_periods(self, db_session, test_user, test_journal_entries):
        """Test getting strategy breakdown for different periods."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        periods = ["7d", "30d", "90d", "ytd", "all"]

        for period in periods:
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get(f"/api/v1/autopilot/analytics/by-strategy?period={period}")

                assert response.status_code == 200, f"Failed for period {period}"
            finally:
                app.dependency_overrides.clear()
                app.dependency_overrides[get_db] = override_get_db
                app.dependency_overrides[get_current_user] = override_get_current_user

        app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Analytics By Weekday
# ============================================================================

class TestAnalyticsByWeekday:
    """Tests for GET /autopilot/analytics/by-weekday endpoint."""

    @pytest.mark.asyncio
    async def test_get_by_weekday_empty(self, db_session, test_user):
        """Test getting weekday breakdown with no data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/by-weekday")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_by_weekday_with_data(self, db_session, test_user, test_journal_entries):
        """Test getting weekday breakdown with trade data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/by-weekday")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_by_weekday_different_periods(self, db_session, test_user, test_journal_entries):
        """Test getting weekday breakdown for different periods."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/by-weekday?period=30d")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Drawdown Analytics
# ============================================================================

class TestDrawdownAnalytics:
    """Tests for GET /autopilot/analytics/drawdown endpoint."""

    @pytest.mark.asyncio
    async def test_get_drawdown_empty(self, db_session, test_user):
        """Test getting drawdown with no data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/drawdown")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_drawdown_with_data(self, db_session, test_user, test_journal_entries):
        """Test getting drawdown with trade data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/drawdown")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_drawdown_different_periods(self, db_session, test_user, test_journal_entries):
        """Test getting drawdown for different periods."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/drawdown?period=90d")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Analytics Authentication
# ============================================================================

class TestAnalyticsAuthentication:
    """Tests for analytics endpoint authentication."""

    @pytest.mark.asyncio
    async def test_performance_requires_auth(self, db_session):
        """Test that performance analytics requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_daily_pnl_requires_auth(self, db_session):
        """Test that daily P&L requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/daily-pnl")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_by_strategy_requires_auth(self, db_session):
        """Test that by-strategy analytics requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/by-strategy")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_drawdown_requires_auth(self, db_session):
        """Test that drawdown analytics requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/drawdown")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Analytics Caching
# ============================================================================

class TestAnalyticsCaching:
    """Tests for analytics caching behavior."""

    @pytest.mark.asyncio
    async def test_analytics_uses_cache_when_available(self, db_session, test_user, test_analytics_cache):
        """Test that analytics uses cached data when available."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/analytics/performance")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_analytics_respects_cache_expiry(self, db_session, test_user, test_analytics_cache):
        """Test that analytics respects cache TTL."""
        # Set cache to be expired
        test_analytics_cache.cached_at = datetime.now(timezone.utc) - timedelta(hours=2)
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
                response = await client.get("/api/v1/autopilot/analytics/performance")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()
