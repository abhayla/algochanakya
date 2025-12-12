"""
Centralized Strategy Types Configuration

This is the SINGLE SOURCE OF TRUTH for all option strategy types used across the application.
Used by:
- Backend API endpoints
- Frontend Strategy Builders (regular + AutoPilot)
- Strategy Library
- Seed scripts

Do NOT hardcode strategy types elsewhere - import from this module.
"""

from typing import Dict, List, Any, Optional


# ============================================================================
# CATEGORIES - Strategy category definitions with display properties
# ============================================================================

CATEGORIES: Dict[str, Dict[str, str]] = {
    "bullish": {
        "name": "Bullish",
        "color": "#00b386",
        "icon": "trending-up",
        "description": "Strategies that profit when the underlying price rises"
    },
    "bearish": {
        "name": "Bearish",
        "color": "#e74c3c",
        "icon": "trending-down",
        "description": "Strategies that profit when the underlying price falls"
    },
    "neutral": {
        "name": "Neutral",
        "color": "#6c757d",
        "icon": "minus",
        "description": "Strategies that profit when the underlying stays in a range"
    },
    "volatile": {
        "name": "Volatile",
        "color": "#9b59b6",
        "icon": "activity",
        "description": "Strategies that profit from large price movements in either direction"
    },
    "income": {
        "name": "Income",
        "color": "#f39c12",
        "icon": "dollar-sign",
        "description": "Strategies focused on generating consistent premium income"
    },
    "advanced": {
        "name": "Advanced",
        "color": "#3498db",
        "icon": "target",
        "description": "Complex strategies requiring experience to manage"
    }
}


# ============================================================================
# STRATEGY TYPES - All strategy configurations with leg definitions
# ============================================================================

