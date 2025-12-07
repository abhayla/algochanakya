# Option Strategies Implementation Plan

> Comprehensive option strategies system for AlgoChanakya with pre-built templates, strategy wizard, and one-click deployment.

## Overview

This document provides complete implementation details for:
1. Database schema for 20+ strategy templates
2. Strategy Wizard (3-question AI recommendation engine)
3. Strategy Library UI with categories
4. One-click deploy to Strategy Builder
5. Strategy comparison tool
6. Educational content for each strategy

---

## PHASE 1: Database Schema

### Create Strategy Template Model

Create file: `backend/app/models/strategy_template.py`

```python
from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, Text, Enum, DateTime
from sqlalchemy.sql import func
from app.db.base import Base
import enum


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Info
    name = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    category = Column(String(50), index=True, nullable=False)  # bullish, bearish, neutral, volatile, income, advanced
    description = Column(Text, nullable=False)
    short_description = Column(String(255))
    
    # Legs Configuration (JSON array)
    # Example: [{"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1}]
    legs_config = Column(JSON, nullable=False)
    
    # Risk/Reward Characteristics
    max_profit = Column(String(50))  # "Limited", "Unlimited"
    max_loss = Column(String(50))    # "Limited", "Unlimited"
    breakeven_count = Column(Integer, default=1)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.MEDIUM)
    
    # Suitability Criteria (for Wizard matching)
    market_outlook = Column(JSON)  # ["mild_bullish", "neutral"]
    volatility_preference = Column(String(20))  # "low", "high", "any"
    ideal_iv_percentile = Column(String(50))  # "Above 50", "Below 30", "Any"
    ideal_dte = Column(String(50))  # "Weekly", "Monthly", "45+ days"
    
    # Greeks Exposure
    theta_positive = Column(Boolean, default=False)
    vega_positive = Column(Boolean, default=False)
    delta_neutral = Column(Boolean, default=False)
    gamma_risk = Column(String(20))  # "low", "medium", "high"
    
    # Probability & Scoring
    win_probability_base = Column(Float, default=50.0)
    popularity_score = Column(Integer, default=0)
    
    # Educational Content
    video_url = Column(String(500), nullable=True)
    when_to_use = Column(JSON)  # List of conditions
    when_to_avoid = Column(JSON)  # List of conditions
    pros = Column(JSON)
    cons = Column(JSON)
    common_mistakes = Column(JSON)
    adjustment_guide = Column(Text, nullable=True)
    exit_rules = Column(JSON)  # List of exit conditions
    
    # Example Trade
    example_setup = Column(Text, nullable=True)
    example_outcome = Column(Text, nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<StrategyTemplate {self.name}>"
```

### Update Database Base

Add to `backend/app/db/base.py`:

```python
from app.models.strategy_template import StrategyTemplate
```

### Create Migration

```bash
cd backend
alembic revision --autogenerate -m "Add strategy_templates table"
alembic upgrade head
```

---

## PHASE 2: Seed Strategy Templates

Create file: `backend/scripts/seed_strategies.py`

