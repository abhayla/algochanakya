"""
Strategy Wizard API Routes

Provides pre-defined strategy templates, AI-powered recommendations, and deployment functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import date
from decimal import Decimal

from app.database import get_db
from app.config import settings
from app.models import User, StrategyTemplate, Strategy, StrategyLeg
from app.schemas.strategy_templates import (
    StrategyTemplateListItem,
    StrategyTemplateDetail,
    CategoriesResponse,
    CategoryCount,
    WizardInputs,
    WizardResponse,
    WizardRecommendation,
    DeployRequest,
    DeployResponse,
    DeployLeg,
    CompareRequest,
    CompareResponse,
    CompareItem,
    PopularStrategiesResponse,
    MarketOutlook,
    VolatilityPreference,
    RiskLevel,
    StrategyCategory,
)
from app.utils.dependencies import get_current_user, get_current_broker_connection
from app.models.broker_connections import BrokerConnection
from app.constants.trading import LOT_SIZES, get_strike_step

router = APIRouter()

# Category display names
CATEGORY_DISPLAY_NAMES = {
    "bullish": "Bullish",
    "bearish": "Bearish",
    "neutral": "Neutral",
    "volatile": "Volatile",
    "income": "Income",
    "advanced": "Advanced",
}


# ==================== TEMPLATES ====================

@router.get("/templates", response_model=List[StrategyTemplateListItem])
async def list_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty level"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    theta_positive: Optional[bool] = Query(None, description="Filter for theta positive strategies"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List all strategy templates with optional filtering.

    Filters:
    - category: bullish, bearish, neutral, volatile, income, advanced
    - risk_level: low, medium, high
    - difficulty: beginner, intermediate, advanced
    - search: Search in name and description
    - theta_positive: True for income strategies
    """
    try:
        query = select(StrategyTemplate)

        if category:
            query = query.where(StrategyTemplate.category == category.lower())
        if risk_level:
            query = query.where(StrategyTemplate.risk_level == risk_level.lower())
        if difficulty:
            query = query.where(StrategyTemplate.difficulty_level == difficulty.lower())
        if theta_positive is not None:
            query = query.where(StrategyTemplate.theta_positive == theta_positive)
        if search:
            search_term = f"%{search.lower()}%"
            query = query.where(
                (func.lower(StrategyTemplate.name).like(search_term)) |
                (func.lower(StrategyTemplate.display_name).like(search_term)) |
                (func.lower(StrategyTemplate.description).like(search_term))
            )

        query = query.order_by(StrategyTemplate.popularity_score.desc())
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        templates = result.scalars().all()

        return templates

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.get("/templates/categories", response_model=CategoriesResponse)
async def get_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all categories with counts.
    """
    try:
        query = select(
            StrategyTemplate.category,
            func.count(StrategyTemplate.id).label("count")
        ).group_by(StrategyTemplate.category)

        result = await db.execute(query)
        rows = result.all()

        categories = [
            CategoryCount(
                category=row.category,
                count=row.count,
                display_name=CATEGORY_DISPLAY_NAMES.get(row.category, row.category.title())
            )
            for row in rows
        ]

        total = sum(c.count for c in categories)

        return CategoriesResponse(categories=categories, total=total)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(e)}"
        )


@router.get("/templates/{name}", response_model=StrategyTemplateDetail)
async def get_template(
    name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get full details of a strategy template by name.
    """
    try:
        result = await db.execute(
            select(StrategyTemplate).where(StrategyTemplate.name == name.lower())
        )
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy template '{name}' not found"
            )

        return template

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


# ==================== WIZARD ====================

@router.post("/wizard", response_model=WizardResponse)
async def run_wizard(
    inputs: WizardInputs,
    db: AsyncSession = Depends(get_db)
):
    """
    AI-powered strategy recommendation wizard.

    Scoring weights:
    - Market outlook match: 40 points
    - Volatility preference match: 25 points
    - Risk tolerance match: 25 points
    - Bonus points: 10 points (experience, capital, etc.)

    Returns top 5 recommendations sorted by score.
    """
    try:
        # Get all templates
        result = await db.execute(select(StrategyTemplate))
        templates = result.scalars().all()

        recommendations = []

        for template in templates:
            score = 0
            match_reasons = []
            warnings = []

            # Market outlook scoring (40 points)
            outlook_match = _score_outlook(inputs.market_outlook.value, template.market_outlook)
            score += outlook_match["score"]
            if outlook_match["reason"]:
                match_reasons.append(outlook_match["reason"])
            if outlook_match.get("warning"):
                warnings.append(outlook_match["warning"])

            # Volatility preference scoring (25 points)
            vol_match = _score_volatility(inputs.volatility_view.value, template.volatility_preference)
            score += vol_match["score"]
            if vol_match["reason"]:
                match_reasons.append(vol_match["reason"])

            # Risk tolerance scoring (25 points)
            risk_match = _score_risk(inputs.risk_tolerance.value, template.risk_level)
            score += risk_match["score"]
            if risk_match["reason"]:
                match_reasons.append(risk_match["reason"])
            if risk_match.get("warning"):
                warnings.append(risk_match["warning"])

            # Bonus points (10 points)
            bonus = _calculate_bonus(inputs, template)
            score += bonus["score"]
            match_reasons.extend(bonus.get("reasons", []))

            # Only include if score > 30
            if score > 30:
                recommendations.append(WizardRecommendation(
                    template=template,
                    score=min(score, 100),
                    match_reasons=match_reasons,
                    warnings=warnings if warnings else None
                ))

        # Sort by score descending, take top 5
        recommendations.sort(key=lambda x: x.score, reverse=True)
        top_recommendations = recommendations[:5]

        return WizardResponse(
            recommendations=top_recommendations,
            inputs=inputs,
            total_matches=len(recommendations)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wizard failed: {str(e)}"
        )


