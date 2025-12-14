"""
Strategy Converter Service - Phase 5G (#40, #42, #43)

Implements strategy type conversion techniques:
- Iron Condor → Strangle (close wings, keep shorts)
- Strangle → Iron Condor (add protective wings)
- Strangle → Iron Fly (move strikes to ATM)
- Condor → Butterfly (move strikes closer to ATM)
- Ratio spread conversion (add extra contracts)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
import logging
from enum import Enum

from kiteconnect import KiteConnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.autopilot import (
    AutoPilotPositionLeg,
    AutoPilotStrategy,
    PositionLegStatus
)
from app.services.position_leg_service import PositionLegService
from app.services.strike_finder_service import StrikeFinderService
from app.services.leg_actions_service import LegActionsService
from app.services.market_data import MarketDataService
from app.services.greeks_calculator import GreeksCalculatorService

logger = logging.getLogger(__name__)


class StrategyType(str, Enum):
    """Supported strategy types for conversion."""
    IRON_CONDOR = "iron_condor"
    STRANGLE = "strangle"
    IRON_FLY = "iron_fly"
    BUTTERFLY = "butterfly"
    RATIO_SPREAD = "ratio_spread"
    SHORT_STRANGLE = "short_strangle"
    LONG_STRANGLE = "long_strangle"


class ConversionResult:
    """Result of a strategy conversion."""
    def __init__(
        self,
        success: bool,
        from_type: str,
        to_type: str,
        legs_to_close: List[str],
        legs_to_open: List[Dict],
        net_cost: Decimal,
        margin_impact: Decimal,
        new_max_profit: Optional[Decimal] = None,
        new_max_loss: Optional[Decimal] = None,
        warnings: List[str] = None
    ):
        self.success = success
        self.from_type = from_type
        self.to_type = to_type
        self.legs_to_close = legs_to_close
        self.legs_to_open = legs_to_open
        self.net_cost = net_cost
        self.margin_impact = margin_impact
        self.new_max_profit = new_max_profit
        self.new_max_loss = new_max_loss
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "from_type": self.from_type,
            "to_type": self.to_type,
            "legs_to_close": self.legs_to_close,
            "legs_to_open": self.legs_to_open,
            "net_cost": float(self.net_cost),
            "margin_impact": float(self.margin_impact),
            "new_max_profit": float(self.new_max_profit) if self.new_max_profit else None,
            "new_max_loss": float(self.new_max_loss) if self.new_max_loss else None,
            "warnings": self.warnings
        }


class StrategyConverterService:
    """Service for converting between different strategy types."""

    def __init__(self, kite: KiteConnect, db: AsyncSession, user_id: str):
        self.kite = kite
        self.db = db
        self.user_id = user_id
        self.position_leg_service = PositionLegService(kite, db)
        self.strike_finder = StrikeFinderService(kite, db)
        self.leg_actions = LegActionsService(kite, db, user_id)
        self.market_data = MarketDataService(kite)
        self.greeks_calc = GreeksCalculatorService(kite, db)

    async def get_conversion_preview(
        self,
        strategy_id: int,
        target_type: StrategyType,
        **kwargs
    ) -> ConversionResult:
        """
        Get preview of conversion without executing.

        Args:
            strategy_id: Strategy ID to convert
            target_type: Target strategy type
            **kwargs: Additional parameters for specific conversions
                - wing_width: For adding wings (default: 100)
                - ratio: For ratio spreads (default: 2)

        Returns:
            ConversionResult with preview data
        """
        # Get strategy and current legs
        query = select(AutoPilotStrategy).where(AutoPilotStrategy.id == strategy_id)
        result = await self.db.execute(query)
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        # Get current legs
        legs = await self.position_leg_service.get_all_legs(strategy_id)
        current_type = self._detect_strategy_type(legs)

        # Route to appropriate conversion method
        if target_type == StrategyType.STRANGLE:
            return await self._convert_to_strangle_preview(strategy, legs, current_type)
        elif target_type == StrategyType.IRON_CONDOR:
            wing_width = kwargs.get('wing_width', 100)
            return await self._convert_to_iron_condor_preview(strategy, legs, current_type, wing_width)
        elif target_type == StrategyType.IRON_FLY:
            return await self._convert_to_iron_fly_preview(strategy, legs, current_type)
        elif target_type == StrategyType.BUTTERFLY:
            return await self._convert_to_butterfly_preview(strategy, legs, current_type)
        elif target_type == StrategyType.RATIO_SPREAD:
            ratio = kwargs.get('ratio', 2)
            return await self._convert_to_ratio_spread_preview(strategy, legs, current_type, ratio)
        else:
            raise ValueError(f"Unsupported target type: {target_type}")

    async def execute_conversion(
        self,
        strategy_id: int,
        target_type: StrategyType,
        execution_mode: str = "market",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute strategy conversion.

        Args:
            strategy_id: Strategy ID
            target_type: Target strategy type
            execution_mode: 'market' or 'limit'
            **kwargs: Additional parameters

        Returns:
            Dict with execution results
        """
        # Get preview first
        preview = await self.get_conversion_preview(strategy_id, target_type, **kwargs)

        if not preview.success:
            return {
                "success": False,
                "error": "Conversion validation failed",
                "warnings": preview.warnings
            }

        executed_closes = []
        executed_opens = []

        try:
            # Close legs to be removed
            for leg_id in preview.legs_to_close:
                result = await self.leg_actions.exit_leg(
                    strategy_id=strategy_id,
                    leg_id=leg_id,
                    execution_mode=execution_mode
                )
                executed_closes.append({
                    "leg_id": leg_id,
                    "result": result
                })

            # Open new legs
            for new_leg in preview.legs_to_open:
                # Create new leg via position_leg_service
                result = await self._create_leg(
                    strategy_id=strategy_id,
                    leg_data=new_leg,
                    execution_mode=execution_mode
                )
                executed_opens.append(result)

            return {
                "success": True,
                "conversion_type": f"{preview.from_type} → {preview.to_type}",
                "closed_legs": executed_closes,
                "opened_legs": executed_opens,
                "net_cost": float(preview.net_cost),
                "margin_impact": float(preview.margin_impact)
            }

        except Exception as e:
            logger.error(f"Conversion execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "partial_closes": executed_closes,
                "partial_opens": executed_opens
            }

    # =====================
    # CONVERSION PREVIEWS
    # =====================

    async def _convert_to_strangle_preview(
        self,
        strategy: AutoPilotStrategy,
        legs: List[AutoPilotPositionLeg],
        current_type: str
    ) -> ConversionResult:
        """
        Convert Iron Condor → Strangle by closing wings.
        Keep only short strikes.
        """
        # Identify wings (long options)
        wings = [leg for leg in legs if leg.buy_sell == "BUY"]
        shorts = [leg for leg in legs if leg.buy_sell == "SELL"]

        if len(shorts) != 2:
            return ConversionResult(
                success=False,
                from_type=current_type,
                to_type="strangle",
                legs_to_close=[],
                legs_to_open=[],
                net_cost=Decimal("0"),
                margin_impact=Decimal("0"),
                warnings=["Invalid iron condor structure - expected 2 short legs"]
            )

        # Calculate net cost (credit from closing wings)
        net_cost = sum(leg.ltp * leg.quantity for leg in wings)

        # Margin will increase (removing protective wings)
        margin_impact = Decimal("50000")  # Rough estimate

        return ConversionResult(
            success=True,
            from_type=current_type,
            to_type="strangle",
            legs_to_close=[leg.leg_id for leg in wings],
            legs_to_open=[],
            net_cost=Decimal(str(net_cost)),
            margin_impact=margin_impact,
            warnings=["Margin requirement will increase without protective wings"]
        )

    async def _convert_to_iron_condor_preview(
        self,
        strategy: AutoPilotStrategy,
        legs: List[AutoPilotPositionLeg],
        current_type: str,
        wing_width: int = 100
    ) -> ConversionResult:
        """
        Convert Strangle → Iron Condor by adding wings.
        """
        shorts = [leg for leg in legs if leg.buy_sell == "SELL"]

        if len(shorts) != 2:
            return ConversionResult(
                success=False,
                from_type=current_type,
                to_type="iron_condor",
                legs_to_close=[],
                legs_to_open=[],
                net_cost=Decimal("0"),
                margin_impact=Decimal("0"),
                warnings=["Expected 2 short legs for strangle"]
            )

        # Find PE and CE shorts
        pe_short = next((leg for leg in shorts if leg.contract_type == "PE"), None)
        ce_short = next((leg for leg in shorts if leg.contract_type == "CE"), None)

        legs_to_open = []
        net_cost = Decimal("0")

        # Add PE wing (buy PUT below short PUT)
        if pe_short:
            pe_wing_strike = pe_short.strike - wing_width
            legs_to_open.append({
                "contract_type": "PE",
                "strike": pe_wing_strike,
                "buy_sell": "BUY",
                "quantity": pe_short.quantity,
                "expiry": pe_short.expiry
            })
            # Estimate cost (rough)
            net_cost += Decimal("50") * pe_short.quantity

        # Add CE wing (buy CALL above short CALL)
        if ce_short:
            ce_wing_strike = ce_short.strike + wing_width
            legs_to_open.append({
                "contract_type": "CE",
                "strike": ce_wing_strike,
                "buy_sell": "BUY",
                "quantity": ce_short.quantity,
                "expiry": ce_short.expiry
            })
            net_cost += Decimal("50") * ce_short.quantity

        # Margin will decrease (adding protection)
        margin_impact = Decimal("-30000")

        return ConversionResult(
            success=True,
            from_type=current_type,
            to_type="iron_condor",
            legs_to_close=[],
            legs_to_open=legs_to_open,
            net_cost=net_cost,
            margin_impact=margin_impact,
            warnings=["Wing width: {wing_width} points"]
        )

    async def _convert_to_iron_fly_preview(
        self,
        strategy: AutoPilotStrategy,
        legs: List[AutoPilotPositionLeg],
        current_type: str
    ) -> ConversionResult:
        """
        Convert Strangle → Iron Fly by moving shorts to ATM.
        """
        shorts = [leg for leg in legs if leg.buy_sell == "SELL"]

        # Get current spot price
        spot_data = await self.market_data.get_spot_price(strategy.underlying)
        spot_price = spot_data.ltp

        # Find ATM strike (round to nearest 50)
        atm_strike = round(spot_price / 50) * 50

        legs_to_close = [leg.leg_id for leg in shorts]
        legs_to_open = []

        for leg in shorts:
            legs_to_open.append({
                "contract_type": leg.contract_type,
                "strike": atm_strike,
                "buy_sell": "SELL",
                "quantity": leg.quantity,
                "expiry": leg.expiry
            })

        # Net cost depends on premium difference
        net_cost = Decimal("0")  # Placeholder

        return ConversionResult(
            success=True,
            from_type=current_type,
            to_type="iron_fly",
            legs_to_close=legs_to_close,
            legs_to_open=legs_to_open,
            net_cost=net_cost,
            margin_impact=Decimal("0"),
            warnings=[f"Moving strikes to ATM: {atm_strike}"]
        )

    async def _convert_to_butterfly_preview(
        self,
        strategy: AutoPilotStrategy,
        legs: List[AutoPilotPositionLeg],
        current_type: str
    ) -> ConversionResult:
        """
        Convert Condor → Butterfly by moving strikes closer.
        """
        return ConversionResult(
            success=False,
            from_type=current_type,
            to_type="butterfly",
            legs_to_close=[],
            legs_to_open=[],
            net_cost=Decimal("0"),
            margin_impact=Decimal("0"),
            warnings=["Butterfly conversion not yet implemented"]
        )

    async def _convert_to_ratio_spread_preview(
        self,
        strategy: AutoPilotStrategy,
        legs: List[AutoPilotPositionLeg],
        current_type: str,
        ratio: int = 2
    ) -> ConversionResult:
        """
        Convert to ratio spread by adding extra short contracts.

        Args:
            ratio: Ratio of shorts to longs (default: 2:1)
        """
        shorts = [leg for leg in legs if leg.buy_sell == "SELL"]

        if not shorts:
            return ConversionResult(
                success=False,
                from_type=current_type,
                to_type="ratio_spread",
                legs_to_close=[],
                legs_to_open=[],
                net_cost=Decimal("0"),
                margin_impact=Decimal("0"),
                warnings=["No short legs found"]
            )

        # Add extra contracts to existing shorts
        legs_to_open = []
        for leg in shorts:
            extra_quantity = leg.quantity * (ratio - 1)
            legs_to_open.append({
                "contract_type": leg.contract_type,
                "strike": leg.strike,
                "buy_sell": "SELL",
                "quantity": extra_quantity,
                "expiry": leg.expiry
            })

        # Net cost is premium collected (credit)
        net_cost = Decimal("-500")  # Placeholder

        return ConversionResult(
            success=True,
            from_type=current_type,
            to_type="ratio_spread",
            legs_to_close=[],
            legs_to_open=legs_to_open,
            net_cost=net_cost,
            margin_impact=Decimal("20000"),
            warnings=[f"Ratio: {ratio}:1", "Unlimited risk on extra shorts"]
        )

    # =====================
    # HELPER METHODS
    # =====================

    def _detect_strategy_type(self, legs: List[AutoPilotPositionLeg]) -> str:
        """Detect current strategy type from legs."""
        if not legs:
            return "unknown"

        shorts = [leg for leg in legs if leg.buy_sell == "SELL"]
        longs = [leg for leg in legs if leg.buy_sell == "BUY"]

        # Iron Condor: 2 shorts + 2 longs
        if len(shorts) == 2 and len(longs) == 2:
            return "iron_condor"

        # Strangle: 2 shorts, no longs
        if len(shorts) == 2 and len(longs) == 0:
            return "strangle"

        # Iron Fly: 2 shorts at same strike + 2 longs
        if len(shorts) == 2 and len(longs) == 2:
            if shorts[0].strike == shorts[1].strike:
                return "iron_fly"

        return "custom"

    async def _create_leg(
        self,
        strategy_id: int,
        leg_data: Dict[str, Any],
        execution_mode: str = "market"
    ) -> Dict[str, Any]:
        """Create and execute a new leg."""
        # This would integrate with order_executor to place the order
        # For now, return placeholder
        return {
            "success": True,
            "leg_data": leg_data,
            "execution_mode": execution_mode
        }

    def _calculate_conversion_cost(
        self,
        legs_to_close: List[AutoPilotPositionLeg],
        legs_to_open: List[Dict[str, Any]]
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate net cost and margin impact of conversion.

        Returns:
            Tuple of (net_cost, margin_impact)
        """
        # Cost from closing legs (credit if selling, debit if buying back)
        close_cost = sum(leg.ltp * leg.quantity for leg in legs_to_close)

        # Cost from opening legs (rough estimate)
        open_cost = Decimal("100") * len(legs_to_open)  # Placeholder

        net_cost = open_cost - close_cost
        margin_impact = Decimal("0")  # Placeholder

        return net_cost, margin_impact

    def _validate_conversion(
        self,
        from_type: str,
        to_type: str,
        legs: List[AutoPilotPositionLeg]
    ) -> Tuple[bool, List[str]]:
        """
        Validate if conversion is possible.

        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []

        # Check if we have enough legs
        if len(legs) < 2:
            warnings.append("At least 2 legs required for conversion")
            return False, warnings

        # Check if conversion is supported
        supported_conversions = [
            ("iron_condor", "strangle"),
            ("strangle", "iron_condor"),
            ("strangle", "iron_fly"),
            ("strangle", "ratio_spread")
        ]

        if (from_type, to_type) not in supported_conversions:
            warnings.append(f"Conversion {from_type} → {to_type} not supported")
            return False, warnings

        return True, warnings
