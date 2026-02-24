"""
AI Deployment Trigger and Paper Trading Exit Endpoints

Provides manual deployment triggering and paper trade exit functionality for testing AI Autopilot.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db
from app.utils.dependencies import get_current_user
from app.models.users import User
from app.models.ai import AIUserConfig, AIPaperTrade
from app.services.ai.config_service import AIConfigService
from app.services.ai.kelly_calculator import KellyCalculator
from app.services.ai.market_regime import MarketRegimeClassifier
from app.services.ai.strategy_recommender import StrategyRecommender
from app.services.ai.strike_selector import StrikeSelector
from app.services.ai.deployment_executor import DeploymentExecutor


router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class DeployTriggerRequest(BaseModel):
    """Request schema for manual deployment trigger."""
    underlying: str = Field(..., description="Underlying symbol (NIFTY, BANKNIFTY, FINNIFTY)")
    force: bool = Field(default=False, description="Bypass VIX/time checks for testing")


class LegDetail(BaseModel):
    """Details of a strategy leg."""
    strike: int
    option_type: str  # CE, PE
    transaction_type: str  # BUY, SELL
    entry_premium: float
    qty: int


class DeployTriggerResponse(BaseModel):
    """Response schema for deployment trigger."""
    success: bool
    paper_trade_id: Optional[str] = None
    deployment_id: Optional[str] = None
    strategy_name: Optional[str] = None
    legs: List[LegDetail] = []
    order_ids: List[str] = []
    confidence: Optional[float] = None
    regime: Optional[str] = None
    position_size_lots: Optional[int] = None
    sizing_mode: Optional[str] = None
    error: Optional[str] = None


class PaperExitRequest(BaseModel):
    """Request schema for exiting a paper trade."""
    paper_trade_id: str = Field(..., description="UUID of the paper trade to exit")
    exit_reason: str = Field(default="manual", description="Reason for exit")


class PaperExitResponse(BaseModel):
    """Response schema for paper trade exit."""
    success: bool
    paper_trade_id: str
    entry_total_premium: Optional[float] = None
    exit_total_premium: Optional[float] = None
    realized_pnl: Optional[float] = None
    hold_time_minutes: Optional[int] = None
    exit_reason: Optional[str] = None
    error: Optional[str] = None


class PaperTradeRecord(BaseModel):
    """Individual paper trade record."""
    id: str
    strategy_name: str
    underlying: str
    entry_time: datetime
    entry_regime: str
    entry_confidence: float
    sizing_mode: str
    lots: int
    legs: List[dict]
    entry_total_premium: float
    exit_time: Optional[datetime] = None
    exit_total_premium: Optional[float] = None
    realized_pnl: Optional[float] = None
    status: str


class PaperTradeSummary(BaseModel):
    """Summary of paper trading statistics."""
    total_trades: int
    active_trades: int
    closed_trades: int
    total_pnl: float
    win_rate: float
    avg_pnl_per_trade: float


class PaperTradeListResponse(BaseModel):
    """Response schema for paper trade list."""
    active: List[PaperTradeRecord]
    closed: List[PaperTradeRecord]
    summary: PaperTradeSummary


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/trigger", response_model=DeployTriggerResponse)
async def trigger_deploy(
    request: DeployTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger AI deployment for testing.

    This endpoint allows manual triggering of AI deployment for paper trading testing.
    It will:
    1. Check if AI is enabled
    2. Get current market regime
    3. Get strategy recommendation
    4. Calculate position size based on sizing mode
    5. Create a simulated paper trade

    Args:
        request: Deployment trigger request with underlying and force flag
        current_user: Authenticated user
        db: Database session

    Returns:
        Deployment result with paper trade details

    Raises:
        HTTPException: If AI is disabled or deployment fails
    """
    try:
        # Get user's AI configuration
        user_config = await AIConfigService.get_or_create_config(current_user.id, db)

        # Validate AI is enabled
        if not user_config.ai_enabled:
            raise HTTPException(
                status_code=400,
                detail="AI is not enabled. Please enable AI in settings first."
            )

        # TEST MODE: Use mock data when force=True (for E2E testing)
        if request.force:
            # Mock regime data
            regime_data = {
                'regime_type': 'RANGEBOUND',
                'confidence': 75.0,
                'vix': 15.0
            }
        else:
            # Get current market regime
            regime_classifier = MarketRegimeClassifier(db)
            regime_data = await regime_classifier.classify_regime(request.underlying)

        if not regime_data:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to classify market regime for {request.underlying}"
            )

        # TEST MODE: Use mock recommendation when force=True
        if request.force:
            recommendation = {
                'strategy_name': 'Iron Condor',
                'confidence': 75.0
            }
        else:
            # Get strategy recommendation
            recommender = StrategyRecommender(db)
            recommendations = await recommender.get_top_recommendations(
                regime=regime_data['regime_type'],
                underlying=request.underlying,
                top_n=1
            )

            if not recommendations:
                raise HTTPException(
                    status_code=404,
                    detail=f"No strategy recommendations available for regime {regime_data['regime_type']}"
                )

            recommendation = recommendations[0]

        # Calculate position size based on sizing mode
        lots = await _calculate_position_size(
            user_config=user_config,
            confidence=recommendation['confidence'],
            user_id=current_user.id,
            db=db
        )

        # TEST MODE: Use mock strikes when force=True
        if request.force:
            # Mock Iron Condor strikes for NIFTY at ~25000
            atm = 25000
            leg_configs = [
                {'strike': atm - 200, 'option_type': 'PE', 'transaction_type': 'BUY', 'premium': 50, 'qty': lots * 25},
                {'strike': atm - 100, 'option_type': 'PE', 'transaction_type': 'SELL', 'premium': 100, 'qty': lots * 25},
                {'strike': atm + 100, 'option_type': 'CE', 'transaction_type': 'SELL', 'premium': 100, 'qty': lots * 25},
                {'strike': atm + 200, 'option_type': 'CE', 'transaction_type': 'BUY', 'premium': 50, 'qty': lots * 25}
            ]
        else:
            # Select strikes for the strategy
            strike_selector = StrikeSelector(db)
            leg_configs = await strike_selector.select_strikes(
                strategy_template_name=recommendation['strategy_name'],
                underlying=request.underlying,
                vix=regime_data.get('vix', 15.0)
            )

            if not leg_configs:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to select strikes for strategy {recommendation['strategy_name']}"
                )

        # Create paper trade record
        paper_trade = AIPaperTrade(
            user_id=current_user.id,
            strategy_name=recommendation['strategy_name'],
            underlying=request.underlying,
            entry_time=datetime.utcnow(),
            entry_regime=regime_data['regime_type'],
            entry_confidence=Decimal(str(recommendation['confidence'])),
            sizing_mode=user_config.sizing_mode,
            lots=lots,
            legs=leg_configs,
            entry_total_premium=Decimal(str(sum(leg.get('premium', 0) * leg.get('qty', 0) for leg in leg_configs))),
            status='open'
        )

        db.add(paper_trade)
        await db.commit()
        await db.refresh(paper_trade)

        # DEBUG: Log paper trade creation
        print(f"[DEBUG] Created paper trade: ID={paper_trade.id}, strategy={paper_trade.strategy_name}, status={paper_trade.status}, lots={paper_trade.lots}")

        # Generate simulated order IDs
        order_ids = [f"PAPER_{i}" for i in range(len(leg_configs))]

        # Build response
        return DeployTriggerResponse(
            success=True,
            paper_trade_id=str(paper_trade.id),
            deployment_id=str(paper_trade.id),
            strategy_name=recommendation['strategy_name'],
            legs=[
                LegDetail(
                    strike=leg['strike'],
                    option_type=leg['option_type'],
                    transaction_type=leg['transaction_type'],
                    entry_premium=leg.get('premium', 0),
                    qty=leg.get('qty', 0)
                )
                for leg in leg_configs
            ],
            order_ids=order_ids,
            confidence=recommendation['confidence'],
            regime=regime_data['regime_type'],
            position_size_lots=lots,
            sizing_mode=user_config.sizing_mode
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        return DeployTriggerResponse(
            success=False,
            error=str(e)
        )


@router.post("/paper-trade/exit", response_model=PaperExitResponse)
async def exit_paper_trade(
    request: PaperExitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Exit a paper trade and calculate P&L.

    Simulates closing a paper trade by:
    1. Fetching the paper trade record
    2. Simulating exit premiums (using entry premiums + random P&L for now)
    3. Calculating P&L
    4. Updating graduation stats

    Args:
        request: Exit request with paper_trade_id
        current_user: Authenticated user
        db: Database session

    Returns:
        Exit result with P&L details

    Raises:
        HTTPException: If paper trade not found or already closed
    """
    try:
        # Fetch paper trade
        stmt = select(AIPaperTrade).where(
            AIPaperTrade.id == UUID(request.paper_trade_id),
            AIPaperTrade.user_id == current_user.id
        )
        result = await db.execute(stmt)
        paper_trade = result.scalar_one_or_none()

        if not paper_trade:
            raise HTTPException(
                status_code=404,
                detail=f"Paper trade {request.paper_trade_id} not found"
            )

        if paper_trade.status == 'closed':
            raise HTTPException(
                status_code=400,
                detail=f"Paper trade {request.paper_trade_id} is already closed"
            )

        # Calculate hold time (use timezone-aware datetime to match entry_time)
        hold_time = (datetime.now(timezone.utc) - paper_trade.entry_time).total_seconds() / 60

        # Simulate exit premiums (simplified - in real implementation, fetch live prices)
        # For paper trading, we'll use a simple simulation:
        # Assume a random P&L between -20% to +20% of entry premium
        import random
        exit_premium_multiplier = 1 + (random.random() * 0.4 - 0.2)  # 0.8 to 1.2

        exit_total_premium = float(paper_trade.entry_total_premium) * exit_premium_multiplier

        # Calculate P&L (for SELL positions, profit when premium decreases)
        # For simplicity, assuming all legs are SELL for now
        realized_pnl = float(paper_trade.entry_total_premium) - exit_total_premium

        # Update paper trade
        paper_trade.exit_time = datetime.now(timezone.utc)
        paper_trade.exit_reason = request.exit_reason
        paper_trade.exit_total_premium = Decimal(str(exit_total_premium))
        paper_trade.realized_pnl = Decimal(str(realized_pnl))
        paper_trade.status = 'closed'

        # Update user's paper trading stats
        stmt_config = select(AIUserConfig).where(AIUserConfig.user_id == current_user.id)
        result_config = await db.execute(stmt_config)
        user_config = result_config.scalar_one_or_none()

        if user_config:
            user_config.paper_trades_completed += 1
            user_config.paper_total_pnl += Decimal(str(realized_pnl))

            # Recalculate win rate
            if user_config.paper_trades_completed > 0:
                # Count winning trades (simplified - checking if this trade is a win)
                is_win = realized_pnl > 0
                old_wins = int((user_config.paper_win_rate / 100) * (user_config.paper_trades_completed - 1))
                new_wins = old_wins + (1 if is_win else 0)
                user_config.paper_win_rate = Decimal(str((new_wins / user_config.paper_trades_completed) * 100))

        await db.commit()
        await db.refresh(paper_trade)

        return PaperExitResponse(
            success=True,
            paper_trade_id=str(paper_trade.id),
            entry_total_premium=float(paper_trade.entry_total_premium),
            exit_total_premium=float(paper_trade.exit_total_premium),
            realized_pnl=float(paper_trade.realized_pnl),
            hold_time_minutes=int(hold_time),
            exit_reason=paper_trade.exit_reason
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        return PaperExitResponse(
            success=False,
            paper_trade_id=request.paper_trade_id,
            error=str(e)
        )


@router.get("/paper-trade/list", response_model=PaperTradeListResponse)
async def list_paper_trades(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of paper trades (active and closed).

    Returns all paper trades for the current user, separated into active and closed,
    along with summary statistics.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of paper trades with summary
    """
    try:
        # Fetch all paper trades for user
        stmt = select(AIPaperTrade).where(
            AIPaperTrade.user_id == current_user.id
        ).order_by(AIPaperTrade.entry_time.desc())

        result = await db.execute(stmt)
        all_trades = result.scalars().all()

        # DEBUG: Log what we found
        print(f"[DEBUG] List paper trades: Found {len(all_trades)} total trades for user {current_user.id}")
        for t in all_trades:
            print(f"  - {t.id}: {t.strategy_name} ({t.status})")

        # Separate active and closed
        active_trades = [t for t in all_trades if t.status == 'open']
        closed_trades = [t for t in all_trades if t.status == 'closed']

        print(f"[DEBUG] Active: {len(active_trades)}, Closed: {len(closed_trades)}")

        # Calculate summary
        total_pnl = sum(float(t.realized_pnl or 0) for t in closed_trades)
        winning_trades = sum(1 for t in closed_trades if (t.realized_pnl or 0) > 0)
        win_rate = (winning_trades / len(closed_trades) * 100) if closed_trades else 0
        avg_pnl = (total_pnl / len(closed_trades)) if closed_trades else 0

        # Build response
        return PaperTradeListResponse(
            active=[
                PaperTradeRecord(
                    id=str(t.id),
                    strategy_name=t.strategy_name,
                    underlying=t.underlying,
                    entry_time=t.entry_time,
                    entry_regime=t.entry_regime,
                    entry_confidence=float(t.entry_confidence),
                    sizing_mode=t.sizing_mode,
                    lots=t.lots,
                    legs=t.legs,
                    entry_total_premium=float(t.entry_total_premium),
                    status=t.status
                )
                for t in active_trades
            ],
            closed=[
                PaperTradeRecord(
                    id=str(t.id),
                    strategy_name=t.strategy_name,
                    underlying=t.underlying,
                    entry_time=t.entry_time,
                    entry_regime=t.entry_regime,
                    entry_confidence=float(t.entry_confidence),
                    sizing_mode=t.sizing_mode,
                    lots=t.lots,
                    legs=t.legs,
                    entry_total_premium=float(t.entry_total_premium),
                    exit_time=t.exit_time,
                    exit_total_premium=float(t.exit_total_premium) if t.exit_total_premium else None,
                    realized_pnl=float(t.realized_pnl) if t.realized_pnl else None,
                    status=t.status
                )
                for t in closed_trades
            ],
            summary=PaperTradeSummary(
                total_trades=len(all_trades),
                active_trades=len(active_trades),
                closed_trades=len(closed_trades),
                total_pnl=total_pnl,
                win_rate=win_rate,
                avg_pnl_per_trade=avg_pnl
            )
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Helper Functions
# ============================================================================

async def _calculate_position_size(
    user_config: AIUserConfig,
    confidence: float,
    user_id=None,
    db: AsyncSession = None
) -> int:
    """
    Calculate position size based on sizing mode and confidence.

    Args:
        user_config: User's AI configuration
        confidence: Strategy confidence score (0-100)
        user_id: User ID (required for Kelly mode)
        db: Database session (required for Kelly mode)

    Returns:
        Number of lots to trade
    """
    if user_config.sizing_mode == 'fixed':
        return user_config.base_lots

    elif user_config.sizing_mode == 'tiered':
        # Find the appropriate tier
        for tier in user_config.confidence_tiers:
            if tier['min'] <= confidence < tier['max']:
                return int(user_config.base_lots * tier['multiplier'])
        # Default to base_lots if no tier matches
        return user_config.base_lots

    elif user_config.sizing_mode == 'kelly':
        if db is None or user_id is None:
            return user_config.base_lots

        calculator = KellyCalculator(db)
        # Use a default capital estimate from base_lots × typical margin per lot
        # Capital and max_loss_per_lot defaults; callers can extend this later
        capital = float(user_config.base_lots) * 50000.0  # rough per-lot margin
        max_loss_per_lot = capital / max(user_config.base_lots, 1) * 0.1  # 10% of margin

        result = await calculator.get_kelly_recommendation(
            user_id=user_id,
            capital=capital,
            max_loss_per_lot=max_loss_per_lot,
            underlying=(user_config.preferred_underlyings or ["NIFTY"])[0],
            lookback_days=90,
        )

        if result.get("enabled") and result.get("optimal_lots", 0) > 0:
            return result["optimal_lots"]

        # Kelly not reliable yet — fall back to confidence-scaled base
        return max(1, int(user_config.base_lots * (confidence / 100)))

    else:
        return user_config.base_lots