def _score_outlook(user_outlook: str, template_outlook: str) -> dict:
    """Score market outlook match. Max 40 points."""
    if user_outlook == template_outlook:
        return {"score": 40, "reason": f"Perfect match for {user_outlook} market"}

    # Partial matches
    if user_outlook == "bullish" and template_outlook == "neutral":
        return {"score": 20, "reason": "Works in sideways-to-bullish markets"}
    if user_outlook == "bearish" and template_outlook == "neutral":
        return {"score": 20, "reason": "Works in sideways-to-bearish markets"}
    if user_outlook == "volatile" and template_outlook in ["bullish", "bearish"]:
        return {"score": 15, "reason": "Can profit from directional moves", "warning": "Requires direction to be correct"}
    if user_outlook == "neutral" and template_outlook in ["bullish", "bearish"]:
        return {"score": 10, "reason": "Limited directional bias"}

    return {"score": 0, "reason": None}


def _score_volatility(user_vol: str, template_vol: str) -> dict:
    """Score volatility preference match. Max 25 points."""
    if template_vol == "any":
        return {"score": 20, "reason": "Works in any volatility environment"}
    if user_vol == template_vol:
        return {"score": 25, "reason": f"Ideal for {user_vol.replace('_', ' ').title()} environments"}
    if user_vol == "any":
        return {"score": 15, "reason": "Suitable for current conditions"}

    return {"score": 0, "reason": None}


def _score_risk(user_risk: str, template_risk: str) -> dict:
    """Score risk tolerance match. Max 25 points."""
    if user_risk == template_risk:
        return {"score": 25, "reason": f"Matches your {user_risk} risk tolerance"}

    risk_order = {"low": 1, "medium": 2, "high": 3}
    user_level = risk_order.get(user_risk, 2)
    template_level = risk_order.get(template_risk, 2)

    if user_level >= template_level:
        return {"score": 15, "reason": "Within your risk tolerance"}
    else:
        return {"score": 5, "reason": None, "warning": f"Higher risk than your {user_risk} preference"}


def _calculate_bonus(inputs: WizardInputs, template: StrategyTemplate) -> dict:
    """Calculate bonus points. Max 10 points."""
    bonus = 0
    reasons = []

    # Experience level bonus
    if inputs.experience_level:
        exp_order = {"beginner": 1, "intermediate": 2, "advanced": 3}
        user_exp = exp_order.get(inputs.experience_level.value, 2)
        template_exp = exp_order.get(template.difficulty_level, 2)

        if user_exp >= template_exp:
            bonus += 5
            if template.difficulty_level == "beginner":
                reasons.append("Easy to understand and execute")
        elif user_exp == template_exp - 1:
            bonus += 2
            reasons.append("Good for learning")

    # Capital size bonus
    if inputs.capital_size:
        if inputs.capital_size == template.capital_requirement:
            bonus += 3
            reasons.append(f"Suitable for {inputs.capital_size} capital")

    # Popularity bonus
    if template.popularity_score >= 80:
        bonus += 2
        reasons.append("Popular among traders")

    return {"score": bonus, "reasons": reasons}


# ==================== DEPLOY ====================

