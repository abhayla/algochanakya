"""
AI Strike Selector Service

Intelligently selects option strikes based on:
- Strategy type (Iron Condor, Spreads, Straddles, etc.)
- Current market regime and volatility
- User risk tolerance
- Delta-based or ATM-based selection

Uses broker abstraction layer for broker-agnostic operation.
"""

from typing import List, Dict, Optional, Tuple, TYPE_CHECKING, Union
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from kiteconnect import KiteConnect

from app.models.ai import AIUserConfig
from app.services.ai.market_regime import RegimeType
from app.services.brokers.base import BrokerAdapter
from app.constants.trading import get_strike_step

if TYPE_CHECKING:
    from app.schemas.ai import RegimeResponse


class StrikeSelection:
    """Strike selection result for a single leg."""

    def __init__(
        self,
        strike: float,
        option_type: str,  # "CE" or "PE"
        delta: Optional[float] = None,
        distance_from_spot: float = 0.0,
        reasoning: str = ""
    ):
        self.strike = strike
        self.option_type = option_type
        self.delta = delta
        self.distance_from_spot = distance_from_spot
        self.reasoning = reasoning

    def to_dict(self) -> Dict:
        return {
            "strike": self.strike,
            "option_type": self.option_type,
            "delta": self.delta,
            "distance_from_spot": self.distance_from_spot,
            "reasoning": self.reasoning
        }


class StrategyStrikes:
    """Complete strike selection for a multi-leg strategy."""

    def __init__(
        self,
        strategy_name: str,
        underlying: str,
        spot_price: float,
        legs: List[StrikeSelection]
    ):
        self.strategy_name = strategy_name
        self.underlying = underlying
        self.spot_price = spot_price
        self.legs = legs

    def to_dict(self) -> Dict:
        return {
            "strategy_name": self.strategy_name,
            "underlying": self.underlying,
            "spot_price": self.spot_price,
            "legs": [leg.to_dict() for leg in self.legs]
        }


# Strike selection rules for different strategies
# Maps strategy names to their leg configurations
STRATEGY_STRIKE_RULES = {
    "iron_condor": {
        "legs": 4,
        "structure": [
            {"type": "PE", "delta_target": -0.20, "description": "Far OTM Put (Sell)"},
            {"type": "PE", "delta_target": -0.10, "description": "Far OTM Put (Buy)"},
            {"type": "CE", "delta_target": 0.10, "description": "Far OTM Call (Buy)"},
            {"type": "CE", "delta_target": 0.20, "description": "Far OTM Call (Sell)"}
        ],
        "vix_adjustment": True  # Widen wings in high VIX
    },
    "short_strangle": {
        "legs": 2,
        "structure": [
            {"type": "PE", "delta_target": -0.30, "description": "OTM Put (Sell)"},
            {"type": "CE", "delta_target": 0.30, "description": "OTM Call (Sell)"}
        ],
        "vix_adjustment": True
    },
    "iron_butterfly": {
        "legs": 4,
        "structure": [
            {"type": "PE", "delta_target": -0.15, "description": "OTM Put (Buy)"},
            {"type": "PE", "delta_target": -0.50, "description": "ATM Put (Sell)"},
            {"type": "CE", "delta_target": 0.50, "description": "ATM Call (Sell)"},
            {"type": "CE", "delta_target": 0.15, "description": "OTM Call (Buy)"}
        ],
        "vix_adjustment": True
    },
    "bull_call_spread": {
        "legs": 2,
        "structure": [
            {"type": "CE", "delta_target": 0.60, "description": "ITM/ATM Call (Buy)"},
            {"type": "CE", "delta_target": 0.30, "description": "OTM Call (Sell)"}
        ],
        "vix_adjustment": False
    },
    "bear_put_spread": {
        "legs": 2,
        "structure": [
            {"type": "PE", "delta_target": -0.60, "description": "ITM/ATM Put (Buy)"},
            {"type": "PE", "delta_target": -0.30, "description": "OTM Put (Sell)"}
        ],
        "vix_adjustment": False
    },
    "long_straddle": {
        "legs": 2,
        "structure": [
            {"type": "PE", "delta_target": -0.50, "description": "ATM Put (Buy)"},
            {"type": "CE", "delta_target": 0.50, "description": "ATM Call (Buy)"}
        ],
        "vix_adjustment": False
    },
    "short_straddle": {
        "legs": 2,
        "structure": [
            {"type": "PE", "delta_target": -0.50, "description": "ATM Put (Sell)"},
            {"type": "CE", "delta_target": 0.50, "description": "ATM Call (Sell)"}
        ],
        "vix_adjustment": False
    }
}


