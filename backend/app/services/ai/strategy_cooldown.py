"""
Strategy Cooldown Service

Prevents repeated losses from the same strategy-regime combination by implementing
progressive cooldown periods based on failure frequency and recency.
"""

import logging
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from uuid import UUID

from app.models.ai_strategy_cooldown import AIStrategyCooldown
from app.services.ai.market_regime import RegimeType

logger = logging.getLogger(__name__)


class StrategyCooldownService:
    """
    Strategy-Regime cooldown manager.

    Tracks failures and implements progressive cooldown periods:
    - 1 failure: 1 day cooldown
    - 2 failures in 7 days: 3 day cooldown
    - 3+ failures in 14 days: 7 day cooldown + alert user

    Prevents AI from repeatedly deploying losing strategies in specific regimes.
    """

    # Cooldown rules
    COOLDOWN_RULES = [
        {
            "failure_count": 1,
            "lookback_days": None,  # No lookback for first failure
            "cooldown_days": 1,
            "description": "First failure - 1 day cooldown"
        },
        {
            "failure_count": 2,
            "lookback_days": 7,
            "cooldown_days": 3,
            "description": "2 failures in 7 days - 3 day cooldown"
        },
        {
            "failure_count": 3,
            "lookback_days": 14,
            "cooldown_days": 7,
            "description": "3+ failures in 14 days - 7 day cooldown (alert user)"
        }
    ]

    def __init__(self, db: AsyncSession):
        """
        Initialize Cooldown Service.

        Args:
            db: Async database session
        """
        self.db = db

    async def record_failure(
        self,
        user_id: UUID,
        strategy_name: str,
        regime_type: RegimeType,
        loss_amount: Decimal
    ) -> AIStrategyCooldown:
        """
        Record strategy failure and apply cooldown.

        Args:
            user_id: User UUID
            strategy_name: Strategy name (e.g., "iron_condor")
            regime_type: Market regime type
            loss_amount: Loss amount (positive number)

        Returns:
            AIStrategyCooldown record
        """
        try:
            # Get or create cooldown record
            cooldown_record = await self._get_or_create_cooldown(
                user_id, strategy_name, regime_type
            )

            # Increment failure count
            cooldown_record.failure_count += 1
            cooldown_record.total_loss += abs(loss_amount)
            cooldown_record.last_failure_at = datetime.utcnow()

            # Calculate and apply cooldown
            cooldown_days = self._calculate_cooldown_days(
                cooldown_record.failure_count,
                cooldown_record.created_at
            )

            cooldown_record.cooldown_until = datetime.utcnow() + timedelta(days=cooldown_days)

            await self.db.commit()
            await self.db.refresh(cooldown_record)

            logger.warning(
                f"Strategy failure recorded: user={user_id}, strategy={strategy_name}, "
                f"regime={regime_type.value}, failures={cooldown_record.failure_count}, "
                f"cooldown_until={cooldown_record.cooldown_until}, loss={loss_amount}"
            )

            # Alert user if 3+ failures
            if cooldown_record.failure_count >= 3:
                logger.error(
                    f"ALERT: User {user_id} has {cooldown_record.failure_count} failures "
                    f"for {strategy_name} in {regime_type.value} regime. "
                    f"Total loss: {cooldown_record.total_loss}"
                )

            return cooldown_record

        except Exception as e:
            logger.error(f"Error recording strategy failure: {e}")
            await self.db.rollback()
            raise

    async def is_on_cooldown(
        self,
        user_id: UUID,
        strategy_name: str,
        regime_type: RegimeType
    ) -> bool:
        """
        Check if strategy is on cooldown for current regime.

        Args:
            user_id: User UUID
            strategy_name: Strategy name
            regime_type: Current market regime

        Returns:
            True if strategy is on cooldown, False otherwise
        """
        try:
            # Get cooldown record
            stmt = select(AIStrategyCooldown).where(
                and_(
                    AIStrategyCooldown.user_id == user_id,
                    AIStrategyCooldown.strategy_name == strategy_name,
                    AIStrategyCooldown.regime_type == regime_type.value
                )
            )
            result = await self.db.execute(stmt)
            cooldown_record = result.scalar_one_or_none()

            if not cooldown_record:
                return False

            # Check if cooldown has expired
            if cooldown_record.cooldown_until:
                now = datetime.utcnow()
                is_cooling = now < cooldown_record.cooldown_until

                if is_cooling:
                    logger.debug(
                        f"Strategy {strategy_name} is on cooldown for {regime_type.value} "
                        f"until {cooldown_record.cooldown_until}"
                    )
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking cooldown status: {e}")
            return False  # Fail open - allow trading if error

    async def get_cooldown_until(
        self,
        user_id: UUID,
        strategy_name: str,
        regime_type: RegimeType
    ) -> Optional[datetime]:
        """
        Get cooldown expiration time.

        Args:
            user_id: User UUID
            strategy_name: Strategy name
            regime_type: Market regime

        Returns:
            Cooldown expiration datetime, or None if not on cooldown
        """
        try:
            stmt = select(AIStrategyCooldown).where(
                and_(
                    AIStrategyCooldown.user_id == user_id,
                    AIStrategyCooldown.strategy_name == strategy_name,
                    AIStrategyCooldown.regime_type == regime_type.value
                )
            )
            result = await self.db.execute(stmt)
            cooldown_record = result.scalar_one_or_none()

            if not cooldown_record:
                return None

            # Check if cooldown has expired
            if cooldown_record.cooldown_until:
                now = datetime.utcnow()
                if now < cooldown_record.cooldown_until:
                    return cooldown_record.cooldown_until

            return None

        except Exception as e:
            logger.error(f"Error getting cooldown expiration: {e}")
            return None

    async def get_all_cooldowns(self, user_id: UUID) -> List[AIStrategyCooldown]:
        """
        Get all active cooldowns for user.

        Args:
            user_id: User UUID

        Returns:
            List of active cooldown records
        """
        try:
            now = datetime.utcnow()

            stmt = (
                select(AIStrategyCooldown)
                .where(
                    and_(
                        AIStrategyCooldown.user_id == user_id,
                        AIStrategyCooldown.cooldown_until > now
                    )
                )
                .order_by(desc(AIStrategyCooldown.cooldown_until))
            )
            result = await self.db.execute(stmt)
            cooldowns = result.scalars().all()

            return list(cooldowns)

        except Exception as e:
            logger.error(f"Error getting all cooldowns: {e}")
            return []

    async def clear_cooldown(
        self,
        user_id: UUID,
        strategy_name: str,
        regime_type: RegimeType
    ) -> bool:
        """
        Manually clear cooldown for strategy-regime combination.

        Args:
            user_id: User UUID
            strategy_name: Strategy name
            regime_type: Market regime

        Returns:
            True if cooldown was cleared, False if not found
        """
        try:
            stmt = select(AIStrategyCooldown).where(
                and_(
                    AIStrategyCooldown.user_id == user_id,
                    AIStrategyCooldown.strategy_name == strategy_name,
                    AIStrategyCooldown.regime_type == regime_type.value
                )
            )
            result = await self.db.execute(stmt)
            cooldown_record = result.scalar_one_or_none()

            if not cooldown_record:
                return False

            # Clear cooldown by setting expiration to past
            cooldown_record.cooldown_until = datetime.utcnow() - timedelta(days=1)

            await self.db.commit()

            logger.info(
                f"Manually cleared cooldown: user={user_id}, "
                f"strategy={strategy_name}, regime={regime_type.value}"
            )

            return True

        except Exception as e:
            logger.error(f"Error clearing cooldown: {e}")
            await self.db.rollback()
            return False

    async def _get_or_create_cooldown(
        self,
        user_id: UUID,
        strategy_name: str,
        regime_type: RegimeType
    ) -> AIStrategyCooldown:
        """
        Get or create cooldown record.

        Args:
            user_id: User UUID
            strategy_name: Strategy name
            regime_type: Market regime

        Returns:
            AIStrategyCooldown record
        """
        # Try to get existing record
        stmt = select(AIStrategyCooldown).where(
            and_(
                AIStrategyCooldown.user_id == user_id,
                AIStrategyCooldown.strategy_name == strategy_name,
                AIStrategyCooldown.regime_type == regime_type.value
            )
        )
        result = await self.db.execute(stmt)
        cooldown_record = result.scalar_one_or_none()

        if cooldown_record:
            return cooldown_record

        # Create new record
        cooldown_record = AIStrategyCooldown(
            user_id=user_id,
            strategy_name=strategy_name,
            regime_type=regime_type.value,
            failure_count=0,  # Will be incremented immediately
            total_loss=Decimal('0')
        )
        self.db.add(cooldown_record)
        await self.db.flush()  # Get ID without committing

        logger.info(
            f"Created new cooldown record: user={user_id}, "
            f"strategy={strategy_name}, regime={regime_type.value}"
        )

        return cooldown_record

    def _calculate_cooldown_days(
        self,
        failure_count: int,
        first_failure_at: datetime
    ) -> int:
        """
        Calculate cooldown period based on failure count and timing.

        Args:
            failure_count: Total number of failures
            first_failure_at: Timestamp of first failure

        Returns:
            Number of days for cooldown
        """
        # Apply progressive cooldown rules
        for rule in reversed(self.COOLDOWN_RULES):
            if failure_count >= rule["failure_count"]:
                # Check lookback period if specified
                if rule["lookback_days"]:
                    days_since_first = (datetime.utcnow() - first_failure_at).days
                    if days_since_first > rule["lookback_days"]:
                        # Failures are too old, use lower tier
                        continue

                logger.debug(
                    f"Applying cooldown rule: {rule['description']} "
                    f"(failures={failure_count}, cooldown={rule['cooldown_days']} days)"
                )
                return rule["cooldown_days"]

        # Default: 1 day cooldown
        return 1


__all__ = ["StrategyCooldownService"]
