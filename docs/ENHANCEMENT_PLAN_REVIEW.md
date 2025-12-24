# AlgoChanakya Enhancement Plan
## External Review Document

**Version**: 1.0
**Date**: December 2024
**Purpose**: Feature and usability review for stakeholders unfamiliar with the codebase

---

## Executive Summary

AlgoChanakya is an options trading platform for the Indian stock market (NSE F&O segment). This document outlines planned enhancements to transform the platform into a **fully automated, hands-off trading system** that helps users maximize profits while minimizing manual intervention.

### Current State
- Manual strategy creation and activation required daily
- Limited automation for entry/exit timing
- Basic paper trading without analytics
- Single broker support (Zerodha)

### Target State
- **Set once, profit forever** - Strategies deploy automatically based on rules
- **Smart recommendations** - System suggests optimal strategies based on market conditions
- **Complete automation** - From entry to exit, minimal human intervention needed
- **Risk-free testing** - Full paper trading with performance analytics

---

## Design Principles

1. **Automation First**: Every feature should reduce manual steps
2. **Safety by Default**: Risk management features are always on, not optional
3. **Transparency**: Users always know what the system is doing and why
4. **Simplicity**: Complex features hidden behind simple interfaces
5. **No Lock-in**: Signal mode allows use with any broker

---

## Feature Roadmap

### PHASE 1: Core Automation (Critical)
*Goal: Enable true "set and forget" trading*

#### 1.1 Automation Rules Engine
**What it does**: Users define rules like "Every Monday at 9:20 AM, if market is calm, deploy Iron Condor on NIFTY"

**User Story**:
> As a trader, I want to set up a rule once and have the system automatically deploy my strategy every week, so I don't have to manually create strategies daily.

**Key Features**:
| Feature | Description |
|---------|-------------|
| Schedule-based deployment | Daily, weekly, monthly, or on expiry days |
| Market condition filters | Only deploy when VIX < 20, PCR is neutral, etc. |
| Auto-activation | Strategy starts monitoring immediately (no manual "Activate" click) |
| Holiday awareness | Skips NSE holidays automatically |
| Expiry selection | Auto-picks weekly or monthly expiry based on rule |