class StrikeSelector:
    """
    Intelligent strike selection for option strategies.

    Selects strikes based on delta targets, VIX adjustments, and regime conditions.
    """

    def __init__(self, broker_adapter: Union[BrokerAdapter, KiteConnect]):
        """
        Initialize Strike Selector.

        Args:
            broker_adapter: BrokerAdapter instance (preferred) or KiteConnect (legacy)
        """
        # Support both BrokerAdapter and legacy KiteConnect
        if isinstance(broker_adapter, BrokerAdapter):
            self.broker_adapter = broker_adapter
            self.kite = broker_adapter.get_kite_client()
        else:
            # Legacy KiteConnect passed directly
            self.kite = broker_adapter
            self.broker_adapter = None

    async def select_strikes(
        self,
        strategy_name: str,
        underlying: str,
        spot_price: float,
        regime: "RegimeResponse",
        user_config: AIUserConfig,
        db: AsyncSession
    ) -> Optional[StrategyStrikes]:
        """
        Select strikes for a complete strategy.

        Args:
            strategy_name: Name of the strategy (e.g., "iron_condor")
            underlying: Index name (NIFTY, BANKNIFTY, etc.)
            spot_price: Current spot price
            regime: Current market regime
            user_config: User's AI configuration
            db: Database session

        Returns:
            StrategyStrikes object with all legs, or None if strategy unknown
        """
        if strategy_name not in STRATEGY_STRIKE_RULES:
            return None

        rules = STRATEGY_STRIKE_RULES[strategy_name]
        strike_step = get_strike_step(underlying)

        # Round spot price to nearest strike
        atm_strike = self._round_to_strike(spot_price, strike_step)

        # VIX adjustment multiplier (widen strikes in high VIX)
        vix_multiplier = 1.0
        if rules.get("vix_adjustment") and regime.indicators.vix:
            if regime.indicators.vix > 20:
                vix_multiplier = 1.5  # Widen by 50%
            elif regime.indicators.vix > 15:
                vix_multiplier = 1.25  # Widen by 25%

        # Select strikes for each leg
        legs: List[StrikeSelection] = []

        for leg_config in rules["structure"]:
            strike = self._select_strike_by_delta(
                atm_strike=atm_strike,
                delta_target=leg_config["delta_target"],
                option_type=leg_config["type"],
                strike_step=strike_step,
                vix_multiplier=vix_multiplier
            )

            distance = abs(strike - spot_price)
            distance_pct = (distance / spot_price) * 100

            leg = StrikeSelection(
                strike=strike,
                option_type=leg_config["type"],
                delta=leg_config["delta_target"],
                distance_from_spot=distance,
                reasoning=f"{leg_config['description']} | {distance_pct:.1f}% from spot"
            )
            legs.append(leg)

        return StrategyStrikes(
            strategy_name=strategy_name,
            underlying=underlying,
            spot_price=spot_price,
            legs=legs
        )

    def _round_to_strike(self, price: float, strike_step: int) -> float:
        """Round price to nearest strike interval."""
        return round(price / strike_step) * strike_step

    def _select_strike_by_delta(
        self,
        atm_strike: float,
        delta_target: float,
        option_type: str,
        strike_step: int,
        vix_multiplier: float = 1.0
    ) -> float:
        """
        Select strike based on delta approximation.

        Delta approximation (simplified Black-Scholes):
        - Delta ≈ 0.50: ATM
        - Delta ≈ 0.70: ~0.5 SD ITM
        - Delta ≈ 0.30: ~0.5 SD OTM
        - Delta ≈ 0.10-0.20: ~1-1.5 SD OTM

        Args:
            atm_strike: ATM strike price
            delta_target: Target delta (-1 to 1)
            option_type: "CE" or "PE"
            strike_step: Strike step interval
            vix_multiplier: VIX-based adjustment multiplier

        Returns:
            Selected strike price
        """
        abs_delta = abs(delta_target)

        # Approximate distance from ATM based on delta
        if abs_delta >= 0.60:
            # ITM: ~0.5-1 SD
            otm_distance_pct = -2.0  # Negative for ITM
        elif abs_delta >= 0.45:
            # ATM: Within 0.25 SD
            otm_distance_pct = 0.0
        elif abs_delta >= 0.30:
            # OTM: ~0.5 SD
            otm_distance_pct = 2.0
        elif abs_delta >= 0.20:
            # Far OTM: ~1 SD
            otm_distance_pct = 4.0
        else:
            # Very far OTM: ~1.5 SD
            otm_distance_pct = 6.0

        # Apply VIX adjustment
        otm_distance_pct *= vix_multiplier

        # Convert percentage to actual strike distance
        otm_distance = atm_strike * (otm_distance_pct / 100)

        # Calculate target strike
        if option_type == "CE":
            # Call: Positive delta means higher strike for OTM
            target_strike = atm_strike + otm_distance
        else:
            # Put: Negative delta means lower strike for OTM
            target_strike = atm_strike - otm_distance

        # Round to nearest strike step
        return self._round_to_strike(target_strike, strike_step)


__all__ = [
    "StrikeSelector",
    "StrikeSelection",
    "StrategyStrikes",
    "STRATEGY_STRIKE_RULES"
]