```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.strategy_template import StrategyTemplate, RiskLevel

STRATEGY_TEMPLATES = [
    # ==================== BULLISH STRATEGIES ====================
    {
        "name": "bull_call_spread",
        "display_name": "Bull Call Spread",
        "category": "bullish",
        "description": "A vertical spread where you buy a call at a lower strike and sell a call at a higher strike. This is a debit spread with limited risk and limited profit potential.",
        "short_description": "Buy lower call, sell higher call. Limited risk bullish play.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 0, "quantity": 1},
            {"type": "CE", "position": "SELL", "strike_offset": 200, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 1,
        "risk_level": RiskLevel.LOW,
        "market_outlook": ["mild_bullish", "strong_bullish"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 50",
        "ideal_dte": "30-45 days",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability_base": 45.0,
        "popularity_score": 85,
        "when_to_use": [
            "You expect moderate upward movement",
            "IV is relatively low (options are cheap)",
            "You want defined risk",
            "You have a price target for the underlying"
        ],
        "when_to_avoid": [
            "You expect a very large move (buy call instead)",
            "IV is very high",
            "Market is extremely volatile"
        ],
        "pros": [
            "Limited and known maximum loss",
            "Lower cost than buying calls outright",
            "Defined risk/reward ratio",
            "Benefits from rising prices"
        ],
        "cons": [
            "Limited profit potential",
            "Requires directional move to profit",
            "Time decay works against you",
            "Both legs can expire worthless"
        ],
        "common_mistakes": [
            "Setting strike widths too wide (reduces probability)",
            "Not exiting when target price is reached",
            "Holding through expiry unnecessarily",
            "Trading when IV is too high"
        ],
        "adjustment_guide": "If underlying moves against you: Consider rolling down the long call to reduce cost basis. If underlying moves in your favor: Consider taking profits at 50-75% of max profit rather than waiting for expiry.",
        "exit_rules": [
            "Exit at 50% of max profit",
            "Exit if underlying breaks below support",
            "Exit 7-10 days before expiry if not profitable"
        ],
        "example_setup": "NIFTY at 26000. Buy 26000 CE at ₹150, Sell 26200 CE at ₹80. Net debit: ₹70 (₹5,250 for 1 lot). Max profit: ₹130 (₹9,750).",
        "example_outcome": "NIFTY closes at 26200+. Both calls expire ITM. Profit: ₹9,750 per lot."
    },
    {
        "name": "bull_put_spread",
        "display_name": "Bull Put Spread",
        "category": "bullish",
        "description": "A credit spread where you sell a put at a higher strike and buy a put at a lower strike. Profits if the underlying stays above the short put strike.",
        "short_description": "Sell higher put, buy lower put. Credit spread for bullish bias.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "PE", "position": "BUY", "strike_offset": -200, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 1,
        "risk_level": RiskLevel.LOW,
        "market_outlook": ["mild_bullish", "neutral"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability_base": 65.0,
        "popularity_score": 92,
        "when_to_use": [
            "You're mildly bullish or neutral",
            "You want time decay on your side",
            "IV is elevated (higher premiums)",
            "Strong support level exists below"
        ],
        "when_to_avoid": [
            "You expect a large downward move",
            "IV is very low",
            "No clear support levels"
        ],
        "pros": [
            "Time decay works in your favor",
            "Can profit even if underlying doesn't move",
            "High probability of profit",
            "Receive credit upfront"
        ],
        "cons": [
            "Limited profit potential",
            "Risk is greater than potential reward",
            "Requires margin",
            "Assignment risk on short put"
        ],
        "common_mistakes": [
            "Selling strikes too close to current price",
            "Not adjusting when position is tested",
            "Over-leveraging due to high win rate",
            "Ignoring earnings or events"
        ],
        "adjustment_guide": "If put side is tested: Roll the entire spread down and out to a further expiry. If profitable early: Consider closing at 50% profit rather than waiting.",
        "exit_rules": [
            "Exit at 50% of max profit",
            "Exit if short put goes ITM",
            "Exit if loss reaches 1.5x the credit received"
        ],
        "example_setup": "NIFTY at 26000. Sell 25800 PE at ₹60, Buy 25600 PE at ₹35. Net credit: ₹25 (₹1,875). Max loss: ₹175 (₹13,125).",
        "example_outcome": "NIFTY stays above 25800. Both puts expire worthless. Profit: ₹1,875 per lot."
    },
    {
        "name": "synthetic_long",
        "display_name": "Synthetic Long",
        "category": "bullish",
        "description": "Buy ATM call and sell ATM put. Mimics holding the underlying asset with less capital but unlimited risk.",
        "short_description": "Buy call + sell put at same strike. Mimics long underlying.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 0, "quantity": 1},
            {"type": "PE", "position": "SELL", "strike_offset": 0, "quantity": 1}
        ],
        "max_profit": "Unlimited",
        "max_loss": "Unlimited",
        "breakeven_count": 1,
        "risk_level": RiskLevel.HIGH,
        "market_outlook": ["strong_bullish"],
        "volatility_preference": "any",
        "ideal_iv_percentile": "Any",
        "ideal_dte": "Monthly",
        "theta_positive": False,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability_base": 50.0,
        "popularity_score": 60,
        "when_to_use": [
            "You're very bullish",
            "You want leveraged exposure",
            "You believe in strong upside move"
        ],
        "when_to_avoid": [
            "You're uncertain about direction",
            "You can't handle unlimited downside risk"
        ],
        "pros": [
            "Unlimited upside potential",
            "Lower capital than buying underlying",
            "Near-zero cost if premiums match"
        ],
        "cons": [
            "Unlimited downside risk",
            "High margin requirement",
            "Assignment risk on short put"
        ],
        "common_mistakes": [
            "Underestimating downside risk",
            "Not having stop-loss",
            "Over-leveraging"
        ],
        "exit_rules": [
            "Exit if underlying drops 3-5%",
            "Take profits on strong rally"
        ]
    },
    
    # ==================== BEARISH STRATEGIES ====================
    {
        "name": "bear_put_spread",
        "display_name": "Bear Put Spread",
        "category": "bearish",
        "description": "Buy a put at higher strike, sell a put at lower strike. Debit spread that profits from declining prices.",
        "short_description": "Buy higher put, sell lower put. Limited risk bearish play.",
        "legs_config": [
            {"type": "PE", "position": "BUY", "strike_offset": 0, "quantity": 1},
            {"type": "PE", "position": "SELL", "strike_offset": -200, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 1,
        "risk_level": RiskLevel.LOW,
        "market_outlook": ["mild_bearish", "strong_bearish"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 50",
        "ideal_dte": "30-45 days",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability_base": 45.0,
        "popularity_score": 80,
        "when_to_use": [
            "You expect moderate downward movement",
            "IV is relatively low",
            "You want defined risk",
            "Clear resistance level above"
        ],
        "when_to_avoid": [
            "You expect a very large drop",
            "IV is very high",
            "Strong uptrend is in place"
        ],
        "pros": [
            "Limited and known risk",
            "Cheaper than buying puts outright",
            "Benefits from falling prices"
        ],
        "cons": [
            "Limited profit potential",
            "Requires directional move",
            "Time decay hurts"
        ],
        "common_mistakes": [
            "Fighting strong uptrends",
            "Setting strikes too narrow",
            "Holding too long in losing trade"
        ],
        "exit_rules": [
            "Exit at 50% of max profit",
            "Exit if underlying breaks above resistance"
        ]
    },
    {
        "name": "bear_call_spread",
        "display_name": "Bear Call Spread",
        "category": "bearish",
        "description": "Sell a call at lower strike, buy a call at higher strike. Credit spread for bearish or neutral outlook.",
        "short_description": "Sell lower call, buy higher call. Credit spread for bearish bias.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 1,
        "risk_level": RiskLevel.LOW,
        "market_outlook": ["mild_bearish", "neutral"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability_base": 65.0,
        "popularity_score": 88,
        "when_to_use": [
            "You're mildly bearish or neutral",
            "Strong resistance level exists above",
            "IV is elevated"
        ],
        "when_to_avoid": [
            "You expect a breakout",
            "IV is very low"
        ],
        "pros": [
            "Time decay works for you",
            "Can profit if market stays flat",
            "Receive credit upfront",
            "Defined risk"
        ],
        "cons": [
            "Limited profit",
            "Requires margin",
            "Risk exceeds reward"
        ],
        "common_mistakes": [
            "Selling too close to current price",
            "Ignoring breakout signals"
        ],
        "exit_rules": [
            "Exit at 50% profit",
            "Exit if short call goes ITM"
        ]
    },
    {
        "name": "synthetic_short",
        "display_name": "Synthetic Short",
        "category": "bearish",
        "description": "Sell ATM call and buy ATM put. Mimics shorting the underlying asset with unlimited risk to upside.",
        "short_description": "Sell call + buy put at same strike. Mimics short underlying.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "PE", "position": "BUY", "strike_offset": 0, "quantity": 1}
        ],
        "max_profit": "Unlimited (downside)",
        "max_loss": "Unlimited (upside)",
        "breakeven_count": 1,
        "risk_level": RiskLevel.HIGH,
        "market_outlook": ["strong_bearish"],
        "volatility_preference": "any",
        "ideal_iv_percentile": "Any",
        "ideal_dte": "Monthly",
        "theta_positive": False,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability_base": 50.0,
        "popularity_score": 55,
        "when_to_use": [
            "You're very bearish",
            "You want leveraged short exposure",
            "You expect a crash"
        ],
        "when_to_avoid": [
            "Market is in uptrend",
            "You can't handle unlimited upside risk"
        ],
        "pros": [
            "Unlimited profit potential on downside",
            "Lower capital than shorting futures",
            "Near-zero cost if premiums match"
        ],
        "cons": [
            "Unlimited upside risk",
            "High margin requirement"
        ],
        "common_mistakes": [
            "Fighting the trend",
            "Not having stop-loss"
        ],
        "exit_rules": [
            "Exit if underlying rallies 3-5%",
            "Take profits on crash"
        ]
    },
    
    # ==================== NEUTRAL STRATEGIES ====================
    {
        "name": "iron_condor",
        "display_name": "Iron Condor",
        "category": "neutral",
        "description": "Sell an OTM put spread and an OTM call spread simultaneously. Profits when the underlying stays within a defined range.",
        "short_description": "Sell OTM strangle + buy wings. Range-bound income strategy.",
        "legs_config": [
            {"type": "PE", "position": "BUY", "strike_offset": -400, "quantity": 1},
            {"type": "PE", "position": "SELL", "strike_offset": -200, "quantity": 1},
            {"type": "CE", "position": "SELL", "strike_offset": 200, "quantity": 1},
            {"type": "CE", "position": "BUY", "strike_offset": 400, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["neutral"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "medium",
        "win_probability_base": 68.0,
        "popularity_score": 95,
        "when_to_use": [
            "Market is range-bound",
            "IV is elevated",
            "No major events expected",
            "Clear support/resistance levels exist",
            "You want defined risk"
        ],
        "when_to_avoid": [
            "Big move expected (earnings, events)",
            "IV is very low",
            "Strong trend is in place"
        ],
        "pros": [
            "High probability of profit (68%+)",
            "Defined risk on both sides",
            "Benefits from time decay",
            "Benefits from IV crush",
            "Works in sideways markets"
        ],
        "cons": [
            "Limited profit potential",
            "Requires active management",
            "Multiple legs = more commissions",
            "Wide bid-ask spreads can hurt entry/exit"
        ],
        "common_mistakes": [
            "Setting wings too narrow (reduces probability)",
            "Not adjusting when one side is tested",
            "Holding to expiry when already profitable",
            "Trading in low IV environment",
            "Over-sizing positions"
        ],
        "adjustment_guide": "If put side tested: Roll put spread down and/or out. If call side tested: Roll call spread up and/or out. If IV spikes: Consider closing early for profit. At 50% profit: Strongly consider closing.",
        "exit_rules": [
            "Exit at 50% of max profit",
            "Exit if either short strike is breached",
            "Exit 7-10 days before expiry",
            "Exit if loss reaches 2x the credit"
        ],
        "example_setup": "NIFTY at 26000. Sell 25800/25600 PE spread + Sell 26200/26400 CE spread. Net credit: ₹30 (₹2,250). Max loss: ₹170 (₹12,750).",
        "example_outcome": "NIFTY closes at 26000. All options expire worthless. Profit: ₹2,250 per lot."
    },
    {
        "name": "iron_butterfly",
        "display_name": "Iron Butterfly",
        "category": "neutral",
        "description": "Sell ATM straddle and buy OTM strangle for protection. Maximum profit if underlying pins exactly to the strike.",
        "short_description": "Sell ATM straddle + buy wings. Max profit at strike.",
        "legs_config": [
            {"type": "PE", "position": "BUY", "strike_offset": -200, "quantity": 1},
            {"type": "PE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["neutral"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 60",
        "ideal_dte": "Weekly or expiry day",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability_base": 40.0,
        "popularity_score": 75,
        "when_to_use": [
            "You expect underlying to pin to specific strike",
            "IV is very high",
            "Expiry is near (weekly expiry plays)",
            "Max pain aligns with your strike"
        ],
        "when_to_avoid": [
            "Market is trending",
            "Big move expected",
            "Far from expiry"
        ],
        "pros": [
            "Higher max profit than iron condor",
            "Defined risk",
            "Great for expiry day trades"
        ],
        "cons": [
            "Lower probability than iron condor",
            "Very narrow profit zone",
            "Requires precise timing"
        ],
        "common_mistakes": [
            "Choosing strike far from max pain",
            "Trading too far from expiry",
            "Not closing at target profit"
        ],
        "exit_rules": [
            "Exit at 25-50% of max profit",
            "Exit if underlying moves more than 1%"
        ]
    },
    {
        "name": "short_straddle",
        "display_name": "Short Straddle",
        "category": "neutral",
        "description": "Sell ATM call and ATM put. Maximum premium collection strategy with unlimited risk on both sides.",
        "short_description": "Sell ATM call + put. High premium, unlimited risk.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "PE", "position": "SELL", "strike_offset": 0, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Unlimited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.HIGH,
        "market_outlook": ["neutral"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 70",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "very_high",
        "win_probability_base": 45.0,
        "popularity_score": 70,
        "when_to_use": [
            "You expect very low movement",
            "IV is extremely high (pre-earnings crush)",
            "You can actively manage",
            "You have sufficient capital and risk tolerance"
        ],
        "when_to_avoid": [
            "Big move expected",
            "You can't monitor actively",
            "IV is low or normal"
        ],
        "pros": [
            "Maximum theta collection",
            "Profits from IV crush",
            "Higher premium than strangle"
        ],
        "cons": [
            "Unlimited risk on both sides",
            "Very high margin requirement",
            "Needs active management",
            "Stressful to hold overnight"
        ],
        "common_mistakes": [
            "Not having stop loss plan",
            "Over-sizing positions",
            "Holding through events/earnings"
        ],
        "exit_rules": [
            "Exit at 25% profit",
            "Exit if underlying moves 1.5-2%",
            "Always have stop loss"
        ]
    },
    {
        "name": "short_strangle",
        "display_name": "Short Strangle",
        "category": "neutral",
        "description": "Sell OTM call and OTM put. Wider profit zone than straddle but with unlimited risk.",
        "short_description": "Sell OTM call + put. Wide profit zone, unlimited risk.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 200, "quantity": 1},
            {"type": "PE", "position": "SELL", "strike_offset": -200, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Unlimited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.HIGH,
        "market_outlook": ["neutral"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability_base": 68.0,
        "popularity_score": 90,
        "when_to_use": [
            "Market is range-bound",
            "IV is elevated",
            "Strong support/resistance levels exist",
            "You have margin for naked positions"
        ],
        "when_to_avoid": [
            "Big move expected",
            "IV is low",
            "You don't have stop-loss discipline"
        ],
        "pros": [
            "High probability of profit",
            "Wide profit zone",
            "Great theta decay",
            "Flexible strike selection"
        ],
        "cons": [
            "Unlimited risk both sides",
            "High margin requirement",
            "Requires constant monitoring"
        ],
        "common_mistakes": [
            "Selling strikes too close to spot",
            "Not having exit plan for gap moves",
            "Ignoring IV changes"
        ],
        "exit_rules": [
            "Exit at 50% profit",
            "Exit if either short goes ITM",
            "Always have mental stop"
        ]
    },
    {
        "name": "jade_lizard",
        "display_name": "Jade Lizard",
        "category": "neutral",
        "description": "Sell OTM put + bear call spread. Structured so there's no risk to the upside if done correctly.",
        "short_description": "Short put + bear call spread. No upside risk if structured right.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -100, "quantity": 1},
            {"type": "CE", "position": "SELL", "strike_offset": 100, "quantity": 1},
            {"type": "CE", "position": "BUY", "strike_offset": 300, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited (downside only)",
        "breakeven_count": 1,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["neutral", "mild_bullish"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "medium",
        "win_probability_base": 72.0,
        "popularity_score": 78,
        "when_to_use": [
            "Bullish bias but want neutral exposure",
            "Want to eliminate upside risk",
            "IV is elevated"
        ],
        "when_to_avoid": [
            "Strongly bearish",
            "Can't afford downside loss"
        ],
        "pros": [
            "No risk to upside (if structured correctly)",
            "High probability of profit",
            "Theta positive"
        ],
        "cons": [
            "Full downside risk on put",
            "Complex structure",
            "Lower premium than pure strangle"
        ],
        "common_mistakes": [
            "Not ensuring call credit > put credit",
            "Setting up for net debit",
            "Ignoring downside risk"
        ],
        "exit_rules": [
            "Exit at 50% profit",
            "Manage downside put like a naked put"
        ]
    },
    
    # ==================== VOLATILE STRATEGIES ====================
    {
        "name": "long_straddle",
        "display_name": "Long Straddle",
        "category": "volatile",
        "description": "Buy ATM call and ATM put. Profits from a big move in either direction. Best when IV is low.",
        "short_description": "Buy ATM call + put. Profits from big move either direction.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 0, "quantity": 1},
            {"type": "PE", "position": "BUY", "strike_offset": 0, "quantity": 1}
        ],
        "max_profit": "Unlimited",
        "max_loss": "Limited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["volatile"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 30",
        "ideal_dte": "30-45 days",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability_base": 35.0,
        "popularity_score": 75,
        "when_to_use": [
            "Big move expected (earnings, RBI, elections)",
            "IV is low (options are cheap)",
            "Direction is uncertain but magnitude expected",
            "Before major news events"
        ],
        "when_to_avoid": [
            "IV is already high (options expensive)",
            "Market is range-bound",
            "No catalyst in sight"
        ],
        "pros": [
            "Unlimited profit potential",
            "Profits from IV expansion",
            "No directional bias needed",
            "Limited and known risk"
        ],
        "cons": [
            "Expensive (buying two ATM options)",
            "Time decay hurts aggressively",
            "Needs big move to profit",
            "Low probability of profit"
        ],
        "common_mistakes": [
            "Buying when IV is already high",
            "Holding too long (time decay)",
            "Not sizing position properly",
            "Expecting profit from small moves"
        ],
        "exit_rules": [
            "Exit on big move (don't get greedy)",
            "Exit before event if IV has risen",
            "Exit if no move after event"
        ]
    },
    {
        "name": "long_strangle",
        "display_name": "Long Strangle",
        "category": "volatile",
        "description": "Buy OTM call and OTM put. Cheaper than straddle but needs a bigger move to profit.",
        "short_description": "Buy OTM call + put. Cheaper bet on big move.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 1},
            {"type": "PE", "position": "BUY", "strike_offset": -200, "quantity": 1}
        ],
        "max_profit": "Unlimited",
        "max_loss": "Limited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["volatile"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 30",
        "ideal_dte": "30-45 days",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "medium",
        "win_probability_base": 28.0,
        "popularity_score": 70,
        "when_to_use": [
            "Expecting very big move",
            "IV is very low",
            "Want cheaper alternative to straddle"
        ],
        "when_to_avoid": [
            "IV is high",
            "Small move expected",
            "Close to expiry"
        ],
        "pros": [
            "Cheaper than straddle",
            "Unlimited profit potential",
            "Lower capital requirement"
        ],
        "cons": [
            "Needs bigger move than straddle",
            "Lower probability of profit",
            "Both options can expire worthless",
            "Time decay still hurts"
        ],
        "common_mistakes": [
            "Buying too far OTM",
            "Trading when IV is high",
            "Not having profit target"
        ],
        "exit_rules": [
            "Exit on big move",
            "Exit if IV spikes without price move"
        ]
    },
    {
        "name": "reverse_iron_condor",
        "display_name": "Reverse Iron Condor",
        "category": "volatile",
        "description": "Buy OTM strangle and sell further OTM strangle. Profits from big moves with limited risk and limited reward.",
        "short_description": "Buy inner strangle, sell outer strangle. Defined risk volatility bet.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -400, "quantity": 1},
            {"type": "PE", "position": "BUY", "strike_offset": -200, "quantity": 1},
            {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 1},
            {"type": "CE", "position": "SELL", "strike_offset": 400, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["volatile"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 30",
        "ideal_dte": "30-45 days",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "medium",
        "win_probability_base": 32.0,
        "popularity_score": 55,
        "when_to_use": [
            "Big move expected",
            "Want defined risk volatility play",
            "IV is low"
        ],
        "when_to_avoid": [
            "Market is range-bound",
            "IV is high"
        ],
        "pros": [
            "Defined risk and reward",
            "Profits from big moves",
            "Cheaper than long strangle"
        ],
        "cons": [
            "Limited profit even on big moves",
            "Low probability",
            "Complex structure"
        ],
        "exit_rules": [
            "Exit if underlying reaches outer strikes",
            "Exit before expiry"
        ]
    },
    
    # ==================== INCOME STRATEGIES ====================
    {
        "name": "covered_call",
        "display_name": "Covered Call",
        "category": "income",
        "description": "Own underlying (or futures) and sell OTM call against it. Generate income while holding.",
        "short_description": "Hold stock + sell OTM call. Income from holdings.",
        "legs_config": [
            {"type": "UNDERLYING", "position": "BUY", "strike_offset": 0, "quantity": 1},
            {"type": "CE", "position": "SELL", "strike_offset": 200, "quantity": 1}
        ],
        "max_profit": "Limited",
        "max_loss": "Large (stock can go to zero)",
        "breakeven_count": 1,
        "risk_level": RiskLevel.LOW,
        "market_outlook": ["neutral", "mild_bullish"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability_base": 70.0,
        "popularity_score": 85,
        "when_to_use": [
            "You own the underlying",
            "You're neutral to mildly bullish",
            "You want income from holdings",
            "You're okay capping upside"
        ],
        "when_to_avoid": [
            "You expect large upside move",
            "You're bearish"
        ],
        "pros": [
            "Generate income from holdings",
            "Reduces cost basis",
            "High probability strategy"
        ],
        "cons": [
            "Caps your upside",
            "Still have full downside risk",
            "May get called away"
        ],
        "exit_rules": [
            "Roll if approaching expiry in profit",
            "Let expire worthless if OTM"
        ]
    },
    {
        "name": "cash_secured_put",
        "display_name": "Cash Secured Put",
        "category": "income",
        "description": "Sell OTM put with cash to buy stock if assigned. Get paid to wait to buy at lower prices.",
        "short_description": "Sell put with cash reserve. Get paid to wait for lower prices.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -200, "quantity": 1}
        ],
        "max_profit": "Limited (premium received)",
        "max_loss": "Large (stock to zero)",
        "breakeven_count": 1,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["neutral", "mild_bullish"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability_base": 70.0,
        "popularity_score": 82,
        "when_to_use": [
            "You want to buy the stock at lower price",
            "You have cash to secure the put",
            "You're bullish but patient"
        ],
        "when_to_avoid": [
            "You don't want to own the stock",
            "You're bearish"
        ],
        "pros": [
            "Get paid to wait",
            "Buy at discount if assigned",
            "High probability"
        ],
        "cons": [
            "Full downside if stock crashes",
            "Ties up capital",
            "May miss rally"
        ],
        "exit_rules": [
            "Let expire if OTM",
            "Roll if tested"
        ]
    },
    {
        "name": "wheel_strategy",
        "display_name": "Wheel Strategy",
        "category": "income",
        "description": "Cycle between cash secured puts and covered calls. Sell puts until assigned, then sell calls until called away.",
        "short_description": "CSP → Covered Call → Repeat. Continuous income cycle.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": -100, "quantity": 1, "phase": "put_phase"}
        ],
        "max_profit": "Unlimited (over time)",
        "max_loss": "Large (stock to zero)",
        "breakeven_count": 1,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["neutral", "mild_bullish"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 40",
        "ideal_dte": "30-45 days",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": False,
        "gamma_risk": "low",
        "win_probability_base": 75.0,
        "popularity_score": 88,
        "when_to_use": [
            "You're okay owning the underlying",
            "You want consistent income",
            "You have long-term horizon"
        ],
        "when_to_avoid": [
            "You don't like the underlying",
            "Stock is in downtrend"
        ],
        "pros": [
            "Consistent income",
            "Works in multiple market conditions",
            "Can accumulate shares at discount"
        ],
        "cons": [
            "Can be stuck with falling stock",
            "Requires patience",
            "Ties up capital"
        ],
        "exit_rules": [
            "Keep cycling through phases",
            "Stop if thesis changes"
        ]
    },
    
    # ==================== ADVANCED STRATEGIES ====================
    {
        "name": "calendar_spread",
        "display_name": "Calendar Spread",
        "category": "advanced",
        "description": "Sell near-term option, buy same strike further-term option. Profits from time decay differential and IV changes.",
        "short_description": "Sell near expiry, buy far expiry at same strike. Time spread.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1, "expiry": "near"},
            {"type": "CE", "position": "BUY", "strike_offset": 0, "quantity": 1, "expiry": "far"}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["neutral"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 50 for back month",
        "ideal_dte": "Near: Weekly, Far: Monthly",
        "theta_positive": True,
        "vega_positive": True,
        "delta_neutral": True,
        "gamma_risk": "medium",
        "win_probability_base": 50.0,
        "popularity_score": 65,
        "when_to_use": [
            "Expect underlying to stay near strike",
            "Near-term IV higher than far-term",
            "Want to profit from IV term structure"
        ],
        "when_to_avoid": [
            "Big move expected",
            "IV is inverted (far > near)"
        ],
        "pros": [
            "Profits from time decay differential",
            "Benefits from IV expansion in back month",
            "Defined risk"
        ],
        "cons": [
            "Complex P/L profile",
            "Gap risk between expiries",
            "Hard to manage"
        ],
        "common_mistakes": [
            "Wrong strike selection",
            "Not accounting for IV skew",
            "Holding through near expiry"
        ],
        "exit_rules": [
            "Exit before near-term expiry",
            "Exit if underlying moves away from strike"
        ]
    },
    {
        "name": "diagonal_spread",
        "display_name": "Diagonal Spread",
        "category": "advanced",
        "description": "Like calendar spread but with different strikes. Sell near-term OTM, buy far-term ATM/ITM. Directional time spread.",
        "short_description": "Calendar spread with different strikes. Directional time spread.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 200, "quantity": 1, "expiry": "near"},
            {"type": "CE", "position": "BUY", "strike_offset": 0, "quantity": 1, "expiry": "far"}
        ],
        "max_profit": "Limited",
        "max_loss": "Limited",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["mild_bullish"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 50",
        "ideal_dte": "Near: Weekly, Far: 45+ days",
        "theta_positive": True,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "medium",
        "win_probability_base": 55.0,
        "popularity_score": 60,
        "when_to_use": [
            "Mildly bullish with time",
            "Want LEAPS with reduced cost",
            "Poor man's covered call"
        ],
        "when_to_avoid": [
            "Expecting quick move",
            "Strongly directional"
        ],
        "pros": [
            "Lower cost than owning stock",
            "Theta positive if managed right",
            "Flexible adjustments"
        ],
        "cons": [
            "Complex management",
            "Assignment risk on short leg"
        ],
        "exit_rules": [
            "Roll short leg at expiry",
            "Close if long leg loses 50%"
        ]
    },
    {
        "name": "butterfly_spread",
        "display_name": "Butterfly Spread",
        "category": "advanced",
        "description": "Buy 1 ITM, sell 2 ATM, buy 1 OTM. Max profit at middle strike. Low cost, high reward if pinned.",
        "short_description": "Buy wings, sell body. Max profit at center strike.",
        "legs_config": [
            {"type": "CE", "position": "BUY", "strike_offset": -200, "quantity": 1},
            {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 2},
            {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 1}
        ],
        "max_profit": "Limited (but high relative to cost)",
        "max_loss": "Limited (net debit)",
        "breakeven_count": 2,
        "risk_level": RiskLevel.LOW,
        "market_outlook": ["neutral"],
        "volatility_preference": "high",
        "ideal_iv_percentile": "Above 50",
        "ideal_dte": "Weekly (expiry plays)",
        "theta_positive": True,
        "vega_positive": False,
        "delta_neutral": True,
        "gamma_risk": "high",
        "win_probability_base": 35.0,
        "popularity_score": 72,
        "when_to_use": [
            "Expect underlying to pin to strike",
            "Expiry day plays",
            "Low cost speculation"
        ],
        "when_to_avoid": [
            "Big move expected",
            "Far from expiry"
        ],
        "pros": [
            "Very low cost",
            "High reward if pinned",
            "Defined risk"
        ],
        "cons": [
            "Low probability",
            "Narrow profit zone",
            "Needs precise timing"
        ],
        "exit_rules": [
            "Exit at 50%+ profit",
            "Exit if underlying moves away"
        ]
    },
    {
        "name": "ratio_backspread_call",
        "display_name": "Call Ratio Backspread",
        "category": "advanced",
        "description": "Sell 1 ATM call, buy 2 OTM calls. Unlimited upside profit, limited downside risk. Best for strong bullish view.",
        "short_description": "Sell 1 call, buy 2 higher calls. Unlimited upside.",
        "legs_config": [
            {"type": "CE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "CE", "position": "BUY", "strike_offset": 200, "quantity": 2}
        ],
        "max_profit": "Unlimited (upside)",
        "max_loss": "Limited (between strikes)",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["strong_bullish"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 30",
        "ideal_dte": "45+ days",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability_base": 40.0,
        "popularity_score": 58,
        "when_to_use": [
            "Strongly bullish",
            "Expecting big upward move",
            "IV is low"
        ],
        "when_to_avoid": [
            "Expecting small move",
            "High IV environment"
        ],
        "pros": [
            "Unlimited upside profit",
            "Can be done for credit",
            "Benefits from IV rise"
        ],
        "cons": [
            "Loss zone between strikes",
            "Needs big move"
        ],
        "exit_rules": [
            "Exit on big rally",
            "Exit if stuck in loss zone"
        ]
    },
    {
        "name": "ratio_backspread_put",
        "display_name": "Put Ratio Backspread",
        "category": "advanced",
        "description": "Sell 1 ATM put, buy 2 OTM puts. Unlimited downside profit potential. Best for crash protection.",
        "short_description": "Sell 1 put, buy 2 lower puts. Crash protection.",
        "legs_config": [
            {"type": "PE", "position": "SELL", "strike_offset": 0, "quantity": 1},
            {"type": "PE", "position": "BUY", "strike_offset": -200, "quantity": 2}
        ],
        "max_profit": "Unlimited (downside)",
        "max_loss": "Limited (between strikes)",
        "breakeven_count": 2,
        "risk_level": RiskLevel.MEDIUM,
        "market_outlook": ["strong_bearish"],
        "volatility_preference": "low",
        "ideal_iv_percentile": "Below 30",
        "ideal_dte": "45+ days",
        "theta_positive": False,
        "vega_positive": True,
        "delta_neutral": False,
        "gamma_risk": "high",
        "win_probability_base": 40.0,
        "popularity_score": 55,
        "when_to_use": [
            "Expecting crash",
            "Want portfolio protection",
            "IV is low"
        ],
        "when_to_avoid": [
            "Expecting small decline",
            "High IV"
        ],
        "pros": [
            "Massive profit potential on crash",
            "Can be free or credit",
            "Great hedge"
        ],
        "cons": [
            "Loss zone if small decline",
            "Needs big move"
        ],
        "exit_rules": [
            "Hold through crash",
            "Exit if mild decline"
        ]
    }
]


async def seed_strategies():
    """Seed the strategy templates into database"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for template_data in STRATEGY_TEMPLATES:
            # Check if exists
            existing = await session.execute(
                select(StrategyTemplate).where(StrategyTemplate.name == template_data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"Skipping {template_data['name']} - already exists")
                continue
            
            template = StrategyTemplate(**template_data)
            session.add(template)
            print(f"Added {template_data['name']}")
        
        await session.commit()
        print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_strategies())
```

