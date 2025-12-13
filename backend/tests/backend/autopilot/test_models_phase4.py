"""
Phase 4 Model Tests - AutoPilot Feature

Tests for Phase 4 SQLAlchemy models:
- AutoPilotTradeJournal
- AutoPilotAnalyticsCache
- AutoPilotReport
- AutoPilotBacktest
- AutoPilotTemplateRating
- AutoPilotTemplate (Phase 4 enhancements)
- AutoPilotStrategy (sharing fields)
"""

import pytest
import pytest_asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.autopilot import (
    AutoPilotTradeJournal, AutoPilotAnalyticsCache, AutoPilotReport,
    AutoPilotBacktest, AutoPilotTemplateRating, AutoPilotTemplate,
    AutoPilotStrategy,
    ExitReason, TemplateCategory, ReportType, ReportFormat, BacktestStatus, ShareMode
)
from app.models.users import User


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestPhase4Enums:
    """Test Phase 4 enum values."""

    def test_exit_reason_enum_values(self):
        """Test ExitReason enum has all expected values."""
        expected = [
            "target_hit", "stop_loss", "trailing_stop", "time_exit",
            "manual_exit", "adjustment_exit", "kill_switch", "auto_exit", "error"
        ]
        actual = [e.value for e in ExitReason]
        assert set(expected) == set(actual)

    def test_template_category_enum_values(self):
        """Test TemplateCategory enum has all expected values."""
        expected = ["income", "directional", "volatility", "hedging", "advanced", "custom"]
        actual = [e.value for e in TemplateCategory]
        assert set(expected) == set(actual)

    def test_report_type_enum_values(self):
        """Test ReportType enum has all expected values."""
        expected = ["daily", "weekly", "monthly", "custom", "strategy", "tax"]
        actual = [e.value for e in ReportType]
        assert set(expected) == set(actual)

    def test_report_format_enum_values(self):
        """Test ReportFormat enum has all expected values."""
        expected = ["pdf", "excel", "csv"]
        actual = [e.value for e in ReportFormat]
        assert set(expected) == set(actual)

    def test_backtest_status_enum_values(self):
        """Test BacktestStatus enum has all expected values."""
        expected = ["pending", "running", "completed", "failed", "cancelled"]
        actual = [e.value for e in BacktestStatus]
        assert set(expected) == set(actual)

    def test_share_mode_enum_values(self):
        """Test ShareMode enum has all expected values."""
        expected = ["private", "link", "public"]
        actual = [e.value for e in ShareMode]
        assert set(expected) == set(actual)


# =============================================================================
# TRADE JOURNAL MODEL TESTS
# =============================================================================

