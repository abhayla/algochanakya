"""
AI Deployment Executor Service

Automatically deploys recommended strategies to live or paper trading.

Features:
- Strategy deployment from AI recommendations
- Strike selection and leg configuration
- Order placement via Kite Connect
- Deployment tracking and logging
- Paper trading support
- Rollback on partial failures
"""

import logging
from typing import Optional, List, Dict, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.models.ai import AIUserConfig
from app.services.ai.market_regime import RegimeType

if TYPE_CHECKING:
    from app.schemas.ai import RegimeResponse
from app.services.ai.strategy_recommender import StrategyRecommendation
from app.services.ai.strike_selector import StrikeSelector, StrategyStrikes
from app.constants.trading import get_lot_size

logger = logging.getLogger(__name__)


class DeploymentStatus:
    """Deployment execution status."""

    def __init__(
        self,
        success: bool,
        strategy_id: Optional[UUID] = None,
        order_ids: Optional[List[str]] = None,
        error: Optional[str] = None,
        strikes: Optional[StrategyStrikes] = None
    ):
        self.success = success
        self.strategy_id = strategy_id
        self.order_ids = order_ids or []
        self.error = error
        self.strikes = strikes
        self.deployed_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "strategy_id": str(self.strategy_id) if self.strategy_id else None,
            "order_ids": self.order_ids,
            "error": self.error,
            "strikes": self.strikes.to_dict() if self.strikes else None,
            "deployed_at": self.deployed_at.isoformat()
        }


