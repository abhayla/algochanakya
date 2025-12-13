"""
Test suite for AutoPilot Phase 4 Reports API endpoints.

Tests cover:
- GET /autopilot/reports - List reports
- POST /autopilot/reports/generate - Generate a new report
- GET /autopilot/reports/{id} - Get report details
- GET /autopilot/reports/{id}/download - Download report file
- DELETE /autopilot/reports/{id} - Delete a report
- GET /autopilot/reports/tax-summary/{year} - Get tax summary
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.autopilot import AutoPilotReport, ReportType, ReportFormat
from app.models.users import User


# ============================================================================
# TEST CLASS: Report Listing
# ============================================================================

class TestReportList:
    """Tests for GET /autopilot/reports endpoint."""

    @pytest.mark.asyncio
    async def test_list_reports_empty(self, db_session, test_user):
        """Test listing reports when none exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["data"] == []
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_reports_with_data(self, db_session, test_user, test_report):
        """Test listing reports returns all available reports."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_reports_filter_by_type(self, db_session, test_user, test_report):
        """Test filtering reports by type."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports?report_type=monthly_performance")

            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_reports_pagination(self, db_session, test_user, test_report):
        """Test pagination of reports."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports?page=1&page_size=10")

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 10
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Generate Report
# ============================================================================

class TestGenerateReport:
    """Tests for POST /autopilot/reports/generate endpoint."""

    @pytest.mark.asyncio
    async def test_generate_monthly_report(self, db_session, test_user):
        """Test generating a monthly performance report."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        report_data = {
            "report_type": "monthly_performance",
            "name": "December 2024 Performance",
            "start_date": "2024-12-01",
            "end_date": "2024-12-31",
            "format": "pdf"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/reports/generate",
                    json=report_data
                )

            assert response.status_code == 201
            data = response.json()
            assert data["data"]["name"] == "December 2024 Performance"
            assert data["data"]["report_type"] == "monthly_performance"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_strategy_report(self, db_session, test_user, test_autopilot_strategy):
        """Test generating a strategy performance report."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        report_data = {
            "report_type": "strategy_performance",
            "name": f"Strategy {test_autopilot_strategy.id} Report",
            "strategy_id": test_autopilot_strategy.id,
            "format": "csv"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/reports/generate",
                    json=report_data
                )

            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_tax_report(self, db_session, test_user):
        """Test generating a tax report."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        report_data = {
            "report_type": "tax_report",
            "name": "FY 2024-25 Tax Report",
            "start_date": "2024-04-01",
            "end_date": "2025-03-31",
            "format": "pdf"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/reports/generate",
                    json=report_data
                )

            assert response.status_code == 201
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_report_missing_required_fields(self, db_session, test_user):
        """Test generating report without required fields fails."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        report_data = {
            "name": "Test Report"
            # Missing report_type and dates
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/reports/generate",
                    json=report_data
                )

            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_report_different_formats(self, db_session, test_user):
        """Test generating reports in different formats."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        formats = ["csv", "pdf", "excel"]

        for fmt in formats:
            report_data = {
                "report_type": "monthly_performance",
                "name": f"Test Report {fmt}",
                "start_date": "2024-12-01",
                "end_date": "2024-12-31",
                "format": fmt
            }

            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/api/v1/autopilot/reports/generate",
                        json=report_data
                    )

                # Should succeed or return 422 if format not supported
                assert response.status_code in [201, 422], f"Failed for format {fmt}"
            finally:
                app.dependency_overrides.clear()
                app.dependency_overrides[get_db] = override_get_db
                app.dependency_overrides[get_current_user] = override_get_current_user

        app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Get Report Details
# ============================================================================

class TestGetReport:
    """Tests for GET /autopilot/reports/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_report_success(self, db_session, test_user, test_report):
        """Test getting report details."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/autopilot/reports/{test_report.id}")

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["id"] == test_report.id
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_report_not_found(self, db_session, test_user):
        """Test getting non-existent report returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports/99999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_report_other_user(self, db_session, test_user, test_report):
        """Test getting another user's report is forbidden."""
        test_report.user_id = test_user.id + 100
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
                response = await client.get(f"/api/v1/autopilot/reports/{test_report.id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Download Report
# ============================================================================

class TestDownloadReport:
    """Tests for GET /autopilot/reports/{id}/download endpoint."""

    @pytest.mark.asyncio
    async def test_download_report_not_ready(self, db_session, test_user, test_report):
        """Test downloading report that is not ready."""
        test_report.is_ready = False
        test_report.file_path = None
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
                response = await client.get(f"/api/v1/autopilot/reports/{test_report.id}/download")

            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_download_report_not_found(self, db_session, test_user):
        """Test downloading non-existent report returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports/99999/download")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Delete Report
# ============================================================================

class TestDeleteReport:
    """Tests for DELETE /autopilot/reports/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_report_success(self, db_session, test_user, test_report):
        """Test deleting a report."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/autopilot/reports/{test_report.id}")

            assert response.status_code == 204
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_report_not_found(self, db_session, test_user):
        """Test deleting non-existent report returns 404."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete("/api/v1/autopilot/reports/99999")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_other_user_report(self, db_session, test_user, test_report):
        """Test deleting another user's report is forbidden."""
        test_report.user_id = test_user.id + 100
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
                response = await client.delete(f"/api/v1/autopilot/reports/{test_report.id}")

            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Tax Summary
# ============================================================================

class TestTaxSummary:
    """Tests for GET /autopilot/reports/tax-summary/{year} endpoint."""

    @pytest.mark.asyncio
    async def test_get_tax_summary_success(self, db_session, test_user, test_journal_entries):
        """Test getting tax summary."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports/tax-summary/2024-25")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_tax_summary_invalid_year_format(self, db_session, test_user):
        """Test tax summary with invalid year format."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports/tax-summary/2024")

            assert response.status_code == 400
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_tax_summary_empty(self, db_session, test_user):
        """Test tax summary when no trades exist."""
        async def override_get_db():
            yield db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports/tax-summary/2024-25")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# TEST CLASS: Reports Authentication
# ============================================================================

class TestReportsAuthentication:
    """Tests for reports endpoint authentication."""

    @pytest.mark.asyncio
    async def test_list_reports_requires_auth(self, db_session):
        """Test that listing reports requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_generate_report_requires_auth(self, db_session):
        """Test that generating report requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        report_data = {
            "report_type": "monthly_performance",
            "name": "Test",
            "start_date": "2024-12-01",
            "end_date": "2024-12-31"
        }

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/autopilot/reports/generate",
                    json=report_data
                )

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_tax_summary_requires_auth(self, db_session):
        """Test that tax summary requires authentication."""
        async def override_get_db():
            yield db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/autopilot/reports/tax-summary/2024-25")

            assert response.status_code in [401, 403, 422]
        finally:
            app.dependency_overrides.clear()