---

## PHASE 3: Strategy Wizard API

Create file: `backend/app/api/routes/strategy_wizard.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from pydantic import BaseModel

from app.db.session import get_db
from app.models.strategy_template import StrategyTemplate, RiskLevel
from app.api.deps import get_current_user
from app.core.kite import get_kite_client

router = APIRouter()

# Lot sizes for Indian indices
LOT_SIZES = {"NIFTY": 75, "BANKNIFTY": 15, "FINNIFTY": 25, "SENSEX": 10}
STRIKE_STEPS = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50, "SENSEX": 100}


class WizardInput(BaseModel):
    outlook: str  # strong_bullish, mild_bullish, neutral, mild_bearish, strong_bearish, volatile
    volatility: str  # low, normal, high
    risk: str  # low, medium, high
    capital: Optional[float] = None


class DeployRequest(BaseModel):
    template_name: str
    underlying: str
    expiry: str
    lots: int = 1
    custom_strikes: Optional[dict] = None  # Optional strike overrides


@router.get("/templates")
async def get_all_templates(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all strategy templates with optional filtering"""
    query = select(StrategyTemplate).where(StrategyTemplate.is_active == True)
    
    if category:
        query = query.where(StrategyTemplate.category == category)
    
    if search:
        query = query.where(
            StrategyTemplate.display_name.ilike(f"%{search}%") |
            StrategyTemplate.description.ilike(f"%{search}%")
        )
    
    query = query.order_by(StrategyTemplate.popularity_score.desc())
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return {"templates": [t.__dict__ for t in templates], "total": len(templates)}


@router.get("/templates/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all available categories with counts"""
    query = select(
        StrategyTemplate.category,
        func.count(StrategyTemplate.id).label("count")
    ).where(StrategyTemplate.is_active == True).group_by(StrategyTemplate.category)
    
    result = await db.execute(query)
    categories = result.all()
    
    category_info = {
        "bullish": {"icon": "📈", "color": "#00b386"},
        "bearish": {"icon": "📉", "color": "#e74c3c"},
        "neutral": {"icon": "➡️", "color": "#9c27b0"},
        "volatile": {"icon": "🌋", "color": "#ff9800"},
        "income": {"icon": "💰", "color": "#2196f3"},
        "advanced": {"icon": "🎓", "color": "#607d8b"}
    }
    
    return {
        "categories": [
            {"name": cat, "count": count, **category_info.get(cat, {})}
            for cat, count in categories
        ]
    }


@router.post("/wizard")
async def strategy_wizard(inputs: WizardInput, db: AsyncSession = Depends(get_db)):
    """AI-powered strategy recommendation based on user inputs"""
    
    outlook_map = {
        "strong_bullish": ["strong_bullish"],
        "mild_bullish": ["mild_bullish", "neutral"],
        "neutral": ["neutral"],
        "mild_bearish": ["mild_bearish", "neutral"],
        "strong_bearish": ["strong_bearish"],
        "volatile": ["volatile"]
    }
    
    suitable_outlooks = outlook_map.get(inputs.outlook, [inputs.outlook])
    
    query = select(StrategyTemplate).where(StrategyTemplate.is_active == True)
    result = await db.execute(query)
    templates = result.scalars().all()
    
    scored_strategies = []
    
    for template in templates:
        score = 0
        reasons = []
        
        # Outlook match (40 points)
        template_outlooks = template.market_outlook or []
        if any(o in template_outlooks for o in suitable_outlooks):
            score += 40
            reasons.append(f"✓ Matches your {inputs.outlook.replace('_', ' ')} outlook")
        
        # Volatility match (25 points)
        vol_pref = template.volatility_preference or "any"
        if vol_pref == "any" or vol_pref == inputs.volatility:
            score += 25 if vol_pref == inputs.volatility else 15
            if vol_pref == inputs.volatility:
                reasons.append(f"✓ Ideal for {inputs.volatility} volatility")
        
        # Risk match (25 points)
        template_risk = template.risk_level.value if template.risk_level else "medium"
        if template_risk == inputs.risk:
            score += 25
            reasons.append(f"✓ Matches your {inputs.risk} risk tolerance")
        
        # Bonus points
        if template.theta_positive and inputs.volatility == "high":
            score += 8
            reasons.append("✓ Time decay works in your favor")
        
        if score > 20:
            scored_strategies.append({
                "template": template.__dict__,
                "score": score,
                "match_percentage": min(int(score), 100),
                "reasons": reasons
            })
    
    scored_strategies.sort(key=lambda x: x["score"], reverse=True)
    
    return {"recommendations": scored_strategies[:5], "inputs": inputs.dict()}


@router.get("/templates/{name}")
async def get_template_details(name: str, db: AsyncSession = Depends(get_db)):
    """Get full details of a specific strategy template"""
    query = select(StrategyTemplate).where(StrategyTemplate.name == name)
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Strategy template not found")
    
    return {"template": template.__dict__}


@router.post("/deploy")
async def deploy_strategy(
    request: DeployRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Deploy a strategy template with real strikes and live prices"""
    
    query = select(StrategyTemplate).where(StrategyTemplate.name == request.template_name)
    result = await db.execute(query)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Strategy template not found")
    
    kite = await get_kite_client(current_user.id, db)
    
    underlying = request.underlying.upper()
    spot_symbol = f"NSE:NIFTY 50" if underlying == "NIFTY" else f"NSE:NIFTY BANK"
    
    try:
        quote = kite.quote([spot_symbol])
        spot_price = list(quote.values())[0]["last_price"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get spot price: {str(e)}")
    
    step = STRIKE_STEPS.get(underlying, 50)
    atm_strike = round(spot_price / step) * step
    lot_size = LOT_SIZES.get(underlying, 75)
    
    legs = []
    for i, leg_config in enumerate(template.legs_config):
        strike_offset = leg_config.get("strike_offset", 0)
        strike = atm_strike + strike_offset
        option_type = leg_config.get("type", "CE")
        position = leg_config.get("position", "BUY")
        
        if option_type == "UNDERLYING":
            continue
        
        trading_symbol = f"{underlying}{request.expiry}{int(strike)}{option_type}"
        
        try:
            option_quote = kite.quote([f"NFO:{trading_symbol}"])
            ltp = list(option_quote.values())[0]["last_price"]
        except:
            ltp = 0
        
        legs.append({
            "strike": strike,
            "contract_type": option_type,
            "transaction_type": "BUY" if position == "BUY" else "SELL",
            "lots": request.lots,
            "entry_price": ltp,
            "expiry_date": request.expiry,
            "trading_symbol": trading_symbol
        })
    
    return {
        "strategy_name": template.display_name,
        "underlying": underlying,
        "expiry": request.expiry,
        "spot_price": spot_price,
        "atm_strike": atm_strike,
        "legs": legs
    }


@router.get("/popular")
async def get_popular_strategies(limit: int = 5, db: AsyncSession = Depends(get_db)):
    """Get most popular strategies"""
    query = select(StrategyTemplate).where(
        StrategyTemplate.is_active == True
    ).order_by(StrategyTemplate.popularity_score.desc()).limit(limit)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return {"popular": [t.__dict__ for t in templates]}
```

