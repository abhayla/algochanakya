"""
Seed script for populating strategy_templates table with 20+ pre-defined options strategies.

Usage:
    cd backend
    python -m scripts.seed_strategies
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.strategy_templates import StrategyTemplate


STRATEGY_TEMPLATES = [
    # ==================== BULLISH STRATEGIES ====================
    {
        "name": "bull_call_spread",
        "display_name": "Bull Call Spread",
        "category": "bullish",
        "description": "Buy a call option at a lower strike and sell a call at a higher strike with the same expiry. Profits from moderate upward price movement with limited risk.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Difference in strikes - Net premium paid)",
        "max_loss": "Limited (Net premium paid)",
        "breakeven": "Lower strike + Net premium paid",
        "market_outlook": "bullish",
        "volatility_preference": "any",
        "ideal_iv_rank": None,
        "risk_level": "low",
        "capital_requirement": "low",
        "margin_requirement": "Net debit (premium paid)",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "medium",
        "win_probability": "~45-50%",
        "profit_target": "50-75% of max profit",
        "when_to_use": "When you expect moderate upward movement in the underlying. The short call reduces cost but caps profit potential.",
        "pros": [
            "Lower cost than buying calls outright",
            "Defined and limited risk",
            "Works in moderately bullish markets"
        ],
        "cons": [
            "Capped profit potential",
            "Requires directional accuracy",
            "Time decay works against if stock doesn't move"
        ],
        "common_mistakes": [
            "Setting strikes too wide (reducing probability)",
            "Holding too long when profitable",
            "Not having a clear exit plan"
        ],
        "exit_rules": [
            "Exit at 50-75% of max profit",
            "Exit if underlying drops below entry price",
            "Roll up if strongly bullish continuation expected"
        ],
        "adjustments": [
            {"trigger": "Stock rises above short strike", "action": "Roll short call up and out"},
            {"trigger": "Stock drops significantly", "action": "Close for remaining value or roll down"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 24000 CE @ Rs.250, Sell 24100 CE @ Rs.180. Net debit: Rs.70. Max profit: Rs.30",
        "popularity_score": 85,
        "difficulty_level": "beginner",
        "tags": ["debit spread", "directional", "defined risk"]
    },
    {
        "name": "bull_put_spread",
        "display_name": "Bull Put Spread",
        "category": "bullish",
        "description": "Sell a put at a higher strike and buy a put at a lower strike. Collects premium upfront and profits if stock stays above short strike.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": -100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Net premium received)",
        "max_loss": "Limited (Difference in strikes - Net premium)",
        "breakeven": "Higher strike - Net premium received",
        "market_outlook": "bullish",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">50%",
        "risk_level": "low",
        "capital_requirement": "medium",
        "margin_requirement": "Difference in strikes minus premium received",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability": "~60-70%",
        "profit_target": "50% of max profit (premium received)",
        "when_to_use": "When you're moderately bullish and want to collect premium. Higher win rate than bull call spread but requires margin.",
        "pros": [
            "High probability of profit",
            "Time decay works in your favor",
            "Premium received upfront"
        ],
        "cons": [
            "Requires margin",
            "Risk/reward less favorable",
            "Can lose more than you receive"
        ],
        "common_mistakes": [
            "Selling too close to ATM",
            "Not managing at 50% profit",
            "Ignoring large gap risk"
        ],
        "exit_rules": [
            "Exit at 50% of max profit",
            "Exit if stock approaches short strike",
            "Close before expiry if near breakeven"
        ],
        "adjustments": [
            {"trigger": "Stock drops near short strike", "action": "Roll down and out for credit"},
            {"trigger": "IV spikes significantly", "action": "Consider closing early"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 23900 PE @ Rs.120, Buy 23800 PE @ Rs.80. Net credit: Rs.40. Max loss: Rs.60",
        "popularity_score": 80,
        "difficulty_level": "beginner",
        "tags": ["credit spread", "income", "high probability"]
    },
    {
        "name": "synthetic_long",
        "display_name": "Synthetic Long",
        "category": "bullish",
        "description": "Buy a call and sell a put at the same strike price. Mimics owning the underlying stock with unlimited upside and downside.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0}
        ],
        "max_profit": "Unlimited",
        "max_loss": "Unlimited (strike price - net premium)",
        "breakeven": "Strike price + Net premium (debit) or - Net credit",
        "market_outlook": "bullish",
        "volatility_preference": "any",
        "ideal_iv_rank": None,
        "risk_level": "high",
        "capital_requirement": "high",
        "margin_requirement": "Similar to holding stock/futures",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability": "~50%",
        "profit_target": "Based on stock target",
        "when_to_use": "When you want synthetic stock exposure without owning shares. Often near zero cost due to put-call parity.",
        "pros": [
            "Capital efficient way to get stock exposure",
            "No early exercise risk (European options)",
            "Can be constructed for near-zero cost"
        ],
        "cons": [
            "Unlimited downside risk",
            "Requires significant margin",
            "Equivalent risk to holding stock"
        ],
        "common_mistakes": [
            "Not understanding the margin requirement",
            "Holding through earnings without hedge",
            "Ignoring the synthetic position's full risk"
        ],
        "exit_rules": [
            "Use same exit rules as stock trading",
            "Set stop-loss based on strike price",
            "Close before expiry to avoid assignment"
        ],
        "adjustments": None,
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 24000 CE @ Rs.300, Sell 24000 PE @ Rs.280. Net debit: Rs.20",
        "popularity_score": 60,
        "difficulty_level": "advanced",
        "tags": ["synthetic", "leveraged", "futures equivalent"]
    },

    # ==================== BEARISH STRATEGIES ====================
    {
        "name": "bear_put_spread",
        "display_name": "Bear Put Spread",
        "category": "bearish",
        "description": "Buy a put at a higher strike and sell a put at a lower strike. Profits from moderate downward price movement.",
        "legs_config": [
            {"type": "PE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Difference in strikes - Net premium paid)",
        "max_loss": "Limited (Net premium paid)",
        "breakeven": "Higher strike - Net premium paid",
        "market_outlook": "bearish",
        "volatility_preference": "any",
        "ideal_iv_rank": None,
        "risk_level": "low",
        "capital_requirement": "low",
        "margin_requirement": "Net debit (premium paid)",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "medium",
        "win_probability": "~45-50%",
        "profit_target": "50-75% of max profit",
        "when_to_use": "When expecting moderate downward movement. Lower cost than buying puts outright.",
        "pros": [
            "Defined and limited risk",
            "Lower cost than naked puts",
            "Works in moderately bearish markets"
        ],
        "cons": [
            "Capped profit potential",
            "Requires directional accuracy",
            "Time decay hurts the position"
        ],
        "common_mistakes": [
            "Setting strikes too far OTM",
            "Holding past optimal exit point",
            "Trading in low volatility environments"
        ],
        "exit_rules": [
            "Exit at 50-75% of max profit",
            "Exit if underlying rallies above entry",
            "Roll down if bearish outlook strengthens"
        ],
        "adjustments": [
            {"trigger": "Stock drops below short strike", "action": "Roll short put down for credit"},
            {"trigger": "Stock rallies", "action": "Close for remaining value"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 24000 PE @ Rs.280, Sell 23900 PE @ Rs.200. Net debit: Rs.80. Max profit: Rs.20",
        "popularity_score": 75,
        "difficulty_level": "beginner",
        "tags": ["debit spread", "directional", "defined risk"]
    },
    {
        "name": "bear_call_spread",
        "display_name": "Bear Call Spread",
        "category": "bearish",
        "description": "Sell a call at a lower strike and buy a call at a higher strike. Collects premium and profits if stock stays below short strike.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Net premium received)",
        "max_loss": "Limited (Difference in strikes - Net premium)",
        "breakeven": "Lower strike + Net premium received",
        "market_outlook": "bearish",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">50%",
        "risk_level": "low",
        "capital_requirement": "medium",
        "margin_requirement": "Difference in strikes minus premium",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability": "~60-70%",
        "profit_target": "50% of max profit",
        "when_to_use": "When moderately bearish to neutral. High probability strategy that benefits from time decay.",
        "pros": [
            "High probability of profit",
            "Time decay advantage",
            "Premium received upfront"
        ],
        "cons": [
            "Requires margin",
            "Limited profit potential",
            "Assignment risk if ITM"
        ],
        "common_mistakes": [
            "Selling too close to the money",
            "Holding to expiry when profitable early",
            "Not having adjustment plan"
        ],
        "exit_rules": [
            "Exit at 50% profit",
            "Exit if stock approaches short strike",
            "Roll up and out if challenged"
        ],
        "adjustments": [
            {"trigger": "Stock rises near short strike", "action": "Roll up and out for credit"},
            {"trigger": "Time decay slows", "action": "Close if near target"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 24100 CE @ Rs.150, Buy 24200 CE @ Rs.100. Net credit: Rs.50. Max loss: Rs.50",
        "popularity_score": 78,
        "difficulty_level": "beginner",
        "tags": ["credit spread", "income", "high probability"]
    },
    {
        "name": "synthetic_short",
        "display_name": "Synthetic Short",
        "category": "bearish",
        "description": "Buy a put and sell a call at the same strike. Replicates shorting the underlying with unlimited profit potential and unlimited risk.",
        "legs_config": [
            {"type": "PE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0}
        ],
        "max_profit": "Unlimited (as stock drops to zero)",
        "max_loss": "Unlimited (as stock rises)",
        "breakeven": "Strike price - Net premium",
        "market_outlook": "bearish",
        "volatility_preference": "any",
        "ideal_iv_rank": None,
        "risk_level": "high",
        "capital_requirement": "high",
        "margin_requirement": "Similar to short stock/futures",
        "theta_positive": False,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability": "~50%",
        "profit_target": "Based on bearish target",
        "when_to_use": "When strongly bearish and want short exposure without borrowing shares.",
        "pros": [
            "No need to borrow shares",
            "Near-zero cost construction",
            "Full downside participation"
        ],
        "cons": [
            "Unlimited upside risk",
            "High margin requirement",
            "Early assignment risk on short call"
        ],
        "common_mistakes": [
            "Underestimating upside risk",
            "No stop-loss discipline",
            "Holding through earnings unhedged"
        ],
        "exit_rules": [
            "Set stop-loss as if short stock",
            "Take profits at target levels",
            "Close before expiry if in profit"
        ],
        "adjustments": None,
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 24000 PE @ Rs.280, Sell 24000 CE @ Rs.300. Net credit: Rs.20",
        "popularity_score": 55,
        "difficulty_level": "advanced",
        "tags": ["synthetic", "leveraged", "unlimited risk"]
    },

    # ==================== NEUTRAL STRATEGIES ====================
    {
        "name": "iron_condor",
        "display_name": "Iron Condor",
        "category": "neutral",
        "description": "Combination of a bull put spread and bear call spread. Profits from low volatility and time decay when stock stays in a range.",
        "legs_config": [
            {"type": "PE", "position": "BUY", "strike_offset": -200, "expiry_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 200, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Total net premium received)",
        "max_loss": "Limited (Width of spread - Net premium)",
        "breakeven": "Two breakevens: Short put - Credit, Short call + Credit",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">50%",
        "risk_level": "medium",
        "capital_requirement": "medium",
        "margin_requirement": "Width of one spread",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "medium",
        "win_probability": "~60-75%",
        "profit_target": "50% of max profit",
        "when_to_use": "When expecting low volatility and range-bound price action. Best entered after IV spike.",
        "pros": [
            "High probability of profit",
            "Benefits from time decay",
            "Defined risk on both sides",
            "No directional bias needed"
        ],
        "cons": [
            "Limited profit potential",
            "Large moves hurt significantly",
            "Requires active management"
        ],
        "common_mistakes": [
            "Trading in low IV environments",
            "Setting wings too narrow",
            "Not managing at 50% profit",
            "Holding too close to expiry"
        ],
        "exit_rules": [
            "Exit at 50% of max profit",
            "Exit if stock breaks a short strike",
            "Roll untested side in for credit"
        ],
        "adjustments": [
            {"trigger": "Stock challenges put side", "action": "Roll put spread down and out"},
            {"trigger": "Stock challenges call side", "action": "Roll call spread up and out"},
            {"trigger": "Early 50% profit", "action": "Close entire position"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 23900/23800 put spread, Sell 24100/24200 call spread. Net credit: Rs.60",
        "popularity_score": 95,
        "difficulty_level": "intermediate",
        "tags": ["income", "defined risk", "neutral", "theta positive"]
    },
    {
        "name": "iron_butterfly",
        "display_name": "Iron Butterfly",
        "category": "neutral",
        "description": "Sell an ATM straddle and buy protective wings. Higher credit than iron condor but narrower profit zone.",
        "legs_config": [
            {"type": "PE", "position": "BUY", "strike_offset": -100, "expiry_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Net premium received)",
        "max_loss": "Limited (Wing width - Net premium)",
        "breakeven": "Strike ± Net premium received",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">60%",
        "risk_level": "medium",
        "capital_requirement": "medium",
        "margin_requirement": "Wing width minus premium",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability": "~30-40%",
        "profit_target": "25-50% of max profit",
        "when_to_use": "When expecting very low volatility and stock to pin near a specific price.",
        "pros": [
            "Higher credit than iron condor",
            "Defined risk",
            "Maximum profit at exact strike"
        ],
        "cons": [
            "Narrow profit zone",
            "Lower probability than iron condor",
            "Requires precise timing"
        ],
        "common_mistakes": [
            "Expecting full max profit",
            "Holding too long",
            "Not adjusting when stock moves"
        ],
        "exit_rules": [
            "Exit at 25-50% of max profit",
            "Exit if stock moves beyond wing",
            "Manage early - don't hold to expiry"
        ],
        "adjustments": [
            {"trigger": "Stock moves away from center", "action": "Roll to new ATM or close"},
            {"trigger": "Early profit target hit", "action": "Close immediately"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 23900 PE, Sell 24000 PE + CE, Buy 24100 CE. Net credit: Rs.100",
        "popularity_score": 70,
        "difficulty_level": "intermediate",
        "tags": ["income", "defined risk", "neutral", "pinning"]
    },
    {
        "name": "short_straddle",
        "display_name": "Short Straddle",
        "category": "neutral",
        "description": "Sell ATM call and put at the same strike. Collects maximum premium but has unlimited risk on both sides.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Total premium received)",
        "max_loss": "Unlimited",
        "breakeven": "Strike ± Total premium received",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">70%",
        "risk_level": "high",
        "capital_requirement": "high",
        "margin_requirement": "High (naked option margin)",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability": "~40%",
        "profit_target": "25-50% of premium received",
        "when_to_use": "When expecting very low volatility and high IV. Extremely risky strategy for experienced traders only.",
        "pros": [
            "Maximum premium collection",
            "Time decay on both sides",
            "Benefits from IV crush"
        ],
        "cons": [
            "Unlimited risk both directions",
            "Requires constant monitoring",
            "Large margin requirement"
        ],
        "common_mistakes": [
            "Holding through earnings",
            "No adjustment plan",
            "Selling in low IV environment",
            "Over-leveraging"
        ],
        "exit_rules": [
            "Exit at 25-50% profit",
            "Exit if stock moves 1 standard deviation",
            "Have stop-loss at 2x premium collected"
        ],
        "adjustments": [
            {"trigger": "Stock moves up", "action": "Buy back call, sell new ATM straddle"},
            {"trigger": "Stock moves down", "action": "Buy back put, sell new ATM straddle"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 24000 CE @ Rs.300, Sell 24000 PE @ Rs.280. Total credit: Rs.580",
        "popularity_score": 65,
        "difficulty_level": "advanced",
        "tags": ["income", "undefined risk", "naked", "theta positive"]
    },
    {
        "name": "short_strangle",
        "display_name": "Short Strangle",
        "category": "neutral",
        "description": "Sell OTM call and put at different strikes. Wider profit zone than straddle but still has unlimited risk.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "PE", "position": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Total premium received)",
        "max_loss": "Unlimited",
        "breakeven": "Put strike - Premium, Call strike + Premium",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">60%",
        "risk_level": "high",
        "capital_requirement": "high",
        "margin_requirement": "High (naked option margin)",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "medium",
        "win_probability": "~60-70%",
        "profit_target": "50% of premium received",
        "when_to_use": "When expecting rangebound movement and high IV. More common than short straddle due to wider breakevens.",
        "pros": [
            "Higher probability than straddle",
            "Wider profit zone",
            "Good premium collection"
        ],
        "cons": [
            "Unlimited risk",
            "Large margin required",
            "Requires monitoring"
        ],
        "common_mistakes": [
            "Strikes too close together",
            "Not managing winners",
            "Trading before major events"
        ],
        "exit_rules": [
            "Exit at 50% profit",
            "Exit if either strike is breached",
            "Roll untested side in for credit"
        ],
        "adjustments": [
            {"trigger": "Stock approaches call strike", "action": "Roll call up and out"},
            {"trigger": "Stock approaches put strike", "action": "Roll put down and out"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 24100 CE @ Rs.180, Sell 23900 PE @ Rs.150. Total credit: Rs.330",
        "popularity_score": 80,
        "difficulty_level": "advanced",
        "tags": ["income", "undefined risk", "naked", "theta positive"]
    },
    {
        "name": "jade_lizard",
        "display_name": "Jade Lizard",
        "category": "neutral",
        "description": "Short put + short call spread. No upside risk if credit received exceeds call spread width. Slight bullish bias.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 200, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Total net premium received)",
        "max_loss": "Limited upside (spread width - credit), Unlimited downside (like short put)",
        "breakeven": "Short put strike - Net credit",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">50%",
        "risk_level": "medium",
        "capital_requirement": "medium",
        "margin_requirement": "Short put margin + spread margin",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "medium",
        "win_probability": "~65%",
        "profit_target": "50% of max profit",
        "when_to_use": "When slightly bullish but want protection against large upside moves. Good alternative to strangle.",
        "pros": [
            "No upside risk if structured correctly",
            "Higher probability than strangle",
            "Good premium collection"
        ],
        "cons": [
            "Downside risk still unlimited",
            "Slightly more complex",
            "Lower credit than strangle"
        ],
        "common_mistakes": [
            "Not collecting enough credit to eliminate upside risk",
            "Ignoring the naked put risk",
            "Holding too long"
        ],
        "exit_rules": [
            "Exit at 50% profit",
            "Exit if put strike is challenged",
            "Close if upside is breached"
        ],
        "adjustments": [
            {"trigger": "Stock drops to short put", "action": "Roll put down and out"},
            {"trigger": "Stock rises sharply", "action": "Let call spread expire worthless"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 23900 PE @ Rs.120, Sell 24100 CE @ Rs.150, Buy 24200 CE @ Rs.100. Net credit: Rs.170",
        "popularity_score": 55,
        "difficulty_level": "intermediate",
        "tags": ["income", "limited upside risk", "theta positive"]
    },

    # ==================== VOLATILE STRATEGIES ====================
    {
        "name": "long_straddle",
        "display_name": "Long Straddle",
        "category": "volatile",
        "description": "Buy ATM call and put at the same strike. Profits from large moves in either direction.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0}
        ],
        "max_profit": "Unlimited",
        "max_loss": "Limited (Total premium paid)",
        "breakeven": "Strike ± Total premium paid",
        "market_outlook": "volatile",
        "volatility_preference": "low_iv",
        "ideal_iv_rank": "<30%",
        "risk_level": "medium",
        "capital_requirement": "medium",
        "margin_requirement": "Total premium paid (debit)",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability": "~30-40%",
        "profit_target": "50-100% of premium paid",
        "when_to_use": "Before major events like earnings, budget, or RBI announcements. Enter when IV is relatively low.",
        "pros": [
            "Unlimited profit potential",
            "Defined risk",
            "Direction neutral"
        ],
        "cons": [
            "Expensive premium",
            "Time decay hurts",
            "Needs large move to profit"
        ],
        "common_mistakes": [
            "Buying when IV is already high",
            "Holding too long after event",
            "Not taking profits when available"
        ],
        "exit_rules": [
            "Exit when target move occurs",
            "Exit if IV spikes significantly",
            "Exit before expiry week if flat"
        ],
        "adjustments": [
            {"trigger": "Stock moves one way significantly", "action": "Sell winning leg, hold loser"},
            {"trigger": "IV crushes", "action": "Exit immediately"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 24000 CE @ Rs.300, Buy 24000 PE @ Rs.280. Total debit: Rs.580",
        "popularity_score": 75,
        "difficulty_level": "beginner",
        "tags": ["debit", "event play", "volatility"]
    },
    {
        "name": "long_strangle",
        "display_name": "Long Strangle",
        "category": "volatile",
        "description": "Buy OTM call and put at different strikes. Cheaper than straddle but needs larger move.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 100, "expiry_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": -100, "expiry_offset": 0}
        ],
        "max_profit": "Unlimited",
        "max_loss": "Limited (Total premium paid)",
        "breakeven": "Put strike - Premium, Call strike + Premium",
        "market_outlook": "volatile",
        "volatility_preference": "low_iv",
        "ideal_iv_rank": "<30%",
        "risk_level": "medium",
        "capital_requirement": "medium",
        "margin_requirement": "Total premium paid (debit)",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability": "~25-35%",
        "profit_target": "100%+ of premium paid",
        "when_to_use": "Before major events when expecting huge move. Cheaper alternative to straddle.",
        "pros": [
            "Cheaper than straddle",
            "Unlimited profit potential",
            "Defined risk"
        ],
        "cons": [
            "Needs larger move than straddle",
            "Lower win rate",
            "Time decay hurts"
        ],
        "common_mistakes": [
            "Strikes too wide",
            "Buying before IV spike",
            "Holding through time decay"
        ],
        "exit_rules": [
            "Exit on large directional move",
            "Exit if IV spikes 50%+",
            "Close before expiry if no move"
        ],
        "adjustments": [
            {"trigger": "Stock makes large move", "action": "Exit profitable leg, hold other"},
            {"trigger": "IV spikes", "action": "Consider closing for IV profit"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 24100 CE @ Rs.180, Buy 23900 PE @ Rs.150. Total debit: Rs.330",
        "popularity_score": 70,
        "difficulty_level": "beginner",
        "tags": ["debit", "event play", "volatility"]
    },
    {
        "name": "reverse_iron_condor",
        "display_name": "Reverse Iron Condor",
        "category": "volatile",
        "description": "Buy iron condor structure. Pay debit for large move in either direction with defined risk.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -200, "expiry_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 200, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Width of spread - Net debit)",
        "max_loss": "Limited (Net debit paid)",
        "breakeven": "Two breakevens based on debit paid",
        "market_outlook": "volatile",
        "volatility_preference": "low_iv",
        "ideal_iv_rank": "<40%",
        "risk_level": "low",
        "capital_requirement": "low",
        "margin_requirement": "Net debit paid",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "medium",
        "win_probability": "~35%",
        "profit_target": "50-75% of max profit",
        "when_to_use": "When expecting large move but want defined risk. Cheaper than long strangle.",
        "pros": [
            "Defined risk",
            "Lower cost than strangle",
            "Benefits from IV expansion"
        ],
        "cons": [
            "Capped profit potential",
            "Lower probability",
            "Time decay hurts"
        ],
        "common_mistakes": [
            "Wings too narrow",
            "Entering too early before event",
            "Not managing at profit target"
        ],
        "exit_rules": [
            "Exit at 50-75% of max profit",
            "Exit if stock moves past wing",
            "Close before expiry"
        ],
        "adjustments": None,
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 23900/24100 strangle, Sell 23800/24200 strangle. Net debit: Rs.40",
        "popularity_score": 50,
        "difficulty_level": "intermediate",
        "tags": ["debit", "defined risk", "event play"]
    },

    # ==================== INCOME STRATEGIES ====================
    {
        "name": "covered_call",
        "display_name": "Covered Call",
        "category": "income",
        "description": "Own stock/futures and sell OTM call. Generates income from the position with limited upside.",
        "legs_config": [
            {"type": "EQ", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Strike - Stock price + Premium)",
        "max_loss": "Unlimited (if stock drops to zero)",
        "breakeven": "Stock purchase price - Premium received",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">40%",
        "risk_level": "medium",
        "capital_requirement": "high",
        "margin_requirement": "Full stock position value",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability": "~70%",
        "profit_target": "Keep premium, repeat monthly",
        "when_to_use": "When holding long stock and expecting sideways to slightly bullish movement.",
        "pros": [
            "Generates income from existing position",
            "Lowers cost basis",
            "High probability strategy"
        ],
        "cons": [
            "Caps upside potential",
            "Still have full downside risk",
            "May have stock called away"
        ],
        "common_mistakes": [
            "Selling too close to the money",
            "Not rolling when necessary",
            "Selling before dividends"
        ],
        "exit_rules": [
            "Let expire OTM for full premium",
            "Roll up and out if challenged",
            "Buy back at 50% profit and resell"
        ],
        "adjustments": [
            {"trigger": "Stock rises above strike", "action": "Roll call up and out for credit"},
            {"trigger": "Stock drops significantly", "action": "Keep call, buy protective put"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Own stock at 24000, Sell 24100 CE @ Rs.150. Breakeven: 23850",
        "popularity_score": 90,
        "difficulty_level": "beginner",
        "tags": ["income", "conservative", "theta positive"]
    },
    {
        "name": "cash_secured_put",
        "display_name": "Cash Secured Put",
        "category": "income",
        "description": "Sell OTM put while holding cash to buy stock if assigned. Generates income with obligation to buy at lower price.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Premium received)",
        "max_loss": "Substantial (Strike - Premium, if stock drops to zero)",
        "breakeven": "Strike price - Premium received",
        "market_outlook": "bullish",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">50%",
        "risk_level": "medium",
        "capital_requirement": "high",
        "margin_requirement": "Cash equal to (Strike x Lot size)",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability": "~70-80%",
        "profit_target": "Keep full premium",
        "when_to_use": "When willing to buy stock at a lower price. Good way to enter positions with income.",
        "pros": [
            "Get paid to wait for lower price",
            "High probability of profit",
            "Time decay advantage"
        ],
        "cons": [
            "Must have capital to buy shares",
            "Opportunity cost of cash",
            "Assignment risk in crash"
        ],
        "common_mistakes": [
            "Selling on stocks you don't want to own",
            "Not having cash reserved",
            "Over-leveraging with multiple positions"
        ],
        "exit_rules": [
            "Let expire OTM for full premium",
            "Buy back at 50% profit",
            "Roll down and out if challenged"
        ],
        "adjustments": [
            {"trigger": "Stock drops to strike", "action": "Roll down and out for credit"},
            {"trigger": "Assignment", "action": "Accept stock, start selling covered calls"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 23800 PE @ Rs.80. Max profit: Rs.80. Breakeven: 23720",
        "popularity_score": 85,
        "difficulty_level": "beginner",
        "tags": ["income", "conservative", "wheel strategy"]
    },
    {
        "name": "wheel_strategy",
        "display_name": "Wheel Strategy",
        "category": "income",
        "description": "Cycle between cash-secured puts and covered calls. Systematic income generation approach.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -100, "expiry_offset": 0}
        ],
        "max_profit": "Continuous premium income",
        "max_loss": "Stock drops significantly while holding",
        "breakeven": "Varies with each cycle",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">40%",
        "risk_level": "medium",
        "capital_requirement": "high",
        "margin_requirement": "Cash for stock purchase",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability": "~70%",
        "profit_target": "Consistent monthly income",
        "when_to_use": "On quality stocks you want to own long-term. Best for patient, income-focused traders.",
        "pros": [
            "Systematic approach",
            "Works in multiple market conditions",
            "Lowers average cost basis"
        ],
        "cons": [
            "Can be stuck holding loser",
            "Requires significant capital",
            "May underperform in strong bull market"
        ],
        "common_mistakes": [
            "Starting on speculative stocks",
            "Not sticking to the system",
            "Over-allocating to wheel"
        ],
        "exit_rules": [
            "Phase 1: Sell puts until assigned",
            "Phase 2: Sell calls until called away",
            "Repeat cycle continuously"
        ],
        "adjustments": [
            {"trigger": "Put assigned", "action": "Start selling covered calls"},
            {"trigger": "Stock called away", "action": "Return to selling puts"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Step 1: Sell 23800 PE. If assigned, Step 2: Sell 24100 CE. Repeat.",
        "popularity_score": 75,
        "difficulty_level": "beginner",
        "tags": ["income", "systematic", "long-term"]
    },

    # ==================== ADVANCED STRATEGIES ====================
    {
        "name": "calendar_spread",
        "display_name": "Calendar Spread",
        "category": "advanced",
        "description": "Buy far-dated option and sell near-dated option at same strike. Profits from time decay differential.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 0, "expiry_offset": 1}
        ],
        "max_profit": "Limited (depends on IV and time)",
        "max_loss": "Limited (Net debit paid)",
        "breakeven": "Complex - depends on IV",
        "market_outlook": "neutral",
        "volatility_preference": "low_iv",
        "ideal_iv_rank": "<40%",
        "risk_level": "medium",
        "capital_requirement": "medium",
        "margin_requirement": "Net debit + calendar margin",
        "theta_positive": True,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "low",
        "win_probability": "~50%",
        "profit_target": "25-50% of debit",
        "when_to_use": "When expecting stock to stay near strike through near-term expiry. Benefits from IV expansion.",
        "pros": [
            "Time decay on short leg",
            "IV expansion helps",
            "Defined risk"
        ],
        "cons": [
            "Complex to manage",
            "Narrow profit zone",
            "IV crush hurts"
        ],
        "common_mistakes": [
            "Wrong strike selection",
            "Holding past short expiry",
            "Not understanding IV impact"
        ],
        "exit_rules": [
            "Exit before short expiry",
            "Exit at 25-50% profit",
            "Close if stock moves away from strike"
        ],
        "adjustments": [
            {"trigger": "Stock moves away from strike", "action": "Roll to new ATM strike"},
            {"trigger": "Short expiry approaching", "action": "Close or roll to next expiry"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 24000 CE (current expiry) @ Rs.200, Buy 24000 CE (next month) @ Rs.350. Net debit: Rs.150",
        "popularity_score": 60,
        "difficulty_level": "advanced",
        "tags": ["time spread", "vega positive", "advanced"]
    },
    {
        "name": "diagonal_spread",
        "display_name": "Diagonal Spread",
        "category": "advanced",
        "description": "Like calendar spread but with different strikes. Combines time and directional elements.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 0, "expiry_offset": 1}
        ],
        "max_profit": "Limited (complex calculation)",
        "max_loss": "Limited (Net debit paid)",
        "breakeven": "Complex - depends on IV and time",
        "market_outlook": "bullish",
        "volatility_preference": "low_iv",
        "ideal_iv_rank": "<40%",
        "risk_level": "medium",
        "capital_requirement": "medium",
        "margin_requirement": "Net debit + diagonal margin",
        "theta_positive": True,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability": "~55%",
        "profit_target": "25-50% of debit",
        "when_to_use": "When slightly directional and want time decay. Often called 'poor man's covered call'.",
        "pros": [
            "Directional with time decay",
            "Capital efficient",
            "Multiple profit sources"
        ],
        "cons": [
            "Complex management",
            "Requires experience",
            "IV changes affect significantly"
        ],
        "common_mistakes": [
            "Wrong strike relationship",
            "Ignoring assignment risk",
            "Holding too long"
        ],
        "exit_rules": [
            "Exit at 25-50% profit",
            "Roll short call when profitable",
            "Close before short expiry"
        ],
        "adjustments": [
            {"trigger": "Stock rises above short strike", "action": "Roll short call up and out"},
            {"trigger": "Stock drops", "action": "Close for loss or roll down"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 24100 CE (current) @ Rs.150, Buy 24000 CE (next month) @ Rs.350. Net debit: Rs.200",
        "popularity_score": 55,
        "difficulty_level": "advanced",
        "tags": ["diagonal", "directional", "advanced"]
    },
    {
        "name": "butterfly_spread",
        "display_name": "Butterfly Spread",
        "category": "advanced",
        "description": "Buy-sell-buy pattern at three consecutive strikes. Maximum profit at middle strike with defined risk.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "SELL", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 100, "expiry_offset": 0}
        ],
        "max_profit": "Limited (Wing width - Net debit)",
        "max_loss": "Limited (Net debit paid)",
        "breakeven": "Lower strike + Debit, Upper strike - Debit",
        "market_outlook": "neutral",
        "volatility_preference": "high_iv",
        "ideal_iv_rank": ">50%",
        "risk_level": "low",
        "capital_requirement": "low",
        "margin_requirement": "Net debit paid",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability": "~30-40%",
        "profit_target": "25-50% of max profit",
        "when_to_use": "When expecting stock to pin at a specific price. Low cost speculation on exact price.",
        "pros": [
            "Very low cost",
            "High reward/risk ratio",
            "Defined risk"
        ],
        "cons": [
            "Narrow profit zone",
            "Low probability",
            "Needs exact pinning"
        ],
        "common_mistakes": [
            "Expecting full max profit",
            "Holding to expiry",
            "Wrong strike selection"
        ],
        "exit_rules": [
            "Exit at 25-50% of max profit",
            "Exit if stock moves beyond wings",
            "Close 1-2 days before expiry"
        ],
        "adjustments": [
            {"trigger": "Stock moves away", "action": "Close and reposition"},
            {"trigger": "Near target profit", "action": "Close immediately"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Buy 23900 CE, Sell 2x 24000 CE, Buy 24100 CE. Net debit: Rs.20",
        "popularity_score": 65,
        "difficulty_level": "advanced",
        "tags": ["defined risk", "pinning", "low cost"]
    },
    {
        "name": "ratio_backspread_call",
        "display_name": "Call Ratio Backspread",
        "category": "advanced",
        "description": "Sell ITM call and buy more OTM calls. Profits from large upside moves with limited or no downside risk.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": -100, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "CE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0}
        ],
        "max_profit": "Unlimited (on upside)",
        "max_loss": "Limited (at long strike at expiry)",
        "breakeven": "Complex - two breakeven points",
        "market_outlook": "bullish",
        "volatility_preference": "low_iv",
        "ideal_iv_rank": "<40%",
        "risk_level": "medium",
        "capital_requirement": "low",
        "margin_requirement": "Low if done for credit",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability": "~40%",
        "profit_target": "50-100% of premium",
        "when_to_use": "When very bullish but want protection if wrong. Often done for credit.",
        "pros": [
            "Unlimited upside potential",
            "Can be done for credit",
            "Limited max loss"
        ],
        "cons": [
            "Zone of max loss at strike",
            "Needs large move to profit",
            "Time decay hurts"
        ],
        "common_mistakes": [
            "Wrong ratio selection",
            "Not understanding risk zone",
            "Holding through sideways action"
        ],
        "exit_rules": [
            "Exit on large upside move",
            "Exit if stuck at max loss zone",
            "Close before expiry"
        ],
        "adjustments": [
            {"trigger": "Stock at long strike", "action": "Buy back short call"},
            {"trigger": "Large upside move", "action": "Take profits on long calls"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 1x 23900 CE @ Rs.400, Buy 2x 24000 CE @ Rs.300 each. Net debit: Rs.200",
        "popularity_score": 45,
        "difficulty_level": "advanced",
        "tags": ["ratio spread", "unlimited profit", "advanced"]
    },
    {
        "name": "ratio_backspread_put",
        "display_name": "Put Ratio Backspread",
        "category": "advanced",
        "description": "Sell ITM put and buy more OTM puts. Profits from large downside moves with limited upside risk.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": 100, "expiry_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0},
            {"type": "PE", "position": "BUY", "strike_offset": 0, "expiry_offset": 0}
        ],
        "max_profit": "Unlimited (if stock drops to zero)",
        "max_loss": "Limited (at long strike at expiry)",
        "breakeven": "Complex - two breakeven points",
        "market_outlook": "bearish",
        "volatility_preference": "low_iv",
        "ideal_iv_rank": "<40%",
        "risk_level": "medium",
        "capital_requirement": "low",
        "margin_requirement": "Low if done for credit",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability": "~40%",
        "profit_target": "50-100% of premium",
        "when_to_use": "When very bearish but want protection if wrong. Good for crash protection.",
        "pros": [
            "Unlimited downside profit potential",
            "Can be done for credit",
            "Excellent crash protection"
        ],
        "cons": [
            "Max loss zone at long strike",
            "Needs large move",
            "Time decay hurts"
        ],
        "common_mistakes": [
            "Wrong ratio",
            "Not understanding loss zone",
            "Over-paying for protection"
        ],
        "exit_rules": [
            "Exit on large downside move",
            "Exit if stock rallies strongly",
            "Close before expiry"
        ],
        "adjustments": [
            {"trigger": "Stock at long strike", "action": "Buy back short put"},
            {"trigger": "Large downside move", "action": "Take profits on long puts"}
        ],
        "example_underlying": "NIFTY",
        "example_spot": 24000,
        "example_setup": "Sell 1x 24100 PE @ Rs.380, Buy 2x 24000 PE @ Rs.280 each. Net debit: Rs.180",
        "popularity_score": 40,
        "difficulty_level": "advanced",
        "tags": ["ratio spread", "crash protection", "advanced"]
    }
]


async def seed_strategies():
    """Seed the strategy_templates table with pre-defined strategies."""
    print("Starting strategy templates seed...")

    async with AsyncSessionLocal() as session:
        try:
            # Check if templates already exist
            result = await session.execute(select(StrategyTemplate).limit(1))
            existing = result.scalar_one_or_none()

            if existing:
                print("Strategy templates already exist. Clearing and re-seeding...")
                await session.execute(delete(StrategyTemplate))
                await session.commit()

            # Insert all templates
            for template_data in STRATEGY_TEMPLATES:
                template = StrategyTemplate(**template_data)
                session.add(template)

            await session.commit()
            print(f"Successfully seeded {len(STRATEGY_TEMPLATES)} strategy templates!")

            # Verify
            result = await session.execute(select(StrategyTemplate))
            templates = result.scalars().all()
            print(f"\nSeeded templates by category:")
            categories = {}
            for t in templates:
                categories[t.category] = categories.get(t.category, 0) + 1
            for cat, count in sorted(categories.items()):
                print(f"  {cat}: {count}")

        except Exception as e:
            await session.rollback()
            print(f"Error seeding strategies: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(seed_strategies())
