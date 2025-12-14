"""Fix missing autopilot columns

Revision ID: 0f99bf85164b
Revises: 006_autopilot_phase5i
Create Date: 2025-12-14 15:21:06.796837

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f99bf85164b'
down_revision: Union[str, Sequence[str], None] = '006_autopilot_phase5i'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to autopilot_strategies table if they don't exist."""

    # Use raw SQL to add columns only if they don't exist
    op.execute("""
        DO $$
        BEGIN
            -- Add greeks_snapshot column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='greeks_snapshot'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN greeks_snapshot JSONB;
            END IF;

            -- Add position_legs_snapshot column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='position_legs_snapshot'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN position_legs_snapshot JSONB;
            END IF;

            -- Add net_delta column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='net_delta'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN net_delta NUMERIC(6, 4);
            END IF;

            -- Add net_theta column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='net_theta'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN net_theta NUMERIC(10, 2);
            END IF;

            -- Add net_gamma column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='net_gamma'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN net_gamma NUMERIC(6, 4);
            END IF;

            -- Add net_vega column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='net_vega'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN net_vega NUMERIC(10, 2);
            END IF;

            -- Add breakeven_lower column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='breakeven_lower'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN breakeven_lower NUMERIC(10, 2);
            END IF;

            -- Add breakeven_upper column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='breakeven_upper'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN breakeven_upper NUMERIC(10, 2);
            END IF;

            -- Add dte column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_strategies' AND column_name='dte'
            ) THEN
                ALTER TABLE autopilot_strategies ADD COLUMN dte INTEGER;
            END IF;

            -- Add missing columns to autopilot_user_settings table
            -- Add delta_watch_threshold column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_user_settings' AND column_name='delta_watch_threshold'
            ) THEN
                ALTER TABLE autopilot_user_settings ADD COLUMN delta_watch_threshold NUMERIC(4, 2) NOT NULL DEFAULT 0.20;
            END IF;

            -- Add delta_warning_threshold column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_user_settings' AND column_name='delta_warning_threshold'
            ) THEN
                ALTER TABLE autopilot_user_settings ADD COLUMN delta_warning_threshold NUMERIC(4, 2) NOT NULL DEFAULT 0.30;
            END IF;

            -- Add delta_danger_threshold column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_user_settings' AND column_name='delta_danger_threshold'
            ) THEN
                ALTER TABLE autopilot_user_settings ADD COLUMN delta_danger_threshold NUMERIC(4, 2) NOT NULL DEFAULT 0.40;
            END IF;

            -- Add delta_alert_enabled column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_user_settings' AND column_name='delta_alert_enabled'
            ) THEN
                ALTER TABLE autopilot_user_settings ADD COLUMN delta_alert_enabled BOOLEAN NOT NULL DEFAULT true;
            END IF;

            -- Add suggestions_enabled column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_user_settings' AND column_name='suggestions_enabled'
            ) THEN
                ALTER TABLE autopilot_user_settings ADD COLUMN suggestions_enabled BOOLEAN NOT NULL DEFAULT true;
            END IF;

            -- Add prefer_round_strikes column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='autopilot_user_settings' AND column_name='prefer_round_strikes'
            ) THEN
                ALTER TABLE autopilot_user_settings ADD COLUMN prefer_round_strikes BOOLEAN NOT NULL DEFAULT true;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """This migration is for fixing missing columns - downgrade not supported."""
    pass