STRATEGY_TYPES: Dict[str, Dict[str, Any]] = {
    # ==================== BULLISH STRATEGIES ====================
    "bull_call_spread": {
        "display_name": "Bull Call Spread",
        "category": "bullish",
        "description": "Buy a call option at a lower strike and sell a call at a higher strike",
        "legs": [
            {"type": "CE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 100, "expiry_offset": 0}
        ],
        "risk_level": "low",
        "difficulty": "beginner",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "bull_put_spread": {
        "display_name": "Bull Put Spread",
        "category": "bullish",
        "description": "Sell a put at a higher strike and buy a put at a lower strike",
        "legs": [
            {"type": "PE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "action": "BUY", "strike_offset": -100, "expiry_offset": 0}
        ],
        "risk_level": "low",
        "difficulty": "beginner",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "synthetic_long": {
        "display_name": "Synthetic Long",
        "category": "bullish",
        "description": "Buy a call and sell a put at the same strike to mimic stock ownership",
        "legs": [
            {"type": "CE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0}
        ],
        "risk_level": "high",
        "difficulty": "advanced",
        "max_profit": "Unlimited",
        "max_loss": "Unlimited"
    },

    # ==================== BEARISH STRATEGIES ====================
    "bear_put_spread": {
        "display_name": "Bear Put Spread",
        "category": "bearish",
        "description": "Buy a put at a higher strike and sell a put at a lower strike",
        "legs": [
            {"type": "PE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "action": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "risk_level": "low",
        "difficulty": "beginner",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "bear_call_spread": {
        "display_name": "Bear Call Spread",
        "category": "bearish",
        "description": "Sell a call at a lower strike and buy a call at a higher strike",
        "legs": [
            {"type": "CE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 100, "expiry_offset": 0}
        ],
        "risk_level": "low",
        "difficulty": "beginner",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "synthetic_short": {
        "display_name": "Synthetic Short",
        "category": "bearish",
        "description": "Buy a put and sell a call at the same strike to mimic shorting stock",
        "legs": [
            {"type": "PE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0}
        ],
        "risk_level": "high",
        "difficulty": "advanced",
        "max_profit": "Unlimited",
        "max_loss": "Unlimited"
    },

    # ==================== NEUTRAL STRATEGIES ====================
    "iron_condor": {
        "display_name": "Iron Condor",
        "category": "neutral",
        "description": "Combination of bull put spread and bear call spread for range-bound trading",
        "legs": [
            {"type": "PE", "action": "BUY", "strike_offset": -200, "expiry_offset": 0},
            {"type": "PE", "action": "SELL", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 200, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "intermediate",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "iron_butterfly": {
        "display_name": "Iron Butterfly",
        "category": "neutral",
        "description": "Sell an ATM straddle and buy protective wings for maximum premium at center strike",
        "legs": [
            {"type": "PE", "action": "BUY", "strike_offset": -100, "expiry_offset": 0},
            {"type": "PE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 100, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "intermediate",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "short_straddle": {
        "display_name": "Short Straddle",
        "category": "neutral",
        "description": "Sell ATM call and put at the same strike for maximum premium collection",
        "legs": [
            {"type": "CE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0}
        ],
        "risk_level": "high",
        "difficulty": "advanced",
        "max_profit": "Limited",
        "max_loss": "Unlimited"
    },
    "short_strangle": {
        "display_name": "Short Strangle",
        "category": "neutral",
        "description": "Sell OTM call and put at different strikes for wider profit zone",
        "legs": [
            {"type": "CE", "action": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "PE", "action": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "risk_level": "high",
        "difficulty": "advanced",
        "max_profit": "Limited",
        "max_loss": "Unlimited"
    },
    "jade_lizard": {
        "display_name": "Jade Lizard",
        "category": "neutral",
        "description": "Short put with a short call spread - no upside risk if structured correctly",
        "legs": [
            {"type": "PE", "action": "SELL", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 200, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "intermediate",
        "max_profit": "Limited",
        "max_loss": "Limited upside, Unlimited downside"
    },

    # ==================== VOLATILE STRATEGIES ====================
    "long_straddle": {
        "display_name": "Long Straddle",
        "category": "volatile",
        "description": "Buy ATM call and put at the same strike to profit from large moves",
        "legs": [
            {"type": "CE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "beginner",
        "max_profit": "Unlimited",
        "max_loss": "Limited"
    },
    "long_strangle": {
        "display_name": "Long Strangle",
        "category": "volatile",
        "description": "Buy OTM call and put at different strikes - cheaper than straddle",
        "legs": [
            {"type": "CE", "action": "BUY", "strike_offset": 100, "expiry_offset": 0},
            {"type": "PE", "action": "BUY", "strike_offset": -100, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "beginner",
        "max_profit": "Unlimited",
        "max_loss": "Limited"
    },
    "reverse_iron_condor": {
        "display_name": "Reverse Iron Condor",
        "category": "volatile",
        "description": "Buy strangle structure with defined risk for large moves",
        "legs": [
            {"type": "PE", "action": "SELL", "strike_offset": -200, "expiry_offset": 0},
            {"type": "PE", "action": "BUY", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 200, "expiry_offset": 0}
        ],
        "risk_level": "low",
        "difficulty": "intermediate",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },

    # ==================== INCOME STRATEGIES ====================
    "covered_call": {
        "display_name": "Covered Call",
        "category": "income",
        "description": "Own stock/futures and sell OTM call to generate income",
        "legs": [
            {"type": "EQ", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 100, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "beginner",
        "max_profit": "Limited",
        "max_loss": "Unlimited (stock risk)"
    },
    "cash_secured_put": {
        "display_name": "Cash Secured Put",
        "category": "income",
        "description": "Sell OTM put while holding cash to buy stock if assigned",
        "legs": [
            {"type": "PE", "action": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "beginner",
        "max_profit": "Limited",
        "max_loss": "Substantial"
    },
    "wheel_strategy": {
        "display_name": "Wheel Strategy",
        "category": "income",
        "description": "Systematic cycling between cash-secured puts and covered calls",
        "legs": [
            {"type": "PE", "action": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "beginner",
        "max_profit": "Continuous income",
        "max_loss": "Stock holding risk"
    },

    # ==================== ADVANCED STRATEGIES ====================
    "calendar_spread": {
        "display_name": "Calendar Spread",
        "category": "advanced",
        "description": "Buy far-dated option and sell near-dated option at same strike",
        "legs": [
            {"type": "CE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 0, "expiry_offset": 1}
        ],
        "risk_level": "medium",
        "difficulty": "advanced",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "diagonal_spread": {
        "display_name": "Diagonal Spread",
        "category": "advanced",
        "description": "Like calendar spread but with different strikes - directional time spread",
        "legs": [
            {"type": "CE", "action": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 0, "expiry_offset": 1}
        ],
        "risk_level": "medium",
        "difficulty": "advanced",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "butterfly_spread": {
        "display_name": "Butterfly Spread",
        "category": "advanced",
        "description": "Buy-sell-sell-buy pattern at three consecutive strikes for pinning profit",
        "legs": [
            {"type": "CE", "action": "BUY", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 100, "expiry_offset": 0}
        ],
        "risk_level": "low",
        "difficulty": "advanced",
        "max_profit": "Limited",
        "max_loss": "Limited"
    },
    "ratio_backspread_call": {
        "display_name": "Call Ratio Backspread",
        "category": "advanced",
        "description": "Sell ITM call and buy more OTM calls for unlimited upside",
        "legs": [
            {"type": "CE", "action": "SELL", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "advanced",
        "max_profit": "Unlimited",
        "max_loss": "Limited"
    },
    "ratio_backspread_put": {
        "display_name": "Put Ratio Backspread",
        "category": "advanced",
        "description": "Sell ITM put and buy more OTM puts for crash protection",
        "legs": [
            {"type": "PE", "action": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "PE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "action": "BUY", "strike_offset": 0, "expiry_offset": 0}
        ],
        "risk_level": "medium",
        "difficulty": "advanced",
        "max_profit": "Unlimited",
        "max_loss": "Limited"
    },

    # ==================== CUSTOM ====================
    "custom": {
        "display_name": "Custom Strategy",
        "category": "advanced",
        "description": "Create your own custom strategy with manual leg entry",
        "legs": [],  # No auto-populate for custom
        "risk_level": "varies",
        "difficulty": "varies",
        "max_profit": "Varies",
        "max_loss": "Varies"
    }
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_strategy_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a strategy type by its key name."""
    strategy = STRATEGY_TYPES.get(name)
    if strategy:
        return {"key": name, **strategy}
    return None


def get_strategies_by_category(category: str) -> List[Dict[str, Any]]:
    """Get all strategies in a specific category."""
    return [
        {"key": key, **strategy}
        for key, strategy in STRATEGY_TYPES.items()
        if strategy.get("category") == category
    ]


def get_all_strategies_grouped() -> Dict[str, List[Dict[str, Any]]]:
    """Get all strategies grouped by category."""
    grouped = {}
    for category in CATEGORIES.keys():
        grouped[category] = get_strategies_by_category(category)
    return grouped


def get_strategy_legs(name: str) -> List[Dict[str, Any]]:
    """Get the leg configuration for a strategy type."""
    strategy = STRATEGY_TYPES.get(name)
    if strategy:
        return strategy.get("legs", [])
    return []
