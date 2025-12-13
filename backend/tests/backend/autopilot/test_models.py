"""
AutoPilot Model Tests

Tests for SQLAlchemy models:
- AutoPilotUserSettings
- AutoPilotStrategy
- AutoPilotOrder
- AutoPilotLog
- AutoPilotTemplate
- AutoPilotConditionEval
- AutoPilotDailySummary

Tests enum values, relationships, JSON fields, and cascade behavior.
"""

import pytest
import pytest_asyncio
from datetime import datetime, date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User
from app.models.autopilot import (
    AutoPilotUserSettings, AutoPilotStrategy, AutoPilotOrder, AutoPilotLog,
    AutoPilotTemplate, AutoPilotConditionEval, AutoPilotDailySummary,
    StrategyStatus, Underlying, PositionType, OrderStatus, OrderPurpose, LogSeverity
)


# =============================================================================
# USER SETTINGS TESTS
# =============================================================================

class TestAutoPilotUserSettings:
    """Tests for AutoPilotUserSettings model."""

    @pytest.mark.asyncio
    async def test_create_user_settings(self, db_session: AsyncSession, test_user: User):
        """Test creating user settings with all fields."""
        settings = AutoPilotUserSettings(
            user_id=test_user.id,
            daily_loss_limit=Decimal("25000.00"),
            per_strategy_loss_limit=Decimal("12500.00"),
            max_capital_deployed=Decimal("750000.00"),
            max_active_strategies=5,
            no_trade_first_minutes=10,
            no_trade_last_minutes=10,
            cooldown_after_loss=True,
            cooldown_minutes=45,
            cooldown_threshold=Decimal("7500.00"),
            default_order_settings={"order_type": "LIMIT"},
            notification_prefs={"email": True, "sms": False},
            failure_handling={"on_error": "pause"},
            paper_trading_mode=True,
            show_advanced_features=True
        )
        db_session.add(settings)
        await db_session.commit()
        await db_session.refresh(settings)

        assert settings.id is not None
        assert settings.user_id == test_user.id
        assert settings.daily_loss_limit == Decimal("25000.00")
        assert settings.per_strategy_loss_limit == Decimal("12500.00")
        assert settings.max_capital_deployed == Decimal("750000.00")
        assert settings.max_active_strategies == 5
        assert settings.no_trade_first_minutes == 10
        assert settings.no_trade_last_minutes == 10
        assert settings.cooldown_after_loss is True
        assert settings.cooldown_minutes == 45
        assert settings.cooldown_threshold == Decimal("7500.00")
        assert settings.default_order_settings == {"order_type": "LIMIT"}
        assert settings.notification_prefs == {"email": True, "sms": False}
        assert settings.failure_handling == {"on_error": "pause"}
        assert settings.paper_trading_mode is True
        assert settings.show_advanced_features is True
        assert settings.created_at is not None
        assert settings.updated_at is not None

    @pytest.mark.asyncio
    async def test_user_settings_defaults(self, db_session: AsyncSession, test_user: User):
        """Test default values for user settings."""
        # Create another user for this test
        user = User(id=uuid4(), email="defaults_test@example.com")
        db_session.add(user)
        await db_session.commit()

        settings = AutoPilotUserSettings(user_id=user.id)
        db_session.add(settings)
        await db_session.commit()
        await db_session.refresh(settings)

        assert settings.daily_loss_limit == Decimal("20000.00")
        assert settings.per_strategy_loss_limit == Decimal("10000.00")
        assert settings.max_capital_deployed == Decimal("500000.00")
        assert settings.max_active_strategies == 3
        assert settings.no_trade_first_minutes == 5
        assert settings.no_trade_last_minutes == 5
        assert settings.cooldown_after_loss is False
        assert settings.cooldown_minutes == 30
        assert settings.paper_trading_mode is False
        assert settings.show_advanced_features is False


# =============================================================================
# STRATEGY TESTS
# =============================================================================

