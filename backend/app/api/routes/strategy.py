"""
Strategy Builder API Routes

CRUD operations for strategies and strategy legs, P/L calculations, and sharing.
"""
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import date

from app.database import get_db
from app.models import User, Strategy, StrategyLeg
from app.schemas.strategies import (
    StrategyCreate,
    StrategyUpdate,
    StrategyResponse,
    StrategyListResponse,
    StrategyLegCreate,
    StrategyLegUpdate,
    StrategyLegResponse,
    PnLCalculateRequest,
    PnLCalculateResponse,
    ShareStrategyResponse,
)
from app.services.pnl_calculator import pnl_calculator, generate_spot_range, PnLCalculator
from app.utils.dependencies import get_current_user

router = APIRouter()


# ==================== STRATEGY CRUD ====================

@router.get("", response_model=List[StrategyListResponse])
async def list_strategies(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (open, closed)"),
    underlying: Optional[str] = Query(None, description="Filter by underlying"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all strategies for the current user.

    Args:
        status_filter: Optional status filter
        underlying: Optional underlying filter

    Returns:
        List of user's strategies
    """
    try:
        conditions = [Strategy.user_id == user.id]

        if status_filter:
            conditions.append(Strategy.status == status_filter.lower())
        if underlying:
            conditions.append(Strategy.underlying == underlying.upper())

        query = select(Strategy).options(
            selectinload(Strategy.legs)
        ).where(
            and_(*conditions)
        ).order_by(Strategy.updated_at.desc())

        result = await db.execute(query)
        strategies = result.scalars().all()

        return [
            StrategyListResponse(
                id=s.id,
                name=s.name,
                underlying=s.underlying,
                status=s.status,
                legs_count=len(s.legs),
                created_at=s.created_at
            )
            for s in strategies
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list strategies: {str(e)}"
        )


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    strategy_data: StrategyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new strategy with optional legs.

    Args:
        strategy_data: Strategy creation data

    Returns:
        Created strategy with legs
    """
    try:
        # Validate underlying
        underlying = strategy_data.underlying.upper()
        if underlying not in ["NIFTY", "BANKNIFTY", "FINNIFTY"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Underlying must be NIFTY, BANKNIFTY, or FINNIFTY"
            )

        # Create strategy
        strategy = Strategy(
            user_id=user.id,
            name=strategy_data.name,
            underlying=underlying,
            status="open"
        )
        db.add(strategy)
        await db.flush()

        # Add legs if provided
        if strategy_data.legs:
            for leg_data in strategy_data.legs:
                leg = StrategyLeg(
                    strategy_id=strategy.id,
                    expiry_date=leg_data.expiry_date,
                    contract_type=leg_data.contract_type.value,
                    transaction_type=leg_data.transaction_type.value,
                    strike_price=leg_data.strike_price,
                    lots=leg_data.lots,
                    strategy_type=leg_data.strategy_type,
                    entry_price=leg_data.entry_price,
                    exit_price=leg_data.exit_price,
                    instrument_token=leg_data.instrument_token,
                    position_status="pending"
                )
                db.add(leg)

        await db.commit()
        await db.refresh(strategy)

        # Load legs
        result = await db.execute(
            select(Strategy).options(
                selectinload(Strategy.legs)
            ).where(Strategy.id == strategy.id)
        )
        strategy = result.scalar_one()

        return strategy

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy: {str(e)}"
        )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a strategy by ID with all legs.

    Args:
        strategy_id: Strategy UUID

    Returns:
        Strategy with legs
    """
    try:
        result = await db.execute(
            select(Strategy).options(
                selectinload(Strategy.legs)
            ).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == user.id
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        return strategy

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get strategy: {str(e)}"
        )


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    strategy_data: StrategyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a strategy.

    Args:
        strategy_id: Strategy UUID
        strategy_data: Update data

    Returns:
        Updated strategy
    """
    try:
        result = await db.execute(
            select(Strategy).options(
                selectinload(Strategy.legs)
            ).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == user.id
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Update fields
        if strategy_data.name is not None:
            strategy.name = strategy_data.name
        if strategy_data.status is not None:
            strategy.status = strategy_data.status.value

        await db.commit()
        await db.refresh(strategy)

        return strategy

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy: {str(e)}"
        )


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a strategy and all its legs.

    Args:
        strategy_id: Strategy UUID
    """
    try:
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == user.id
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        await db.delete(strategy)
        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete strategy: {str(e)}"
        )


# ==================== STRATEGY LEGS ====================

@router.post("/{strategy_id}/legs", response_model=StrategyLegResponse, status_code=status.HTTP_201_CREATED)
async def add_leg(
    strategy_id: UUID,
    leg_data: StrategyLegCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a leg to a strategy.

    Args:
        strategy_id: Strategy UUID
        leg_data: Leg creation data

    Returns:
        Created leg
    """
    try:
        # Verify strategy ownership
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == user.id
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Create leg
        leg = StrategyLeg(
            strategy_id=strategy_id,
            expiry_date=leg_data.expiry_date,
            contract_type=leg_data.contract_type.value,
            transaction_type=leg_data.transaction_type.value,
            strike_price=leg_data.strike_price,
            lots=leg_data.lots,
            strategy_type=leg_data.strategy_type,
            entry_price=leg_data.entry_price,
            exit_price=leg_data.exit_price,
            instrument_token=leg_data.instrument_token,
            position_status="pending"
        )
        db.add(leg)
        await db.commit()
        await db.refresh(leg)

        return leg

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add leg: {str(e)}"
        )