---

## PHASE 4: Register Routes

Update `backend/app/api/routes/__init__.py`:

```python
from app.api.routes import strategy_wizard

api_router.include_router(
    strategy_wizard.router, 
    prefix="/strategy-wizard", 
    tags=["strategy-wizard"]
)
```

---

## PHASE 5: Frontend Store

Create file: `frontend/src/stores/strategyLibrary.js`

```javascript
import { defineStore } from 'pinia';
import api from '@/services/api';

export const useStrategyLibraryStore = defineStore('strategyLibrary', {
  state: () => ({
    templates: [],
    categories: [],
    selectedCategory: null,
    searchQuery: '',
    wizardStep: 1,
    wizardInputs: { outlook: null, volatility: null, risk: null },
    recommendations: [],
    templateDetails: null,
    isLoading: false,
    showWizard: false,
    showDetails: false,
    error: null
  }),
  
  getters: {
    filteredTemplates: (state) => {
      let result = state.templates;
      if (state.selectedCategory) {
        result = result.filter(t => t.category === state.selectedCategory);
      }
      if (state.searchQuery) {
        const q = state.searchQuery.toLowerCase();
        result = result.filter(t => 
          t.display_name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q)
        );
      }
      return result;
    },
    wizardComplete: (state) => {
      return state.wizardInputs.outlook && state.wizardInputs.volatility && state.wizardInputs.risk;
    }
  },
  
  actions: {
    async fetchTemplates() {
      this.isLoading = true;
      try {
        const response = await api.get('/api/strategy-wizard/templates');
        this.templates = response.data.templates;
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load';
      } finally {
        this.isLoading = false;
      }
    },
    
    async fetchCategories() {
      const response = await api.get('/api/strategy-wizard/templates/categories');
      this.categories = response.data.categories;
    },
    
    async fetchTemplateDetails(name) {
      this.isLoading = true;
      const response = await api.get(`/api/strategy-wizard/templates/${name}`);
      this.templateDetails = response.data.template;
      this.showDetails = true;
      this.isLoading = false;
    },
    
    async runWizard() {
      if (!this.wizardComplete) return;
      this.isLoading = true;
      const response = await api.post('/api/strategy-wizard/wizard', this.wizardInputs);
      this.recommendations = response.data.recommendations;
      this.showWizard = false;
      this.isLoading = false;
    },
    
    async deployStrategy(templateName, config) {
      const response = await api.post('/api/strategy-wizard/deploy', {
        template_name: templateName,
        ...config
      });
      return response.data;
    },
    
    resetWizard() {
      this.wizardStep = 1;
      this.wizardInputs = { outlook: null, volatility: null, risk: null };
      this.recommendations = [];
    }
  }
});
```

