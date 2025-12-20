"""
Position Leg Service - Phase 5

Manages individual position legs with Greeks and P&L tracking.
Provides CRUD operations and real-time updates.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import logging

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload

from app.models.autopilot import (
    AutoPilotPositionLeg,
    AutoPilotStrategy,
    PositionLegStatus
)
from app.services.greeks_calculator import GreeksCalculatorService
from app.services.market_data import MarketDataService
from app.constants import get_lot_size

logger = logging.getLogger(__name__)


class PositionLegService:
    """Service for managing position legs."""

    def __init__(self, kite: KiteConnect, db: AsyncSession):
        self.kite = kite
        self.db = db
        self.greeks_calc = GreeksCalculatorService()
        self.market_data = MarketDataService(kite)

    async def create_position_leg(
        self,
        strategy_id: int,
        leg_id: str,
        contract_type: str,
        action: str,
        strike: Decimal,
        expiry: date,
        lots: int,
        tradingsymbol: Optional[str] = None,
        instrument_token: Optional[int] = None,
        entry_price: Optional[Decimal] = None
    ) -> AutoPilotPositionLeg:
        """
        Create a new position leg.

        Args:
            strategy_id: Strategy ID
            leg_id: Unique leg identifier within strategy
            contract_type: CE or PE
            action: BUY or SELL
            strike: Strike price
            expiry: Expiry date
            lots: Number of lots
            tradingsymbol: Trading symbol
            instrument_token: Instrument token
            entry_price: Entry price (if already entered)

        Returns:
            Created position leg
        """
        try:
            leg = AutoPilotPositionLeg(
                strategy_id=strategy_id,
                leg_id=leg_id,
                contract_type=contract_type,
                action=action,
                strike=strike,
                expiry=expiry,
                lots=lots,
                tradingsymbol=tradingsymbol,
                instrument_token=instrument_token,
                entry_price=entry_price,
                status=PositionLegStatus.PENDING.value
            )

            self.db.add(leg)
            await self.db.commit()
            await self.db.refresh(leg)

            logger.info(f"Created position leg {leg_id} for strategy {strategy_id}")
            return leg

        except Exception as e:
            logger.error(f"Error creating position leg: {e}")
            await self.db.rollback()
            raise

    async def get_position_leg(
        self,
        strategy_id: int,
        leg_id: str
    ) -> Optional[AutoPilotPositionLeg]:
        """
        Get a position leg by strategy_id and leg_id.

        Args:
            strategy_id: Strategy ID
            leg_id: Leg identifier

        Returns:
            Position leg or None if not found
        """
        try:
            query = select(AutoPilotPositionLeg).where(
                and_(
                    AutoPilotPositionLeg.strategy_id == strategy_id,
                    AutoPilotPositionLeg.leg_id == leg_id
                )
            )

            result = await self.db.execute(query)
            leg = result.scalar_one_or_none()

            return leg

        except Exception as e:
            logger.error(f"Error getting position leg: {e}")
            raise

    async def get_all_strategy_legs(
        self,
        strategy_id: int,
        status_filter: Optional[str] = None
    ) -> List[AutoPilotPositionLeg]:
        """
        Get all position legs for a strategy.

        Args:
            strategy_id: Strategy ID
            status_filter: Optional status filter (open, closed, etc.)

        Returns:
            List of position legs
        """
        try:
            query = select(AutoPilotPositionLeg).where(
                AutoPilotPositionLeg.strategy_id == strategy_id
            )

            if status_filter:
                query = query.where(AutoPilotPositionLeg.status == status_filter)

            query = query.order_by(AutoPilotPositionLeg.created_at)

            result = await self.db.execute(query)
            legs = result.scalars().all()

            return list(legs)

        except Exception as e:
            logger.error(f"Error getting strategy legs: {e}")
            raise

    async def update_leg_entry(
        self,
        strategy_id: int,
        leg_id: str,
        entry_price: Decimal,
        entry_order_ids: List[str],
        entry_time: Optional[datetime] = None
    ) -> AutoPilotPositionLeg:
        """
        Update leg with entry details.

        Args:
            strategy_id: Strategy ID
            leg_id: Leg identifier
            entry_price: Executed entry price
            entry_order_ids: List of order IDs
            entry_time: Entry timestamp

        Returns:
            Updated leg
        """
        try:
            leg = await self.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            leg.entry_price = entry_price
            leg.entry_order_ids = entry_order_ids
            leg.entry_time = entry_time or datetime.now()
            leg.status = PositionLegStatus.OPEN.value

            await self.db.commit()
            await self.db.refresh(leg)

            logger.info(f"Updated entry for leg {leg_id}: price={entry_price}")
            return leg

        except Exception as e:
            logger.error(f"Error updating leg entry: {e}")
            await self.db.rollback()
            raise

    async def update_leg_exit(
        self,
        strategy_id: int,
        leg_id: str,
        exit_price: Decimal,
        exit_order_ids: List[str],
        exit_reason: str,
        exit_time: Optional[datetime] = None
    ) -> AutoPilotPositionLeg:
        """
        Update leg with exit details.

        Args:
            strategy_id: Strategy ID
            leg_id: Leg identifier
            exit_price: Executed exit price
            exit_order_ids: List of order IDs
            exit_reason: Reason for exit
            exit_time: Exit timestamp

        Returns:
            Updated leg
        """
        try:
            leg = await self.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            leg.exit_price = exit_price
            leg.exit_order_ids = exit_order_ids
            leg.exit_reason = exit_reason
            leg.exit_time = exit_time or datetime.now()
            leg.status = PositionLegStatus.CLOSED.value

            # Calculate realized P&L
            if leg.entry_price:
                leg.realized_pnl = await self._calculate_realized_pnl(leg, exit_price)
                leg.unrealized_pnl = Decimal('0')

            await self.db.commit()
            await self.db.refresh(leg)

            logger.info(f"Updated exit for leg {leg_id}: price={exit_price}, P&L={leg.realized_pnl}")
            return leg

        except Exception as e:
            logger.error(f"Error updating leg exit: {e}")
            await self.db.rollback()
            raise

    async def update_leg_greeks(
        self,
        strategy_id: int,
        leg_id: str,
        spot_price: Decimal,
        current_price: Decimal
    ) -> AutoPilotPositionLeg:
        """
        Update leg Greeks and P&L.

        Args:
            strategy_id: Strategy ID
            leg_id: Leg identifier
            spot_price: Current spot price
            current_price: Current option price

        Returns:
            Updated leg
        """
        try:
            leg = await self.get_position_leg(strategy_id, leg_id)
            if not leg:
                raise ValueError(f"Position leg {leg_id} not found")

            if leg.status != PositionLegStatus.OPEN.value:
                logger.debug(f"Leg {leg_id} is not open, skipping Greeks update")
                return leg

            # Calculate Greeks
            greeks = await self._calculate_leg_greeks(
                spot_price=spot_price,
                strike=leg.strike,
                expiry=leg.expiry,
                option_type=leg.contract_type,
                price=current_price
            )

            # Update Greeks
            leg.delta = greeks.get('delta')
            leg.gamma = greeks.get('gamma')
            leg.theta = greeks.get('theta')
            leg.vega = greeks.get('vega')
            leg.iv = greeks.get('iv')

            # Update unrealized P&L
            if leg.entry_price:
                leg.unrealized_pnl = await self._calculate_unrealized_pnl(leg, current_price)

            await self.db.commit()
            await self.db.refresh(leg)

            return leg

        except Exception as e:
            logger.error(f"Error updating leg Greeks: {e}")
            await self.db.rollback()
            raise

    async def update_all_legs_greeks(
        self,
        strategy_id: int,
        spot_price: Decimal
    ) -> List[AutoPilotPositionLeg]:
        """
        Update Greeks for all open legs in a strategy.

        Args:
            strategy_id: Strategy ID
            spot_price: Current spot price

        Returns:
            List of updated legs
        """
        try:
            # Get all open legs
            open_legs = await self.get_all_strategy_legs(
                strategy_id=strategy_id,
                status_filter=PositionLegStatus.OPEN.value
            )

            if not open_legs:
                return []

            # Get current prices for all legs
            instrument_keys = [
                f"NFO:{leg.tradingsymbol}" for leg in open_legs
                if leg.tradingsymbol
            ]

            if not instrument_keys:
                return open_legs

            ltp_data = await self.market_data.get_ltp(instrument_keys)

            # Update each leg
            updated_legs = []
            for leg in open_legs:
                if not leg.tradingsymbol:
                    continue

                key = f"NFO:{leg.tradingsymbol}"
                current_price = ltp_data.get(key)

                if current_price:
                    updated_leg = await self.update_leg_greeks(
                        strategy_id=strategy_id,
                        leg_id=leg.leg_id,
                        spot_price=spot_price,
                        current_price=current_price
                    )
                    updated_legs.append(updated_leg)

            logger.info(f"Updated Greeks for {len(updated_legs)} legs in strategy {strategy_id}")
            return updated_legs

        except Exception as e:
            logger.error(f"Error updating all legs Greeks: {e}")
            raise

    async def mark_leg_as_rolled(
        self,
        strategy_id: int,
        old_leg_id: str,
        new_leg_id: int
    ) -> AutoPilotPositionLeg:
        """
        Mark a leg as rolled (linked to new leg).

        Args:
            strategy_id: Strategy ID
            old_leg_id: Original leg identifier
            new_leg_id: New leg database ID

        Returns:
            Updated old leg
        """
        try:
            leg = await self.get_position_leg(strategy_id, old_leg_id)
            if not leg:
                raise ValueError(f"Position leg {old_leg_id} not found")

            leg.status = PositionLegStatus.ROLLED.value
            leg.rolled_to_leg_id = new_leg_id

            await self.db.commit()
            await self.db.refresh(leg)

            logger.info(f"Marked leg {old_leg_id} as rolled to {new_leg_id}")
            return leg

        except Exception as e:
            logger.error(f"Error marking leg as rolled: {e}")
            await self.db.rollback()
            raise

    async def _calculate_leg_greeks(
        self,
        spot_price: Decimal,
        strike: Decimal,
        expiry: date,
        option_type: str,
        price: Decimal
    ) -> Dict[str, Optional[Decimal]]:
        """Calculate Greeks for a leg."""
        try:
            # Calculate time to expiry
            tte = self.greeks_calc._calculate_time_to_expiry(str(expiry))

            if tte <= 0:
                return {}

            # Calculate IV from price
            iv = self.greeks_calc.calculate_iv_from_price(
                spot_price=float(spot_price),
                strike=float(strike),
                time_to_expiry=tte,
                option_price=float(price),
                option_type=option_type,
                risk_free_rate=0.07
            )

            # Calculate Greeks
            greeks = self.greeks_calc._calculate_greeks(
                spot_price=float(spot_price),
                strike=float(strike),
                time_to_expiry=tte,
                volatility=iv,
                risk_free_rate=0.07,
                option_type=option_type
            )

            return {
                'iv': Decimal(str(round(iv * 100, 2))),  # Convert to percentage
                'delta': Decimal(str(round(greeks['delta'], 4))),
                'gamma': Decimal(str(round(greeks['gamma'], 6))),
                'theta': Decimal(str(round(greeks['theta'], 2))),
                'vega': Decimal(str(round(greeks['vega'], 4))),
            }
        except Exception as e:
            logger.warning(f"Error calculating Greeks: {e}")
            return {}

    async def _calculate_unrealized_pnl(
        self,
        leg: AutoPilotPositionLeg,
        current_price: Decimal
    ) -> Decimal:
        """Calculate unrealized P&L for a leg."""
        if not leg.entry_price:
            return Decimal('0')

        # Get underlying for lot size
        strategy = await self.db.get(AutoPilotStrategy, leg.strategy_id)
        lot_size = get_lot_size(strategy.underlying)
        quantity = leg.lots * lot_size

        # Calculate P&L based on action
        if leg.action == "BUY":
            # Buy: profit when current > entry
            pnl = (current_price - leg.entry_price) * quantity
        else:  # SELL
            # Sell: profit when current < entry
            pnl = (leg.entry_price - current_price) * quantity

        return pnl

    async def _calculate_realized_pnl(
        self,
        leg: AutoPilotPositionLeg,
        exit_price: Decimal
    ) -> Decimal:
        """Calculate realized P&L for a closed leg."""
        if not leg.entry_price:
            return Decimal('0')

        # Get underlying for lot size
        strategy = await self.db.get(AutoPilotStrategy, leg.strategy_id)
        lot_size = get_lot_size(strategy.underlying)
        quantity = leg.lots * lot_size

        # Calculate P&L based on action
        if leg.action == "BUY":
            pnl = (exit_price - leg.entry_price) * quantity
        else:  # SELL
            pnl = (leg.entry_price - exit_price) * quantity

        return pnl