class TestAutoPilotTradeJournal:
    """Tests for AutoPilotTradeJournal model."""

    @pytest.mark.asyncio
    async def test_create_trade_journal_entry(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating a trade journal entry."""
        journal = AutoPilotTradeJournal(
            user_id=test_user.id,
            strategy_name="Test Iron Condor",
            underlying="NIFTY",
            position_type="intraday",
            entry_time=datetime.utcnow() - timedelta(hours=4),
            exit_time=datetime.utcnow(),
            holding_duration_minutes=240,
            legs=[{"leg_id": "leg_1", "tradingsymbol": "NIFTY24D2625000CE"}],
            lots=1,
            total_quantity=25,
            gross_pnl=Decimal("2500.00"),
            net_pnl=Decimal("2400.00"),
            exit_reason="target_hit",
            is_open=False
        )
        db_session.add(journal)
        await db_session.commit()
        await db_session.refresh(journal)

        assert journal.id is not None
        assert journal.strategy_name == "Test Iron Condor"
        assert journal.underlying == "NIFTY"
        assert journal.gross_pnl == Decimal("2500.00")
        assert journal.is_open is False

    @pytest.mark.asyncio
    async def test_trade_journal_with_all_fields(
        self, db_session: AsyncSession, test_user: User, test_strategy
    ):
        """Test trade journal with all optional fields populated."""
        journal = AutoPilotTradeJournal(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            strategy_name="Full Trade Entry",
            underlying="BANKNIFTY",
            position_type="positional",
            entry_time=datetime.utcnow() - timedelta(days=1),
            exit_time=datetime.utcnow(),
            holding_duration_minutes=1440,
            legs=[
                {"leg_id": "leg_1", "tradingsymbol": "BANKNIFTY24D2652000CE", "quantity": 15},
                {"leg_id": "leg_2", "tradingsymbol": "BANKNIFTY24D2652000PE", "quantity": 15}
            ],
            lots=1,
            total_quantity=30,
            entry_premium=Decimal("500.00"),
            exit_premium=Decimal("350.00"),
            gross_pnl=Decimal("2250.00"),
            brokerage=Decimal("60.00"),
            taxes=Decimal("15.00"),
            other_charges=Decimal("5.00"),
            net_pnl=Decimal("2170.00"),
            pnl_percentage=Decimal("4.34"),
            max_profit_reached=Decimal("3000.00"),
            max_loss_reached=Decimal("-500.00"),
            max_drawdown=Decimal("1500.00"),
            exit_reason="trailing_stop",
            market_conditions={"spot_at_entry": 52000, "vix_at_entry": 14.5},
            notes="Good trade with proper trailing stop",
            tags=["banknifty", "positional", "straddle"],
            screenshots=["http://example.com/screenshot1.png"],
            entry_order_ids=[1001, 1002],
            exit_order_ids=[2001, 2002],
            is_open=False
        )
        db_session.add(journal)
        await db_session.commit()
        await db_session.refresh(journal)

        assert journal.strategy_id == test_strategy.id
        assert journal.brokerage == Decimal("60.00")
        assert journal.tags == ["banknifty", "positional", "straddle"]
        assert journal.notes == "Good trade with proper trailing stop"

    @pytest.mark.asyncio
    async def test_trade_journal_open_trade(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating an open (running) trade."""
        journal = AutoPilotTradeJournal(
            user_id=test_user.id,
            strategy_name="Open Trade",
            underlying="NIFTY",
            position_type="intraday",
            entry_time=datetime.utcnow(),
            legs=[{"leg_id": "leg_1", "tradingsymbol": "NIFTY24D2625000CE"}],
            lots=1,
            total_quantity=25,
            is_open=True
        )
        db_session.add(journal)
        await db_session.commit()

        assert journal.is_open is True
        assert journal.exit_time is None
        assert journal.exit_reason is None

    @pytest.mark.asyncio
    async def test_trade_journal_user_relationship(
        self, db_session: AsyncSession, test_trade_journal_in_db
    ):
        """Test trade journal user relationship."""
        result = await db_session.execute(
            select(AutoPilotTradeJournal).where(
                AutoPilotTradeJournal.id == test_trade_journal_in_db.id
            )
        )
        journal = result.scalar_one()

        assert journal.user_id is not None

    @pytest.mark.asyncio
    async def test_trade_journal_requires_user_id(self, db_session: AsyncSession):
        """Test that trade journal requires user_id."""
        journal = AutoPilotTradeJournal(
            strategy_name="No User Trade",
            underlying="NIFTY",
            position_type="intraday",
            entry_time=datetime.utcnow(),
            legs=[],
            lots=1,
            total_quantity=25,
            is_open=True
        )
        db_session.add(journal)
        with pytest.raises(IntegrityError):
            await db_session.commit()


# =============================================================================
# ANALYTICS CACHE MODEL TESTS
# =============================================================================

class TestAutoPilotAnalyticsCache:
    """Tests for AutoPilotAnalyticsCache model."""

    @pytest.mark.asyncio
    async def test_create_analytics_cache(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating an analytics cache entry."""
        cache = AutoPilotAnalyticsCache(
            user_id=test_user.id,
            cache_key="summary_30d",
            start_date=date.today() - timedelta(days=30),
            end_date=date.today(),
            metrics={
                "total_trades": 50,
                "winning_trades": 32,
                "win_rate": 64.0,
                "net_pnl": 125000
            },
            is_valid=True,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(cache)
        await db_session.commit()
        await db_session.refresh(cache)

        assert cache.id is not None
        assert cache.cache_key == "summary_30d"
        assert cache.metrics["total_trades"] == 50
        assert cache.is_valid is True

    @pytest.mark.asyncio
    async def test_analytics_cache_expiry(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test analytics cache with expired timestamp."""
        cache = AutoPilotAnalyticsCache(
            user_id=test_user.id,
            cache_key="expired_cache",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            metrics={"total_trades": 10},
            is_valid=True,
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        db_session.add(cache)
        await db_session.commit()

        assert cache.expires_at < datetime.utcnow()

    @pytest.mark.asyncio
    async def test_analytics_cache_unique_constraint(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test unique constraint on user_id + cache_key."""
        cache1 = AutoPilotAnalyticsCache(
            user_id=test_user.id,
            cache_key="unique_test",
            start_date=date.today(),
            end_date=date.today(),
            metrics={},
            is_valid=True,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(cache1)
        await db_session.commit()

        cache2 = AutoPilotAnalyticsCache(
            user_id=test_user.id,
            cache_key="unique_test",  # Same key
            start_date=date.today(),
            end_date=date.today(),
            metrics={},
            is_valid=True,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(cache2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_analytics_cache_invalidation(
        self, db_session: AsyncSession, test_analytics_cache
    ):
        """Test cache invalidation."""
        test_analytics_cache.is_valid = False
        await db_session.commit()
        await db_session.refresh(test_analytics_cache)

        assert test_analytics_cache.is_valid is False


# =============================================================================
# REPORT MODEL TESTS
# =============================================================================

class TestAutoPilotReport:
    """Tests for AutoPilotReport model."""

    @pytest.mark.asyncio
    async def test_create_monthly_report(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating a monthly P&L report."""
        report = AutoPilotReport(
            user_id=test_user.id,
            report_type="monthly",
            name="December 2024 Report",
            description="Monthly trading report",
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 31),
            report_data={
                "summary": {"total_trades": 40, "net_pnl": 75000},
                "by_strategy": []
            },
            is_ready=True,
            generated_at=datetime.utcnow()
        )
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        assert report.id is not None
        assert report.report_type == "monthly"
        assert report.is_ready is True

    @pytest.mark.asyncio
    async def test_create_tax_report(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating a tax summary report."""
        report = AutoPilotReport(
            user_id=test_user.id,
            report_type="tax",
            name="FY 2024-25 Tax Summary",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            report_data={
                "financial_year": "2024-25",
                "total_turnover": 25000000,
                "net_profit_loss": 170000
            },
            is_ready=False
        )
        db_session.add(report)
        await db_session.commit()

        assert report.report_type == "tax"
        assert report.is_ready is False

    @pytest.mark.asyncio
    async def test_report_with_file_export(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test report with file export details."""
        report = AutoPilotReport(
            user_id=test_user.id,
            report_type="weekly",
            name="Week 50 Report",
            start_date=date(2024, 12, 9),
            end_date=date(2024, 12, 15),
            report_data={"summary": {}},
            format="pdf",
            file_path="/reports/user123/week50_2024.pdf",
            file_size_bytes=1024000,
            is_ready=True,
            generated_at=datetime.utcnow()
        )
        db_session.add(report)
        await db_session.commit()

        assert report.format == "pdf"
        assert report.file_size_bytes == 1024000

    @pytest.mark.asyncio
    async def test_report_strategy_specific(
        self, db_session: AsyncSession, test_user: User, test_strategy
    ):
        """Test strategy-specific report."""
        report = AutoPilotReport(
            user_id=test_user.id,
            report_type="strategy",
            name="Iron Condor Performance",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            strategy_id=test_strategy.id,
            report_data={
                "strategy_name": "Iron Condor",
                "total_executions": 120,
                "net_pnl": 250000
            },
            is_ready=True
        )
        db_session.add(report)
        await db_session.commit()

        assert report.strategy_id == test_strategy.id

    @pytest.mark.asyncio
    async def test_report_error_state(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test report with error message."""
        report = AutoPilotReport(
            user_id=test_user.id,
            report_type="custom",
            name="Failed Report",
            start_date=date.today(),
            end_date=date.today(),
            report_data={},
            is_ready=False,
            error_message="Insufficient data for report generation"
        )
        db_session.add(report)
        await db_session.commit()

        assert report.is_ready is False
        assert report.error_message is not None


# =============================================================================
# BACKTEST MODEL TESTS
# =============================================================================

class TestAutoPilotBacktest:
    """Tests for AutoPilotBacktest model."""

    @pytest.mark.asyncio
    async def test_create_backtest(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test creating a backtest."""
        backtest = AutoPilotBacktest(
            user_id=test_user.id,
            name="Iron Condor Backtest",
            description="Testing Iron Condor strategy",
            strategy_config={
                "underlying": "NIFTY",
                "legs_config": [{"id": "leg_1", "contract_type": "CE"}]
            },
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            initial_capital=Decimal("500000.00"),
            slippage_pct=Decimal("0.1"),
            charges_per_lot=Decimal("40.0"),
            data_interval="1min",
            status="pending",
            progress_pct=0
        )
        db_session.add(backtest)
        await db_session.commit()
        await db_session.refresh(backtest)

        assert backtest.id is not None
        assert backtest.status == "pending"
        assert backtest.progress_pct == 0

    @pytest.mark.asyncio
    async def test_backtest_running_state(
        self, db_session: AsyncSession, test_backtest_in_db
    ):
        """Test backtest in running state."""
        test_backtest_in_db.status = "running"
        test_backtest_in_db.progress_pct = 45
        test_backtest_in_db.started_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(test_backtest_in_db)

        assert test_backtest_in_db.status == "running"
        assert test_backtest_in_db.progress_pct == 45
        assert test_backtest_in_db.started_at is not None

    @pytest.mark.asyncio
    async def test_backtest_completed_with_results(
        self, db_session: AsyncSession, test_backtest_completed
    ):
        """Test completed backtest with full results."""
        assert test_backtest_completed.status == "completed"
        assert test_backtest_completed.progress_pct == 100
        assert test_backtest_completed.total_trades == 120
        assert test_backtest_completed.winning_trades == 78
        assert test_backtest_completed.win_rate == Decimal("65.0")
        assert test_backtest_completed.sharpe_ratio == Decimal("1.85")
        assert test_backtest_completed.profit_factor == Decimal("2.15")
        assert test_backtest_completed.equity_curve is not None
        assert len(test_backtest_completed.equity_curve) > 0

    @pytest.mark.asyncio
    async def test_backtest_failed_state(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test backtest failure with error message."""
        backtest = AutoPilotBacktest(
            user_id=test_user.id,
            name="Failed Backtest",
            strategy_config={},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            initial_capital=Decimal("100000.00"),
            slippage_pct=Decimal("0.1"),
            charges_per_lot=Decimal("40.0"),
            status="failed",
            progress_pct=25,
            error_message="Insufficient historical data for the selected period"
        )
        db_session.add(backtest)
        await db_session.commit()

        assert backtest.status == "failed"
        assert backtest.error_message is not None

    @pytest.mark.asyncio
    async def test_backtest_drawdown_metrics(
        self, db_session: AsyncSession, test_backtest_completed
    ):
        """Test backtest drawdown metrics."""
        assert test_backtest_completed.max_drawdown == Decimal("28000.0")
        assert test_backtest_completed.max_drawdown_pct == Decimal("5.6")


# =============================================================================
# TEMPLATE RATING MODEL TESTS
# =============================================================================

class TestAutoPilotTemplateRating:
    """Tests for AutoPilotTemplateRating model."""

    @pytest.mark.asyncio
    async def test_create_template_rating(
        self, db_session: AsyncSession, test_user: User, test_template_in_db
    ):
        """Test creating a template rating."""
        rating = AutoPilotTemplateRating(
            template_id=test_template_in_db.id,
            user_id=test_user.id,
            rating=5,
            review="Excellent strategy for neutral markets"
        )
        db_session.add(rating)
        await db_session.commit()
        await db_session.refresh(rating)

        assert rating.id is not None
        assert rating.rating == 5
        assert rating.review is not None

    @pytest.mark.asyncio
    async def test_template_rating_without_review(
        self, db_session: AsyncSession, test_user: User, test_template_in_db
    ):
        """Test rating without review text."""
        rating = AutoPilotTemplateRating(
            template_id=test_template_in_db.id,
            user_id=test_user.id,
            rating=4
        )
        db_session.add(rating)
        await db_session.commit()

        assert rating.rating == 4
        assert rating.review is None

    @pytest.mark.asyncio
    async def test_template_rating_unique_per_user(
        self, db_session: AsyncSession, test_user: User, test_template_in_db
    ):
        """Test one rating per user per template constraint."""
        rating1 = AutoPilotTemplateRating(
            template_id=test_template_in_db.id,
            user_id=test_user.id,
            rating=4
        )
        db_session.add(rating1)
        await db_session.commit()

        rating2 = AutoPilotTemplateRating(
            template_id=test_template_in_db.id,
            user_id=test_user.id,  # Same user
            rating=5
        )
        db_session.add(rating2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_template_rating_cascade_delete(
        self, db_session: AsyncSession, test_template_rating
    ):
        """Test rating deletion when template is deleted."""
        template_id = test_template_rating.template_id
        rating_id = test_template_rating.id

        # Delete the template
        result = await db_session.execute(
            select(AutoPilotTemplate).where(AutoPilotTemplate.id == template_id)
        )
        template = result.scalar_one()
        await db_session.delete(template)
        await db_session.commit()

        # Rating should be cascade deleted
        result = await db_session.execute(
            select(AutoPilotTemplateRating).where(AutoPilotTemplateRating.id == rating_id)
        )
        assert result.scalar_one_or_none() is None


# =============================================================================
# TEMPLATE PHASE 4 ENHANCEMENTS TESTS
# =============================================================================

class TestAutoPilotTemplatePhase4:
    """Tests for Phase 4 template enhancements."""

    @pytest.mark.asyncio
    async def test_template_phase4_fields(
        self, db_session: AsyncSession, test_template_in_db
    ):
        """Test Phase 4 enhanced template fields."""
        assert test_template_in_db.author_name is not None
        assert test_template_in_db.underlying is not None
        assert test_template_in_db.position_type is not None
        assert test_template_in_db.expected_return_pct is not None
        assert test_template_in_db.max_risk_pct is not None
        assert test_template_in_db.market_outlook is not None
        assert test_template_in_db.iv_environment is not None
        assert test_template_in_db.educational_content is not None

    @pytest.mark.asyncio
    async def test_template_educational_content(
        self, db_session: AsyncSession, test_template_in_db
    ):
        """Test template educational content structure."""
        edu = test_template_in_db.educational_content
        assert "when_to_use" in edu
        assert "pros" in edu
        assert "cons" in edu
        assert isinstance(edu["pros"], list)

    @pytest.mark.asyncio
    async def test_template_ratings_relationship(
        self, db_session: AsyncSession, test_template_in_db, test_user: User
    ):
        """Test template ratings relationship."""
        # Add multiple ratings from different users
        user2 = User(id=uuid4(), email="rater2@example.com")
        db_session.add(user2)
        await db_session.commit()

        rating1 = AutoPilotTemplateRating(
            template_id=test_template_in_db.id,
            user_id=test_user.id,
            rating=5
        )
        rating2 = AutoPilotTemplateRating(
            template_id=test_template_in_db.id,
            user_id=user2.id,
            rating=4
        )
        db_session.add_all([rating1, rating2])
        await db_session.commit()

        # Refresh and check
        await db_session.refresh(test_template_in_db)
        assert len(test_template_in_db.ratings) >= 2


# =============================================================================
# STRATEGY SHARING TESTS
# =============================================================================

class TestAutoPilotStrategySharing:
    """Tests for Phase 4 strategy sharing fields."""

    @pytest.mark.asyncio
    async def test_strategy_default_share_mode(
        self, db_session: AsyncSession, test_strategy
    ):
        """Test strategy default share mode is private."""
        assert test_strategy.share_mode == "private" or test_strategy.share_mode is None
        assert test_strategy.share_token is None

    @pytest.mark.asyncio
    async def test_strategy_link_sharing(
        self, db_session: AsyncSession, test_strategy_with_share_token
    ):
        """Test strategy with link sharing enabled."""
        assert test_strategy_with_share_token.share_mode == "link"
        assert test_strategy_with_share_token.share_token is not None
        assert test_strategy_with_share_token.shared_at is not None

    @pytest.mark.asyncio
    async def test_strategy_public_sharing(
        self, db_session: AsyncSession, test_strategy_public
    ):
        """Test publicly shared strategy."""
        assert test_strategy_public.share_mode == "public"
        assert test_strategy_public.share_token is not None

    @pytest.mark.asyncio
    async def test_share_token_uniqueness(
        self, db_session: AsyncSession, test_user: User
    ):
        """Test share token uniqueness constraint."""
        import secrets
        token = secrets.token_urlsafe(16)

        strategy1 = AutoPilotStrategy(
            user_id=test_user.id,
            name="Strategy 1",
            status="draft",
            underlying="NIFTY",
            expiry_type="current_week",
            lots=1,
            position_type="intraday",
            legs_config=[],
            entry_conditions={},
            share_mode="link",
            share_token=token
        )
        db_session.add(strategy1)
        await db_session.commit()

        strategy2 = AutoPilotStrategy(
            user_id=test_user.id,
            name="Strategy 2",
            status="draft",
            underlying="NIFTY",
            expiry_type="current_week",
            lots=1,
            position_type="intraday",
            legs_config=[],
            entry_conditions={},
            share_mode="link",
            share_token=token  # Same token - should fail
        )
        db_session.add(strategy2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_unshare_strategy(
        self, db_session: AsyncSession, test_strategy_with_share_token
    ):
        """Test reverting strategy to private."""
        test_strategy_with_share_token.share_mode = "private"
        test_strategy_with_share_token.share_token = None
        test_strategy_with_share_token.shared_at = None
        await db_session.commit()
        await db_session.refresh(test_strategy_with_share_token)

        assert test_strategy_with_share_token.share_mode == "private"
        assert test_strategy_with_share_token.share_token is None
