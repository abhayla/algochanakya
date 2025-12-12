"""
AutoPilot Phase 4 - Analytics & Templates Migration

Revision ID: 003_autopilot_phase4
Revises: 002_autopilot_phase3
Create Date: 2025-12-10

This migration adds:
- Enhanced Strategy Templates with categories, ratings, system templates
- Trade Journal for automatic trade logging
- Analytics Cache for pre-calculated metrics
- Reports table for generated reports
- Backtests table for backtest results
- Strategy sharing columns

New tables:
- autopilot_trade_journal
- autopilot_analytics_cache
- autopilot_reports
- autopilot_backtests
- autopilot_template_ratings

Updated tables:
- autopilot_templates (new columns for Phase 4)
- autopilot_strategies (sharing columns)

Run with: alembic upgrade head
Rollback with: alembic downgrade 002_autopilot_phase3
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003_autopilot_phase4'
down_revision = '002_autopilot_phase3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add Phase 4 tables and columns.
    """

    # =========================================================================
    # STEP 1: CREATE NEW ENUM TYPES
    # =========================================================================

    # Exit reason enum for trade journal
    op.execute("""
        CREATE TYPE autopilot_exit_reason AS ENUM (
            'target_hit',
            'stop_loss',
            'trailing_stop',
            'time_exit',
            'manual_exit',
            'adjustment_exit',
            'kill_switch',
            'auto_exit',
            'error'
        )
    """)

    # Template category enum
    op.execute("""
        CREATE TYPE autopilot_template_category AS ENUM (
            'income',
            'directional',
            'volatility',
            'hedging',
            'advanced',
            'custom'
        )
    """)

    # Report type enum
    op.execute("""
        CREATE TYPE autopilot_report_type AS ENUM (
            'daily',
            'weekly',
            'monthly',
            'custom',
            'strategy',
            'tax'
        )
    """)

    # Report format enum
    op.execute("""
        CREATE TYPE autopilot_report_format AS ENUM (
            'pdf',
            'excel',
            'csv'
        )
    """)

    # Backtest status enum
    op.execute("""
        CREATE TYPE autopilot_backtest_status AS ENUM (
            'pending',
            'running',
            'completed',
            'failed',
            'cancelled'
        )
    """)

    # Share mode enum
    op.execute("""
        CREATE TYPE autopilot_share_mode AS ENUM (
            'private',
            'link',
            'public'
        )
    """)

    # Add new event types to autopilot_log_event enum
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'journal_entry_created';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'report_generated';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'backtest_started';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'backtest_completed';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'template_deployed';
    """)
    op.execute("""
        ALTER TYPE autopilot_log_event ADD VALUE IF NOT EXISTS 'strategy_shared';
    """)

    # =========================================================================
    # STEP 2: ENHANCE EXISTING TABLES
    # =========================================================================

    # -------------------------------------------------------------------------
    # autopilot_templates - Add new columns for Phase 4
    # -------------------------------------------------------------------------

    # Add author column (user display name)
    op.add_column('autopilot_templates',
        sa.Column('author_name', sa.String(100), nullable=True)
    )

    # Add underlying column
    op.add_column('autopilot_templates',
        sa.Column('underlying', sa.String(20), nullable=True)
    )

    # Add position_type column
    op.add_column('autopilot_templates',
        sa.Column('position_type', sa.String(20), nullable=True)
    )

    # Add expected_return_pct column
    op.add_column('autopilot_templates',
        sa.Column('expected_return_pct', sa.Numeric(5, 2), nullable=True)
    )

    # Add max_risk_pct column
    op.add_column('autopilot_templates',
        sa.Column('max_risk_pct', sa.Numeric(5, 2), nullable=True)
    )

    # Add market_outlook column
    op.add_column('autopilot_templates',
        sa.Column('market_outlook', sa.String(50), nullable=True)
    )

    # Add iv_environment column
    op.add_column('autopilot_templates',
        sa.Column('iv_environment', sa.String(50), nullable=True)
    )

    # Add thumbnail_url column
    op.add_column('autopilot_templates',
        sa.Column('thumbnail_url', sa.String(500), nullable=True)
    )

    # Add educational_content column (JSONB)
    op.add_column('autopilot_templates',
        sa.Column('educational_content', postgresql.JSONB(), nullable=True,
                  server_default='{}')
    )

    # -------------------------------------------------------------------------
    # autopilot_strategies - Add sharing columns
    # -------------------------------------------------------------------------

    op.add_column('autopilot_strategies',
        sa.Column('share_mode',
                  postgresql.ENUM('private', 'link', 'public',
                                  name='autopilot_share_mode', create_type=False),
                  nullable=False, server_default='private')
    )

    op.add_column('autopilot_strategies',
        sa.Column('share_token', sa.String(50), nullable=True, unique=True)
    )

    op.add_column('autopilot_strategies',
        sa.Column('shared_at', sa.DateTime(timezone=True), nullable=True)
    )

    # =========================================================================
    # STEP 3: CREATE NEW TABLES
    # =========================================================================

    # -------------------------------------------------------------------------
    # Table: autopilot_trade_journal - Automatic trade logging
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_trade_journal',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', sa.BigInteger(),
                  sa.ForeignKey('autopilot_strategies.id', ondelete='SET NULL'), nullable=True),

        # Strategy Info (snapshot at trade time)
        sa.Column('strategy_name', sa.String(100), nullable=False),
        sa.Column('underlying', sa.String(20), nullable=False),
        sa.Column('position_type', sa.String(20), nullable=False),

        # Trade Timing
        sa.Column('entry_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('exit_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('holding_duration_minutes', sa.Integer(), nullable=True),

        # Legs Snapshot (JSONB)
        sa.Column('legs', postgresql.JSONB(), nullable=False, server_default='[]'),

        # Quantities
        sa.Column('lots', sa.Integer(), nullable=False),
        sa.Column('total_quantity', sa.Integer(), nullable=False),

        # Prices
        sa.Column('entry_premium', sa.Numeric(12, 2), nullable=True),
        sa.Column('exit_premium', sa.Numeric(12, 2), nullable=True),

        # P&L
        sa.Column('gross_pnl', sa.Numeric(14, 2), nullable=True),
        sa.Column('brokerage', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('taxes', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('other_charges', sa.Numeric(10, 2), nullable=True, server_default='0'),
        sa.Column('net_pnl', sa.Numeric(14, 2), nullable=True),
        sa.Column('pnl_percentage', sa.Numeric(8, 4), nullable=True),

        # Tracking metrics
        sa.Column('max_profit_reached', sa.Numeric(14, 2), nullable=True),
        sa.Column('max_loss_reached', sa.Numeric(14, 2), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(14, 2), nullable=True),

        # Exit Details
        sa.Column('exit_reason',
                  postgresql.ENUM('target_hit', 'stop_loss', 'trailing_stop', 'time_exit',
                                  'manual_exit', 'adjustment_exit', 'kill_switch', 'auto_exit', 'error',
                                  name='autopilot_exit_reason', create_type=False),
                  nullable=True),

        # Market Conditions (JSONB)
        sa.Column('market_conditions', postgresql.JSONB(), nullable=True,
                  server_default='{}'),

        # User Notes & Tags
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=True, server_default='{}'),

        # Screenshots (JSONB array of URLs)
        sa.Column('screenshots', postgresql.JSONB(), nullable=True, server_default='[]'),

        # Order IDs (for reference)
        sa.Column('entry_order_ids', postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column('exit_order_ids', postgresql.ARRAY(sa.BigInteger()), nullable=True),

        # Status
        sa.Column('is_open', sa.Boolean(), nullable=False, server_default='true'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

    # Indexes for autopilot_trade_journal
    op.create_index('idx_trade_journal_user', 'autopilot_trade_journal', ['user_id'])
    op.create_index('idx_trade_journal_strategy', 'autopilot_trade_journal', ['strategy_id'])
    op.create_index('idx_trade_journal_entry_time', 'autopilot_trade_journal',
                    [sa.text('entry_time DESC')])
    op.create_index('idx_trade_journal_exit_time', 'autopilot_trade_journal',
                    [sa.text('exit_time DESC')])
    op.create_index('idx_trade_journal_user_entry', 'autopilot_trade_journal',
                    ['user_id', sa.text('entry_time DESC')])
    op.create_index('idx_trade_journal_underlying', 'autopilot_trade_journal', ['underlying'])
    op.create_index('idx_trade_journal_exit_reason', 'autopilot_trade_journal', ['exit_reason'])

    # Partial index for open trades
    op.execute("""
        CREATE INDEX idx_trade_journal_open
        ON autopilot_trade_journal(user_id, strategy_id)
        WHERE is_open = true
    """)

    # GIN index for tags
    op.execute("""
        CREATE INDEX idx_trade_journal_tags
        ON autopilot_trade_journal USING GIN (tags)
    """)

    # -------------------------------------------------------------------------
    # Table: autopilot_analytics_cache - Pre-calculated analytics
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_analytics_cache',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Cache Key (e.g., 'summary_30d', 'performance_ytd')
        sa.Column('cache_key', sa.String(100), nullable=False),

        # Date Range
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),

        # Cached Metrics (JSONB)
        sa.Column('metrics', postgresql.JSONB(), nullable=False),

        # Cache Validity
        sa.Column('is_valid', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

    # Indexes for autopilot_analytics_cache
    op.create_index('idx_analytics_cache_user', 'autopilot_analytics_cache', ['user_id'])
    op.create_index('idx_analytics_cache_key', 'autopilot_analytics_cache', ['user_id', 'cache_key'])
    op.create_index('idx_analytics_cache_valid', 'autopilot_analytics_cache',
                    ['user_id', 'is_valid', 'expires_at'])

    # Unique constraint on user + cache_key
    op.create_unique_constraint('uq_analytics_cache_user_key', 'autopilot_analytics_cache',
                                ['user_id', 'cache_key'])

    # -------------------------------------------------------------------------
    # Table: autopilot_reports - Generated reports
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_reports',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Report Type
        sa.Column('report_type',
                  postgresql.ENUM('daily', 'weekly', 'monthly', 'custom', 'strategy', 'tax',
                                  name='autopilot_report_type', create_type=False),
                  nullable=False),

        # Report Name
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),

        # Date Range
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),

        # Strategy Filter (optional)
        sa.Column('strategy_id', sa.BigInteger(),
                  sa.ForeignKey('autopilot_strategies.id', ondelete='SET NULL'), nullable=True),

        # Report Data (JSONB)
        sa.Column('report_data', postgresql.JSONB(), nullable=False),

        # Export Format & File
        sa.Column('format',
                  postgresql.ENUM('pdf', 'excel', 'csv',
                                  name='autopilot_report_format', create_type=False),
                  nullable=True),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),

        # Status
        sa.Column('is_ready', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error_message', sa.String(500), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Indexes for autopilot_reports
    op.create_index('idx_reports_user', 'autopilot_reports', ['user_id'])
    op.create_index('idx_reports_type', 'autopilot_reports', ['user_id', 'report_type'])
    op.create_index('idx_reports_created', 'autopilot_reports',
                    [sa.text('created_at DESC')])

    # -------------------------------------------------------------------------
    # Table: autopilot_backtests - Backtest results
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_backtests',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Backtest Name
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),

        # Strategy Configuration (JSONB snapshot)
        sa.Column('strategy_config', postgresql.JSONB(), nullable=False),

        # Backtest Parameters
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('initial_capital', sa.Numeric(14, 2), nullable=False),
        sa.Column('slippage_pct', sa.Numeric(5, 2), nullable=False, server_default='0.1'),
        sa.Column('charges_per_lot', sa.Numeric(10, 2), nullable=False, server_default='40'),
        sa.Column('data_interval', sa.String(20), nullable=False, server_default='1min'),

        # Status
        sa.Column('status',
                  postgresql.ENUM('pending', 'running', 'completed', 'failed', 'cancelled',
                                  name='autopilot_backtest_status', create_type=False),
                  nullable=False, server_default='pending'),
        sa.Column('progress_pct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.String(500), nullable=True),

        # Results (JSONB)
        sa.Column('results', postgresql.JSONB(), nullable=True),

        # Summary Metrics
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('winning_trades', sa.Integer(), nullable=True),
        sa.Column('losing_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Numeric(5, 2), nullable=True),
        sa.Column('gross_pnl', sa.Numeric(14, 2), nullable=True),
        sa.Column('net_pnl', sa.Numeric(14, 2), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(14, 2), nullable=True),
        sa.Column('max_drawdown_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(6, 3), nullable=True),
        sa.Column('profit_factor', sa.Numeric(6, 3), nullable=True),

        # Equity Curve (JSONB array)
        sa.Column('equity_curve', postgresql.JSONB(), nullable=True, server_default='[]'),

        # Trades List (JSONB array)
        sa.Column('trades', postgresql.JSONB(), nullable=True, server_default='[]'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Indexes for autopilot_backtests
    op.create_index('idx_backtests_user', 'autopilot_backtests', ['user_id'])
    op.create_index('idx_backtests_status', 'autopilot_backtests', ['user_id', 'status'])
    op.create_index('idx_backtests_created', 'autopilot_backtests',
                    [sa.text('created_at DESC')])

    # -------------------------------------------------------------------------
    # Table: autopilot_template_ratings - User ratings for templates
    # -------------------------------------------------------------------------
    op.create_table(
        'autopilot_template_ratings',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('template_id', sa.BigInteger(),
                  sa.ForeignKey('autopilot_templates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),

        # Rating
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )

    # Indexes for autopilot_template_ratings
    op.create_index('idx_template_ratings_template', 'autopilot_template_ratings', ['template_id'])
    op.create_index('idx_template_ratings_user', 'autopilot_template_ratings', ['user_id'])

    # Unique constraint - one rating per user per template
    op.create_unique_constraint('uq_template_rating_user', 'autopilot_template_ratings',
                                ['template_id', 'user_id'])

    # Check constraint for rating value (1-5)
    op.execute("""
        ALTER TABLE autopilot_template_ratings
        ADD CONSTRAINT chk_rating_value
        CHECK (rating >= 1 AND rating <= 5)
    """)

    # =========================================================================
    # STEP 4: CREATE TRIGGERS
    # =========================================================================

    # Trigger for updated_at on new tables
    op.execute("""
        CREATE TRIGGER tr_autopilot_trade_journal_updated
        BEFORE UPDATE ON autopilot_trade_journal
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER tr_autopilot_analytics_cache_updated
        BEFORE UPDATE ON autopilot_analytics_cache
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    op.execute("""
        CREATE TRIGGER tr_autopilot_template_ratings_updated
        BEFORE UPDATE ON autopilot_template_ratings
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # =========================================================================
    # STEP 5: CREATE INDEXES ON EXISTING TABLES
    # =========================================================================

    # Index for share_token lookup
    op.create_index('idx_strategies_share_token', 'autopilot_strategies', ['share_token'],
                    unique=True, postgresql_where=sa.text("share_token IS NOT NULL"))

    # Index for public templates
    op.execute("""
        CREATE INDEX idx_templates_public
        ON autopilot_templates(category, avg_rating DESC, usage_count DESC)
        WHERE is_public = true
    """)

    # Index for system templates
    op.execute("""
        CREATE INDEX idx_templates_system
        ON autopilot_templates(category, name)
        WHERE is_system = true
    """)

    print("AutoPilot Phase 4 migration completed successfully!")
    print("   - 6 new enum types created")
    print("   - 6 new event types added to autopilot_log_event")
    print("   - 9 new columns added to autopilot_templates")
    print("   - 3 new columns added to autopilot_strategies")
    print("   - 5 new tables created:")
    print("     - autopilot_trade_journal")
    print("     - autopilot_analytics_cache")
    print("     - autopilot_reports")
    print("     - autopilot_backtests")
    print("     - autopilot_template_ratings")


def downgrade() -> None:
    """
    Remove Phase 4 tables and columns.
    """

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS tr_autopilot_trade_journal_updated ON autopilot_trade_journal")
    op.execute("DROP TRIGGER IF EXISTS tr_autopilot_analytics_cache_updated ON autopilot_analytics_cache")
    op.execute("DROP TRIGGER IF EXISTS tr_autopilot_template_ratings_updated ON autopilot_template_ratings")

    # Drop indexes
    op.drop_index('idx_templates_public', table_name='autopilot_templates')
    op.drop_index('idx_templates_system', table_name='autopilot_templates')
    op.drop_index('idx_strategies_share_token', table_name='autopilot_strategies')

    # Drop new tables
    op.drop_table('autopilot_template_ratings')
    op.drop_table('autopilot_backtests')
    op.drop_table('autopilot_reports')
    op.drop_table('autopilot_analytics_cache')
    op.drop_table('autopilot_trade_journal')

    # Drop columns from autopilot_strategies
    op.drop_column('autopilot_strategies', 'shared_at')
    op.drop_column('autopilot_strategies', 'share_token')
    op.drop_column('autopilot_strategies', 'share_mode')

    # Drop columns from autopilot_templates
    op.drop_column('autopilot_templates', 'educational_content')
    op.drop_column('autopilot_templates', 'thumbnail_url')
    op.drop_column('autopilot_templates', 'iv_environment')
    op.drop_column('autopilot_templates', 'market_outlook')
    op.drop_column('autopilot_templates', 'max_risk_pct')
    op.drop_column('autopilot_templates', 'expected_return_pct')
    op.drop_column('autopilot_templates', 'position_type')
    op.drop_column('autopilot_templates', 'underlying')
    op.drop_column('autopilot_templates', 'author_name')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS autopilot_share_mode CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_backtest_status CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_report_format CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_report_type CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_template_category CASCADE")
    op.execute("DROP TYPE IF EXISTS autopilot_exit_reason CASCADE")

    # Note: We cannot remove enum values from autopilot_log_event in PostgreSQL
    # without recreating the type, which is complex. Leaving them as-is.

    print("AutoPilot Phase 4 migration rolled back successfully!")
