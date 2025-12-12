"""
Constants API endpoints

Provides centralized constants to frontend including strategy types, categories, etc.
"""

from fastapi import APIRouter

from app.constants.strategy_types import (
    STRATEGY_TYPES,
    CATEGORIES,
    get_all_strategies_grouped,
    get_strategies_by_category,
    get_strategy_by_name
)

router = APIRouter()


@router.get("/strategy-types")
async def get_strategy_types():
    """
    Get all strategy types with their leg configurations.

    Used by frontend to populate Strategy Type dropdown and auto-populate legs.

    Returns:
        dict: Contains strategy_types (all strategies) and categories (category metadata)
    """
    return {
        "strategy_types": STRATEGY_TYPES,
        "categories": CATEGORIES
    }


@router.get("/strategy-types/grouped")
async def get_strategy_types_grouped():
    """
    Get all strategy types grouped by category.

    Returns:
        dict: Strategies grouped by category key
    """
    return {
        "grouped": get_all_strategies_grouped(),
        "categories": CATEGORIES
    }


@router.get("/strategy-types/{strategy_name}")
async def get_strategy_type(strategy_name: str):
    """
    Get a specific strategy type by name.

    Args:
        strategy_name: The key name of the strategy (e.g., 'iron_condor')

    Returns:
        dict: Strategy configuration including legs, or 404 if not found
    """
    strategy = get_strategy_by_name(strategy_name)
    if not strategy:
        return {"error": f"Strategy '{strategy_name}' not found", "status": 404}
    return strategy


@router.get("/categories")
async def get_categories():
    """
    Get all strategy categories with display properties.

    Returns:
        dict: Category definitions with name, color, icon
    """
    return {"categories": CATEGORIES}


@router.get("/categories/{category_name}/strategies")
async def get_category_strategies(category_name: str):
    """
    Get all strategies in a specific category.

    Args:
        category_name: The category key (e.g., 'bullish', 'neutral')

    Returns:
        list: All strategies in the category
    """
    if category_name not in CATEGORIES:
        return {"error": f"Category '{category_name}' not found", "status": 404}

    return {
        "category": CATEGORIES[category_name],
        "strategies": get_strategies_by_category(category_name)
    }
