"""
Phase 4 Schema Tests - AutoPilot Feature

Tests for Phase 4 Pydantic schemas:
- Template schemas (TemplateListItem, TemplateResponse, TemplateCreateRequest, etc.)
- Trade Journal schemas (TradeJournalListItem, TradeJournalResponse, etc.)
- Analytics schemas (PerformanceMetrics, AnalyticsSummary, etc.)
- Report schemas (ReportListItem, ReportResponse, ReportGenerateRequest, etc.)
- Backtest schemas (BacktestListItem, BacktestResponse, BacktestCreateRequest)
- Sharing schemas (StrategyShareRequest, StrategyShareResponse, SharedStrategyResponse)
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.autopilot import (
    # Phase 4 Enums
    ExitReason, TemplateCategory, ReportType, ReportFormat,
    BacktestStatus, ShareMode, MarketOutlook, IVEnvironment,
    # Template schemas
    TemplateEducationalContent, TemplateListItem, TemplateResponse,
    TemplateCreateRequest, TemplateUpdateRequest, TemplateDeployRequest,
    TemplateRatingRequest, TemplateRatingResponse,
    # Trade Journal schemas
    MarketConditions, TradeJournalLegSnapshot, TradeJournalListItem,
    TradeJournalResponse, TradeJournalUpdateRequest, TradeJournalExportRequest,
    # Analytics schemas
    PerformanceMetrics, DailyPnL, WeeklyPnL, MonthlyPnL,
    StrategyPerformance, WeekdayPerformance, AnalyticsSummary,
    AnalyticsPerformanceResponse,
    # Report schemas
    ReportListItem, ReportResponse, ReportGenerateRequest, TaxSummary,
    # Backtest schemas
    BacktestListItem, BacktestResponse, BacktestCreateRequest,
    # Sharing schemas
    StrategyShareRequest, StrategyShareResponse, SharedStrategyResponse,
    StrategyCloneFromSharedRequest,
    # Existing enums for validation
    ExecutionMode
)


# =============================================================================
# PHASE 4 ENUM TESTS
# =============================================================================

class TestPhase4SchemaEnums:
    """Test Phase 4 schema enums."""

    def test_exit_reason_enum_values(self):
        """Test ExitReason enum has all expected values."""
        assert ExitReason.target_hit.value == "target_hit"
        assert ExitReason.stop_loss.value == "stop_loss"
        assert ExitReason.trailing_stop.value == "trailing_stop"
        assert ExitReason.kill_switch.value == "kill_switch"

    def test_template_category_enum_values(self):
        """Test TemplateCategory enum values."""
        assert TemplateCategory.income.value == "income"
        assert TemplateCategory.directional.value == "directional"
        assert TemplateCategory.volatility.value == "volatility"
        assert TemplateCategory.custom.value == "custom"

    def test_report_type_enum_values(self):
        """Test ReportType enum values."""
        assert ReportType.daily.value == "daily"
        assert ReportType.weekly.value == "weekly"
        assert ReportType.monthly.value == "monthly"
        assert ReportType.tax.value == "tax"

    def test_backtest_status_enum_values(self):
        """Test BacktestStatus enum values."""
        assert BacktestStatus.pending.value == "pending"
        assert BacktestStatus.running.value == "running"
        assert BacktestStatus.completed.value == "completed"
        assert BacktestStatus.failed.value == "failed"

    def test_share_mode_enum_values(self):
        """Test ShareMode enum values."""
        assert ShareMode.private.value == "private"
        assert ShareMode.link.value == "link"
        assert ShareMode.public.value == "public"

    def test_market_outlook_enum_values(self):
        """Test MarketOutlook enum values."""
        assert MarketOutlook.bullish.value == "bullish"
        assert MarketOutlook.bearish.value == "bearish"
        assert MarketOutlook.neutral.value == "neutral"
        assert MarketOutlook.volatile.value == "volatile"

    def test_iv_environment_enum_values(self):
        """Test IVEnvironment enum values."""
        assert IVEnvironment.high.value == "high"
        assert IVEnvironment.low.value == "low"
        assert IVEnvironment.normal.value == "normal"


# =============================================================================
# TEMPLATE SCHEMA TESTS
# =============================================================================

class TestTemplateEducationalContent:
    """Tests for TemplateEducationalContent schema."""

    def test_create_educational_content(self):
        """Test creating educational content."""
        content = TemplateEducationalContent(
            when_to_use="Best for neutral markets",
            pros=["Limited risk", "Time decay"],
            cons=["Limited profit"],
            common_mistakes=["Not adjusting when needed"],
            exit_rules=["Exit at 50% profit"],
            adjustments=["Roll when delta > 0.3"]
        )
        assert content.when_to_use == "Best for neutral markets"
        assert len(content.pros) == 2
        assert len(content.cons) == 1

    def test_educational_content_defaults(self):
        """Test educational content default values."""
        content = TemplateEducationalContent()
        assert content.when_to_use is None
        assert content.pros == []
        assert content.cons == []


class TestTemplateListItem:
    """Tests for TemplateListItem schema."""

    def test_create_template_list_item(self):
        """Test creating template list item."""
        item = TemplateListItem(
            id=1,
            name="Iron Condor",
            description="Neutral strategy",
            category="income",
            underlying="NIFTY",
            position_type="intraday",
            risk_level="medium",
            market_outlook="neutral",
            iv_environment="normal",
            expected_return_pct=Decimal("2.5"),
            max_risk_pct=Decimal("5.0"),
            usage_count=100,
            avg_rating=Decimal("4.5"),
            rating_count=50,
            is_system=True,
            is_public=True,
            tags=["neutral", "income"],
            created_at=datetime.utcnow()
        )
        assert item.id == 1
        assert item.name == "Iron Condor"
        assert item.usage_count == 100

    def test_template_list_item_optional_fields(self):
        """Test template list item with minimal fields."""
        item = TemplateListItem(
            id=1,
            name="Test Template",
            description=None,
            category=None,
            underlying=None,
            position_type=None,
            risk_level=None,
            market_outlook=None,
            iv_environment=None,
            expected_return_pct=None,
            max_risk_pct=None,
            usage_count=0,
            avg_rating=None,
            rating_count=0,
            is_system=False,
            is_public=False,
            created_at=datetime.utcnow()
        )
        assert item.name == "Test Template"
        assert item.avg_rating is None


class TestTemplateCreateRequest:
    """Tests for TemplateCreateRequest schema."""

    def test_create_template_request_valid(self):
        """Test valid template create request."""
        request = TemplateCreateRequest(
            name="My Strategy Template",
            description="A test template",
            category="income",
            underlying="NIFTY",
            position_type="intraday",
            risk_level="medium",
            tags=["test", "custom"],
            strategy_config={
                "legs_config": [{"id": "leg_1", "contract_type": "CE"}]
            },
            is_public=False
        )
        assert request.name == "My Strategy Template"
        assert len(request.tags) == 2

    def test_create_template_request_name_too_short(self):
        """Test template create request with empty name."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateCreateRequest(
                name="",
                strategy_config={}
            )
        assert "min_length" in str(exc_info.value)

    def test_create_template_request_name_too_long(self):
        """Test template create request with name too long."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateCreateRequest(
                name="x" * 101,  # 101 characters
                strategy_config={}
            )
        assert "max_length" in str(exc_info.value)


class TestTemplateDeployRequest:
    """Tests for TemplateDeployRequest schema."""

    def test_deploy_request_valid(self):
        """Test valid deploy request."""
        request = TemplateDeployRequest(
            name="My Deployed Strategy",
            lots=2,
            expiry_type="current_week",
            execution_mode=ExecutionMode.auto,
            activate_immediately=True
        )
        assert request.lots == 2
        assert request.activate_immediately is True

    def test_deploy_request_lots_validation(self):
        """Test deploy request lots validation."""
        with pytest.raises(ValidationError):
            TemplateDeployRequest(
                lots=0  # Must be >= 1
            )

        with pytest.raises(ValidationError):
            TemplateDeployRequest(
                lots=51  # Must be <= 50
            )


class TestTemplateRatingRequest:
    """Tests for TemplateRatingRequest schema."""

    def test_rating_request_valid(self):
        """Test valid rating request."""
        request = TemplateRatingRequest(
            rating=5,
            review="Great strategy!"
        )
        assert request.rating == 5

    def test_rating_request_invalid_rating(self):
        """Test rating request with invalid rating value."""
        with pytest.raises(ValidationError):
            TemplateRatingRequest(rating=0)

        with pytest.raises(ValidationError):
            TemplateRatingRequest(rating=6)


# =============================================================================
# TRADE JOURNAL SCHEMA TESTS
# =============================================================================

class TestMarketConditions:
    """Tests for MarketConditions schema."""

    def test_create_market_conditions(self):
        """Test creating market conditions."""
        conditions = MarketConditions(
            vix_at_entry=15.5,
            vix_at_exit=14.2,
            spot_at_entry=Decimal("25000"),
            spot_at_exit=Decimal("25100"),
            iv_rank=35.5,
            trend_direction="sideways"
        )
        assert conditions.vix_at_entry == 15.5
        assert conditions.spot_at_entry == Decimal("25000")

    def test_market_conditions_defaults(self):
        """Test market conditions with defaults."""
        conditions = MarketConditions()
        assert conditions.vix_at_entry is None
        assert conditions.spot_at_entry is None


class TestTradeJournalLegSnapshot:
    """Tests for TradeJournalLegSnapshot schema."""

    def test_create_leg_snapshot(self):
        """Test creating leg snapshot."""
        leg = TradeJournalLegSnapshot(
            leg_id="leg_1",
            contract_type="CE",
            transaction_type="SELL",
            strike=Decimal("25000"),
            expiry=date.today() + timedelta(days=7),
            entry_price=Decimal("100"),
            exit_price=Decimal("75"),
            quantity=25
        )
        assert leg.leg_id == "leg_1"
        assert leg.entry_price == Decimal("100")


class TestTradeJournalListItem:
    """Tests for TradeJournalListItem schema."""

    def test_create_journal_list_item(self):
        """Test creating journal list item."""
        item = TradeJournalListItem(
            id=1,
            strategy_id=100,
            strategy_name="Iron Condor",
            underlying="NIFTY",
            position_type="intraday",
            entry_time=datetime.utcnow(),
            exit_time=datetime.utcnow(),
            holding_duration_minutes=180,
            lots=1,
            gross_pnl=Decimal("2500"),
            net_pnl=Decimal("2400"),
            pnl_percentage=Decimal("4.8"),
            exit_reason="target_hit",
            tags=["profitable"],
            is_open=False
        )
        assert item.strategy_name == "Iron Condor"
        assert item.is_open is False


class TestTradeJournalUpdateRequest:
    """Tests for TradeJournalUpdateRequest schema."""

    def test_update_request_notes(self):
        """Test update request with notes."""
        request = TradeJournalUpdateRequest(
            notes="Updated trade notes",
            tags=["review", "profitable"]
        )
        assert request.notes == "Updated trade notes"
        assert len(request.tags) == 2


class TestTradeJournalExportRequest:
    """Tests for TradeJournalExportRequest schema."""

    def test_export_request_valid(self):
        """Test valid export request."""
        request = TradeJournalExportRequest(
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
            underlying="NIFTY",
            format=ReportFormat.csv
        )
        assert request.format == ReportFormat.csv


# =============================================================================
# ANALYTICS SCHEMA TESTS
# =============================================================================

class TestPerformanceMetrics:
    """Tests for PerformanceMetrics schema."""

    def test_create_performance_metrics(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            win_rate=65.0,
            gross_pnl=Decimal("150000"),
            net_pnl=Decimal("140000"),
            total_brokerage=Decimal("10000"),
            avg_win=Decimal("3000"),
            avg_loss=Decimal("1500"),
            profit_factor=2.1,
            max_drawdown=Decimal("20000"),
            max_drawdown_pct=4.0,
            sharpe_ratio=1.85,
            expectancy=Decimal("1400")
        )
        assert metrics.total_trades == 100
        assert metrics.win_rate == 65.0
        assert metrics.sharpe_ratio == 1.85


class TestDailyPnL:
    """Tests for DailyPnL schema."""

    def test_create_daily_pnl(self):
        """Test creating daily P&L entry."""
        pnl = DailyPnL(
            date=date.today(),
            pnl=Decimal("2500"),
            trades=5,
            cumulative_pnl=Decimal("50000")
        )
        assert pnl.pnl == Decimal("2500")
        assert pnl.trades == 5


class TestAnalyticsSummary:
    """Tests for AnalyticsSummary schema."""

    def test_create_analytics_summary(self):
        """Test creating analytics summary."""
        performance = PerformanceMetrics(
            total_trades=50,
            winning_trades=32,
            losing_trades=18,
            win_rate=64.0,
            gross_pnl=Decimal("100000"),
            net_pnl=Decimal("95000"),
            total_brokerage=Decimal("5000")
        )
        summary = AnalyticsSummary(
            period="30d",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
            performance=performance,
            best_trade=Decimal("8000"),
            worst_trade=Decimal("-3000"),
            avg_trade_pnl=Decimal("1900"),
            avg_holding_minutes=180,
            most_traded_underlying="NIFTY",
            most_profitable_strategy="Iron Condor"
        )
        assert summary.period == "30d"
        assert summary.best_trade == Decimal("8000")


# =============================================================================
# REPORT SCHEMA TESTS
# =============================================================================

class TestReportListItem:
    """Tests for ReportListItem schema."""

    def test_create_report_list_item(self):
        """Test creating report list item."""
        item = ReportListItem(
            id=1,
            report_type="monthly",
            name="November 2024 Report",
            description="Monthly P&L report",
            start_date=date(2024, 11, 1),
            end_date=date(2024, 11, 30),
            format="pdf",
            is_ready=True,
            file_size_bytes=1024000,
            created_at=datetime.utcnow(),
            generated_at=datetime.utcnow()
        )
        assert item.report_type == "monthly"
        assert item.is_ready is True


class TestReportGenerateRequest:
    """Tests for ReportGenerateRequest schema."""

    def test_generate_report_request_valid(self):
        """Test valid report generate request."""
        request = ReportGenerateRequest(
            report_type=ReportType.monthly,
            name="December 2024 Report",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            format=ReportFormat.pdf
        )
        assert request.report_type == ReportType.monthly
        assert request.format == ReportFormat.pdf

    def test_generate_tax_report_request(self):
        """Test tax report generate request."""
        request = ReportGenerateRequest(
            report_type=ReportType.tax,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31)
        )
        assert request.report_type == ReportType.tax


class TestTaxSummary:
    """Tests for TaxSummary schema."""

    def test_create_tax_summary(self):
        """Test creating tax summary."""
        summary = TaxSummary(
            financial_year="2024-25",
            total_turnover=Decimal("25000000"),
            speculative_pnl=Decimal("0"),
            non_speculative_pnl=Decimal("170000"),
            total_brokerage=Decimal("54000"),
            total_taxes_paid=Decimal("25000"),
            net_taxable_income=Decimal("91000"),
            audit_required=False
        )
        assert summary.financial_year == "2024-25"
        assert summary.audit_required is False


# =============================================================================
# BACKTEST SCHEMA TESTS
# =============================================================================

class TestBacktestListItem:
    """Tests for BacktestListItem schema."""

    def test_create_backtest_list_item(self):
        """Test creating backtest list item."""
        item = BacktestListItem(
            id=1,
            name="Iron Condor Backtest",
            description="Testing Iron Condor strategy",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            initial_capital=Decimal("500000"),
            status="completed",
            progress_pct=100,
            total_trades=120,
            win_rate=Decimal("65.0"),
            net_pnl=Decimal("175000"),
            max_drawdown_pct=Decimal("5.6"),
            sharpe_ratio=Decimal("1.85"),
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        assert item.status == "completed"
        assert item.total_trades == 120


class TestBacktestCreateRequest:
    """Tests for BacktestCreateRequest schema."""

    def test_create_backtest_request_valid(self):
        """Test valid backtest create request."""
        request = BacktestCreateRequest(
            name="Test Backtest",
            description="Testing strategy",
            strategy_config={
                "underlying": "NIFTY",
                "legs_config": [{"id": "leg_1"}]
            },
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            initial_capital=Decimal("500000"),
            slippage_pct=Decimal("0.1"),
            charges_per_lot=Decimal("40"),
            data_interval="1min"
        )
        assert request.name == "Test Backtest"
        assert request.initial_capital == Decimal("500000")

    def test_create_backtest_request_name_validation(self):
        """Test backtest create request name validation."""
        with pytest.raises(ValidationError):
            BacktestCreateRequest(
                name="",  # Too short
                strategy_config={},
                start_date=date.today(),
                end_date=date.today()
            )

    def test_create_backtest_request_capital_validation(self):
        """Test backtest create request capital validation."""
        with pytest.raises(ValidationError):
            BacktestCreateRequest(
                name="Test",
                strategy_config={},
                start_date=date.today(),
                end_date=date.today(),
                initial_capital=Decimal("-1000")  # Must be > 0
            )

    def test_create_backtest_request_slippage_validation(self):
        """Test backtest create request slippage validation."""
        with pytest.raises(ValidationError):
            BacktestCreateRequest(
                name="Test",
                strategy_config={},
                start_date=date.today(),
                end_date=date.today(),
                slippage_pct=Decimal("10")  # Must be <= 5
            )


# =============================================================================
# SHARING SCHEMA TESTS
# =============================================================================

class TestStrategyShareRequest:
    """Tests for StrategyShareRequest schema."""

    def test_share_request_link_mode(self):
        """Test share request with link mode."""
        request = StrategyShareRequest(share_mode=ShareMode.link)
        assert request.share_mode == ShareMode.link

    def test_share_request_default_mode(self):
        """Test share request default mode."""
        request = StrategyShareRequest()
        assert request.share_mode == ShareMode.link


class TestStrategyShareResponse:
    """Tests for StrategyShareResponse schema."""

    def test_share_response(self):
        """Test share response."""
        response = StrategyShareResponse(
            share_token="abc123xyz",
            share_url="https://app.example.com/shared/abc123xyz",
            share_mode="link",
            shared_at=datetime.utcnow()
        )
        assert response.share_token == "abc123xyz"
        assert "abc123xyz" in response.share_url


class TestSharedStrategyResponse:
    """Tests for SharedStrategyResponse schema."""

    def test_shared_strategy_response(self):
        """Test shared strategy response."""
        response = SharedStrategyResponse(
            id=1,
            name="Shared Iron Condor",
            description="A shared strategy",
            underlying="NIFTY",
            position_type="intraday",
            legs_config=[{"id": "leg_1", "contract_type": "CE"}],
            entry_conditions={"logic": "AND", "conditions": []},
            adjustment_rules=[],
            risk_settings={"max_loss": 5000},
            author_name="TestUser",
            shared_at=datetime.utcnow(),
            performance_stats={"win_rate": 65.0, "net_pnl": 50000}
        )
        assert response.name == "Shared Iron Condor"
        assert response.performance_stats["win_rate"] == 65.0


class TestStrategyCloneFromSharedRequest:
    """Tests for StrategyCloneFromSharedRequest schema."""

    def test_clone_request_valid(self):
        """Test valid clone request."""
        request = StrategyCloneFromSharedRequest(
            new_name="My Cloned Strategy",
            lots=2
        )
        assert request.new_name == "My Cloned Strategy"
        assert request.lots == 2

    def test_clone_request_lots_validation(self):
        """Test clone request lots validation."""
        with pytest.raises(ValidationError):
            StrategyCloneFromSharedRequest(lots=0)

        with pytest.raises(ValidationError):
            StrategyCloneFromSharedRequest(lots=51)


# =============================================================================
# RESPONSE SCHEMA SERIALIZATION TESTS
# =============================================================================

class TestResponseSchemaSerialization:
    """Tests for response schema serialization."""

    def test_template_response_from_attributes(self):
        """Test TemplateResponse from_attributes config."""
        # Create a mock object with attributes
        class MockTemplate:
            id = 1
            name = "Test Template"
            description = "Test"
            category = "income"
            underlying = "NIFTY"
            position_type = "intraday"
            risk_level = "medium"
            market_outlook = "neutral"
            iv_environment = "normal"
            expected_return_pct = Decimal("2.5")
            max_risk_pct = Decimal("5.0")
            usage_count = 100
            avg_rating = Decimal("4.5")
            rating_count = 50
            is_system = True
            is_public = True
            tags = ["test"]
            thumbnail_url = None
            author_name = "Author"
            strategy_config = {"legs": []}
            educational_content = {}
            user_id = uuid4()
            created_at = datetime.utcnow()
            updated_at = datetime.utcnow()

        response = TemplateResponse.model_validate(MockTemplate())
        assert response.id == 1
        assert response.name == "Test Template"

    def test_trade_journal_response_from_attributes(self):
        """Test TradeJournalResponse from_attributes config."""
        class MockJournal:
            id = 1
            user_id = uuid4()
            strategy_id = 100
            strategy_name = "Test Strategy"
            underlying = "NIFTY"
            position_type = "intraday"
            entry_time = datetime.utcnow()
            exit_time = datetime.utcnow()
            holding_duration_minutes = 180
            legs = []
            lots = 1
            total_quantity = 25
            entry_premium = Decimal("100")
            exit_premium = Decimal("75")
            gross_pnl = Decimal("625")
            brokerage = Decimal("40")
            taxes = Decimal("10")
            other_charges = Decimal("5")
            net_pnl = Decimal("570")
            pnl_percentage = Decimal("2.5")
            max_profit_reached = Decimal("800")
            max_loss_reached = Decimal("-100")
            max_drawdown = Decimal("200")
            exit_reason = "target_hit"
            market_conditions = {}
            notes = "Test"
            tags = []
            screenshots = []
            entry_order_ids = []
            exit_order_ids = []
            is_open = False
            created_at = datetime.utcnow()
            updated_at = datetime.utcnow()

        response = TradeJournalResponse.model_validate(MockJournal())
        assert response.strategy_name == "Test Strategy"

    def test_backtest_response_from_attributes(self):
        """Test BacktestResponse from_attributes config."""
        class MockBacktest:
            id = 1
            user_id = uuid4()
            name = "Test Backtest"
            description = "Test"
            strategy_config = {}
            start_date = date(2024, 1, 1)
            end_date = date(2024, 6, 30)
            initial_capital = Decimal("500000")
            slippage_pct = Decimal("0.1")
            charges_per_lot = Decimal("40")
            data_interval = "1min"
            status = "completed"
            progress_pct = 100
            error_message = None
            results = {}
            total_trades = 120
            winning_trades = 78
            losing_trades = 42
            win_rate = Decimal("65.0")
            gross_pnl = Decimal("185000")
            net_pnl = Decimal("175200")
            max_drawdown = Decimal("28000")
            max_drawdown_pct = Decimal("5.6")
            sharpe_ratio = Decimal("1.85")
            profit_factor = Decimal("2.15")
            equity_curve = []
            trades = []
            created_at = datetime.utcnow()
            started_at = datetime.utcnow()
            completed_at = datetime.utcnow()

        response = BacktestResponse.model_validate(MockBacktest())
        assert response.name == "Test Backtest"
        assert response.status == "completed"
