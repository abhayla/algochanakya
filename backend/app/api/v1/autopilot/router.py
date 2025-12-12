"""
AutoPilot API Router

Reference: docs/autopilot/api-contracts.md

Phase 3 Endpoints (Advanced Features):
- Kill Switch: /kill-switch/status, /kill-switch/trigger, /kill-switch/reset
- Confirmations: /confirmations, /confirmations/{id}/confirm, /confirmations/{id}/reject
- Adjustments: /strategies/{id}/adjust
- Trailing Stop: /strategies/{id}/trailing-stop
- Position Sizing: /position-sizing/calculate
- Greeks: /strategies/{id}/greeks
"""
from datetime import datetime, date, timezone
from typing import Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.users import User
from app.models.autopilot import (
    AutoPilotStrategy, AutoPilotUserSettings, AutoPilotOrder, AutoPilotLog,
    AutoPilotPendingConfirmation, ConfirmationStatus
)
from app.schemas.autopilot import (
    StrategyCreateRequest, StrategyUpdateRequest, StrategyResponse,
    StrategyListItem, ActivateRequest, ExitRequest, CloneRequest,
    UserSettingsResponse, UserSettingsUpdateRequest,
    DashboardSummary, RiskMetrics, DataResponse, PaginatedResponse,
    # Phase 3 schemas
    KillSwitchStatus, KillSwitchTriggerRequest, KillSwitchTriggerResponse,
    PendingConfirmationResponse, ConfirmationActionRequest, ConfirmationActionResponse,
    ManualAdjustmentRequest, AdjustmentLogResponse,
    TrailingStopStatus, TrailingStopConfig,
    PositionSizingRequest, PositionSizingResponse,
    GreeksSnapshot, PositionGreeksResponse
)
from app.services.kill_switch import KillSwitchService
from app.services.confirmation_service import ConfirmationService
from app.services.adjustment_engine import AdjustmentEngine
from app.services.trailing_stop import TrailingStopService
from app.services.position_sizing import PositionSizingService
from app.services.greeks_calculator import GreeksCalculatorService

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


# ============================================================================
# ORDERS ENDPOINTS
# ============================================================================

