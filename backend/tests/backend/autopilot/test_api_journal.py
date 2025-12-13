"""
Test suite for AutoPilot Phase 4 Trade Journal API endpoints.

Tests cover:
- GET /autopilot/journal - List trade journal entries with filters
- GET /autopilot/journal/stats - Get journal statistics
- GET /autopilot/journal/export - Export trades to CSV
- GET /autopilot/journal/{id} - Get trade details
- PUT /autopilot/journal/{id} - Update trade (notes/tags)
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.autopilot import AutoPilotTradeJournal, ExitReason
from app.models.users import User


# ============================================================================
# TEST CLASS: Trade Journal Listing
# ============================================================================

class TestTradeJournalList:
    """Tests for GET /autopilot/journal endpoint."""

    @pytest.mark.asyncio
    async def test_list_trades_empty(self, db_session, test_user):
        """Test listing trades when none exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["data"] == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_with_data(self, db_session, test_user, test_journal_entries):
        """Test listing trades returns all entries."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_filter_by_date_range(self, db_session, test_user, test_journal_entries):
        """Test filtering trades by date range."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/autopilot/journal?start_date={start}&end_date={end}"
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_filter_by_underlying(self, db_session, test_user, test_journal_entries):
        """Test filtering trades by underlying."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal?underlying=NIFTY")

            assert response.status_code == 200
            data = response.json()
            for trade in data["data"]:
                assert trade.get("underlying") == "NIFTY"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_filter_by_exit_reason(self, db_session, test_user, test_journal_entries):
        """Test filtering trades by exit reason."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal?exit_reason=target_hit")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_filter_by_tags(self, db_session, test_user, test_trade_journal_in_db):
        """Test filtering trades by tags."""
        # Add tags to test trade
        test_trade_journal_in_db.tags = ["iron_condor", "weekly"]
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
                response = await client.get("/api/v1/autopilot/journal?tags=iron_condor")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_filter_open_trades(self, db_session, test_user, test_open_trade):
        """Test filtering only open trades."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal?is_open=true")

            assert response.status_code == 200
            data = response.json()
            for trade in data["data"]:
                assert trade.get("exit_time") is None or trade.get("is_open") is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_filter_by_pnl_range(self, db_session, test_user, test_journal_entries):
        """Test filtering trades by P&L range."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal?min_pnl=0&max_pnl=10000")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_trades_pagination(self, db_session, test_user, test_journal_entries):
        """Test pagination of trades."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal?page=1&page_size=5")

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 5
            assert len(data["data"]) <= 5
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Trade Journal Statistics
# ============================================================================

class TestTradeJournalStats:
    """Tests for GET /autopilot/journal/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, db_session, test_user):
        """Test getting stats when no trades exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal/stats")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, db_session, test_user, test_journal_entries):
        """Test getting stats with trade data."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal/stats")

            assert response.status_code == 200
            data = response.json()
            # Should contain stats like total_trades, win_rate, etc.
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_stats_filtered_by_date(self, db_session, test_user, test_journal_entries):
        """Test getting stats filtered by date range."""
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
                    f"/api/v1/autopilot/journal/stats?start_date={start}&end_date={end}"
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Trade Journal Export
# ============================================================================