**Example Rules**:
- "Every Tuesday at 9:20 AM, deploy Short Strangle on BANKNIFTY if VIX < 18"
- "On monthly expiry -1 day, deploy Iron Condor on NIFTY"
- "Every day at 9:30 AM, deploy Bull Call Spread if NIFTY is up 0.5%"

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  Create Automation Rule                                      │
├─────────────────────────────────────────────────────────────┤
│  Rule Name: [Weekly Iron Condor                           ] │
│                                                             │
│  Strategy Template: [Iron Condor ▼]                         │
│  Underlying: [NIFTY ▼]                                      │
│                                                             │
│  Schedule:                                                  │
│  ○ Daily  ● Weekly  ○ Monthly  ○ Expiry Day                │
│  Days: [✓] Mon [ ] Tue [ ] Wed [ ] Thu [ ] Fri             │
│  Time: [09:20 AM]                                           │
│                                                             │
│  Market Conditions (optional):                              │
│  [✓] VIX below [18]                                        │
│  [✓] PCR between [0.8] and [1.2]                           │
│  [ ] Spot change less than [1%]                            │
│                                                             │
│  [✓] Auto-activate when deployed                           │
│                                                             │
│  [Cancel]                              [Create Rule]        │
└─────────────────────────────────────────────────────────────┘
```

---

#### 1.2 Position Sync with Broker
**What it does**: Automatically detects when user modifies positions outside the app (via broker's app/website) and updates accordingly.

**User Story**:
> As a trader, I want the system to know when I manually exit a position via my broker's app, so that AutoPilot doesn't think the position is still open.

**Problem it solves**:
- User exits a leg via Zerodha Kite app
- AlgoChanakya still shows the position as open
- System tries to exit again → error or double trade

**Key Features**:
| Feature | Description |
|---------|-------------|
| Real-time sync | Checks broker positions every 30 seconds |
| Mismatch detection | Alerts when positions don't match |
| Auto-reconciliation | Option to automatically match broker state |
| Audit trail | Logs all discrepancies for review |

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Position Mismatch Detected                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  AutoPilot shows: NIFTY 24500 CE - 50 qty                  │
│  Broker shows: NIFTY 24500 CE - 0 qty (exited)             │
│                                                             │
│  This position was likely exited via Kite app.              │
│                                                             │
│  [Sync Now]  [Ignore]  [View Details]                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

#### 1.3 Complete Paper Trading
**What it does**: Full simulation environment with virtual capital to test strategies without risking real money.

**User Story**:
> As a new trader, I want to test my automation rules with fake money first, so I can gain confidence before using real capital.

**Key Features**:
| Feature | Description |
|---------|-------------|
| Virtual capital | Start with ₹10 Lakh (configurable) |
| Realistic fills | Orders fill at market price with simulated slippage |
| Complete history | All paper trades logged with timestamps |
| Performance analytics | Win rate, P&L curve, drawdown, etc. |
| Easy toggle | Switch between paper/live with one click |
| Visual indicator | Clear "PAPER MODE" banner so user always knows |

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  🧪 PAPER TRADING MODE                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Virtual Capital: ₹10,00,000                               │
│  Current Value:   ₹10,45,230  (+4.52%)                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  P&L Curve (Last 30 Days)                           │   │
│  │  📈 ▁▂▃▄▅▆▇█▇▆▇█▇▆▅▆▇█▇▆▇█                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Stats:                                                     │
│  Total Trades: 45  |  Win Rate: 71%  |  Avg Profit: ₹2,340 │
│  Max Drawdown: ₹28,000 (2.8%)  |  Sharpe: 1.8              │
│                                                             │
│  [View Trade History]  [Reset Account]  [Switch to LIVE]   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### PHASE 2: Smart Recommendations
*Goal: Help users pick the right strategy for current market conditions*

#### 2.1 Market Regime Detection
**What it does**: Automatically analyzes market conditions and classifies them into regimes (trending, rangebound, volatile).

**User Story**:
> As a trader, I want the system to tell me whether the market is trending or sideways, so I can pick the appropriate strategy.

**Market Regimes**:
| Regime | Indicators | Best Strategies |
|--------|------------|-----------------|
| **Trending Bull** | Strong uptrend, ADX > 25 | Bull Call Spread, Call Butterfly |
| **Trending Bear** | Strong downtrend, ADX > 25 | Bear Put Spread, Put Butterfly |
| **Rangebound Low Vol** | Sideways, VIX < 15 | Iron Condor, Short Strangle |
| **Rangebound High Vol** | Sideways, VIX > 20 | Iron Butterfly, Straddle |
| **Volatile/Event** | VIX spike, news event | Long Straddle, Strangle |

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Market Analysis                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  NIFTY 50                                                   │
│  Current Regime: RANGEBOUND LOW VOLATILITY                  │
│  Confidence: 85%                                            │
│                                                             │
│  Indicators:                                                │
│  • VIX: 13.2 (Low)                                         │
│  • ADX: 18.5 (Weak trend)                                  │
│  • RSI: 52.3 (Neutral)                                     │
│  • PCR: 1.05 (Neutral)                                     │
│                                                             │
│  💡 Recommended Strategies:                                 │
│  1. Iron Condor (92% match)                                │
│  2. Short Strangle (88% match)                             │
│  3. Iron Butterfly (85% match)                             │
│                                                             │
│  [Deploy Iron Condor]  [View All Strategies]               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

#### 2.2 Enhanced Strategy Wizard
**What it does**: Auto-detects market conditions and recommends strategies with one-click deployment.

**Current Flow** (6+ clicks):
1. User opens Strategy Library
2. User guesses market outlook
3. User selects volatility preference
4. User picks risk level
5. User selects strategy from list
6. User configures strikes manually
7. User clicks Deploy

**New Flow** (2 clicks):
1. User clicks "Strategy Wizard" → System auto-detects market regime
2. User clicks on recommended strategy → Deployed with optimal strikes

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  🧙 Strategy Wizard                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📡 Live Market Analysis (auto-detected):                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Market: Rangebound  |  Volatility: Low  |  VIX: 13  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🎯 Top Strategies for Current Market:                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🥇 IRON CONDOR                         [Deploy →]   │   │
│  │    Match: 92%  |  Risk: Medium  |  Max Profit: ₹8K  │   │
│  │    "Best for calm, range-bound markets"             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🥈 SHORT STRANGLE                      [Deploy →]   │   │
│  │    Match: 88%  |  Risk: High  |  Max Profit: ₹12K   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Show All Strategies]  [Manual Selection]                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

#### 2.3 OI-Based Intelligence
**What it does**: Uses Open Interest (OI) data to provide strike selection hints and directional bias.

**User Story**:
> As a trader, I want to know where major OI buildup is, so I can avoid strikes that might act as support/resistance.

**Key Features**:
| Feature | Description |
|---------|-------------|
| PCR Trend | Rising PCR = bullish (institutions writing puts) |
| Max Pain | Price tends to gravitate toward max pain at expiry |
| OI Buildup | High OI at strike = strong support/resistance |
| Strike Hints | "Avoid 24500 CE - massive OI buildup (resistance)" |

---

### PHASE 3: Advanced Exit & Risk Automation
*Goal: Optimize exits and protect capital automatically*

#### 3.1 Per-Strategy Time Stop
**What it does**: Each strategy can have its own exit time, not just a global setting.

**Example**:
- Strategy A (intraday): Exit at 3:15 PM
- Strategy B (BTST): Exit next day at 9:30 AM
- Strategy C (positional): No time stop

---

#### 3.2 DTE-Based Auto-Exit
**What it does**: Automatically exits positions based on Days To Expiry.

**User Story**:
> As a trader, I want my positions to automatically close 1 day before expiry, so I avoid gamma risk and don't accidentally let options expire.

**Options**:
- Exit when DTE = 0 (expiry day)
- Exit when DTE <= 1 (day before expiry)
- Exit at specific time on expiry day (e.g., 12:00 PM)
- Offer to roll instead of exit

---

#### 3.3 Partial Profit Booking
**What it does**: Book profits in stages rather than all-or-nothing.

**Example Configuration**:
- Target 1: Exit 50% position at 50% of max profit
- Target 2: Exit remaining 50% at 80% of max profit
- Or: Exit 50% at ₹5,000 profit, trail the rest

**Why this matters**:
- Locks in some profit early
- Lets remaining position run for more gains
- Reduces regret of "exited too early" or "held too long"

---

#### 3.4 Breakeven Trailing Stop
**What it does**: Once in profit, moves stop loss to breakeven, then trails from there.

**Example**:
1. Entry: Premium collected = ₹10,000
2. P&L hits +₹3,000 (30%) → Stop moves to breakeven (₹0)
3. P&L hits +₹5,000 (50%) → Stop moves to +₹2,000 (locks ₹2K profit)
4. P&L hits +₹7,000 (70%) → Stop moves to +₹4,000 (locks ₹4K profit)

**Benefit**: Never turns a winning trade into a losing trade.

---

### PHASE 4: Dashboard & UX Enhancements
*Goal: Show everything important at a glance*

#### 4.1 Conditions Progress Indicator
**What it does**: Shows how close each waiting strategy is to triggering entry.

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  📋 Waiting Strategy: "Weekly Iron Condor"                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Entry Conditions Progress:                                 │
│                                                             │
│  TIME >= 09:20      ████████████████████ 100% ✓            │
│  VIX < 18           ████████████░░░░░░░░  65% (14.2/18)    │
│  PCR 0.8-1.2        ████████████████████ 100% ✓ (1.05)     │
│                                                             │
│  Overall: 88% ready                                         │
│  Estimated entry: ~5 minutes (waiting for VIX)             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

#### 4.2 Portfolio Greeks Dashboard
**What it does**: Shows combined risk metrics across all active positions.

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Portfolio Risk Overview                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Net Delta: +0.15                                          │
│  ├──────────●──────────┤                                   │
│  -1.0      0.0       +1.0                                  │
│  (Slightly bullish bias)                                   │
│                                                             │
│  Net Theta: +₹3,450/day                                    │
│  (You earn ₹3,450 daily from time decay)                   │
│                                                             │
│  Net Vega: -₹12,000                                        │
│  (If VIX rises 1%, you lose ₹12,000)                       │
│                                                             │
│  ⚠️ Warning: Delta exceeds 0.10 threshold                  │
│  💡 Suggestion: Add hedge to reduce directional risk       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

#### 4.3 One-Click Quick Actions
**What it does**: Common actions accessible with single click.

**Quick Actions Bar**:
```
┌─────────────────────────────────────────────────────────────┐
│  [🛑 Exit All]  [⏸️ Pause All]  [🔄 Roll Expiring]  [⭐ Deploy Favorite]  │
└─────────────────────────────────────────────────────────────┘
```

**Keyboard Shortcuts**:
- `Ctrl+E` - Exit All Positions
- `Ctrl+P` - Pause All Strategies
- `Ctrl+R` - Roll All Expiring Today

---

### PHASE 5: Advanced Automation
*Goal: Further reduce manual intervention*

#### 5.1 Auto-Roll Before Expiry
**What it does**: Automatically rolls positions to next expiry instead of closing.

**Flow**:
1. DTE reaches 1 → System notifies: "Rolling to next weekly in 60 seconds"
2. User can cancel if needed
3. After 60 seconds → Auto-rolls to same strikes in next expiry
4. New strategy created with rolled positions

---

#### 5.2 Strategy Cloning & Personal Templates
**What it does**: Save your configurations as reusable templates.

**Features**:
- "Clone" button on any strategy
- "Save as My Template" - save to personal library
- Quick deploy from personal templates
- Share templates with others (optional)

---

#### 5.3 Backtest Before Deploy
**What it does**: Test strategy performance on historical data before using real money.

**User Interface**:
```
┌─────────────────────────────────────────────────────────────┐
│  📈 Backtest Results: Iron Condor on NIFTY                  │
│     Period: Last 90 days                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Simulated Trades: 12                                       │
│  Win Rate: 75% (9 wins, 3 losses)                          │
│  Total P&L: +₹84,500                                       │
│  Average P&L: +₹7,042/trade                                │
│  Max Drawdown: ₹18,000 (on Aug 5)                          │
│  Sharpe Ratio: 1.65                                        │
│                                                             │
│  ⚠️ Note: Past performance doesn't guarantee future results │
│                                                             │
│  [Deploy This Strategy]  [Modify & Retest]  [Compare]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### PHASE 6: Signal Mode (Broker-Agnostic)
*Goal: Allow users without Zerodha to benefit from the platform*

