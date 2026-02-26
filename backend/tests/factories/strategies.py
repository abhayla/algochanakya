"""
Factory functions for AutoPilot strategy and leg test objects.

Replaces the dozens of duplicated `sample_strategy` and `sample_leg`
fixtures scattered across autopilot test files.

Usage:
    from tests.factories.strategies import make_strategy, make_leg, make_condition

    strategy = make_strategy(underlying="BANKNIFTY")
    legs = [make_leg("CE", "SELL"), make_leg("PE", "SELL")]
    strategy = make_strategy(legs_config=legs)
"""

from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4


# ─────────────────────────────────────────────────────────────────────────────
# Leg config factory
# ─────────────────────────────────────────────────────────────────────────────

def make_leg(
    contract_type: str = "CE",
    transaction_type: str = "SELL",
    leg_id: str = None,
    strike_offset: int = 0,
    lots: int = 1,
    **overrides,
) -> dict:
    """
    Create a leg config dict.

    Args:
        contract_type: "CE" or "PE"
        transaction_type: "BUY" or "SELL"
        leg_id: Unique leg ID (auto-generated if None)
        strike_offset: Strike offset from ATM in points (e.g. 200 = OTM+200)
        lots: Number of lots
    """
    leg = {
        "id": leg_id or f"leg_{uuid4().hex[:8]}",
        "contract_type": contract_type,
        "transaction_type": transaction_type,
        "strike_offset": strike_offset,
        "lots": lots,
        "product_type": "NRML",
        "order_type": "MARKET",
        "tag": f"test_{contract_type}_{transaction_type}",
    }
    leg.update(overrides)
    return leg


# ─────────────────────────────────────────────────────────────────────────────
# Strategy factory
# ─────────────────────────────────────────────────────────────────────────────

def make_strategy(
    underlying: str = "NIFTY",
    legs_config: list = None,
    position_type: str = "intraday",
    expiry: date = None,
    strategy_id: str = None,
    **overrides,
):
    """
    Create a mock AutoPilotStrategy object.

    Returns a MagicMock with all expected attributes set.
    Pass overrides as keyword args to change specific attributes.

    Usage:
        strategy = make_strategy(underlying="BANKNIFTY")
        strategy = make_strategy(legs_config=[make_leg("CE"), make_leg("PE")])
    """
    from app.models.autopilot import AutoPilotStrategy  # noqa: F401 — for spec

    strategy = MagicMock()
    strategy.id = strategy_id or uuid4()
    strategy.underlying = underlying
    strategy.position_type = position_type
    strategy.expiry = expiry or (date.today() + timedelta(days=7))
    strategy.legs_config = legs_config or [
        make_leg("CE", "SELL", strike_offset=200),
        make_leg("PE", "SELL", strike_offset=-200),
    ]
    strategy.status = "active"
    strategy.max_loss = Decimal("5000.00")
    strategy.max_profit = Decimal("2000.00")
    strategy.target_profit_pct = Decimal("25.0")
    strategy.stop_loss_pct = Decimal("50.0")
    strategy.entry_time = None
    strategy.exit_time = None

    for key, value in overrides.items():
        setattr(strategy, key, value)

    return strategy


# ─────────────────────────────────────────────────────────────────────────────
# Condition factory
# ─────────────────────────────────────────────────────────────────────────────

def make_condition(
    condition_type: str = "pnl_percent",
    operator: str = "lte",
    value: float = -50.0,
    **overrides,
) -> dict:
    """Create a strategy condition dict."""
    condition = {
        "type": condition_type,
        "operator": operator,
        "value": value,
    }
    condition.update(overrides)
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# Pre-built strategy presets (common strategy shapes used across tests)
# ─────────────────────────────────────────────────────────────────────────────

def make_short_strangle(underlying: str = "NIFTY", **overrides):
    """Short strangle: sell OTM CE + OTM PE."""
    return make_strategy(
        underlying=underlying,
        legs_config=[
            make_leg("CE", "SELL", strike_offset=200),
            make_leg("PE", "SELL", strike_offset=-200),
        ],
        **overrides,
    )


def make_iron_condor(underlying: str = "NIFTY", **overrides):
    """Iron condor: buy far OTM, sell near OTM on both sides."""
    return make_strategy(
        underlying=underlying,
        legs_config=[
            make_leg("PE", "BUY",  strike_offset=-400),
            make_leg("PE", "SELL", strike_offset=-200),
            make_leg("CE", "SELL", strike_offset=200),
            make_leg("CE", "BUY",  strike_offset=400),
        ],
        **overrides,
    )


def make_bull_call_spread(underlying: str = "NIFTY", **overrides):
    """Bull call spread: buy ATM CE, sell OTM CE."""
    return make_strategy(
        underlying=underlying,
        legs_config=[
            make_leg("CE", "BUY",  strike_offset=0),
            make_leg("CE", "SELL", strike_offset=200),
        ],
        **overrides,
    )