@router.get("/orders", response_model=PaginatedResponse)
async def list_orders(
    strategy_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List AutoPilot orders with pagination."""
    query = select(AutoPilotOrder).where(
        AutoPilotOrder.user_id == current_user.id
    )

    # Apply filters
    if strategy_id:
        query = query.where(AutoPilotOrder.strategy_id == strategy_id)
    if status:
        query = query.where(AutoPilotOrder.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting and pagination
    query = query.order_by(AutoPilotOrder.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    orders = result.scalars().all()

    # Convert to response format
    items = []
    for order in orders:
        items.append({
            "id": order.id,
            "strategy_id": order.strategy_id,
            "broker_order_id": order.broker_order_id,
            "leg_id": order.leg_id,
            "instrument_token": order.instrument_token,
            "tradingsymbol": order.tradingsymbol,
            "transaction_type": order.transaction_type,
            "quantity": order.quantity,
            "order_type": order.order_type,
            "price": float(order.price) if order.price else None,
            "status": order.status,
            "fill_price": float(order.fill_price) if order.fill_price else None,
            "slippage": float(order.slippage) if order.slippage else None,
            "created_at": order.created_at.isoformat(),
            "filled_at": order.filled_at.isoformat() if order.filled_at else None
        })

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


# ============================================================================
# LOGS ENDPOINTS
# ============================================================================

@router.get("/logs", response_model=PaginatedResponse)
async def list_logs(
    strategy_id: Optional[int] = None,
    severity: Optional[str] = None,
    event_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List AutoPilot activity logs with pagination."""
    query = select(AutoPilotLog).where(
        AutoPilotLog.user_id == current_user.id
    )

    # Apply filters
    if strategy_id:
        query = query.where(AutoPilotLog.strategy_id == strategy_id)
    if severity:
        query = query.where(AutoPilotLog.severity == severity)
    if event_type:
        query = query.where(AutoPilotLog.event_type == event_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting and pagination
    query = query.order_by(AutoPilotLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Convert to response format
    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "strategy_id": log.strategy_id,
            "event_type": log.event_type,
            "severity": log.severity,
            "message": log.message,
            "event_data": log.event_data,
            "created_at": log.created_at.isoformat()
        })

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


# ============================================================================
# KILL SWITCH ENDPOINT
# ============================================================================

@router.post("/kill-switch", response_model=DataResponse)
async def kill_switch(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Emergency stop all active strategies (legacy endpoint - use /kill-switch/trigger instead)."""
    # Find all active strategies
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.user_id == current_user.id,
            AutoPilotStrategy.status.in_(["waiting", "active", "pending"])
        )
    )
    strategies = result.scalars().all()

    stopped_count = 0
    stopped_ids = []

    for strategy in strategies:
        strategy.status = "paused"
        stopped_count += 1
        stopped_ids.append(strategy.id)

        # Log the kill switch activation
        log = AutoPilotLog(
            user_id=current_user.id,
            strategy_id=strategy.id,
            event_type="kill_switch_activated",
            severity="warning",
            message=f"Strategy '{strategy.name}' stopped by kill switch",
            event_data={"reason": "Manual kill switch activation"}
        )
        db.add(log)

    await db.commit()

    return DataResponse(
        message=f"Kill switch activated. {stopped_count} strategies stopped.",
        data={
            "strategies_stopped": stopped_count,
            "strategy_ids": stopped_ids
        },
        timestamp=datetime.utcnow()
    )


# ============================================================================
# PHASE 3: KILL SWITCH ENHANCED ENDPOINTS
# ============================================================================

@router.get("/kill-switch/status", response_model=DataResponse)
async def get_kill_switch_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current kill switch status."""
    service = KillSwitchService(db, current_user.id)
    status = await service.get_status()

    return DataResponse(
        data=status,
        timestamp=datetime.now(timezone.utc)
    )


@router.post("/kill-switch/trigger", response_model=DataResponse)
async def trigger_kill_switch(
    request: KillSwitchTriggerRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger kill switch - emergency stop all active strategies.

    This will:
    - Exit all active positions with market orders
    - Pause all waiting strategies
    - Prevent new strategy activations until reset
    """
    service = KillSwitchService(db, current_user.id)

    reason = request.reason if request else None
    force = request.force if request else False

    try:
        result = await service.trigger(reason=reason, force=force)
        return DataResponse(
            message=result.message,
            data=result,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill-switch/reset", response_model=DataResponse)
async def reset_kill_switch(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset kill switch to allow new strategy activations.

    Requires explicit confirmation.
    """
    service = KillSwitchService(db, current_user.id)

    try:
        result = await service.reset(confirm=True)
        return DataResponse(
            message=result.get("message", "Kill switch reset"),
            data=result,
            timestamp=datetime.now(timezone.utc)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 3: CONFIRMATION ENDPOINTS
# ============================================================================

@router.get("/confirmations", response_model=DataResponse)
async def list_pending_confirmations(
    strategy_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all pending confirmations for semi-auto execution mode."""
    service = ConfirmationService(db, current_user.id)
    confirmations = await service.get_pending_confirmations(strategy_id=strategy_id)

    return DataResponse(
        data=confirmations,
        timestamp=datetime.now(timezone.utc)
    )


@router.post("/confirmations/{confirmation_id}/confirm", response_model=DataResponse)
async def confirm_action(
    confirmation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Confirm a pending action and execute it."""
    service = ConfirmationService(db, current_user.id)

    try:
        result = await service.confirm(confirmation_id)
        return DataResponse(
            message=result.message,
            data=result,
            timestamp=datetime.now(timezone.utc)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirmations/{confirmation_id}/reject", response_model=DataResponse)
async def reject_action(
    confirmation_id: int,
    request: ConfirmationActionRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reject a pending action."""
    service = ConfirmationService(db, current_user.id)
    reason = request.reason if request else None

    try:
        result = await service.reject(confirmation_id, reason=reason)
        return DataResponse(
            message=result.message,
            data=result,
            timestamp=datetime.now(timezone.utc)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 3: ADJUSTMENT ENDPOINTS
# ============================================================================

@router.post("/strategies/{strategy_id}/adjust", response_model=DataResponse)
async def manual_adjustment(
    strategy_id: int,
    request: ManualAdjustmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger an adjustment for a strategy.

    This bypasses automatic rule evaluation and executes the specified action.
    """
    # Get strategy
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot adjust strategy in '{strategy.status}' status"
        )

    engine = AdjustmentEngine(db, current_user.id)

    # Create a manual rule
    manual_rule = {
        'id': f"manual_{datetime.now(timezone.utc).timestamp()}",
        'name': request.description or "Manual Adjustment",
        'trigger': {'type': 'manual'},
        'action': request.action.model_dump()
    }

    manual_evaluation = {
        'triggered': True,
        'reason': request.description or "Manual trigger by user"
    }

    try:
        execution_result = await engine.execute_adjustment(
            strategy=strategy,
            rule=manual_rule,
            evaluation=manual_evaluation,
            execution_mode=request.execution_mode
        )

        return DataResponse(
            message="Adjustment executed successfully",
            data=execution_result,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy_id}/adjustments", response_model=PaginatedResponse)
async def list_adjustment_history(
    strategy_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get adjustment history for a strategy."""
    from app.models.autopilot import AutoPilotAdjustmentLog

    # Verify strategy ownership
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Query adjustment logs
    query = select(AutoPilotAdjustmentLog).where(
        AutoPilotAdjustmentLog.strategy_id == strategy_id
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    query = query.order_by(AutoPilotAdjustmentLog.executed_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    items = [AdjustmentLogResponse.model_validate(log) for log in logs]

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


# ============================================================================
# PHASE 3: TRAILING STOP ENDPOINTS
# ============================================================================

@router.get("/strategies/{strategy_id}/trailing-stop", response_model=DataResponse)
async def get_trailing_stop_status(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trailing stop status for a strategy."""
    # Get strategy
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    service = TrailingStopService(db, current_user.id)

    # Get current P&L from runtime state
    current_pnl = Decimal(str(
        strategy.runtime_state.get('current_pnl', 0) if strategy.runtime_state else 0
    ))

    status = await service.get_status(strategy, current_pnl)

    return DataResponse(
        data=status,
        timestamp=datetime.now(timezone.utc)
    )


@router.put("/strategies/{strategy_id}/trailing-stop", response_model=DataResponse)
async def update_trailing_stop_config(
    strategy_id: int,
    config: TrailingStopConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update trailing stop configuration for a strategy."""
    # Get strategy
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Update configuration
    strategy.trailing_stop_config = config.model_dump()
    await db.commit()
    await db.refresh(strategy)

    return DataResponse(
        message="Trailing stop configuration updated",
        data=config,
        timestamp=datetime.now(timezone.utc)
    )


# ============================================================================
# PHASE 3: POSITION SIZING ENDPOINTS
# ============================================================================

@router.post("/position-sizing/calculate", response_model=DataResponse)
async def calculate_position_size(
    request: PositionSizingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate optimal position size based on risk parameters.

    Takes into account:
    - Account capital
    - Risk per trade (% or fixed amount)
    - Strategy max loss estimate
    - Current VIX for volatility adjustment
    """
    service = PositionSizingService(db, current_user.id)

    try:
        result = await service.calculate_position_size(request)
        return DataResponse(
            data=result,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 3: GREEKS ENDPOINTS
# ============================================================================

@router.get("/strategies/{strategy_id}/greeks", response_model=DataResponse)
async def get_strategy_greeks(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get current Greeks for a strategy's positions.

    Returns delta, gamma, theta, vega for the entire position
    as well as per-leg breakdowns.
    """
    # Get strategy
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Get current positions from runtime state
    runtime_state = strategy.runtime_state or {}
    positions = runtime_state.get('positions', [])

    if not positions and strategy.legs_config:
        # Fall back to legs_config if no positions yet
        positions = strategy.legs_config

    # Get spot price from runtime state or use default
    spot_price = float(runtime_state.get('spot_price', 0))

    if spot_price == 0:
        raise HTTPException(
            status_code=400,
            detail="Spot price not available. Strategy may not be active."
        )

    service = GreeksCalculatorService(db, current_user.id)

    try:
        greeks = await service.calculate_position_greeks(
            legs=positions,
            spot_price=spot_price
        )

        return DataResponse(
            data=greeks,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/greeks/calculate", response_model=DataResponse)
async def calculate_greeks(
    legs: List[dict],
    spot_price: float = Query(..., description="Current spot price"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Calculate Greeks for arbitrary leg configurations.

    Useful for pre-trade analysis and what-if scenarios.
    """
    service = GreeksCalculatorService(db, current_user.id)

    try:
        greeks = await service.calculate_position_greeks(
            legs=legs,
            spot_price=spot_price
        )

        return DataResponse(
            data=greeks,
            timestamp=datetime.now(timezone.utc)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 4: STRATEGY TEMPLATES
# ============================================================================

@router.get("/templates", response_model=PaginatedResponse)
async def list_templates(
    category: Optional[str] = None,
    underlying: Optional[str] = None,
    market_outlook: Optional[str] = None,
    risk_level: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List strategy templates with filters."""
    from app.services.template_service import TemplateService
    from app.schemas.autopilot import TemplateListItem

    result = await TemplateService.list_templates(
        db=db,
        user_id=current_user.id,
        category=category,
        underlying=underlying,
        market_outlook=market_outlook,
        risk_level=risk_level,
        search=search,
        page=page,
        page_size=page_size
    )

    items = [TemplateListItem.model_validate(t) for t in result["templates"]]
    total = result["total"]
    total_pages = result["total_pages"]

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.get("/templates/categories", response_model=DataResponse)
async def get_template_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get template categories with counts."""
    from app.services.template_service import TemplateService

    categories = await TemplateService.get_categories(db, current_user.id)

    return DataResponse(
        data=categories,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/templates/popular", response_model=DataResponse)
async def get_popular_templates(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get most popular templates."""
    from app.services.template_service import TemplateService

    templates = await TemplateService.get_popular_templates(db, limit)

    return DataResponse(
        data=templates,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/templates/{template_id}", response_model=DataResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get template details."""
    from app.services.template_service import TemplateService
    from app.schemas.autopilot import TemplateResponse

    template = await TemplateService.get_template(db, template_id, current_user.id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return DataResponse(
        data=TemplateResponse.model_validate(template),
        timestamp=datetime.now(timezone.utc)
    )


@router.post("/templates", response_model=DataResponse, status_code=201)
async def create_template(
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new template from strategy."""
    from app.services.template_service import TemplateService
    from app.schemas.autopilot import TemplateCreateRequest, TemplateResponse

    template_request = TemplateCreateRequest(**request)

    template = await TemplateService.create_template(
        db=db,
        user_id=current_user.id,
        request=template_request
    )

    return DataResponse(
        message="Template created successfully",
        data=TemplateResponse.model_validate(template),
        timestamp=datetime.now(timezone.utc)
    )


@router.put("/templates/{template_id}", response_model=DataResponse)
async def update_template(
    template_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a template."""
    from app.services.template_service import TemplateService
    from app.schemas.autopilot import TemplateUpdateRequest, TemplateResponse

    template_request = TemplateUpdateRequest(**request)

    template = await TemplateService.update_template(
        db=db,
        template_id=template_id,
        user_id=current_user.id,
        request=template_request
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or not authorized")

    return DataResponse(
        message="Template updated successfully",
        data=TemplateResponse.model_validate(template),
        timestamp=datetime.now(timezone.utc)
    )


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a user-created template."""
    from app.services.template_service import TemplateService

    success = await TemplateService.delete_template(db, template_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Template not found or not authorized")


@router.post("/templates/{template_id}/deploy", response_model=DataResponse, status_code=201)
async def deploy_template(
    template_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deploy a template as a new strategy."""
    from app.services.template_service import TemplateService
    from app.schemas.autopilot import TemplateDeployRequest

    deploy_request = TemplateDeployRequest(**request)

    strategy = await TemplateService.deploy_template(
        db=db,
        template_id=template_id,
        user_id=current_user.id,
        request=deploy_request
    )

    if not strategy:
        raise HTTPException(status_code=404, detail="Template not found")

    return DataResponse(
        message="Template deployed successfully",
        data=StrategyResponse.model_validate(strategy),
        timestamp=datetime.now(timezone.utc)
    )


@router.post("/templates/{template_id}/rate", response_model=DataResponse)
async def rate_template(
    template_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rate a template."""
    from app.services.template_service import TemplateService
    from app.schemas.autopilot import TemplateRatingRequest, TemplateRatingResponse

    rating_request = TemplateRatingRequest(**request)

    rating = await TemplateService.rate_template(
        db=db,
        template_id=template_id,
        user_id=current_user.id,
        request=rating_request
    )

    if not rating:
        raise HTTPException(status_code=404, detail="Template not found")

    return DataResponse(
        message="Rating submitted successfully",
        data=TemplateRatingResponse.model_validate(rating),
        timestamp=datetime.now(timezone.utc)
    )


# ============================================================================
# PHASE 4: TRADE JOURNAL
# ============================================================================

@router.get("/journal", response_model=PaginatedResponse)
async def list_trades(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    underlying: Optional[str] = None,
    exit_reason: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated
    is_open: Optional[bool] = None,
    min_pnl: Optional[Decimal] = None,
    max_pnl: Optional[Decimal] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List trade journal entries with filters."""
    from app.services.trade_journal import TradeJournalService
    from app.schemas.autopilot import TradeJournalListItem

    tags_list = tags.split(",") if tags else None

    result = await TradeJournalService.list_trades(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        underlying=underlying,
        exit_reason=exit_reason,
        tags=tags_list,
        is_open=is_open,
        min_pnl=min_pnl,
        max_pnl=max_pnl,
        page=page,
        page_size=page_size
    )

    items = [TradeJournalListItem.model_validate(t) for t in result["trades"]]
    total = result["total"]
    total_pages = result["total_pages"]

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.get("/journal/stats", response_model=DataResponse)
async def get_journal_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trade journal statistics."""
    from app.services.trade_journal import TradeJournalService

    stats = await TradeJournalService.get_journal_stats(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )

    return DataResponse(
        data=stats,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/journal/export", response_model=DataResponse)
async def export_trades(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    underlying: Optional[str] = None,
    exit_reason: Optional[str] = None,
    format: str = "csv",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export trade journal to CSV."""
    from app.services.trade_journal import TradeJournalService
    from app.schemas.autopilot import TradeJournalExportRequest, ReportFormat

    export_request = TradeJournalExportRequest(
        start_date=start_date,
        end_date=end_date,
        underlying=underlying,
        exit_reason=exit_reason,
        format=ReportFormat(format) if format else ReportFormat.csv
    )

    csv_content = await TradeJournalService.export_trades(
        db=db,
        user_id=current_user.id,
        request=export_request
    )

    return DataResponse(
        data={"content": csv_content, "format": "csv"},
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/journal/{trade_id}", response_model=DataResponse)
async def get_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get trade journal entry details."""
    from app.services.trade_journal import TradeJournalService
    from app.schemas.autopilot import TradeJournalResponse

    trade = await TradeJournalService.get_trade(db, trade_id, current_user.id)

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return DataResponse(
        data=TradeJournalResponse.model_validate(trade),
        timestamp=datetime.now(timezone.utc)
    )


@router.put("/journal/{trade_id}", response_model=DataResponse)
async def update_trade(
    trade_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update trade journal entry (notes/tags)."""
    from app.services.trade_journal import TradeJournalService
    from app.schemas.autopilot import TradeJournalUpdateRequest, TradeJournalResponse

    update_request = TradeJournalUpdateRequest(**request)

    trade = await TradeJournalService.update_trade(
        db=db,
        trade_id=trade_id,
        user_id=current_user.id,
        request=update_request
    )

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return DataResponse(
        message="Trade updated successfully",
        data=TradeJournalResponse.model_validate(trade),
        timestamp=datetime.now(timezone.utc)
    )


# ============================================================================
# PHASE 4: ANALYTICS
# ============================================================================

@router.get("/analytics/performance", response_model=DataResponse)
async def get_performance_analytics(
    period: str = Query("30d", pattern="^(7d|30d|90d|ytd|all)$"),
    underlying: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance analytics for the specified period."""
    from app.services.analytics import AnalyticsService

    analytics = await AnalyticsService.get_performance(
        db=db,
        user_id=current_user.id,
        period=period,
        underlying=underlying
    )

    return DataResponse(
        data=analytics,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/analytics/daily-pnl", response_model=DataResponse)
async def get_daily_pnl(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get daily P&L data for charts."""
    from app.services.analytics import AnalyticsService

    daily_pnl = await AnalyticsService.get_daily_pnl(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date
    )

    return DataResponse(
        data=daily_pnl,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/analytics/by-strategy", response_model=DataResponse)
async def get_analytics_by_strategy(
    period: str = Query("30d", pattern="^(7d|30d|90d|ytd|all)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance breakdown by strategy."""
    from app.services.analytics import AnalyticsService

    by_strategy = await AnalyticsService.get_by_strategy(
        db=db,
        user_id=current_user.id,
        period=period
    )

    return DataResponse(
        data=by_strategy,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/analytics/by-weekday", response_model=DataResponse)
async def get_analytics_by_weekday(
    period: str = Query("30d", pattern="^(7d|30d|90d|ytd|all)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance breakdown by weekday."""
    from app.services.analytics import AnalyticsService

    by_weekday = await AnalyticsService.get_by_weekday(
        db=db,
        user_id=current_user.id,
        period=period
    )

    return DataResponse(
        data=by_weekday,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/analytics/drawdown", response_model=DataResponse)
async def get_drawdown_analysis(
    period: str = Query("30d", pattern="^(7d|30d|90d|ytd|all)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get drawdown analysis."""
    from app.services.analytics import AnalyticsService

    drawdown = await AnalyticsService.get_drawdown(
        db=db,
        user_id=current_user.id,
        period=period
    )

    return DataResponse(
        data=drawdown,
        timestamp=datetime.now(timezone.utc)
    )


# ============================================================================
# PHASE 4: REPORTS
# ============================================================================

@router.get("/reports", response_model=PaginatedResponse)
async def list_reports(
    report_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List generated reports."""
    from app.services.reports import ReportService
    from app.schemas.autopilot import ReportListItem

    result = await ReportService.list_reports(
        db=db,
        user_id=current_user.id,
        report_type=report_type,
        page=page,
        page_size=page_size
    )

    items = [ReportListItem.model_validate(r) for r in result["reports"]]
    total = result["total"]
    total_pages = result["total_pages"]

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.post("/reports/generate", response_model=DataResponse, status_code=201)
async def generate_report(
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a new report."""
    from app.services.reports import ReportService
    from app.schemas.autopilot import ReportGenerateRequest, ReportResponse

    report_request = ReportGenerateRequest(**request)

    report = await ReportService.generate_report(
        db=db,
        user_id=current_user.id,
        request=report_request
    )

    return DataResponse(
        message="Report generation started",
        data=ReportResponse.model_validate(report),
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/reports/{report_id}", response_model=DataResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get report details."""
    from app.services.reports import ReportService
    from app.schemas.autopilot import ReportResponse

    report = await ReportService.get_report(db, report_id, current_user.id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return DataResponse(
        data=ReportResponse.model_validate(report),
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a generated report file."""
    from app.services.reports import ReportService
    from fastapi.responses import FileResponse

    report = await ReportService.get_report(db, report_id, current_user.id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.is_ready or not report.file_path:
        raise HTTPException(status_code=400, detail="Report not ready for download")

    return FileResponse(
        path=report.file_path,
        filename=f"{report.name}.{report.format}",
        media_type="application/octet-stream"
    )


@router.delete("/reports/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a report."""
    from app.services.reports import ReportService

    success = await ReportService.delete_report(db, report_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Report not found")


@router.get("/reports/tax-summary/{financial_year}", response_model=DataResponse)
async def get_tax_summary(
    financial_year: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get tax summary for a financial year (e.g., '2024-25')."""
    from app.services.reports import ReportService

    # Validate format
    if not financial_year or len(financial_year) != 7 or financial_year[4] != '-':
        raise HTTPException(status_code=400, detail="Invalid financial year format. Use 'YYYY-YY' (e.g., '2024-25')")

    summary = await ReportService.get_tax_summary(
        db=db,
        user_id=current_user.id,
        financial_year=financial_year
    )

    return DataResponse(
        data=summary,
        timestamp=datetime.now(timezone.utc)
    )


# ============================================================================
# PHASE 4: BACKTESTS
# ============================================================================

@router.get("/backtests", response_model=PaginatedResponse)
async def list_backtests(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List backtests."""
    from app.services.backtest import BacktestService
    from app.schemas.autopilot import BacktestListItem

    result = await BacktestService.list_backtests(
        db=db,
        user_id=current_user.id,
        status=status,
        page=page,
        page_size=page_size
    )

    items = [BacktestListItem.model_validate(b) for b in result["backtests"]]
    total = result["total"]
    total_pages = result["total_pages"]

    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )


@router.post("/backtests", response_model=DataResponse, status_code=201)
async def create_backtest(
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create and start a new backtest."""
    from app.services.backtest import BacktestService
    from app.schemas.autopilot import BacktestCreateRequest, BacktestResponse

    backtest_request = BacktestCreateRequest(**request)

    backtest = await BacktestService.create_backtest(
        db=db,
        user_id=current_user.id,
        request=backtest_request
    )

    return DataResponse(
        message="Backtest created and started",
        data=BacktestResponse.model_validate(backtest),
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/backtests/{backtest_id}", response_model=DataResponse)
async def get_backtest(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get backtest details and results."""
    from app.services.backtest import BacktestService
    from app.schemas.autopilot import BacktestResponse

    backtest = await BacktestService.get_backtest(db, backtest_id, current_user.id)

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    return DataResponse(
        data=BacktestResponse.model_validate(backtest),
        timestamp=datetime.now(timezone.utc)
    )


@router.post("/backtests/{backtest_id}/cancel", response_model=DataResponse)
async def cancel_backtest(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a running backtest."""
    from app.services.backtest import BacktestService

    success = await BacktestService.cancel_backtest(db, backtest_id, current_user.id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel backtest")

    return DataResponse(
        message="Backtest cancelled",
        data={"cancelled": True},
        timestamp=datetime.now(timezone.utc)
    )


@router.delete("/backtests/{backtest_id}", status_code=204)
async def delete_backtest(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a backtest."""
    from app.services.backtest import BacktestService

    success = await BacktestService.delete_backtest(db, backtest_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Backtest not found")


# ============================================================================
# PHASE 4: STRATEGY SHARING
# ============================================================================

@router.post("/strategies/{strategy_id}/share", response_model=DataResponse)
async def share_strategy(
    strategy_id: int,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Share a strategy via link."""
    from app.schemas.autopilot import StrategyShareRequest, StrategyShareResponse
    import secrets

    share_request = StrategyShareRequest(**request)

    # Get strategy
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Generate share token
    share_token = secrets.token_urlsafe(16)
    strategy.share_mode = share_request.share_mode.value
    strategy.share_token = share_token
    strategy.shared_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(strategy)

    # Build share URL (this would need to be configured based on environment)
    share_url = f"/autopilot/shared/{share_token}"

    return DataResponse(
        message="Strategy shared successfully",
        data=StrategyShareResponse(
            share_token=share_token,
            share_url=share_url,
            share_mode=strategy.share_mode,
            shared_at=strategy.shared_at
        ),
        timestamp=datetime.now(timezone.utc)
    )


@router.delete("/strategies/{strategy_id}/share", response_model=DataResponse)
async def unshare_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove sharing from a strategy."""
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.id == strategy_id,
            AutoPilotStrategy.user_id == current_user.id
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy.share_mode = "private"
    strategy.share_token = None
    strategy.shared_at = None

    await db.commit()

    return DataResponse(
        message="Strategy sharing removed",
        data={"unshared": True},
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/shared/{share_token}", response_model=DataResponse)
async def get_shared_strategy(
    share_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a shared strategy (public endpoint)."""
    from app.schemas.autopilot import SharedStrategyResponse

    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.share_token == share_token,
            AutoPilotStrategy.share_mode != "private"
        )
    )
    strategy = result.scalar_one_or_none()

    if not strategy:
        raise HTTPException(status_code=404, detail="Shared strategy not found")

    return DataResponse(
        data=SharedStrategyResponse(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            underlying=strategy.underlying,
            position_type=strategy.position_type,
            legs_config=strategy.legs_config,
            entry_conditions=strategy.entry_conditions,
            adjustment_rules=strategy.adjustment_rules,
            risk_settings=strategy.risk_settings,
            shared_at=strategy.shared_at
        ),
        timestamp=datetime.now(timezone.utc)
    )


@router.post("/shared/{share_token}/clone", response_model=DataResponse, status_code=201)
async def clone_shared_strategy(
    share_token: str,
    request: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clone a shared strategy to your account."""
    from app.schemas.autopilot import StrategyCloneFromSharedRequest

    clone_request = StrategyCloneFromSharedRequest(**request)

    # Get shared strategy
    result = await db.execute(
        select(AutoPilotStrategy).where(
            AutoPilotStrategy.share_token == share_token,
            AutoPilotStrategy.share_mode != "private"
        )
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Shared strategy not found")

    # Create clone
    clone_name = clone_request.new_name or f"{original.name} (Cloned)"

    clone = AutoPilotStrategy(
        user_id=current_user.id,
        name=clone_name,
        description=original.description,
        status="draft",
        underlying=original.underlying,
        expiry_type=original.expiry_type,
        lots=clone_request.lots,
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

    # Log cloning
    log = AutoPilotLog(
        user_id=current_user.id,
        strategy_id=clone.id,
        event_type="strategy_cloned",
        severity="info",
        message=f"Strategy '{clone.name}' cloned from shared strategy",
        event_data={"source_id": original.id, "source_name": original.name}
    )
    db.add(log)
    await db.commit()

    return DataResponse(
        message="Strategy cloned successfully",
        data=StrategyResponse.model_validate(clone),
        timestamp=datetime.now(timezone.utc)
    )