---

## PHASE 6: Add Route and Navigation

Update `frontend/src/router/index.js`:

```javascript
{
  path: '/strategies',
  name: 'StrategyLibrary',
  component: () => import('@/views/StrategyLibraryView.vue'),
  meta: { requiresAuth: true }
}
```

Update navigation in `KiteHeader.vue`:

```javascript
const navItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/optionchain', label: 'Option Chain' },
  { path: '/strategies', label: 'Strategies' },
  { path: '/strategy', label: 'Builder' },
  { path: '/positions', label: 'Positions' },
];
```

---

## Summary

### Files Created

| File | Description |
|------|-------------|
| `backend/app/models/strategy_templates.py` | Database model |
| `backend/scripts/seed_strategies.py` | 22 strategy templates |
| `backend/app/api/routes/strategy_wizard.py` | API endpoints (prefix: `/api/strategy-library/`) |
| `frontend/src/stores/strategyLibrary.js` | Pinia store |
| `frontend/src/views/StrategyLibraryView.vue` | Main view (uses KiteLayout wrapper) |
| `frontend/src/components/strategy/StrategyCard.vue` | Strategy card component |
| `frontend/src/components/strategy/StrategyWizardModal.vue` | Wizard modal |
| `frontend/src/components/strategy/StrategyDetailsModal.vue` | Details modal |
| `frontend/src/components/strategy/StrategyDeployModal.vue` | Deploy modal |
| `frontend/src/components/strategy/StrategyCompareModal.vue` | Compare modal |

### API Prefix

**Important**: The API routes use `/api/strategy-library/` prefix (not `/api/strategy-wizard/` as shown in examples above).

### Commands

```bash
cd backend
alembic revision --autogenerate -m "Add strategy_templates table"
alembic upgrade head
python scripts/seed_strategies.py
```

### Features

- 22 pre-built strategies with educational content
- 3-question AI wizard for recommendations
- One-click deploy with live prices
- Strategy comparison tool (compare 2-4 strategies side by side)
- Greeks indicators (θ+, ν+, Δ0)
- Win probability display
- Categorized by: Bullish, Bearish, Neutral, Volatile, Income, Advanced
- Consistent UI with KiteHeader navigation (via KiteLayout wrapper)