@router.put("/{strategy_id}/legs/{leg_id}", response_model=StrategyLegResponse)
async def update_leg(
    strategy_id: UUID,
    leg_id: UUID,
    leg_data: StrategyLegUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a strategy leg.

    Args:
        strategy_id: Strategy UUID
        leg_id: Leg UUID
        leg_data: Update data

    Returns:
        Updated leg
    """
    try:
        # Verify strategy ownership and get leg
        result = await db.execute(
            select(StrategyLeg).join(Strategy).where(
                and_(
                    StrategyLeg.id == leg_id,
                    StrategyLeg.strategy_id == strategy_id,
                    Strategy.user_id == user.id
                )
            )
        )
        leg = result.scalar_one_or_none()

        if not leg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leg not found"
            )

        # Update fields
        update_fields = leg_data.model_dump(exclude_unset=True)
        for field, value in update_fields.items():
            if value is not None:
                if hasattr(value, 'value'):  # Handle Enums
                    setattr(leg, field, value.value)
                else:
                    setattr(leg, field, value)

        await db.commit()
        await db.refresh(leg)

        return leg

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update leg: {str(e)}"
        )


@router.delete("/{strategy_id}/legs/{leg_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_leg(
    strategy_id: UUID,
    leg_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a strategy leg.

    Args:
        strategy_id: Strategy UUID
        leg_id: Leg UUID
    """
    try:
        # Verify strategy ownership and get leg
        result = await db.execute(
            select(StrategyLeg).join(Strategy).where(
                and_(
                    StrategyLeg.id == leg_id,
                    StrategyLeg.strategy_id == strategy_id,
                    Strategy.user_id == user.id
                )
            )
        )
        leg = result.scalar_one_or_none()

        if not leg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Leg not found"
            )

        await db.delete(leg)
        await db.commit()

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete leg: {str(e)}"
        )


# ==================== P/L CALCULATION ====================

@router.post("/calculate", response_model=PnLCalculateResponse)
async def calculate_pnl(
    request: PnLCalculateRequest,
    user: User = Depends(get_current_user)
):
    """
    Calculate P/L grid for strategy legs.

    Uses two-pass calculation:
    1. First pass on base spot range to determine breakeven points
    2. Second pass with enhanced spot range including breakevens, strikes, and ATM

    Args:
        request: P/L calculation request with legs and mode

    Returns:
        P/L grid with spot prices and P/L values
    """
    try:
        if not request.legs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one leg is required"
            )

        # Convert legs to dict format for calculator
        legs = []
        strikes = []
        for leg in request.legs:
            strike = float(leg.strike)
            strikes.append(strike)
            legs.append({
                "strike": strike,
                "contract_type": leg.contract_type.value,
                "transaction_type": leg.transaction_type.value,
                "lots": leg.lots,
                "lot_size": leg.lot_size,
                "entry_price": float(leg.entry_price),
                "expiry_date": leg.expiry_date
            })

        # Use current_spot from request if provided, otherwise estimate from strikes
        current_spot = request.current_spot if request.current_spot else (sum(strikes) / len(strikes) if strikes else 25000)

        # PASS 1: Calculate on base spot range to get breakeven points
        base_spot_prices = generate_spot_range(strikes, current_spot, include_strikes=False)
        target_date = request.target_date or date.today()

        first_pass = pnl_calculator.calculate_pnl_grid(
            legs=legs,
            spot_prices=base_spot_prices,
            mode=request.mode.value,
            target_date=target_date,
            volatility=request.volatility or 0.15
        )

        # PASS 2: Regenerate spot range including breakevens, strikes, and ATM
        breakevens = first_pass.get("breakeven", [])
        final_spot_prices = generate_spot_range(
            strikes,
            current_spot,
            breakevens=breakevens,
            include_strikes=True
        )

        # Calculate final P/L on enhanced spot range
        result = pnl_calculator.calculate_pnl_grid(
            legs=legs,
            spot_prices=final_spot_prices,
            mode=request.mode.value,
            target_date=target_date,
            volatility=request.volatility or 0.15
        )

        return PnLCalculateResponse(
            spot_prices=result["spot_prices"],
            leg_pnl=result["leg_pnl"],
            total_pnl=result["total_pnl"],
            current_spot=current_spot,
            max_profit=result["max_profit"],
            max_loss=result["max_loss"],
            breakeven=result["breakeven"]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate P/L: {str(e)}"
        )


# ==================== SHARING ====================

@router.post("/{strategy_id}/share", response_model=ShareStrategyResponse)
async def share_strategy(
    strategy_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a share link for a strategy.

    Args:
        strategy_id: Strategy UUID

    Returns:
        Share code and URL
    """
    try:
        result = await db.execute(
            select(Strategy).where(
                and_(
                    Strategy.id == strategy_id,
                    Strategy.user_id == user.id
                )
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )

        # Generate share code if not exists
        if not strategy.share_code:
            strategy.share_code = secrets.token_urlsafe(12)
            await db.commit()
            await db.refresh(strategy)

        # Construct share URL (frontend will handle this route)
        share_url = f"/strategy/shared/{strategy.share_code}"

        return ShareStrategyResponse(
            share_code=strategy.share_code,
            share_url=share_url
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share strategy: {str(e)}"
        )


@router.get("/shared/{share_code}", response_model=StrategyResponse)
async def get_shared_strategy(
    share_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a shared strategy by share code (public, no auth required).

    Args:
        share_code: Strategy share code

    Returns:
        Strategy with legs
    """
    try:
        result = await db.execute(
            select(Strategy).options(
                selectinload(Strategy.legs)
            ).where(Strategy.share_code == share_code)
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared strategy not found"
            )

        return strategy

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shared strategy: {str(e)}"
        )
