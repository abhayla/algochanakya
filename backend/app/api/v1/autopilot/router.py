"""
AutoPilot API Router

Reference: docs/autopilot/api-contracts.md
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.users import User
from app.models.autopilot import (
    AutoPilotStrategy, AutoPilotUserSettings, AutoPilotOrder, AutoPilotLog
)
from app.schemas.autopilot import (
    StrategyCreateRequest, StrategyUpdateRequest, StrategyResponse,
    StrategyListItem, ActivateRequest, ExitRequest, CloneRequest,
    UserSettingsResponse, UserSettingsUpdateRequest,
    DashboardSummary, RiskMetrics, DataResponse, PaginatedResponse
)

router = APIRouter(prefix="/autopilot", tags=["autopilot"])


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================

@router.get("/settings", response_model=DataResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's AutoPilot settings."""
    result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        # Create default settings
        settings = AutoPilotUserSettings(
            user_id=current_user.id,
            default_order_settings={
                "order_type": "MARKET",
                "execution_style": "sequential",
                "delay_between_legs": 2
            },
            notification_prefs={
                "enabled": True,
                "channels": ["in_app"]
            },
            failure_handling={
                "on_network_error": "retry",
                "max_retries": 3
            }
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return DataResponse(
        data=UserSettingsResponse.model_validate(settings),
        timestamp=datetime.utcnow()
    )


@router.put("/settings", response_model=DataResponse)
async def update_settings(
    request: UserSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update user's AutoPilot settings."""
    result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = result.scalar_one_or_none()

    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Validate constraints
    update_data = request.model_dump(exclude_unset=True)

    if 'per_strategy_loss_limit' in update_data and 'daily_loss_limit' in update_data:
        if update_data['per_strategy_loss_limit'] > update_data['daily_loss_limit']:
            raise HTTPException(
                status_code=400,
                detail="per_strategy_loss_limit cannot exceed daily_loss_limit"
            )

    # Apply updates
    for key, value in update_data.items():
        setattr(settings, key, value)

    await db.commit()
    await db.refresh(settings)

    return DataResponse(
        message="Settings updated successfully",
        data=UserSettingsResponse.model_validate(settings),
        timestamp=datetime.utcnow()
    )


# ============================================================================
# STRATEGY ENDPOINTS
# ============================================================================

@router.get("/strategies", response_model=PaginatedResponse)
async def list_strategies(
    status: Optional[str] = None,
    underlying: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List user's AutoPilot strategies with pagination."""
    query = select(AutoPilotStrategy).where(
        AutoPilotStrategy.user_id == current_user.id
    )

    # Apply filters
    if status:
        query = query.where(AutoPilotStrategy.status == status)
    if underlying:
        query = query.where(AutoPilotStrategy.underlying == underlying)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting
    sort_column = getattr(AutoPilotStrategy, sort_by, AutoPilotStrategy.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    strategies = result.scalars().all()

    # Convert to list items
    items = []
    for s in strategies:
        items.append(StrategyListItem(
            id=s.id,
            name=s.name,
            status=s.status,
            underlying=s.underlying,
            lots=s.lots,
            leg_count=len(s.legs_config) if s.legs_config else 0,
            current_pnl=s.runtime_state.get('current_pnl') if s.runtime_state else None,
            margin_used=s.runtime_state.get('margin_used') if s.runtime_state else None,
            priority=s.priority,
            created_at=s.created_at,
            updated_at=s.updated_at
        ))

    total_pages = (total + page_size - 1) // page_size if total else 0

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.post("/strategies", response_model=DataResponse, status_code=201)
async def create_strategy(
    request: StrategyCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new AutoPilot strategy."""
    # Check strategy count limit
    count_result = await db.execute(
        select(func.count()).where(
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy_count = count_result.scalar()

    if strategy_count >= 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 strategies allowed per user"
        )

    # Create strategy
    strategy = AutoPilotStrategy(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        status="draft",
        underlying=request.underlying.value,
        expiry_type=request.expiry_type.value,
        expiry_date=request.expiry_date,
        lots=request.lots,
        position_type=request.position_type.value,
        legs_config=[leg.model_dump() for leg in request.legs_config],
        entry_conditions=request.entry_conditions.model_dump(),
        adjustment_rules=request.adjustment_rules,
        order_settings=request.order_settings.model_dump() if request.order_settings else {},
        risk_settings=request.risk_settings.model_dump() if request.risk_settings else {},
        schedule_config=request.schedule_config.model_dump() if request.schedule_config else {},
        priority=request.priority,
        source_template_id=request.source_template_id
    )

    db.add(strategy)
    await db.commit()
    await db.refresh(strategy)

    # Log creation
    log = AutoPilotLog(
        user_id=current_user.id,
        strategy_id=strategy.id,
        event_type="strategy_created",
        severity="info",
        message=f"Strategy '{strategy.name}' created",
        event_data={"strategy_id": strategy.id, "name": strategy.name}
    )
    db.add(log)
    await db.commit()

    return DataResponse(
        message="Strategy created successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.get("/strategies/{strategy_id}", response_model=DataResponse)
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get strategy details."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return DataResponse(
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.put("/strategies/{strategy_id}", response_model=DataResponse)
async def update_strategy(
    strategy_id: int,
    request: StrategyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update strategy configuration."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Only allow updates for draft/paused strategies
    if strategy.status not in ["draft", "paused"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update strategy in '{strategy.status}' status"
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'legs_config' and value:
            value = [leg.model_dump() if hasattr(leg, 'model_dump') else leg for leg in value]
        elif key in ['entry_conditions', 'order_settings', 'risk_settings', 'schedule_config'] and value:
            value = value.model_dump() if hasattr(value, 'model_dump') else value
        setattr(strategy, key, value)

    await db.commit()
    await db.refresh(strategy)

    return DataResponse(
        message="Strategy updated successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.delete("/strategies/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Only allow deletion for draft/completed/error strategies
    if strategy.status not in ["draft", "completed", "error"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete strategy in '{strategy.status}' status. Pause or exit first."
        )

    await db.delete(strategy)
    await db.commit()


@router.post("/strategies/{strategy_id}/activate", response_model=DataResponse)
async def activate_strategy(
    strategy_id: int,
    request: ActivateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activate a draft strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate strategy in '{strategy.status}' status"
        )

    # Check max active strategies
    settings_result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = settings_result.scalar_one_or_none()
    max_active = settings.max_active_strategies if settings else 3

    active_count_result = await db.execute(
        select(func.count()).where(
            AutoPilotStrategy.user_id == current_user.id,
            AutoPilotStrategy.status.in_(["waiting", "active", "pending"])
        )
    )
    active_count = active_count_result.scalar()

    if active_count >= max_active:
        raise HTTPException(
            status_code=409,
            detail=f"Maximum active strategies limit ({max_active}) reached"
        )

    # Activate
    strategy.status = "waiting"
    strategy.activated_at = datetime.utcnow()
    strategy.runtime_state = {
        "paper_trading": request.paper_trading,
        "current_pnl": 0,
        "margin_used": 0,
        "current_positions": [],
        "adjustments_made": []
    }

    await db.commit()
    await db.refresh(strategy)

    # Log activation
    log = AutoPilotLog(
        user_id=current_user.id,
        strategy_id=strategy.id,
        event_type="strategy_activated",
        severity="info",
        message=f"Strategy '{strategy.name}' activated",
        event_data={"paper_trading": request.paper_trading}
    )
    db.add(log)
    await db.commit()

    return DataResponse(
        message="Strategy activated successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.post("/strategies/{strategy_id}/pause", response_model=DataResponse)
async def pause_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause an active strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status not in ["waiting", "active", "pending"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause strategy in '{strategy.status}' status"
        )

    strategy.status = "paused"
    await db.commit()
    await db.refresh(strategy)

    return DataResponse(
        message="Strategy paused successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.post("/strategies/{strategy_id}/resume", response_model=DataResponse)
async def resume_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status != "paused":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume strategy in '{strategy.status}' status"
        )

    # Resume to waiting (will become active when conditions met)
    strategy.status = "waiting"
    await db.commit()
    await db.refresh(strategy)

    return DataResponse(
        message="Strategy resumed successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.utcnow()
    )


@router.post("/strategies/{strategy_id}/clone", response_model=DataResponse, status_code=201)
async def clone_strategy(
    strategy_id: int,
    request: CloneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clone an existing strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Create clone
    clone_name = request.new_name or f"{original.name} (Copy)"

    clone = AutoPilotStrategy(
        user_id=current_user.id,
        name=clone_name,
        description=original.description,
        status="draft",
        underlying=original.underlying,
        expiry_type=original.expiry_type,
        expiry_date=None if request.reset_schedule else original.expiry_date,
        lots=original.lots,
        position_type=original.position_type,
        legs_config=original.legs_config,
        entry_conditions=original.entry_conditions,
        adjustment_rules=original.adjustment_rules,
        order_settings=original.order_settings,
        risk_settings=original.risk_settings,
        schedule_config=original.schedule_config,
        priority=original.priority,
        cloned_from_id=original.id
    )

    db.add(clone)
    await db.commit()
    await db.refresh(clone)

    return DataResponse(
        message="Strategy cloned successfully",
        data=StrategyResponse.model_validate(clone),
        timestamp=datetime.utcnow()
    )


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard/summary", response_model=DataResponse)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard summary."""
    # Get strategy counts
    strategies_result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategies = strategies_result.scalars().all()

    active_strategies = [s for s in strategies if s.status == "active"]
    waiting_strategies = [s for s in strategies if s.status == "waiting"]
    pending_strategies = [s for s in strategies if s.status == "pending"]

    # Calculate P&L
    today_realized = sum(
        float(s.runtime_state.get('realized_pnl', 0) or 0)
        for s in strategies if s.runtime_state
    )
    today_unrealized = sum(
        float(s.runtime_state.get('current_pnl', 0) or 0)
        for s in strategies if s.runtime_state and s.status in ['active', 'waiting']
    )

    # Get settings for risk metrics
    settings_result = await db.execute(
        select(AutoPilotUserSettings).where(
            AutoPilotUserSettings.user_id == current_user.id
        )
    )
    settings = settings_result.scalar_one_or_none()

    daily_loss_limit = float(settings.daily_loss_limit) if settings else 20000
    max_capital = float(settings.max_capital_deployed) if settings else 500000
    max_active = settings.max_active_strategies if settings else 3

    capital_used = sum(
        float(s.runtime_state.get('margin_used', 0) or 0)
        for s in strategies if s.runtime_state and s.status in ['active', 'waiting', 'pending']
    )

    # Determine risk status
    loss_pct = abs(min(today_realized + today_unrealized, 0)) / daily_loss_limit * 100 if daily_loss_limit else 0
    if loss_pct >= 90:
        risk_status = "critical"
    elif loss_pct >= 70:
        risk_status = "warning"
    else:
        risk_status = "safe"

    risk_metrics = RiskMetrics(
        daily_loss_limit=daily_loss_limit,
        daily_loss_used=abs(min(today_realized + today_unrealized, 0)),
        daily_loss_pct=loss_pct,
        max_capital=max_capital,
        capital_used=capital_used,
        capital_pct=(capital_used / max_capital * 100) if max_capital else 0,
        max_active_strategies=max_active,
        active_strategies_count=len(active_strategies) + len(waiting_strategies) + len(pending_strategies),
        status=risk_status
    )

    # Convert strategies to list items
    strategy_items = []
    for s in strategies:
        if s.status in ['active', 'waiting', 'pending', 'paused']:
            strategy_items.append(StrategyListItem(
                id=s.id,
                name=s.name,
                status=s.status,
                underlying=s.underlying,
                lots=s.lots,
                leg_count=len(s.legs_config) if s.legs_config else 0,
                current_pnl=s.runtime_state.get('current_pnl') if s.runtime_state else None,
                margin_used=s.runtime_state.get('margin_used') if s.runtime_state else None,
                priority=s.priority,
                created_at=s.created_at,
                updated_at=s.updated_at
            ))

    summary = DashboardSummary(
        active_strategies=len(active_strategies),
        waiting_strategies=len(waiting_strategies),
        pending_confirmations=len(pending_strategies),
        today_realized_pnl=today_realized,
        today_unrealized_pnl=today_unrealized,
        today_total_pnl=today_realized + today_unrealized,
        risk_metrics=risk_metrics,
        strategies=strategy_items,
        kite_connected=True,  # TODO: Check actual connection
        websocket_connected=True,  # TODO: Check actual connection
        last_update=datetime.utcnow()
    )

    return DataResponse(
        data=summary,
        timestamp=datetime.utcnow()
    )