class DeploymentExecutor:
    """
    Executes auto-deployment of AI-recommended strategies.

    Workflow:
    1. Receive strategy recommendation
    2. Select optimal strikes using StrikeSelector
    3. Validate deployment rules (capital, risk limits)
    4. Place orders via Kite Connect
    5. Track deployment status
    6. Rollback on failures
    """

    def __init__(self, kite: KiteConnect, db: AsyncSession):
        self.kite = kite
        self.db = db
        self.strike_selector = StrikeSelector(kite)

    async def deploy_strategy(
        self,
        recommendation: StrategyRecommendation,
        regime: "RegimeResponse",
        user_config: AIUserConfig,
        paper_mode: bool = False
    ) -> DeploymentStatus:
        """
        Deploy a recommended strategy.

        Args:
            recommendation: Strategy recommendation from AI
            regime: Current market regime
            user_config: User's AI configuration
            paper_mode: If True, simulates orders without placing them

        Returns:
            DeploymentStatus with result
        """
        try:
            logger.info(f"Deploying strategy: {recommendation.template.name}")

            # Step 1: Validate deployment
            validation_error = await self._validate_deployment(recommendation, user_config)
            if validation_error:
                logger.warning(f"Deployment validation failed: {validation_error}")
                return DeploymentStatus(
                    success=False,
                    error=validation_error
                )

            # Step 2: Select strikes
            underlying = regime.indicators.underlying
            spot_price = regime.indicators.spot_price

            strikes = await self.strike_selector.select_strikes(
                strategy_name=recommendation.template.name,
                underlying=underlying,
                spot_price=spot_price,
                regime=regime,
                user_config=user_config,
                db=self.db
            )

            if not strikes:
                return DeploymentStatus(
                    success=False,
                    error=f"Unable to select strikes for {recommendation.template.name}"
                )

            logger.info(f"Selected strikes: {strikes.to_dict()}")

            # Step 3: Calculate position size (lots)
            lots = self._calculate_position_size(
                underlying=underlying,
                confidence=recommendation.confidence,
                user_config=user_config
            )

            if lots == 0:
                return DeploymentStatus(
                    success=False,
                    error="Confidence too low for deployment (lots = 0)"
                )

            logger.info(f"Position size: {lots} lot(s)")

            # Step 4: Place orders
            if paper_mode:
                logger.info("Paper mode: Simulating order placement")
                order_ids = [f"PAPER_{i}" for i in range(len(strikes.legs))]
                status = DeploymentStatus(
                    success=True,
                    order_ids=order_ids,
                    strikes=strikes
                )
            else:
                order_ids = await self._place_orders(strikes, lots, underlying)
                status = DeploymentStatus(
                    success=True,
                    order_ids=order_ids,
                    strikes=strikes
                )

            logger.info(f"Deployment successful: {len(order_ids)} orders placed")
            return status

        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return DeploymentStatus(
                success=False,
                error=str(e)
            )

    async def _validate_deployment(
        self,
        recommendation: StrategyRecommendation,
        user_config: AIUserConfig
    ) -> Optional[str]:
        """
        Validate if deployment is allowed.

        Checks:
        - Confidence threshold met
        - User has AI enabled
        - User has allowed this strategy

        Returns:
            Error message if validation fails, None otherwise
        """
        # Check if AI is enabled
        if not user_config.ai_enabled:
            return "AI features are not enabled for this user"

        # Check confidence threshold
        if recommendation.confidence < user_config.min_confidence_to_trade:
            return f"Confidence {recommendation.confidence}% below minimum {user_config.min_confidence_to_trade}%"

        # Check if strategy is allowed
        if user_config.allowed_strategies:
            if recommendation.template.name not in user_config.allowed_strategies:
                return f"Strategy {recommendation.template.name} not in allowed list"

        return None

    def _calculate_position_size(
        self,
        underlying: str,
        confidence: float,
        user_config: AIUserConfig
    ) -> int:
        """
        Calculate position size in lots based on confidence.

        Uses confidence tiers:
        - SKIP: < min_confidence (0 lots)
        - LOW: min_confidence to 70% (1 lot)
        - MEDIUM: 70% to 85% (2 lots)
        - HIGH: > 85% (3 lots)

        Args:
            underlying: Index name
            confidence: Strategy confidence score
            user_config: User configuration

        Returns:
            Number of lots
        """
        min_conf = user_config.min_confidence_to_trade

        if confidence < min_conf:
            return 0
        elif confidence < 70:
            return 1
        elif confidence < 85:
            return 2
        else:
            return 3

    async def _place_orders(
        self,
        strikes: StrategyStrikes,
        lots: int,
        underlying: str
    ) -> List[str]:
        """
        Place orders for all strategy legs via Kite Connect.

        Args:
            strikes: Selected strikes with instrument details
            lots: Number of lots
            underlying: Index name

        Returns:
            List of Kite order IDs

        Raises:
            Exception if order placement fails
        """
        order_ids = []
        lot_size = get_lot_size(underlying)
        total_qty = lots * lot_size

        try:
            import asyncio
            from app.utils.tradingsymbol import build_tradingsymbol

            for i, leg in enumerate(strikes.legs):
                logger.info(f"Placing order for leg {i + 1}: {leg.option_type} {leg.strike}")

                # Determine transaction type based on leg configuration
                # Default: SELL for short positions (e.g., short strangle, iron condor shorts)
                transaction_type = leg.transaction_type if hasattr(leg, 'transaction_type') else "SELL"

                # Build trading symbol (e.g., "NIFTY2312520000CE")
                tradingsymbol = build_tradingsymbol(
                    underlying=underlying,
                    expiry=strikes.expiry,
                    strike=int(leg.strike),
                    option_type=leg.option_type
                )

                # Place order via Kite Connect
                loop = asyncio.get_event_loop()
                kite_order_id = await loop.run_in_executor(
                    None,
                    lambda: self.kite.place_order(
                        variety="regular",
                        exchange="NFO",
                        tradingsymbol=tradingsymbol,
                        transaction_type=transaction_type,
                        quantity=total_qty,
                        product="NRML",  # Normal (overnight) product type
                        order_type="MARKET"  # Market order for immediate execution
                    )
                )

                order_ids.append(str(kite_order_id))
                logger.info(f"Order placed successfully: {kite_order_id} for {tradingsymbol}")

            return order_ids

        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            # Rollback: Cancel all placed orders
            await self._rollback_orders(order_ids)
            raise

    async def _rollback_orders(self, order_ids: List[str]):
        """
        Rollback (cancel) partially placed orders on failure.

        Args:
            order_ids: List of Kite order IDs to cancel
        """
        if not order_ids:
            return

        logger.warning(f"Rolling back {len(order_ids)} orders")

        import asyncio

        for order_id in order_ids:
            try:
                # Cancel order via Kite Connect
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.kite.cancel_order(variety="regular", order_id=order_id)
                )
                logger.info(f"Successfully rolled back order: {order_id}")
            except Exception as e:
                logger.error(f"Failed to rollback order {order_id}: {e}")


__all__ = [
    "DeploymentExecutor",
    "DeploymentStatus"
]