@router.post("/deploy", response_model=DeployResponse)
async def deploy_template(
    request: DeployRequest,
    user: User = Depends(get_current_user),
    broker_connection: BrokerConnection = Depends(get_current_broker_connection),
    db: AsyncSession = Depends(get_db)
):
    """
    Deploy a strategy template with live market data.

    - Fetches current spot price from Kite
    - Calculates ATM strike
    - Determines actual strikes based on template offsets
    - Fetches instrument tokens and LTP for each leg
    """
    from kiteconnect import KiteConnect

    try:
        # Get template
        result = await db.execute(
            select(StrategyTemplate).where(StrategyTemplate.name == request.template_name.lower())
        )
        template = result.scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy template '{request.template_name}' not found"
            )

        # Initialize Kite
        kite = KiteConnect(api_key=settings.KITE_API_KEY)
        kite.set_access_token(broker_connection.access_token)

        # Get underlying symbol and lot size
        underlying = request.underlying.upper()
        underlying_symbol = f"NSE:{underlying}"
        if underlying == "BANKNIFTY":
            underlying_symbol = "NSE:NIFTY BANK"

        lot_size = LOT_SIZES.get(underlying, 25)

        # Get spot price
        try:
            ltp_data = kite.ltp([underlying_symbol])
            spot_price = ltp_data[underlying_symbol]["last_price"]
        except Exception:
            # Fallback spot prices
            spot_price = {"NIFTY": 24000, "BANKNIFTY": 52000, "FINNIFTY": 24000}.get(underlying, 24000)

        # Calculate ATM strike
        strike_interval = get_strike_step(underlying)
        atm_strike = request.atm_strike or Decimal(round(spot_price / strike_interval) * strike_interval)

        # Get expiry
        if request.expiry:
            expiry = request.expiry
        else:
            # Get nearest Thursday (weekly expiry)
            from datetime import timedelta
            today = date.today()
            days_until_thursday = (3 - today.weekday()) % 7
            if days_until_thursday == 0 and today.weekday() == 3:
                days_until_thursday = 7  # Skip to next Thursday if today is Thursday
            expiry = today + timedelta(days=days_until_thursday)

        # Build legs from template
        deployed_legs = []
        for leg_config in template.legs_config:
            leg_type = leg_config.get("type", "CE")
            position = leg_config.get("position", "SELL")
            strike_offset = leg_config.get("strike_offset", 0)

            # Skip EQ legs for now (futures/stock)
            if leg_type == "EQ":
                continue

            # Calculate actual strike
            strike = atm_strike + Decimal(strike_offset)

            # Build tradingsymbol
            expiry_str = expiry.strftime("%y%b").upper()  # e.g., "24DEC"
            day_str = str(expiry.day)
            tradingsymbol = f"{underlying}{expiry_str[0:2]}{expiry.strftime('%b').upper()}{strike}{leg_type}"

            # Try to get instrument token (simplified - in production would query instruments table)
            instrument_token = None
            ltp = None

            try:
                instrument_str = f"NFO:{tradingsymbol}"
                ltp_data = kite.ltp([instrument_str])
                if instrument_str in ltp_data:
                    ltp = ltp_data[instrument_str]["last_price"]
                    instrument_token = ltp_data[instrument_str].get("instrument_token")
            except Exception:
                pass

            deployed_legs.append(DeployLeg(
                type=leg_type,
                position=position,
                strike=strike,
                expiry=expiry,
                instrument_token=instrument_token or 0,
                tradingsymbol=tradingsymbol,
                ltp=ltp,
                lots=request.lots
            ))

        # Create Strategy in database
        strategy = Strategy(
            user_id=user.id,
            name=template.display_name,
            underlying=underlying,
            status="open"
        )
        db.add(strategy)
        await db.flush()

        # Create StrategyLeg records
        for leg in deployed_legs:
            strategy_leg = StrategyLeg(
                strategy_id=strategy.id,
                expiry_date=leg.expiry,
                contract_type=leg.type,
                transaction_type="BUY" if leg.position == "BUY" else "SELL",
                strike_price=leg.strike,
                lots=leg.lots,
                strategy_type="hedged",
                entry_price=leg.ltp,
                instrument_token=leg.instrument_token,
                position_status="pending"
            )
            db.add(strategy_leg)

        await db.commit()

        return DeployResponse(
            template_name=template.name,
            display_name=template.display_name,
            underlying=underlying,
            spot_price=spot_price,
            atm_strike=atm_strike,
            expiry=expiry,
            legs=deployed_legs,
            estimated_premium=None,  # Could calculate based on LTPs
            margin_required=None,
            strategy_id=str(strategy.id)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy template: {str(e)}"
        )


# ==================== COMPARE ====================

@router.post("/compare", response_model=CompareResponse)
async def compare_strategies(
    request: CompareRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Compare multiple strategy templates side by side.
    """
    try:
        result = await db.execute(
            select(StrategyTemplate).where(
                StrategyTemplate.name.in_([name.lower() for name in request.template_names])
            )
        )
        templates = result.scalars().all()

        if len(templates) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 valid templates required for comparison"
            )

        strategies = []
        comparison_matrix = {}

        for template in templates:
            metrics = {
                "max_profit": template.max_profit,
                "max_loss": template.max_loss,
                "win_probability": template.win_probability,
                "risk_level": template.risk_level,
                "theta_positive": template.theta_positive,
                "vega_positive": template.vega_positive,
                "delta_neutral": template.delta_neutral,
                "capital_requirement": template.capital_requirement,
                "difficulty": template.difficulty_level,
                "num_legs": len(template.legs_config),
            }

            strategies.append(CompareItem(
                template=template,
                metrics=metrics
            ))

            comparison_matrix[template.name] = metrics

        return CompareResponse(
            strategies=strategies,
            comparison_matrix=comparison_matrix
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare strategies: {str(e)}"
        )


# ==================== POPULAR ====================

@router.get("/popular", response_model=PopularStrategiesResponse)
async def get_popular_strategies(
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Get most popular strategy templates.
    """
    try:
        result = await db.execute(
            select(StrategyTemplate)
            .order_by(StrategyTemplate.popularity_score.desc())
            .limit(limit)
        )
        templates = result.scalars().all()

        return PopularStrategiesResponse(strategies=templates)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular strategies: {str(e)}"
        )
