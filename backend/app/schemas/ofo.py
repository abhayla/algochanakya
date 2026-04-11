"""
OFO (Options For Options) Schemas

Request/response schemas for the OFO feature that finds and ranks
the best strategy combinations from option chain data.
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OFOCalculateRequest(BaseModel):
    """Request schema for OFO calculation."""

    underlying: str = Field(..., description="Underlying index: NIFTY, BANKNIFTY, FINNIFTY")
    expiry: str = Field(..., description="Expiry date in YYYY-MM-DD format")
    strategy_types: List[str] = Field(
        ...,
        description="List of strategy types to calculate: iron_condor, short_straddle, etc."
    )
    strike_range: int = Field(
        default=10,
        ge=5,
        le=20,
        description="Number of strikes to consider on each side of ATM (±5, ±10, ±15, ±20)"
    )
    lots: int = Field(
        default=1,
        ge=1,
        le=50,
        description="Number of lots per leg"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "underlying": "NIFTY",
                "expiry": "2025-01-09",
                "strategy_types": ["iron_condor", "short_strangle", "bull_call_spread"],
                "strike_range": 10,
                "lots": 1
            }
        }


class OFOLegResult(BaseModel):
    """Individual leg details in OFO result."""

    expiry: str = Field(..., description="Expiry date")
    contract_type: str = Field(..., description="CE or PE")
    transaction_type: str = Field(..., description="BUY or SELL")
    strike: float = Field(..., description="Strike price")
    cmp: float = Field(..., description="Current market price (LTP)")
    lots: int = Field(..., description="Number of lots")
    qty: int = Field(..., description="Total quantity (lots × lot_size)")
    instrument_token: int = Field(..., description="Kite instrument token for order placement")
    tradingsymbol: str = Field(..., description="Trading symbol for order placement")

    class Config:
        json_schema_extra = {
            "example": {
                "expiry": "2025-01-09",
                "contract_type": "CE",
                "transaction_type": "SELL",
                "strike": 24200.0,
                "cmp": 150.50,
                "lots": 1,
                "qty": 25,
                "instrument_token": 12345678,
                "tradingsymbol": "NIFTY2510924200CE"
            }
        }


class OFOStrategyResult(BaseModel):
    """Single strategy combination result."""

    strategy_type: str = Field(..., description="Strategy type key (e.g., iron_condor)")
    strategy_name: str = Field(..., description="Display name (e.g., Iron Condor)")
    max_profit: float = Field(..., description="Maximum profit at expiry")
    max_loss: float = Field(..., description="Maximum loss at expiry")
    breakevens: List[float] = Field(default_factory=list, description="Breakeven points")
    net_premium: float = Field(..., description="Net premium received/paid (positive = credit)")
    risk_reward_ratio: float = Field(..., description="Max profit / Max loss ratio")
    legs: List[OFOLegResult] = Field(..., description="List of option legs")

    class Config:
        json_schema_extra = {
            "example": {
                "strategy_type": "iron_condor",
                "strategy_name": "Iron Condor",
                "max_profit": 4500.0,
                "max_loss": -8000.0,
                "breakevens": [23850.0, 24350.0],
                "net_premium": 180.0,
                "risk_reward_ratio": 0.56,
                "legs": []
            }
        }


class OFOCalculateResponse(BaseModel):
    """Response schema for OFO calculation."""

    underlying: str = Field(..., description="Underlying index")
    expiry: str = Field(..., description="Expiry date")
    spot_price: float = Field(..., description="Current spot price of underlying")
    atm_strike: float = Field(..., description="ATM strike price")
    lot_size: int = Field(..., description="Lot size for this underlying")
    calculated_at: datetime = Field(..., description="Timestamp of calculation")
    calculation_time_ms: int = Field(..., description="Time taken to calculate in milliseconds")
    total_combinations_evaluated: int = Field(
        default=0,
        description="Total number of combinations evaluated across all strategies"
    )
    results: Dict[str, List[OFOStrategyResult]] = Field(
        ...,
        description="Results grouped by strategy type, each containing top 3 combinations"
    )
    data_freshness: str = Field(
        default="LIVE",
        description="'LIVE' when market is open, 'LAST_KNOWN' when showing previous session's close prices"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "underlying": "NIFTY",
                "expiry": "2025-01-09",
                "spot_price": 24100.50,
                "atm_strike": 24100.0,
                "lot_size": 25,
                "calculated_at": "2025-01-02T10:30:00",
                "calculation_time_ms": 1250,
                "total_combinations_evaluated": 15420,
                "results": {
                    "iron_condor": [],
                    "short_strangle": [],
                    "bull_call_spread": []
                }
            }
        }


# Available strategies for OFO (9 popular strategies)
OFO_AVAILABLE_STRATEGIES = [
    {
        "key": "iron_condor",
        "name": "Iron Condor",
        "category": "neutral",
        "legs_count": 4,
        "description": "Bull put spread + Bear call spread for range-bound trading"
    },
    {
        "key": "iron_butterfly",
        "name": "Iron Butterfly",
        "category": "neutral",
        "legs_count": 4,
        "description": "ATM short straddle with protective wings"
    },
    {
        "key": "short_straddle",
        "name": "Short Straddle",
        "category": "neutral",
        "legs_count": 2,
        "description": "Sell ATM CE + PE at same strike"
    },
    {
        "key": "short_strangle",
        "name": "Short Strangle",
        "category": "neutral",
        "legs_count": 2,
        "description": "Sell OTM CE + PE at different strikes"
    },
    {
        "key": "long_straddle",
        "name": "Long Straddle",
        "category": "volatile",
        "legs_count": 2,
        "description": "Buy ATM CE + PE at same strike"
    },
    {
        "key": "long_strangle",
        "name": "Long Strangle",
        "category": "volatile",
        "legs_count": 2,
        "description": "Buy OTM CE + PE at different strikes"
    },
    {
        "key": "bull_call_spread",
        "name": "Bull Call Spread",
        "category": "bullish",
        "legs_count": 2,
        "description": "Buy lower CE, sell higher CE"
    },
    {
        "key": "bear_put_spread",
        "name": "Bear Put Spread",
        "category": "bearish",
        "legs_count": 2,
        "description": "Buy higher PE, sell lower PE"
    },
    {
        "key": "butterfly_spread",
        "name": "Butterfly Spread",
        "category": "neutral",
        "legs_count": 4,
        "description": "Buy low + high strikes, sell 2x middle strike"
    }
]
