"""
AI Configuration API Endpoints

REST API for managing user AI trading configuration.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.users import User
from app.models.strategy_templates import StrategyTemplate
from app.schemas.ai import (
    AIUserConfigResponse,
    AIUserConfigUpdate,
    AIConfigDefaults,
    PositionSizingConfig,
    DeploymentScheduleConfig,
    AILimitsConfig,
    ConfidenceTier,
    ClaudeKeyValidationRequest,
    ClaudeKeyValidationResponse,
    PaperTradingStatus
)
from app.services.ai.config_service import AIConfigService
from app.utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=AIUserConfigResponse, summary="Get AI Configuration")
async def get_ai_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's AI configuration.

    Creates default configuration if one doesn't exist.

    Returns:
        AIUserConfigResponse: User's AI configuration
    """
    try:
        config = await AIConfigService.get_or_create_config(user.id, db)
        return AIUserConfigResponse.model_validate(config)

    except Exception as e:
        logger.error(f"Error getting AI config for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get AI configuration: {str(e)}"
        )


@router.put("/", response_model=AIUserConfigResponse, summary="Update AI Configuration")
async def update_ai_config(
    updates: AIUserConfigUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's AI configuration.

    Validates all updates before applying. Partial updates supported - only
    provided fields will be updated.

    Args:
        updates: Configuration updates to apply

    Returns:
        AIUserConfigResponse: Updated configuration

    Raises:
        HTTPException 400: If validation fails
        HTTPException 404: If configuration not found
        HTTPException 500: If update fails
    """
    try:
        # Validate strategy IDs if provided
        if updates.allowed_strategies is not None:
            is_valid, errors = await AIConfigService.validate_allowed_strategies(
                updates.allowed_strategies, db
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid strategy IDs: {'; '.join(errors)}"
                )

        # Update configuration
        config = await AIConfigService.update_config(user.id, updates, db)
        return AIUserConfigResponse.model_validate(config)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating AI config for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI configuration: {str(e)}"
        )


@router.get("/defaults", response_model=AIConfigDefaults, summary="Get Default Configuration")
async def get_defaults():
    """
    Get default AI configuration template.

    This endpoint does not require authentication and can be used to show
    users what the default configuration looks like before they create one.

    Returns:
        AIConfigDefaults: Default configuration values
    """
    return AIConfigDefaults(
        deployment=DeploymentScheduleConfig(
            auto_deploy_enabled=False,
            deploy_time="09:20",
            deploy_days=["MON", "TUE", "WED", "THU", "FRI"],
            skip_event_days=True,
            skip_weekly_expiry=False
        ),
        sizing=PositionSizingConfig(
            sizing_mode="tiered",
            base_lots=1,
            confidence_tiers=[
                ConfidenceTier(name="SKIP", min=0, max=60, multiplier=0),
                ConfidenceTier(name="LOW", min=60, max=75, multiplier=1.0),
                ConfidenceTier(name="MEDIUM", min=75, max=85, multiplier=1.5),
                ConfidenceTier(name="HIGH", min=85, max=100, multiplier=2.0)
            ]
        ),
        limits=AILimitsConfig(
            max_lots_per_strategy=2,
            max_lots_per_day=6,
            max_strategies_per_day=5,
            min_confidence_to_trade=60.0,
            max_vix_to_trade=25.0,
            min_dte_to_enter=2,
            weekly_loss_limit=50000.00
        )
    )


@router.get("/strategies", response_model=List[dict], summary="Get Allowed Strategies")
async def get_allowed_strategies(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of strategy templates allowed for this user.

    Returns full strategy template details for each allowed template ID.

    Returns:
        List[dict]: List of allowed strategy templates
    """
    try:
        # Get user's config
        config = await AIConfigService.get_or_create_config(user.id, db)

        if not config.allowed_strategies:
            return []

        # Fetch strategy templates
        result = await db.execute(
            select(StrategyTemplate).where(
                StrategyTemplate.id.in_(config.allowed_strategies)
            )
        )
        templates = result.scalars().all()

        # Convert to dicts
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "risk_profile": t.risk_profile,
                "max_profit": t.max_profit,
                "max_loss": t.max_loss
            }
            for t in templates
        ]

    except Exception as e:
        logger.error(f"Error getting allowed strategies for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get allowed strategies: {str(e)}"
        )


