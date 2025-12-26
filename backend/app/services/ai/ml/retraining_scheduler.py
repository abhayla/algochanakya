"""
Retraining Scheduler

Determines when ML models should be retrained based on user-specific cadence configuration.
Implements volume-based, time-based, and hybrid retraining triggers.

Priority 2.3: Retraining Frequency Optimization
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIUserConfig, AILearningReport

logger = logging.getLogger(__name__)


class RetrainingScheduler:
    """
    Determines when to retrain ML models based on configured cadence.

    Supports three retraining strategies:
    1. **Weekly** (default) - Retrain once per week
    2. **Daily** - Retrain daily (for high-volume users)
    3. **Volume-based** - Retrain after N completed trades

    High-volume users (>50 trades/week) automatically switch from weekly to daily.
    """

    def __init__(self):
        """Initialize retraining scheduler."""
        pass

    async def should_retrain_user_model(
        self,
        user_id: UUID,
        db: AsyncSession,
        force_check: bool = False
    ) -> Dict:
        """
        Check if user's personalized model should be retrained.

        Args:
            user_id: User ID
            db: Database session
            force_check: Skip cache and force fresh check

        Returns:
            Dict with:
                - should_retrain (bool): Whether to retrain
                - reason (str): Reason code (volume_threshold, weekly_cadence, daily_cadence, not_due)
                - trades_since_last (int): Trades completed since last retrain
                - days_since_last (int|None): Days since last retrain
                - next_retrain_date (datetime|None): Next scheduled retrain (time-based only)
        """
        # Get user config
        stmt = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await db.execute(stmt)
        user_config = result.scalar_one_or_none()

        if not user_config:
            logger.warning(f"No AI config found for user {user_id}")
            return {
                'should_retrain': False,
                'reason': 'no_config',
                'trades_since_last': 0,
                'days_since_last': None,
                'next_retrain_date': None
            }

        # Check cadence mode
        cadence = user_config.retraining_cadence
        trades_since_last = user_config.trades_since_last_retrain
        last_retrain_at = user_config.last_user_model_retrain_at

        # Calculate days since last retrain
        days_since_last = None
        if last_retrain_at:
            days_since_last = (datetime.now(last_retrain_at.tzinfo) - last_retrain_at).days

        # Adaptive cadence: High-volume users switch to daily
        if cadence == 'weekly':
            recent_volume = await self._get_weekly_trade_volume(user_id, db)
            if recent_volume >= user_config.high_volume_trades_per_week:
                logger.info(
                    f"User {user_id} has high volume ({recent_volume} trades/week), "
                    f"switching to daily retraining"
                )
                cadence = 'daily'

        # Volume-based retraining
        if cadence == 'volume_based':
            if trades_since_last >= user_config.retraining_volume_threshold:
                return {
                    'should_retrain': True,
                    'reason': 'volume_threshold',
                    'trades_since_last': trades_since_last,
                    'days_since_last': days_since_last,
                    'next_retrain_date': None,
                    'threshold': user_config.retraining_volume_threshold
                }

        # Daily retraining
        elif cadence == 'daily':
            if last_retrain_at is None:
                # Never retrained before
                return {
                    'should_retrain': True,
                    'reason': 'first_retrain',
                    'trades_since_last': trades_since_last,
                    'days_since_last': None,
                    'next_retrain_date': None
                }

            if days_since_last >= 1:
                return {
                    'should_retrain': True,
                    'reason': 'daily_cadence',
                    'trades_since_last': trades_since_last,
                    'days_since_last': days_since_last,
                    'next_retrain_date': last_retrain_at + timedelta(days=1)
                }

        # Weekly retraining (default)
        elif cadence == 'weekly':
            if last_retrain_at is None:
                # Never retrained before
                return {
                    'should_retrain': True,
                    'reason': 'first_retrain',
                    'trades_since_last': trades_since_last,
                    'days_since_last': None,
                    'next_retrain_date': None
                }

            if days_since_last >= 7:
                return {
                    'should_retrain': True,
                    'reason': 'weekly_cadence',
                    'trades_since_last': trades_since_last,
                    'days_since_last': days_since_last,
                    'next_retrain_date': last_retrain_at + timedelta(days=7)
                }

        # Not due for retraining
        next_retrain_date = None
        if last_retrain_at:
            if cadence == 'daily':
                next_retrain_date = last_retrain_at + timedelta(days=1)
            elif cadence == 'weekly':
                next_retrain_date = last_retrain_at + timedelta(days=7)

        return {
            'should_retrain': False,
            'reason': 'not_due',
            'trades_since_last': trades_since_last,
            'days_since_last': days_since_last,
            'next_retrain_date': next_retrain_date,
            'cadence': cadence
        }

    async def _get_weekly_trade_volume(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> int:
        """
        Get user's trade volume over the last 7 days.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Number of trades completed in last 7 days
        """
        week_ago = datetime.now() - timedelta(days=7)

        # Query learning reports from last 7 days
        stmt = select(AILearningReport).where(
            AILearningReport.user_id == user_id,
            AILearningReport.report_date >= week_ago.date()
        )
        result = await db.execute(stmt)
        reports = result.scalars().all()

        # Sum total trades
        total_trades = sum(report.total_trades for report in reports if report.total_trades)

        return total_trades

    async def record_retrain_event(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> None:
        """
        Record that a model retrain has occurred.

        Updates last_user_model_retrain_at and resets trades_since_last_retrain counter.

        Args:
            user_id: User ID
            db: Database session
        """
        stmt = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await db.execute(stmt)
        user_config = result.scalar_one_or_none()

        if user_config:
            user_config.last_user_model_retrain_at = datetime.now()
            user_config.trades_since_last_retrain = 0
            await db.commit()
            await db.refresh(user_config)

            logger.info(f"Recorded retrain event for user {user_id}")

    async def increment_trade_counter(
        self,
        user_id: UUID,
        db: AsyncSession,
        count: int = 1
    ) -> None:
        """
        Increment the trades_since_last_retrain counter.

        Should be called after each completed trade.

        Args:
            user_id: User ID
            db: Database session
            count: Number of trades to add (default: 1)
        """
        stmt = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await db.execute(stmt)
        user_config = result.scalar_one_or_none()

        if user_config:
            user_config.trades_since_last_retrain += count
            user_config.total_trades_completed += count  # Also update total
            await db.commit()

            logger.debug(
                f"Incremented trade counter for user {user_id}: "
                f"{user_config.trades_since_last_retrain} trades since last retrain"
            )

    async def get_retraining_status(
        self,
        user_id: UUID,
        db: AsyncSession
    ) -> Dict:
        """
        Get comprehensive retraining status for a user.

        Args:
            user_id: User ID
            db: Database session

        Returns:
            Dict with configuration, status, and next retrain info
        """
        stmt = select(AIUserConfig).where(AIUserConfig.user_id == user_id)
        result = await db.execute(stmt)
        user_config = result.scalar_one_or_none()

        if not user_config:
            return {'error': 'no_config'}

        # Check if retrain is due
        retrain_check = await self.should_retrain_user_model(user_id, db)

        # Get weekly volume
        weekly_volume = await self._get_weekly_trade_volume(user_id, db)

        return {
            'cadence': user_config.retraining_cadence,
            'volume_threshold': user_config.retraining_volume_threshold,
            'high_volume_threshold': user_config.high_volume_trades_per_week,
            'trades_since_last_retrain': user_config.trades_since_last_retrain,
            'last_retrain_at': user_config.last_user_model_retrain_at.isoformat() if user_config.last_user_model_retrain_at else None,
            'should_retrain': retrain_check['should_retrain'],
            'retrain_reason': retrain_check['reason'],
            'next_retrain_date': retrain_check['next_retrain_date'].isoformat() if retrain_check.get('next_retrain_date') else None,
            'weekly_trade_volume': weekly_volume,
            'is_high_volume_user': weekly_volume >= user_config.high_volume_trades_per_week,
            'enable_confidence_weighting': user_config.enable_confidence_weighting,
            'min_stability_threshold': float(user_config.min_model_stability_threshold)
        }


__all__ = ["RetrainingScheduler"]