#### 6.1 Signal-Only Mode
**What it does**: Generates trade signals without executing orders.

**User Story**:
> As a trader using Upstox, I want to receive trade signals from AlgoChanakya that I can execute manually on my broker.

**Signal Format**:
```
┌─────────────────────────────────────────────────────────────┐
│  🔔 NEW SIGNAL: Iron Condor Entry                          │
│     Time: 09:22:15 AM                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  LEG 1: SELL NIFTY 24500 CE @ ₹145  |  Qty: 50             │
│  LEG 2: BUY  NIFTY 24700 CE @ ₹85   |  Qty: 50             │
│  LEG 3: SELL NIFTY 24200 PE @ ₹130  |  Qty: 50             │
│  LEG 4: BUY  NIFTY 24000 PE @ ₹75   |  Qty: 50             │
│                                                             │
│  Net Credit: ₹5,750                                        │
│  Max Profit: ₹5,750  |  Max Loss: ₹4,250                   │
│                                                             │
│  [Copy to Clipboard]  [Mark as Executed]                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Future Enhancement**: Telegram/WhatsApp notifications for signals.

---

## Implementation Timeline

| Phase | Features | Priority | Duration | Cumulative |
|-------|----------|----------|----------|------------|
| **Phase 1** | Auto-Deploy, Position Sync, Paper Trading | Critical | 2 weeks | Week 2 |
| **Phase 2** | Market Regime, Smart Wizard, OI Intelligence | High | 2 weeks | Week 4 |
| **Phase 3** | Time Stop, DTE Exit, Partial Profit, Trailing | High | 1 week | Week 5 |
| **Phase 4** | Conditions Progress, Portfolio Greeks, Quick Actions | Medium | 1 week | Week 6 |
| **Phase 5** | Auto-Roll, Cloning, Backtesting | Medium | 2 weeks | Week 8 |
| **Phase 6** | Signal Mode | Low | 1 week | Week 9 |

---

## Success Metrics

After implementation, users should experience:

| Metric | Before | After |
|--------|--------|-------|
| Daily manual actions | 10-15 clicks | 0-2 clicks |
| Strategy setup time | 5-10 minutes | 30 seconds |
| Missed opportunities | Common (forgot to activate) | Rare (auto-deploy) |
| Position sync errors | Occasional | Never |
| Strategy testing | None (risk real money) | Full paper trading |
| Exit optimization | All-or-nothing | Multi-target, trailing |
| Market analysis | Manual research | Auto-detected |

---

## Risk Considerations

| Risk | Mitigation |
|------|------------|
| **Over-automation** | User confirmation for high-impact actions (Exit All, Kill Switch) |
| **Wrong regime detection** | Show confidence %, allow manual override |
| **Paper ≠ Live** | Add slippage simulation, show warning banner |
| **Position sync lag** | 30-second sync interval, manual sync button |
| **Auto-roll losses** | P&L check before rolling, 60-second cancel window |

---

## Questions for Review

1. **Automation Rules**: Should there be a limit on how many automation rules a user can create?

2. **Paper Trading Capital**: Is ₹10 Lakh default appropriate? Should it be percentage-based?

3. **Position Sync**: Should auto-reconciliation be default, or require user confirmation each time?

4. **Partial Profit**: Should we support more than 3 profit targets?

5. **Signal Mode**: Should signals include recommended limit prices, or only market orders?

6. **Mobile**: Should Phase 4 include mobile-specific optimizations, or defer to a separate mobile app?

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **AutoPilot** | Automated strategy execution system |
| **DTE** | Days To Expiry - days remaining until option expiration |
| **Greeks** | Risk metrics: Delta (direction), Theta (time decay), Vega (volatility), Gamma (acceleration) |
| **Iron Condor** | Options strategy that profits when price stays in a range |
| **Max Pain** | Strike price where maximum options expire worthless |
| **OI** | Open Interest - total outstanding option contracts |
| **PCR** | Put-Call Ratio - ratio of put OI to call OI |
| **VIX** | Volatility Index - measure of market fear/uncertainty |
| **Roll** | Close current position and open same position in next expiry |
| **Paper Trading** | Simulated trading with virtual money |

---

*Document prepared for external review. For technical implementation details, see `plans/shiny-launching-raccoon.md`*