@router.put("/strategies", response_model=AIUserConfigResponse, summary="Update Allowed Strategies")
async def update_allowed_strategies(
    strategy_ids: List[int],
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update list of allowed strategy templates.

    Validates that all template IDs exist before updating.

    Args:
        strategy_ids: List of strategy template IDs to allow

    Returns:
        AIUserConfigResponse: Updated configuration

    Raises:
        HTTPException 400: If any template ID is invalid
    """
    try:
        # Validate strategy IDs
        is_valid, errors = await AIConfigService.validate_allowed_strategies(
            strategy_ids, db
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy IDs: {'; '.join(errors)}"
            )

        # Update config
        updates = AIUserConfigUpdate(allowed_strategies=strategy_ids)
        config = await AIConfigService.update_config(user.id, updates, db)

        return AIUserConfigResponse.model_validate(config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating allowed strategies for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update allowed strategies: {str(e)}"
        )


@router.get("/sizing", response_model=PositionSizingConfig, summary="Get Position Sizing Config")
async def get_sizing_config(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get position sizing configuration.

    Returns:
        PositionSizingConfig: Position sizing settings
    """
    try:
        config = await AIConfigService.get_or_create_config(user.id, db)

        # Convert confidence_tiers from JSONB to Pydantic models
        tiers = [ConfidenceTier(**tier) for tier in config.confidence_tiers]

        return PositionSizingConfig(
            sizing_mode=config.sizing_mode,
            base_lots=config.base_lots,
            confidence_tiers=tiers
        )

    except Exception as e:
        logger.error(f"Error getting sizing config for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sizing configuration: {str(e)}"
        )


@router.put("/sizing", response_model=AIUserConfigResponse, summary="Update Position Sizing Config")
async def update_sizing_config(
    sizing: PositionSizingConfig,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update position sizing configuration.

    Validates that tiers have no gaps or overlaps.

    Args:
        sizing: Position sizing configuration

    Returns:
        AIUserConfigResponse: Updated configuration

    Raises:
        HTTPException 400: If validation fails
    """
    try:
        # Pydantic validation already ensures no gaps/overlaps
        updates = AIUserConfigUpdate(
            sizing_mode=sizing.sizing_mode,
            base_lots=sizing.base_lots,
            confidence_tiers=sizing.confidence_tiers
        )

        config = await AIConfigService.update_config(user.id, updates, db)
        return AIUserConfigResponse.model_validate(config)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating sizing config for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sizing configuration: {str(e)}"
        )


@router.post("/validate-claude", response_model=ClaudeKeyValidationResponse, summary="Validate Claude API Key")
async def validate_claude_key(
    request: ClaudeKeyValidationRequest
):
    """
    Validate Claude API key by making a test call.

    Does NOT save the key - use PUT /config to save after validation.

    Args:
        request: Contains API key to validate

    Returns:
        ClaudeKeyValidationResponse: Validation result
    """
    try:
        is_valid, message = await AIConfigService.validate_claude_api_key(
            request.api_key
        )

        return ClaudeKeyValidationResponse(
            valid=is_valid,
            message=message
        )

    except Exception as e:
        logger.error(f"Error validating Claude API key: {e}")
        return ClaudeKeyValidationResponse(
            valid=False,
            message=f"Validation error: {str(e)}"
        )


@router.get("/paper-trading/status", response_model=PaperTradingStatus, summary="Get Paper Trading Status")
async def get_paper_trading_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paper trading graduation status.

    Returns progress toward graduation criteria including:
    - Number of trades completed
    - Win rate percentage
    - Total P&L
    - Graduation approval status

    Returns:
        PaperTradingStatus: Graduation status and progress
    """
    try:
        config = await AIConfigService.get_or_create_config(user.id, db)
        status = await AIConfigService.get_paper_trading_status(config, db)

        return status

    except Exception as e:
        logger.error(f"Error getting paper trading status for user {user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get paper trading status: {str(e)}"
        )