class TestAutoPilotStrategy:
    """Tests for AutoPilotStrategy model."""

    @pytest.mark.asyncio
    async def test_create_strategy(self, db_session: AsyncSession, test_user: User):
        """Test creating strategy with all required fields."""
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Iron Condor NIFTY",
            description="Weekly Iron Condor strategy",
            status="draft",
            underlying="NIFTY",
            expiry_type="current_week",
            lots=2,
            position_type="intraday",
            legs_config=[{"id": "leg_1", "type": "CE"}],
            entry_conditions={"logic": "AND", "conditions": []},
            adjustment_rules=[],
            order_settings={},
            risk_settings={"max_loss": 5000},
            schedule_config={"active_days": ["MON", "TUE"]},
            priority=50
        )
        db_session.add(strategy)
        await db_session.commit()
        await db_session.refresh(strategy)

        assert strategy.id is not None
        assert strategy.user_id == test_user.id
        assert strategy.name == "Iron Condor NIFTY"
        assert strategy.status == "draft"
        assert strategy.underlying == "NIFTY"
        assert strategy.expiry_type == "current_week"
        assert strategy.lots == 2
        assert strategy.position_type == "intraday"
        assert len(strategy.legs_config) == 1
        assert strategy.entry_conditions["logic"] == "AND"
        assert strategy.risk_settings["max_loss"] == 5000
        assert strategy.priority == 50
        assert strategy.version == 1

    @pytest.mark.asyncio
    async def test_strategy_status_enum(self, db_session: AsyncSession, test_user: User):
        """Test all StrategyStatus enum values."""
        statuses = [
            StrategyStatus.DRAFT, StrategyStatus.WAITING, StrategyStatus.ACTIVE,
            StrategyStatus.PENDING, StrategyStatus.PAUSED, StrategyStatus.COMPLETED,
            StrategyStatus.ERROR, StrategyStatus.EXPIRED
        ]

        for i, status in enumerate(statuses):
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Strategy {status.value}",
                status=status.value,
                underlying="NIFTY",
                expiry_type="current_week",
                legs_config=[],
                entry_conditions={}
            )
            db_session.add(strategy)

        await db_session.commit()

        # Verify all were created
        result = await db_session.execute(
            select(AutoPilotStrategy).where(AutoPilotStrategy.user_id == test_user.id)
        )
        strategies = result.scalars().all()
        assert len(strategies) >= len(statuses)

    @pytest.mark.asyncio
    async def test_strategy_underlying_enum(self, db_session: AsyncSession, test_user: User):
        """Test all Underlying enum values."""
        underlyings = [
            Underlying.NIFTY, Underlying.BANKNIFTY,
            Underlying.FINNIFTY, Underlying.SENSEX
        ]

        for underlying in underlyings:
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Strategy {underlying.value}",
                status="draft",
                underlying=underlying.value,
                expiry_type="current_week",
                legs_config=[],
                entry_conditions={}
            )
            db_session.add(strategy)

        await db_session.commit()

        result = await db_session.execute(
            select(AutoPilotStrategy).where(AutoPilotStrategy.user_id == test_user.id)
        )
        strategies = result.scalars().all()
        underlyings_created = {s.underlying for s in strategies}
        assert "NIFTY" in underlyings_created
        assert "BANKNIFTY" in underlyings_created

    @pytest.mark.asyncio
    async def test_strategy_position_type_enum(self, db_session: AsyncSession, test_user: User):
        """Test all PositionType enum values."""
        for position_type in [PositionType.INTRADAY, PositionType.POSITIONAL]:
            strategy = AutoPilotStrategy(
                user_id=test_user.id,
                name=f"Strategy {position_type.value}",
                status="draft",
                underlying="NIFTY",
                expiry_type="current_week",
                position_type=position_type.value,
                legs_config=[],
                entry_conditions={}
            )
            db_session.add(strategy)

        await db_session.commit()

        result = await db_session.execute(
            select(AutoPilotStrategy).where(AutoPilotStrategy.user_id == test_user.id)
        )
        strategies = result.scalars().all()
        position_types = {s.position_type for s in strategies}
        assert "intraday" in position_types
        assert "positional" in position_types

    @pytest.mark.asyncio
    async def test_strategy_jsonb_fields(self, db_session: AsyncSession, test_user: User):
        """Test JSONB fields store and retrieve correctly."""
        legs_config = [
            {
                "id": "leg_1",
                "contract_type": "CE",
                "transaction_type": "SELL",
                "strike_selection": {"mode": "atm_offset", "offset": 2},
                "quantity_multiplier": 1
            },
            {
                "id": "leg_2",
                "contract_type": "PE",
                "transaction_type": "SELL",
                "strike_selection": {"mode": "atm_offset", "offset": -2},
                "quantity_multiplier": 1
            }
        ]

        entry_conditions = {
            "logic": "AND",
            "conditions": [
                {"id": "c1", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:20"},
                {"id": "c2", "variable": "VIX.VALUE", "operator": "less_than", "value": 20}
            ]
        }

        risk_settings = {
            "max_loss": 5000,
            "trailing_stop": {"enabled": True, "trigger_profit": 3000}
        }

        runtime_state = {
            "current_pnl": 1500.50,
            "current_positions": [{"leg_id": "leg_1", "qty": 25}]
        }

        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="JSONB Test Strategy",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=legs_config,
            entry_conditions=entry_conditions,
            risk_settings=risk_settings,
            runtime_state=runtime_state
        )
        db_session.add(strategy)
        await db_session.commit()

        # Fetch fresh from DB
        result = await db_session.execute(
            select(AutoPilotStrategy).where(AutoPilotStrategy.name == "JSONB Test Strategy")
        )
        fetched = result.scalar_one()

        # Verify JSONB fields
        assert len(fetched.legs_config) == 2
        assert fetched.legs_config[0]["id"] == "leg_1"
        assert fetched.legs_config[0]["strike_selection"]["mode"] == "atm_offset"

        assert fetched.entry_conditions["logic"] == "AND"
        assert len(fetched.entry_conditions["conditions"]) == 2

        assert fetched.risk_settings["max_loss"] == 5000
        assert fetched.risk_settings["trailing_stop"]["enabled"] is True

        assert fetched.runtime_state["current_pnl"] == 1500.50
        assert len(fetched.runtime_state["current_positions"]) == 1


