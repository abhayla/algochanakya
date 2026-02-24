"""
AI Configuration Service

Handles business logic for AI user configuration management including
creation, updates, validation, and helper methods for position sizing and deployment.
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Tuple, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from anthropic import Anthropic

from app.models.ai import AIUserConfig
from app.models.strategy_templates import StrategyTemplate
from app.schemas.ai import (
    AIUserConfigUpdate,
    ConfidenceTier,
    PaperTradingStatus
)
from app.services.ai.market_regime import MarketRegimeClassifier

logger = logging.getLogger(__name__)


class AIConfigService:
    """Service for managing AI user configuration."""

    @staticmethod
    async def get_or_create_config(
        user_id: UUID,
        db: AsyncSession
    ) -> AIUserConfig:
        """
        Get existing AI config for user or create with defaults if doesn't exist.

        Args:
            user_id: User UUID
            db: Database session

        Returns:
            AIUserConfig: User's AI configuration
        """
        try:
            # Try to get existing config
            result = await db.execute(
                select(AIUserConfig).where(AIUserConfig.user_id == user_id)
            )
            config = result.scalar_one_or_none()

            if config:
                logger.info(f"Found existing AI config for user {user_id}")
                return config

            # Create new config with defaults
            logger.info(f"Creating default AI config for user {user_id}")
            config = AIUserConfig(user_id=user_id)
            db.add(config)
            await db.commit()
            await db.refresh(config)

            logger.info(f"Created AI config {config.id} for user {user_id}")
            return config

        except Exception as e:
            logger.error(f"Error getting/creating AI config for user {user_id}: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def update_config(
        user_id: UUID,
        updates: AIUserConfigUpdate,
        db: AsyncSession
    ) -> AIUserConfig:
        """
        Update user's AI configuration.

        Args:
            user_id: User UUID
            updates: Updates to apply
            db: Database session

        Returns:
            AIUserConfig: Updated configuration

        Raises:
            ValueError: If config not found or validation fails
        """
        try:
            # Get existing config
            result = await db.execute(
                select(AIUserConfig).where(AIUserConfig.user_id == user_id)
            )
            config = result.scalar_one_or_none()

            if not config:
                raise ValueError(f"AI config not found for user {user_id}")

            # Apply updates (only non-None values)
            update_data = updates.model_dump(exclude_unset=True, exclude_none=True)

            for field, value in update_data.items():
                # Convert confidence_tiers back to dicts if present
                if field == 'confidence_tiers' and value is not None:
                    value = [tier.model_dump() if hasattr(tier, 'model_dump') else tier
                             for tier in value]

                setattr(config, field, value)

            # Update timestamp
            config.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(config)

            logger.info(f"Updated AI config {config.id} for user {user_id}")
            return config

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating AI config for user {user_id}: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def validate_allowed_strategies(
        strategy_ids: List[int],
        db: AsyncSession
    ) -> Tuple[bool, List[str]]:
        """
        Validate that strategy template IDs exist.

        Args:
            strategy_ids: List of template IDs to validate
            db: Database session

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        if not strategy_ids:
            return True, []

        try:
            result = await db.execute(
                select(StrategyTemplate.id).where(
                    StrategyTemplate.id.in_(strategy_ids)
                )
            )
            existing_ids = {row[0] for row in result.all()}

            missing_ids = set(strategy_ids) - existing_ids
            if missing_ids:
                return False, [f"Template IDs not found: {sorted(missing_ids)}"]

            return True, []

        except Exception as e:
            logger.error(f"Error validating strategy IDs: {e}")
            return False, [f"Validation error: {str(e)}"]

    @staticmethod
    def get_confidence_tier(
        config: AIUserConfig,
        confidence: float
    ) -> Optional[dict]:
        """
        Get the confidence tier for a given confidence score.

        Args:
            config: User's AI configuration
            confidence: Confidence score (0-100)

        Returns:
            Optional[dict]: Matching tier or None if not found
        """
        if not config.confidence_tiers:
            return None

        for tier in config.confidence_tiers:
            if tier['min'] <= confidence <= tier['max']:
                return tier

        return None

    @staticmethod
    def calculate_lots_for_confidence(
        config: AIUserConfig,
        confidence: float
    ) -> int:
        """
        Calculate lot size based on confidence score and tier configuration.

        Args:
            config: User's AI configuration
            confidence: Confidence score (0-100)

        Returns:
            int: Calculated lot size (0 if below threshold or tier not found)
        """
        # Check minimum confidence threshold
        if confidence < float(config.min_confidence_to_trade):
            logger.debug(
                f"Confidence {confidence} below threshold "
                f"{config.min_confidence_to_trade}, returning 0 lots"
            )
            return 0

        # Fixed sizing mode
        if config.sizing_mode == 'fixed':
            return config.base_lots

        # Tiered sizing mode
        if config.sizing_mode == 'tiered':
            tier = AIConfigService.get_confidence_tier(config, confidence)
            if not tier:
                logger.warning(
                    f"No tier found for confidence {confidence}, returning 0 lots"
                )
                return 0

            multiplier = tier.get('multiplier', 0)
            lots = int(config.base_lots * multiplier)

            logger.debug(
                f"Confidence {confidence} in tier '{tier.get('name')}' "
                f"(multiplier {multiplier}), calculated {lots} lots"
            )
            return lots

        # Kelly criterion — requires async db session; this static method cannot call
        # KellyCalculator directly. Callers with db access (deploy.py, order_executor.py)
        # should call KellyCalculator.get_kelly_recommendation() before calling this method.
        # This path is only reached when db is not available — fall back to base_lots.
        if config.sizing_mode == 'kelly':
            logger.info("Kelly sizing requires db session; caller should use KellyCalculator. Falling back to base_lots.")
            return config.base_lots

        logger.error(f"Unknown sizing mode: {config.sizing_mode}")
        return config.base_lots

    @staticmethod
    async def should_deploy_today(
        config: AIUserConfig,
        check_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Check if deployment is allowed today based on configuration.

        Args:
            config: User's AI configuration
            check_date: Date to check (defaults to today)

        Returns:
            Tuple[bool, str]: (should_deploy, reason)
        """
        if not config.auto_deploy_enabled:
            return False, "Auto-deploy is disabled"

        check_date = check_date or date.today()

        # Check day of week
        day_of_week = check_date.strftime('%a').upper()[:3]  # MON, TUE, etc.
        if day_of_week not in config.deploy_days:
            return False, f"{day_of_week} not in deployment days"

        # Check if event day
        if config.skip_event_days:
            is_event, event_name = MarketRegimeClassifier.is_event_day(check_date)
            if is_event:
                return False, f"Event day: {event_name}"

        # Check if weekly expiry (Thursday)
        if config.skip_weekly_expiry and day_of_week == 'THU':
            return False, "Weekly expiry day (Thursday)"

        return True, "Deployment allowed"

    @staticmethod
    async def is_within_limits(
        config: AIUserConfig,
        current_state: dict
    ) -> Tuple[bool, List[str]]:
        """
        Check if current trading state is within configured limits.

        Args:
            config: User's AI configuration
            current_state: Dict with keys:
                - lots_deployed_today: int
                - strategies_deployed_today: int
                - current_vix: float
                - weekly_loss: Decimal

        Returns:
            Tuple[bool, List[str]]: (within_limits, list_of_violations)
        """
        violations = []

        # Check lots limit
        lots_today = current_state.get('lots_deployed_today', 0)
        if lots_today >= config.max_lots_per_day:
            violations.append(
                f"Daily lots limit reached: {lots_today}/{config.max_lots_per_day}"
            )

        # Check strategies limit
        strategies_today = current_state.get('strategies_deployed_today', 0)
        if strategies_today >= config.max_strategies_per_day:
            violations.append(
                f"Daily strategies limit reached: "
                f"{strategies_today}/{config.max_strategies_per_day}"
            )

        # Check VIX limit
        current_vix = current_state.get('current_vix')
        if current_vix is not None and current_vix > float(config.max_vix_to_trade):
            violations.append(
                f"VIX too high: {current_vix} > {config.max_vix_to_trade}"
            )

        # Check weekly loss limit
        weekly_loss = current_state.get('weekly_loss', Decimal('0'))
        if abs(weekly_loss) >= config.weekly_loss_limit:
            violations.append(
                f"Weekly loss limit reached: {weekly_loss}/{config.weekly_loss_limit}"
            )

        within_limits = len(violations) == 0
        return within_limits, violations

    @staticmethod
    async def validate_claude_api_key(api_key: str) -> Tuple[bool, str]:
        """
        Validate Claude API key by making a test call.

        Args:
            api_key: Claude API key to validate

        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        try:
            # Initialize Anthropic client
            client = Anthropic(api_key=api_key)

            # Make a minimal test call
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Cheapest model for validation
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Test"}
                ]
            )

            # If we got here, API key is valid
            logger.info("Claude API key validation successful")
            return True, "API key is valid"

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Claude API key validation failed: {error_msg}")

            # Provide user-friendly error messages
            if "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
                return False, "Invalid API key"
            elif "rate" in error_msg.lower() or "quota" in error_msg.lower():
                return False, "API key valid but rate limit/quota exceeded"
            else:
                return False, f"Validation error: {error_msg}"

    @staticmethod
    async def get_paper_trading_status(
        config: AIUserConfig,
        db: AsyncSession
    ) -> PaperTradingStatus:
        """
        Get paper trading graduation status for user.

        Args:
            config: User's AI configuration
            db: Database session

        Returns:
            PaperTradingStatus: Graduation status with progress

        Note:
            This is a placeholder. Full implementation will come in Week 4
            when trade journal and performance tracking are added.
        """
        return PaperTradingStatus(
            paper_start_date=config.paper_start_date,
            paper_trades_completed=config.paper_trades_completed,
            paper_win_rate=float(config.paper_win_rate),
            paper_total_pnl=config.paper_total_pnl,
            paper_graduation_approved=config.paper_graduation_approved,
            required_trades=25,
            required_win_rate=55.0,
            required_days=15
        )

    @staticmethod
    def can_graduate_to_live(config: AIUserConfig) -> Tuple[bool, List[str]]:
        """
        Check if user meets criteria to graduate from paper to live trading.

        Args:
            config: User's AI configuration

        Returns:
            Tuple[bool, List[str]]: (can_graduate, list_of_unmet_criteria)
        """
        unmet_criteria = []

        # Check trades completed
        if config.paper_trades_completed < 25:
            unmet_criteria.append(
                f"Need {25 - config.paper_trades_completed} more trades "
                f"(completed: {config.paper_trades_completed}/25)"
            )

        # Check win rate
        if float(config.paper_win_rate) < 55.0:
            unmet_criteria.append(
                f"Win rate below 55% (current: {config.paper_win_rate}%)"
            )

        # Check trading days (placeholder - will be implemented in Week 4)
        # For now, assuming start date exists and has been 15+ days
        if config.paper_start_date:
            days_trading = (date.today() - config.paper_start_date).days
            if days_trading < 15:
                unmet_criteria.append(
                    f"Need {15 - days_trading} more trading days "
                    f"(days: {days_trading}/15)"
                )
        else:
            unmet_criteria.append("Paper trading not yet started")

        # Check manual approval
        if not config.paper_graduation_approved:
            unmet_criteria.append("Manual approval not yet granted")

        can_graduate = len(unmet_criteria) == 0
        return can_graduate, unmet_criteria