class TestTradeJournalExport:
    """Tests for GET /autopilot/journal/export endpoint."""

    @pytest.mark.asyncio
    async def test_export_trades_csv(self, db_session, test_user, test_journal_entries):
        """Test exporting trades to CSV."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal/export?format=csv")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert data["data"]["format"] == "csv"
            assert "content" in data["data"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_trades_filtered(self, db_session, test_user, test_journal_entries):
        """Test exporting trades with filters."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    f"/api/v1/autopilot/journal/export?start_date={start}&underlying=NIFTY"
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_trades_empty(self, db_session, test_user):
        """Test exporting when no trades exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal/export")

            assert response.status_code == 200
            data = response.json()
            # Should return empty or header-only CSV
            assert "data" in data
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Get Trade Details
# ============================================================================

class TestGetTrade:
    """Tests for GET /autopilot/journal/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_trade_success(self, db_session, test_user, test_trade_journal_in_db):
        """Test getting trade details."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/journal/{test_trade_journal_in_db.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["id"] == test_trade_journal_in_db.id
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_trade_not_found(self, db_session, test_user):
        """Test getting non-existent trade returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal/99999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_trade_other_user(self, db_session, test_user, test_trade_journal_in_db):
        """Test getting another user's trade is forbidden."""
        # Change trade ownership
        test_trade_journal_in_db.user_id = test_user.id + 100
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
                response = await client.get(f"/api/v1/autopilot/journal/{test_trade_journal_in_db.id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_trade_with_leg_snapshots(self, db_session, test_user, test_trade_journal_in_db):
        """Test getting trade with leg snapshots."""
        # Ensure trade has leg snapshots
        test_trade_journal_in_db.entry_leg_snapshot = [
            {"strike": 25000, "option_type": "CE", "price": 150}
        ]
        await db_session.commit()
        await db_session.refresh(test_trade_journal_in_db)

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/journal/{test_trade_journal_in_db.id}")

            assert response.status_code == 200
            data = response.json()
            assert "entry_leg_snapshot" in data["data"]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Update Trade
# ============================================================================

class TestUpdateTrade:
    """Tests for PUT /autopilot/journal/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_trade_notes(self, db_session, test_user, test_trade_journal_in_db):
        """Test updating trade notes."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {
            "notes": "Updated notes for this trade"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    f"/api/v1/autopilot/journal/{test_trade_journal_in_db.id}",
                    json=update_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["notes"] == "Updated notes for this trade"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_trade_tags(self, db_session, test_user, test_trade_journal_in_db):
        """Test updating trade tags."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {
            "tags": ["iron_condor", "weekly", "high_vix"]
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    f"/api/v1/autopilot/journal/{test_trade_journal_in_db.id}",
                    json=update_data
                )

            assert response.status_code == 200
            data = response.json()
            assert "iron_condor" in data["data"]["tags"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_trade_notes_and_tags(self, db_session, test_user, test_trade_journal_in_db):
        """Test updating both notes and tags."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {
            "notes": "Market was volatile",
            "tags": ["volatile", "adjusted"]
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    f"/api/v1/autopilot/journal/{test_trade_journal_in_db.id}",
                    json=update_data
                )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["notes"] == "Market was volatile"
            assert "volatile" in data["data"]["tags"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_trade_not_found(self, db_session, test_user):
        """Test updating non-existent trade returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {"notes": "Test"}

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    "/api/v1/autopilot/journal/99999",
                    json=update_data
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_update_trade_other_user(self, db_session, test_user, test_trade_journal_in_db):
        """Test updating another user's trade is forbidden."""
        test_trade_journal_in_db.user_id = test_user.id + 100
        await db_session.commit()

        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        update_data = {"notes": "Stealing"}

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.put(
                    f"/api/v1/autopilot/journal/{test_trade_journal_in_db.id}",
                    json=update_data
                )

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Trade Journal Authentication
# ============================================================================

class TestTradeJournalAuthentication:
    """Tests for trade journal endpoint authentication."""

    @pytest.mark.asyncio
    async def test_list_trades_requires_auth(self, db_session):
        """Test that listing trades requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_export_requires_auth(self, db_session):
        """Test that export requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/journal/export")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Trade Journal Multiple Filters
# ============================================================================

class TestTradeJournalMultipleFilters:
    """Tests for combining multiple filters."""

    @pytest.mark.asyncio
    async def test_filter_date_and_underlying(self, db_session, test_user, test_journal_entries):
        """Test filtering by both date range and underlying."""
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
                    f"/api/v1/autopilot/journal?start_date={start}&end_date={end}&underlying=NIFTY"
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_filter_pnl_and_exit_reason(self, db_session, test_user, test_journal_entries):
        """Test filtering by P&L range and exit reason."""
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
                    "/api/v1/autopilot/journal?min_pnl=1000&exit_reason=target_hit"
                )

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_filter_with_pagination(self, db_session, test_user, test_journal_entries):
        """Test combining filters with pagination."""
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
                    "/api/v1/autopilot/journal?underlying=NIFTY&page=1&page_size=10"
                )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 10
        finally:
            app.dependency_overrides.clear()
