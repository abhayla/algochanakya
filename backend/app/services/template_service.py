"""
AutoPilot Template Service

Phase 4: Handles strategy template CRUD, deployment, and rating operations.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.autopilot import (
    AutoPilotTemplate, AutoPilotTemplateRating, AutoPilotStrategy
)
from app.schemas.autopilot import (
    TemplateCreateRequest, TemplateUpdateRequest, TemplateDeployRequest,
    TemplateRatingRequest
)


class TemplateService:
    """Service for managing AutoPilot strategy templates."""

    @staticmethod
    async def list_templates(
        db: AsyncSession,
        user_id: Optional[UUID] = None,
        category: Optional[str] = None,
        underlying: Optional[str] = None,
        risk_level: Optional[str] = None,
        market_outlook: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        include_system: bool = True,
        include_public: bool = True,
        include_own: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """List templates with filters and pagination."""

        # Build base query
        conditions = []

        if include_system and include_public and include_own and user_id:
            # Show system, public, and user's own templates
            conditions.append(
                or_(
                    AutoPilotTemplate.is_system == True,
                    AutoPilotTemplate.is_public == True,
                    AutoPilotTemplate.user_id == user_id
                )
            )
        elif include_system and include_public:
            conditions.append(
                or_(
                    AutoPilotTemplate.is_system == True,
                    AutoPilotTemplate.is_public == True
                )
            )
        elif user_id and include_own:
            conditions.append(AutoPilotTemplate.user_id == user_id)

        # Apply filters
        if category:
            conditions.append(AutoPilotTemplate.category == category)
        if underlying:
            conditions.append(AutoPilotTemplate.underlying == underlying)
        if risk_level:
            conditions.append(AutoPilotTemplate.risk_level == risk_level)
        if market_outlook:
            conditions.append(AutoPilotTemplate.market_outlook == market_outlook)
        if tags:
            conditions.append(AutoPilotTemplate.tags.contains(tags))
        if search:
            search_filter = or_(
                AutoPilotTemplate.name.ilike(f"%{search}%"),
                AutoPilotTemplate.description.ilike(f"%{search}%")
            )
            conditions.append(search_filter)

        # Count total
        count_query = select(func.count(AutoPilotTemplate.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Fetch templates
        query = select(AutoPilotTemplate)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(
            AutoPilotTemplate.is_system.desc(),
            AutoPilotTemplate.avg_rating.desc().nullslast(),
            AutoPilotTemplate.usage_count.desc()
        )
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        templates = result.scalars().all()

        return {
            "templates": templates,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    @staticmethod
    async def get_template(
        db: AsyncSession,
        template_id: int,
        user_id: Optional[UUID] = None
    ) -> Optional[AutoPilotTemplate]:
        """Get a template by ID."""
        query = select(AutoPilotTemplate).where(AutoPilotTemplate.id == template_id)

        # Only allow access to system, public, or own templates
        if user_id:
            query = query.where(
                or_(
                    AutoPilotTemplate.is_system == True,
                    AutoPilotTemplate.is_public == True,
                    AutoPilotTemplate.user_id == user_id
                )
            )
        else:
            query = query.where(
                or_(
                    AutoPilotTemplate.is_system == True,
                    AutoPilotTemplate.is_public == True
                )
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def create_template(
        db: AsyncSession,
        user_id: UUID,
        request: TemplateCreateRequest,
        author_name: Optional[str] = None
    ) -> AutoPilotTemplate:
        """Create a new template from user's strategy config."""
        template = AutoPilotTemplate(
            user_id=user_id,
            name=request.name,
            description=request.description,
            category=request.category,
            underlying=request.underlying,
            position_type=request.position_type,
            risk_level=request.risk_level,
            market_outlook=request.market_outlook,
            iv_environment=request.iv_environment,
            expected_return_pct=request.expected_return_pct,
            max_risk_pct=request.max_risk_pct,
            tags=request.tags,
            strategy_config=request.strategy_config,
            educational_content=request.educational_content,
            is_public=request.is_public,
            is_system=False,
            author_name=author_name
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        return template

    @staticmethod
    async def update_template(
        db: AsyncSession,
        template_id: int,
        user_id: UUID,
        request: TemplateUpdateRequest
    ) -> Optional[AutoPilotTemplate]:
        """Update user's template."""
        query = select(AutoPilotTemplate).where(
            AutoPilotTemplate.id == template_id,
            AutoPilotTemplate.user_id == user_id,
            AutoPilotTemplate.is_system == False
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            return None

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)

        await db.commit()
        await db.refresh(template)

        return template

    @staticmethod
    async def delete_template(
        db: AsyncSession,
        template_id: int,
        user_id: UUID
    ) -> bool:
        """Delete user's template."""
        query = select(AutoPilotTemplate).where(
            AutoPilotTemplate.id == template_id,
            AutoPilotTemplate.user_id == user_id,
            AutoPilotTemplate.is_system == False
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            return False

        await db.delete(template)
        await db.commit()

        return True

    @staticmethod
    async def deploy_template(
        db: AsyncSession,
        template_id: int,
        user_id: UUID,
        request: TemplateDeployRequest
    ) -> Optional[AutoPilotStrategy]:
        """Deploy a template as a new strategy."""
        # Get template
        query = select(AutoPilotTemplate).where(AutoPilotTemplate.id == template_id)
        query = query.where(
            or_(
                AutoPilotTemplate.is_system == True,
                AutoPilotTemplate.is_public == True,
                AutoPilotTemplate.user_id == user_id
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            return None

        # Get strategy config from template
        strategy_config = template.strategy_config or {}

        # Create strategy from template
        strategy = AutoPilotStrategy(
            user_id=user_id,
            name=request.name or f"{template.name}",
            description=template.description,
            underlying=template.underlying or strategy_config.get('underlying', 'NIFTY'),
            expiry_type=request.expiry_type or strategy_config.get('expiry_type', 'current_week'),
            expiry_date=request.expiry_date,
            lots=request.lots,
            position_type=template.position_type or strategy_config.get('position_type', 'intraday'),
            legs_config=strategy_config.get('legs_config', []),
            entry_conditions=strategy_config.get('entry_conditions', {}),
            adjustment_rules=strategy_config.get('adjustment_rules', []),
            order_settings=strategy_config.get('order_settings', {}),
            risk_settings=strategy_config.get('risk_settings', {}),
            schedule_config=strategy_config.get('schedule_config', {}),
            execution_mode=request.execution_mode.value if request.execution_mode else None,
            source_template_id=template_id,
            status="draft"
        )

        db.add(strategy)

        # Increment usage count
        template.usage_count = (template.usage_count or 0) + 1

        await db.commit()
        await db.refresh(strategy)

        # If activate_immediately is True, activate the strategy
        if request.activate_immediately:
            strategy.status = "waiting"
            strategy.activated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(strategy)

        return strategy

    @staticmethod
    async def rate_template(
        db: AsyncSession,
        template_id: int,
        user_id: UUID,
        request: TemplateRatingRequest
    ) -> Optional[AutoPilotTemplateRating]:
        """Rate a template (create or update rating)."""
        # Check template exists and is accessible
        query = select(AutoPilotTemplate).where(AutoPilotTemplate.id == template_id)
        query = query.where(
            or_(
                AutoPilotTemplate.is_system == True,
                AutoPilotTemplate.is_public == True
            )
        )
        result = await db.execute(query)
        template = result.scalar_one_or_none()

        if not template:
            return None

        # Check for existing rating
        rating_query = select(AutoPilotTemplateRating).where(
            AutoPilotTemplateRating.template_id == template_id,
            AutoPilotTemplateRating.user_id == user_id
        )
        result = await db.execute(rating_query)
        existing_rating = result.scalar_one_or_none()

        if existing_rating:
            # Update existing rating
            existing_rating.rating = request.rating
            existing_rating.review = request.review
            rating = existing_rating
        else:
            # Create new rating
            rating = AutoPilotTemplateRating(
                template_id=template_id,
                user_id=user_id,
                rating=request.rating,
                review=request.review
            )
            db.add(rating)
            template.rating_count = (template.rating_count or 0) + 1

        await db.commit()

        # Recalculate average rating
        avg_query = select(func.avg(AutoPilotTemplateRating.rating)).where(
            AutoPilotTemplateRating.template_id == template_id
        )
        avg_result = await db.execute(avg_query)
        avg_rating = avg_result.scalar()

        template.avg_rating = Decimal(str(round(avg_rating, 2))) if avg_rating else None
        await db.commit()

        await db.refresh(rating)

        return rating

    @staticmethod
    async def get_categories(db: AsyncSession) -> Dict[str, int]:
        """Get template categories with counts."""
        query = select(
            AutoPilotTemplate.category,
            func.count(AutoPilotTemplate.id)
        ).where(
            or_(
                AutoPilotTemplate.is_system == True,
                AutoPilotTemplate.is_public == True
            )
        ).group_by(AutoPilotTemplate.category)

        result = await db.execute(query)
        categories = {}
        for row in result.all():
            if row[0]:
                categories[row[0]] = row[1]

        return categories

    @staticmethod
    async def get_popular_templates(
        db: AsyncSession,
        limit: int = 10
    ) -> List[AutoPilotTemplate]:
        """Get most popular templates by usage."""
        query = select(AutoPilotTemplate).where(
            or_(
                AutoPilotTemplate.is_system == True,
                AutoPilotTemplate.is_public == True
            )
        ).order_by(
            AutoPilotTemplate.usage_count.desc()
        ).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())


# System templates data
SYSTEM_TEMPLATES = [
    {
        "name": "Weekly Iron Condor - NIFTY",
        "description": "Sell OTM call and put spreads on NIFTY weekly expiry. Delta 16 strikes for optimal risk/reward.",
        "category": "income",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "risk_level": "moderate",
        "market_outlook": "neutral",
        "iv_environment": "normal",
        "expected_return_pct": Decimal("2.5"),
        "max_risk_pct": Decimal("5.0"),
        "tags": ["weekly", "neutral", "theta-positive", "iron-condor"],
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "sell_ce", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": 0.16}, "quantity_multiplier": 1},
                {"id": "buy_ce", "contract_type": "CE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": 200}, "quantity_multiplier": 1},
                {"id": "sell_pe", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": -0.16}, "quantity_multiplier": 1},
                {"id": "buy_pe", "contract_type": "PE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": -200}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"},
                    {"id": "vix_check", "variable": "VIX.LEVEL", "operator": "between", "value": [12, 18]}
                ]
            },
            "risk_settings": {
                "max_loss": 5000,
                "max_loss_pct": 100,
                "time_stop": "15:15"
            }
        },
        "educational_content": {
            "when_to_use": "Best in range-bound markets with moderate IV. Ideal for weekly expiry trading.",
            "pros": ["Limited risk", "Time decay works in favor", "High win rate if positioned correctly"],
            "cons": ["Limited profit potential", "Requires active management", "Gap risk overnight"],
            "common_mistakes": ["Trading too close to expiry", "Not adjusting when breached", "Ignoring VIX spikes"],
            "exit_rules": ["Exit if any short strike is breached", "Take profit at 50% of max profit", "Exit by 3:15 PM on expiry day"]
        }
    },
    {
        "name": "Weekly Iron Condor - BANKNIFTY",
        "description": "Sell OTM call and put spreads on BANKNIFTY weekly expiry. Delta 16 strikes.",
        "category": "income",
        "underlying": "BANKNIFTY",
        "position_type": "intraday",
        "risk_level": "moderate",
        "market_outlook": "neutral",
        "iv_environment": "normal",
        "expected_return_pct": Decimal("3.0"),
        "max_risk_pct": Decimal("6.0"),
        "tags": ["weekly", "neutral", "theta-positive", "iron-condor", "banknifty"],
        "strategy_config": {
            "underlying": "BANKNIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "sell_ce", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": 0.16}, "quantity_multiplier": 1},
                {"id": "buy_ce", "contract_type": "CE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": 500}, "quantity_multiplier": 1},
                {"id": "sell_pe", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": -0.16}, "quantity_multiplier": 1},
                {"id": "buy_pe", "contract_type": "PE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": -500}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"}
                ]
            },
            "risk_settings": {
                "max_loss": 8000,
                "time_stop": "15:15"
            }
        },
        "educational_content": {
            "when_to_use": "Bank Nifty iron condors for higher premium collection. More volatile than NIFTY.",
            "pros": ["Higher premium than NIFTY", "Good for expiry day trades"],
            "cons": ["Higher volatility", "Wider spreads needed"]
        }
    },
    {
        "name": "ATM Straddle - NIFTY",
        "description": "Sell ATM straddle for maximum theta decay. High risk, high reward strategy.",
        "category": "income",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "risk_level": "aggressive",
        "market_outlook": "neutral",
        "iv_environment": "high",
        "expected_return_pct": Decimal("4.0"),
        "max_risk_pct": Decimal("15.0"),
        "tags": ["straddle", "neutral", "theta-positive", "high-risk"],
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "sell_ce", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}, "quantity_multiplier": 1},
                {"id": "sell_pe", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:45"},
                    {"id": "vix_check", "variable": "VIX.LEVEL", "operator": "greater_than", "value": 15}
                ]
            },
            "risk_settings": {
                "max_loss": 10000,
                "time_stop": "15:15",
                "trailing_stop": {"enabled": True, "trigger_profit": 3000, "trail_amount": 1500}
            }
        },
        "educational_content": {
            "when_to_use": "When expecting low movement and high IV crush",
            "pros": ["Maximum premium collection", "Fastest theta decay"],
            "cons": ["Unlimited risk", "Requires strict stop loss", "Gap risk"]
        }
    },
    {
        "name": "OTM Strangle - NIFTY",
        "description": "Sell OTM strangle for consistent income. Wider breakeven than straddle.",
        "category": "income",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "risk_level": "moderate",
        "market_outlook": "neutral",
        "iv_environment": "high",
        "expected_return_pct": Decimal("2.0"),
        "max_risk_pct": Decimal("10.0"),
        "tags": ["strangle", "neutral", "theta-positive"],
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "sell_ce", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": 0.20}, "quantity_multiplier": 1},
                {"id": "sell_pe", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": -0.20}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"}
                ]
            },
            "risk_settings": {
                "max_loss": 7500,
                "time_stop": "15:15"
            }
        }
    },
    {
        "name": "Bull Call Spread - NIFTY",
        "description": "Bullish strategy with limited risk. Buy ATM call, sell OTM call.",
        "category": "directional",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "risk_level": "conservative",
        "market_outlook": "bullish",
        "iv_environment": "low",
        "expected_return_pct": Decimal("50.0"),
        "max_risk_pct": Decimal("100.0"),
        "tags": ["bullish", "debit-spread", "limited-risk"],
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "buy_ce", "contract_type": "CE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": 0}, "quantity_multiplier": 1},
                {"id": "sell_ce", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 100}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"},
                    {"id": "spot_trend", "variable": "NIFTY.SPOT", "operator": "crosses_above", "value": "NIFTY.VWAP"}
                ]
            },
            "risk_settings": {
                "time_stop": "15:15"
            }
        },
        "educational_content": {
            "when_to_use": "When moderately bullish on the market",
            "pros": ["Limited risk", "Lower cost than naked call"],
            "cons": ["Capped profit", "Time decay works against"]
        }
    },
    {
        "name": "Bear Put Spread - NIFTY",
        "description": "Bearish strategy with limited risk. Buy ATM put, sell OTM put.",
        "category": "directional",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "risk_level": "conservative",
        "market_outlook": "bearish",
        "iv_environment": "low",
        "expected_return_pct": Decimal("50.0"),
        "max_risk_pct": Decimal("100.0"),
        "tags": ["bearish", "debit-spread", "limited-risk"],
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "buy_pe", "contract_type": "PE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": 0}, "quantity_multiplier": 1},
                {"id": "sell_pe", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": -100}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"},
                    {"id": "spot_trend", "variable": "NIFTY.SPOT", "operator": "crosses_below", "value": "NIFTY.VWAP"}
                ]
            },
            "risk_settings": {
                "time_stop": "15:15"
            }
        }
    },
    {
        "name": "Jade Lizard - NIFTY",
        "description": "Sell put spread + naked call. Neutral to bullish bias with no upside risk.",
        "category": "advanced",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "risk_level": "moderate",
        "market_outlook": "neutral",
        "iv_environment": "high",
        "expected_return_pct": Decimal("3.0"),
        "max_risk_pct": Decimal("8.0"),
        "tags": ["jade-lizard", "neutral-bullish", "credit-strategy"],
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "sell_pe", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": -0.20}, "quantity_multiplier": 1},
                {"id": "buy_pe", "contract_type": "PE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": -200}, "quantity_multiplier": 1},
                {"id": "sell_ce", "contract_type": "CE", "transaction_type": "SELL", "strike_selection": {"mode": "delta_based", "target_delta": 0.10}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"}
                ]
            },
            "risk_settings": {
                "max_loss": 6000,
                "time_stop": "15:15"
            }
        },
        "educational_content": {
            "when_to_use": "When slightly bullish and expecting range-bound movement",
            "pros": ["No upside risk if structured correctly", "Good premium collection"],
            "cons": ["Downside risk", "Complex to manage"]
        }
    },
    {
        "name": "Broken Wing Butterfly - NIFTY",
        "description": "Asymmetric butterfly with no risk on one side. Directional bias with limited risk.",
        "category": "advanced",
        "underlying": "NIFTY",
        "position_type": "intraday",
        "risk_level": "moderate",
        "market_outlook": "neutral",
        "iv_environment": "normal",
        "expected_return_pct": Decimal("100.0"),
        "max_risk_pct": Decimal("50.0"),
        "tags": ["butterfly", "directional", "advanced"],
        "strategy_config": {
            "underlying": "NIFTY",
            "expiry_type": "current_week",
            "position_type": "intraday",
            "legs_config": [
                {"id": "buy_pe_itm", "contract_type": "PE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": 100}, "quantity_multiplier": 1},
                {"id": "sell_pe_atm", "contract_type": "PE", "transaction_type": "SELL", "strike_selection": {"mode": "atm_offset", "offset": 0}, "quantity_multiplier": 2},
                {"id": "buy_pe_otm", "contract_type": "PE", "transaction_type": "BUY", "strike_selection": {"mode": "atm_offset", "offset": -200}, "quantity_multiplier": 1}
            ],
            "entry_conditions": {
                "logic": "AND",
                "conditions": [
                    {"id": "time_check", "variable": "TIME.CURRENT", "operator": "greater_than", "value": "09:30"}
                ]
            },
            "risk_settings": {
                "time_stop": "15:15"
            }
        }
    }
]


async def seed_system_templates(db: AsyncSession) -> int:
    """Seed system templates into database."""
    count = 0

    for template_data in SYSTEM_TEMPLATES:
        # Check if template already exists
        query = select(AutoPilotTemplate).where(
            AutoPilotTemplate.name == template_data["name"],
            AutoPilotTemplate.is_system == True
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            continue

        template = AutoPilotTemplate(
            name=template_data["name"],
            description=template_data["description"],
            category=template_data["category"],
            underlying=template_data["underlying"],
            position_type=template_data["position_type"],
            risk_level=template_data["risk_level"],
            market_outlook=template_data["market_outlook"],
            iv_environment=template_data["iv_environment"],
            expected_return_pct=template_data["expected_return_pct"],
            max_risk_pct=template_data["max_risk_pct"],
            tags=template_data["tags"],
            strategy_config=template_data["strategy_config"],
            educational_content=template_data.get("educational_content", {}),
            is_system=True,
            is_public=True,
            author_name="AlgoChanakya"
        )

        db.add(template)
        count += 1

    if count > 0:
        await db.commit()

    return count