# =============================================================================
# ORDER TESTS
# =============================================================================

class TestAutoPilotOrder:
    """Tests for AutoPilotOrder model."""

    @pytest.mark.asyncio
    async def test_create_order(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active
    ):
        """Test creating order with all fields."""
        order = AutoPilotOrder(
            strategy_id=test_strategy_active.id,
            user_id=test_user.id,
            kite_order_id="220101000123",
            kite_exchange_order_id="1100000000123",
            purpose="entry",
            rule_name="Entry Rule",
            leg_index=0,
            exchange="NFO",
            tradingsymbol="NIFTY24D2625000CE",
            instrument_token=12345678,
            underlying="NIFTY",
            contract_type="CE",
            strike=Decimal("25000"),
            expiry=date.today(),
            transaction_type="SELL",
            order_type="MARKET",
            product="MIS",
            quantity=25,
            order_price=None,
            trigger_price=None,
            ltp_at_order=Decimal("150.50"),
            executed_price=Decimal("150.25"),
            executed_quantity=25,
            pending_quantity=0,
            slippage_amount=Decimal("-6.25"),
            slippage_pct=Decimal("-0.17"),
            status="complete",
            order_placed_at=datetime.utcnow(),
            order_filled_at=datetime.utcnow(),
            execution_duration_ms=250,
            retry_count=0
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        assert order.id is not None
        assert order.strategy_id == test_strategy_active.id
        assert order.kite_order_id == "220101000123"
        assert order.purpose == "entry"
        assert order.tradingsymbol == "NIFTY24D2625000CE"
        assert order.strike == Decimal("25000")
        assert order.transaction_type == "SELL"
        assert order.executed_price == Decimal("150.25")
        assert order.status == "complete"

    @pytest.mark.asyncio
    async def test_order_purpose_values(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active
    ):
        """Test all OrderPurpose enum values."""
        purposes = [
            OrderPurpose.ENTRY, OrderPurpose.ADJUSTMENT, OrderPurpose.HEDGE,
            OrderPurpose.EXIT, OrderPurpose.ROLL_CLOSE, OrderPurpose.ROLL_OPEN,
            OrderPurpose.KILL_SWITCH
        ]

        for i, purpose in enumerate(purposes):
            order = AutoPilotOrder(
                strategy_id=test_strategy_active.id,
                user_id=test_user.id,
                kite_order_id=f"22010100000{i}",
                purpose=purpose.value,
                exchange="NFO",
                tradingsymbol=f"NIFTY24D262{i}000CE",
                underlying="NIFTY",
                contract_type="CE",
                expiry=date.today(),
                transaction_type="SELL",
                order_type="MARKET",
                quantity=25,
                status="complete"
            )
            db_session.add(order)

        await db_session.commit()

        result = await db_session.execute(
            select(AutoPilotOrder).where(AutoPilotOrder.strategy_id == test_strategy_active.id)
        )
        orders = result.scalars().all()
        purposes_created = {o.purpose for o in orders}
        assert "entry" in purposes_created
        assert "exit" in purposes_created
        assert "kill_switch" in purposes_created


# =============================================================================
# LOG TESTS
# =============================================================================

class TestAutoPilotLog:
    """Tests for AutoPilotLog model."""

    @pytest.mark.asyncio
    async def test_create_log(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy
    ):
        """Test creating log with all fields."""
        log = AutoPilotLog(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            event_type="strategy_activated",
            severity="info",
            rule_name="Entry Condition",
            condition_id="cond_1",
            event_data={"paper_trading": False},
            message="Strategy activated and waiting for entry conditions"
        )
        db_session.add(log)
        await db_session.commit()
        await db_session.refresh(log)

        assert log.id is not None
        assert log.user_id == test_user.id
        assert log.strategy_id == test_strategy.id
        assert log.event_type == "strategy_activated"
        assert log.severity == "info"
        assert log.event_data["paper_trading"] is False
        assert log.created_at is not None

    @pytest.mark.asyncio
    async def test_log_severity_levels(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy
    ):
        """Test all LogSeverity enum values."""
        severities = [
            LogSeverity.DEBUG, LogSeverity.INFO, LogSeverity.WARNING,
            LogSeverity.ERROR, LogSeverity.CRITICAL
        ]

        for severity in severities:
            log = AutoPilotLog(
                user_id=test_user.id,
                strategy_id=test_strategy.id,
                event_type="test_event",
                severity=severity.value,
                message=f"Test message with {severity.value} severity"
            )
            db_session.add(log)

        await db_session.commit()

        result = await db_session.execute(
            select(AutoPilotLog).where(AutoPilotLog.strategy_id == test_strategy.id)
        )
        logs = result.scalars().all()
        severities_created = {log.severity for log in logs}
        assert "debug" in severities_created
        assert "info" in severities_created
        assert "warning" in severities_created
        assert "error" in severities_created
        assert "critical" in severities_created


# =============================================================================
# TEMPLATE TESTS
# =============================================================================

class TestAutoPilotTemplate:
    """Tests for AutoPilotTemplate model."""

    @pytest.mark.asyncio
    async def test_create_template(self, db_session: AsyncSession):
        """Test creating template with all fields."""
        template = AutoPilotTemplate(
            name="Short Strangle Template",
            description="Weekly short strangle for high IV",
            is_system=True,
            is_public=True,
            strategy_config={
                "underlying": "NIFTY",
                "legs_config": [
                    {"contract_type": "CE", "transaction_type": "SELL"},
                    {"contract_type": "PE", "transaction_type": "SELL"}
                ],
                "entry_conditions": {"logic": "AND", "conditions": []}
            },
            category="neutral",
            tags=["income", "theta", "high-risk"],
            risk_level="high",
            usage_count=50,
            avg_rating=Decimal("4.25"),
            rating_count=20
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        assert template.id is not None
        assert template.name == "Short Strangle Template"
        assert template.is_system is True
        assert template.is_public is True
        assert template.category == "neutral"
        assert "income" in template.tags
        assert template.risk_level == "high"
        assert template.usage_count == 50
        assert template.avg_rating == Decimal("4.25")

    @pytest.mark.asyncio
    async def test_template_user_association(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test template with user association."""
        template = AutoPilotTemplate(
            user_id=test_user.id,
            name="User Custom Template",
            is_system=False,
            is_public=False,
            strategy_config={"underlying": "BANKNIFTY", "legs_config": []}
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        assert template.user_id == test_user.id
        assert template.is_system is False


# =============================================================================
# RELATIONSHIP TESTS
# =============================================================================

class TestRelationships:
    """Tests for model relationships."""

    @pytest.mark.asyncio
    async def test_user_strategy_relationship(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy
    ):
        """Test User → Strategy relationship."""
        # Refresh user to load relationships
        result = await db_session.execute(
            select(User).where(User.id == test_user.id)
        )
        user = result.scalar_one()

        # Get strategies
        result = await db_session.execute(
            select(AutoPilotStrategy).where(AutoPilotStrategy.user_id == user.id)
        )
        strategies = result.scalars().all()

        assert len(strategies) >= 1
        assert any(s.id == test_strategy.id for s in strategies)

    @pytest.mark.asyncio
    async def test_strategy_order_relationship(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_strategy_active,
        test_order
    ):
        """Test Strategy → Order relationship."""
        result = await db_session.execute(
            select(AutoPilotOrder).where(
                AutoPilotOrder.strategy_id == test_strategy_active.id
            )
        )
        orders = result.scalars().all()

        assert len(orders) >= 1
        assert any(o.id == test_order.id for o in orders)

    @pytest.mark.asyncio
    async def test_cascade_delete(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test cascading delete of orders and logs when strategy deleted."""
        # Create strategy
        strategy = AutoPilotStrategy(
            user_id=test_user.id,
            name="Cascade Test Strategy",
            status="active",
            underlying="NIFTY",
            expiry_type="current_week",
            legs_config=[],
            entry_conditions={}
        )
        db_session.add(strategy)
        await db_session.commit()
        await db_session.refresh(strategy)

        strategy_id = strategy.id

        # Create order
        order = AutoPilotOrder(
            strategy_id=strategy_id,
            user_id=test_user.id,
            kite_order_id="CASCADE_TEST_001",
            purpose="entry",
            exchange="NFO",
            tradingsymbol="NIFTY24D2625000CE",
            underlying="NIFTY",
            contract_type="CE",
            expiry=date.today(),
            transaction_type="SELL",
            order_type="MARKET",
            quantity=25,
            status="complete"
        )
        db_session.add(order)
        await db_session.commit()

        # Create log
        log = AutoPilotLog(
            user_id=test_user.id,
            strategy_id=strategy_id,
            event_type="test",
            severity="info",
            message="Test log for cascade"
        )
        db_session.add(log)
        await db_session.commit()

        # Verify created
        result = await db_session.execute(
            select(AutoPilotOrder).where(AutoPilotOrder.strategy_id == strategy_id)
        )
        assert len(result.scalars().all()) == 1

        # Delete strategy
        await db_session.delete(strategy)
        await db_session.commit()

        # Verify orders cascade deleted
        result = await db_session.execute(
            select(AutoPilotOrder).where(AutoPilotOrder.strategy_id == strategy_id)
        )
        assert len(result.scalars().all()) == 0


# =============================================================================
# CONDITION EVAL TESTS
# =============================================================================

class TestAutoPilotConditionEval:
    """Tests for AutoPilotConditionEval model."""

    @pytest.mark.asyncio
    async def test_create_condition_eval(
        self,
        db_session: AsyncSession,
        test_strategy_waiting
    ):
        """Test creating condition evaluation record."""
        eval_record = AutoPilotConditionEval(
            strategy_id=test_strategy_waiting.id,
            condition_type="entry",
            condition_index=0,
            rule_name="Time Entry",
            variable="TIME.CURRENT",
            operator="greater_than",
            target_value="09:20",
            current_value="09:25",
            is_satisfied=True,
            progress_pct=Decimal("100.00"),
            distance_to_trigger="Passed"
        )
        db_session.add(eval_record)
        await db_session.commit()
        await db_session.refresh(eval_record)

        assert eval_record.id is not None
        assert eval_record.strategy_id == test_strategy_waiting.id
        assert eval_record.variable == "TIME.CURRENT"
        assert eval_record.is_satisfied is True
        assert eval_record.progress_pct == Decimal("100.00")


# =============================================================================
# DAILY SUMMARY TESTS
# =============================================================================

class TestAutoPilotDailySummary:
    """Tests for AutoPilotDailySummary model."""

    @pytest.mark.asyncio
    async def test_create_daily_summary(
        self,
        db_session: AsyncSession,
        test_user: User
    ):
        """Test creating daily summary record."""
        summary = AutoPilotDailySummary(
            user_id=test_user.id,
            summary_date=date.today(),
            strategies_run=5,
            strategies_completed=4,
            strategies_errored=1,
            orders_placed=20,
            orders_filled=18,
            orders_rejected=2,
            total_realized_pnl=Decimal("15000.00"),
            total_brokerage=Decimal("250.00"),
            total_slippage=Decimal("125.50"),
            best_strategy_pnl=Decimal("8000.00"),
            best_strategy_name="Iron Condor #1",
            worst_strategy_pnl=Decimal("-3000.00"),
            worst_strategy_name="Short Strangle #2",
            avg_execution_time_ms=350,
            total_adjustments=3,
            kill_switch_used=False,
            max_drawdown=Decimal("5000.00"),
            peak_margin_used=Decimal("250000.00"),
            daily_loss_limit_hit=False
        )
        db_session.add(summary)
        await db_session.commit()
        await db_session.refresh(summary)

        assert summary.id is not None
        assert summary.user_id == test_user.id
        assert summary.summary_date == date.today()
        assert summary.strategies_run == 5
        assert summary.total_realized_pnl == Decimal("15000.00")
        assert summary.best_strategy_name == "Iron Condor #1"
        assert summary.kill_switch_used is False
