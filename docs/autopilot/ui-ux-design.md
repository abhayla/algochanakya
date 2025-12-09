# AutoPilot - UI/UX Design Document

## Auto-Execution & Adjustment System for AlgoChanakya

**Version:** 1.0  
**Date:** December 2025  
**Platform:** Desktop/Web Only

---

## Table of Contents

1. [Feature Overview](#1-feature-overview)
2. [Information Architecture](#2-information-architecture)
3. [Screen Designs & Wireframes](#3-screen-designs--wireframes)
4. [User Flow Diagrams](#4-user-flow-diagrams)
5. [Component Library](#5-component-library)
6. [Gaps & Edge Cases](#6-gaps--edge-cases)
7. [Mitigations & Recommendations](#7-mitigations--recommendations)
8. [Implementation Priorities](#8-implementation-priorities)

---

## 1. Feature Overview

### 1.1 Feature Name: **AutoPilot**

AutoPilot is AlgoChanakya's automated strategy execution and adjustment system that allows advanced traders to:
- Deploy option strategies automatically based on market conditions
- Adjust positions dynamically when predefined thresholds are breached
- Manage risk with multiple safeguards and kill switches

### 1.2 Key Design Principles

| Principle | Description |
|-----------|-------------|
| **Power with Clarity** | Advanced features exposed clearly, not hidden |
| **Progressive Complexity** | Start simple, add complexity as needed |
| **Safety First** | Risk controls prominent, kill switch always accessible |
| **Transparency** | Every automated action logged and visible |
| **No Surprises** | Clear indication of what will happen before it happens |

### 1.3 Design System Alignment

- **Theme:** Dark mode (consistent with AlgoChanakya)
- **Primary Color:** #e74c3c (Red - actions, alerts)
- **Success Color:** #00b386 (Green - profit, active)
- **Warning Color:** #f39c12 (Orange - caution)
- **Neutral:** #212529 (Dark background)
- **Font:** Inter / System UI

---

## 2. Information Architecture

### 2.1 Navigation Structure

```
AlgoChanakya Main Nav
├── Dashboard
├── Option Chain
├── Strategies (Library)
├── Builder
├── Positions
├── Watchlist
└── AutoPilot ← NEW
    ├── Overview (Dashboard)
    ├── My Strategies (List)
    ├── Create New
    ├── Logs & History
    └── Settings
```

### 2.2 AutoPilot Section Structure

```
/autopilot
├── /overview          → Dashboard with all running strategies
├── /strategies        → List of all created strategies (active/paused/draft)
├── /create            → Multi-step strategy creation wizard
├── /edit/:id          → Edit existing strategy
├── /logs              → Execution logs and audit trail
├── /settings          → Global risk limits, notification preferences
└── /backtest/:id      → Backtest a strategy before going live
```

---

## 3. Screen Designs & Wireframes

### 3.1 AutoPilot Overview Dashboard

**URL:** `/autopilot/overview`

**Purpose:** Bird's eye view of all automated activity

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  🤖 AutoPilot                                    [+ Create Strategy]    │ │
│ │                                                                         │ │
│ │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐│ │
│ │  │ ACTIVE      │ │ TODAY P&L   │ │ CAPITAL     │ │ 🔴 KILL SWITCH     ││ │
│ │  │    2/3      │ │  +₹12,450   │ │ ₹2.4L/₹5L   │ │   [STOP ALL]       ││ │
│ │  │ strategies  │ │   ↑ 2.3%    │ │   48% used  │ │   Exit & Cancel    ││ │
│ │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘│ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  RUNNING STRATEGIES                                          [View All] │ │
│ │ ─────────────────────────────────────────────────────────────────────── │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ 🟢 Iron Condor - NIFTY Weekly                          [⏸][✕]  │   │ │
│ │  │                                                                  │   │ │
│ │  │ Status: ACTIVE (2 adjustments made)         P&L: +₹8,200        │   │ │
│ │  │                                                                  │   │ │
│ │  │ Legs: 4 → 6 (after adjustments)            Margin: ₹1,24,000    │   │ │
│ │  │                                                                  │   │ │
│ │  │ ┌──────────────────────────────────────────────────────────┐    │   │ │
│ │  │ │ Next Trigger: Adjustment if NIFTY < 25,800               │    │   │ │
│ │  │ │ Current: 25,950 ████████████████░░░░ 75% to trigger      │    │   │ │
│ │  │ └──────────────────────────────────────────────────────────┘    │   │ │
│ │  │                                                                  │   │ │
│ │  │ [View Details]  [View Logs]  [Edit Rules]                       │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ 🟡 Bull Put Spread - BANKNIFTY                         [▶][✕]  │   │ │
│ │  │                                                                  │   │ │
│ │  │ Status: WAITING FOR ENTRY                   P&L: --             │   │ │
│ │  │                                                                  │   │ │
│ │  │ ┌──────────────────────────────────────────────────────────┐    │   │ │
│ │  │ │ Entry Trigger: When VIX > 15 AND Time > 09:30            │    │   │ │
│ │  │ │ Current: VIX=13.2 ████████████░░░░░░░░ 88% | Time ✓      │    │   │ │
│ │  │ └──────────────────────────────────────────────────────────┘    │   │ │
│ │  │                                                                  │   │ │
│ │  │ [View Details]  [Edit Rules]  [Force Entry]                     │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  RECENT ACTIVITY                                             [View All] │ │
│ │ ─────────────────────────────────────────────────────────────────────── │ │
│ │  🟢 10:45:32  Iron Condor adjustment executed: Added hedge PE 25600     │ │
│ │  🟢 10:45:30  Condition met: NIFTY breached 25,900                      │ │
│ │  🔵 09:31:15  Bull Put Spread: Entry condition partially met (VIX=13.2) │ │
│ │  🟢 09:20:05  Iron Condor entry executed: 4 legs @ net credit ₹4,200    │ │
│ │  🟢 09:20:00  Iron Condor entry triggered: Time=09:20, VIX=14.8         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  RISK MONITOR                                                           │ │
│ │ ─────────────────────────────────────────────────────────────────────── │ │
│ │                                                                         │ │
│ │  Daily Loss Limit    ████████████████░░░░░░░░░░  ₹8,200 / ₹20,000      │ │
│ │  Capital Utilization ████████████░░░░░░░░░░░░░░  ₹2.4L / ₹5L           │ │
│ │  Active Strategies   ██████████████████████░░░░  2 / 3                  │ │
│ │                                                                         │ │
│ │  ⚠️ Approaching daily loss limit (41% used)                             │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Elements:**

| Element | Description |
|---------|-------------|
| **Status Cards** | Active count, Today P&L, Capital usage, Kill switch |
| **Kill Switch** | Always visible, red button, one-click emergency stop |
| **Strategy Cards** | Expandable cards showing status, P&L, next trigger |
| **Condition Progress** | Visual progress bar showing how close to trigger |
| **Recent Activity** | Real-time feed of all automated actions |
| **Risk Monitor** | Visual gauges for limits approaching |

---

### 3.2 Strategy Creation Wizard

**URL:** `/autopilot/create`

**Purpose:** Multi-step wizard to create automated strategy

#### Step 1: Choose Base Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Create AutoPilot Strategy                                    Step 1 of 7   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ○───────○───────○───────○───────○───────○───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│  ●                                                                          │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │  SELECT BASE STRATEGY                                                   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │  ○ Import from Strategy Library                                 │   │ │
│ │  │    Choose from 20+ pre-built templates                          │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │  ○ Import from Current Positions                                │   │ │
│ │  │    Add automation to existing open positions                    │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │  ○ Build Custom Strategy                                        │   │ │
│ │  │    Define legs manually from scratch                            │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │  ○ Clone Existing AutoPilot Strategy                            │   │ │
│ │  │    Duplicate and modify a previous strategy                     │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  SELECTED: Import from Strategy Library                                     │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Search strategies...                                      [Filter ▼]   │ │
│ │                                                                         │ │
│ │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │ │
│ │  │ Iron Condor  │ │ Iron Fly     │ │ Bull Put     │ │ Bear Call    │   │ │
│ │  │ ────────────│ │ ────────────│ │ ────────────│ │ ────────────│   │ │
│ │  │ Neutral     │ │ Neutral     │ │ Bullish     │ │ Bearish     │   │ │
│ │  │ 4 legs      │ │ 4 legs      │ │ 2 legs      │ │ 2 legs      │   │ │
│ │  │ Win: 68%    │ │ Win: 40%    │ │ Win: 65%    │ │ Win: 65%    │   │ │
│ │  │             │ │             │ │             │ │             │   │ │
│ │  │ [Select ●]  │ │ [Select ○]  │ │ [Select ○]  │ │ [Select ○]  │   │ │
│ │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  STRATEGY CONFIGURATION                                                 │ │
│ │                                                                         │ │
│ │  Strategy Name    [ Iron Condor Weekly - Auto______________ ]           │ │
│ │                                                                         │ │
│ │  Underlying       [▼ NIFTY        ]    Expiry  [▼ Current Week    ]     │ │
│ │                                                                         │ │
│ │  Lots             [ 1 ]                Position  ○ Intraday  ● BTST     │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                              [Cancel]  [Save Draft]  [Next →]│
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 2: Entry Conditions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Create AutoPilot Strategy                                    Step 2 of 7   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ○───────●───────○───────○───────○───────○───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│          ●                                                                  │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ENTRY CONDITIONS                                                       │ │
│ │  Define when this strategy should be deployed                           │ │
│ │                                                                         │ │
│ │  Condition Logic:  ● All conditions must be true (AND)                  │ │
│ │                    ○ Any condition can be true (OR)                     │ │
│ │                    ○ Custom logic (Advanced)                            │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  CONDITION BUILDER                                        [Advanced ↗]  │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ Condition 1                                              [🗑️]   │   │ │
│ │  │                                                                  │   │ │
│ │  │ [▼ Time        ] [▼ is after    ] [ 09:20        ]              │   │ │
│ │  │                                                                  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ Condition 2                                              [🗑️]   │   │ │
│ │  │                                                                  │   │ │
│ │  │ [▼ India VIX   ] [▼ is between  ] [ 13    ] and [ 18    ]       │   │ │
│ │  │                                                                  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ Condition 3                                              [🗑️]   │   │ │
│ │  │                                                                  │   │ │
│ │  │ [▼ PCR         ] [▼ is greater  ] [ 0.8         ]               │   │ │
│ │  │                                                                  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │                        [+ Add Condition]                                │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  CONDITION TYPES AVAILABLE                                              │ │
│ │                                                                         │ │
│ │  📊 Price-Based     📅 Time-Based      📈 Indicator-Based              │ │
│ │  • Spot Price       • Specific Time    • RSI                           │ │
│ │  • Premium          • Minutes After    • VWAP                          │ │
│ │  • Strike Distance  • Day of Week      • Moving Average                │ │
│ │                                                                         │ │
│ │  🌊 Volatility      📊 OI-Based        📅 Event-Based                  │ │
│ │  • India VIX        • OI Change %      • Expiry Day                    │ │
│ │  • IV Percentile    • PCR              • Event Calendar                │ │
│ │  • IV Rank          • Max Pain         • Custom Date                   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  PREVIEW                                                                │ │
│ │                                                                         │ │
│ │  📝 Entry will trigger when:                                            │ │
│ │     Time is after 09:20                                                 │ │
│ │     AND India VIX is between 13 and 18                                  │ │
│ │     AND PCR is greater than 0.8                                         │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                        [← Back]  [Save Draft]  [Next →]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 2 (Advanced Mode): Expression Builder

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ADVANCED CONDITION BUILDER                                    [Simple ↗]   │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  Expression Editor                                                      │ │
│ │ ┌─────────────────────────────────────────────────────────────────────┐ │ │
│ │ │                                                                     │ │ │
│ │ │  (TIME > "09:20" AND VIX >= 13 AND VIX <= 18)                       │ │ │
│ │ │  OR                                                                 │ │ │
│ │ │  (TIME > "09:45" AND VIX > 18 AND NIFTY.CHANGE% < -0.5)            │ │ │
│ │ │                                                                     │ │ │
│ │ └─────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  Available Variables:                                                   │ │
│ │  ┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐         │ │
│ │  │  TIME   │  VIX    │  PCR    │  NIFTY  │ BANKNIFTY│  OI     │         │ │
│ │  └─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘         │ │
│ │                                                                         │ │
│ │  Variable Properties (click to insert):                                 │ │
│ │  NIFTY.SPOT | NIFTY.CHANGE | NIFTY.CHANGE% | NIFTY.HIGH | NIFTY.LOW    │ │
│ │  VIX | IV_PERCENTILE | IV_RANK                                          │ │
│ │  PCR | MAX_PAIN | OI_CHANGE%                                            │ │
│ │                                                                         │ │
│ │  Operators:                                                             │ │
│ │  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐                     │ │
│ │  │ AND │ OR  │  >  │  <  │ >= │ <=  │  =  │ != │                     │ │
│ │  └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘                     │ │
│ │                                                                         │ │
│ │  [Validate Expression]                         ✅ Expression is valid   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 2 (Visual Mode): Flowchart Builder

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  VISUAL CONDITION BUILDER                                      [Simple ↗]   │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                                                                         │ │
│ │                          ┌─────────────┐                                │ │
│ │                          │   START     │                                │ │
│ │                          └──────┬──────┘                                │ │
│ │                                 │                                       │ │
│ │                                 ▼                                       │ │
│ │                    ┌────────────────────────┐                           │ │
│ │                    │   Time > 09:20?        │                           │ │
│ │                    └───────────┬────────────┘                           │ │
│ │                          Yes   │                                        │ │
│ │                                ▼                                        │ │
│ │                    ┌────────────────────────┐                           │ │
│ │                    │  VIX between 13-18?    │                           │ │
│ │                    └───────────┬────────────┘                           │ │
│ │                          Yes   │                                        │ │
│ │                                ▼                                        │ │
│ │                    ┌────────────────────────┐                           │ │
│ │                    │     PCR > 0.8?         │                           │ │
│ │                    └───────────┬────────────┘                           │ │
│ │                          Yes   │                                        │ │
│ │                                ▼                                        │ │
│ │                    ┌────────────────────────┐                           │ │
│ │                    │  ✅ TRIGGER ENTRY      │                           │ │
│ │                    └────────────────────────┘                           │ │
│ │                                                                         │ │
│ │  Drag conditions from left panel to build flow                          │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────┐                                                          │
│ │  TOOLBOX      │                                                          │
│ │  ───────────  │                                                          │
│ │  [◇] Condition│                                                          │
│ │  [◆] AND Gate │                                                          │
│ │  [◇] OR Gate  │                                                          │
│ │  [→] Branch   │                                                          │
│ │  [●] Action   │                                                          │
│ └──────────────┘                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 3: Adjustment Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Create AutoPilot Strategy                                    Step 3 of 7   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ○───────○───────●───────○───────○───────○───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│                  ●                                                          │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ADJUSTMENT RULES                                                       │ │
│ │  Define how the strategy should react to market changes                 │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ADJUSTMENT RULE 1                                   [Enable ✓]  [🗑️]   │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │                                                                         │ │
│ │  📍 TRIGGER CONDITION                                                   │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ When [▼ Strategy P&L  ] [▼ loss exceeds ] [₹ 5000        ]      │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  🎯 ACTION                                                              │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ [▼ Add Hedge                                               ]    │   │ │
│ │  │                                                                  │   │ │
│ │  │ Hedge Configuration:                                             │   │ │
│ │  │ Type: [▼ Buy PE    ]  Strike: [▼ 200 pts below spot ]           │   │ │
│ │  │ Qty:  [▼ Same as position ]                                     │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ⚡ EXECUTION MODE                                                      │ │
│ │  ○ Fully Automatic (execute immediately)                                │ │
│ │  ● Semi-Automatic (notify and wait for confirmation)                    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ADJUSTMENT RULE 2                                   [Enable ✓]  [🗑️]   │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │                                                                         │ │
│ │  📍 TRIGGER CONDITION                                                   │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ When [▼ Spot Price   ] [▼ breaches    ] [▼ Sold CE Strike ]     │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  🎯 ACTION                                                              │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ [▼ Shift Strikes                                           ]    │   │ │
│ │  │                                                                  │   │ │
│ │  │ Shift Configuration:                                             │ │ │
│ │  │ Move sold CE from current to [▼ 100 pts higher ]                │   │ │
│ │  │ Move bought CE from current to [▼ 100 pts higher ]              │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ⚡ EXECUTION MODE                                                      │ │
│ │  ● Fully Automatic (execute immediately)                                │ │
│ │  ○ Semi-Automatic (notify and wait for confirmation)                    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ADJUSTMENT RULE 3 - EXIT RULE                       [Enable ✓]  [🗑️]   │ │
│ │  ─────────────────────────────────────────────────────────────────────  │ │
│ │                                                                         │ │
│ │  📍 TRIGGER CONDITION                                                   │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ When [▼ Strategy P&L  ] [▼ profit reaches] [₹ 8000        ]     │   │ │
│ │  │  OR  [▼ Time          ] [▼ is            ] [ 15:15        ]     │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  🎯 ACTION                                                              │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │ [▼ Exit Entire Strategy                                    ]    │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ⚡ EXECUTION MODE                                                      │ │
│ │  ● Fully Automatic (execute immediately)                                │ │
│ │  ○ Semi-Automatic (notify and wait for confirmation)                    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                        [+ Add Adjustment Rule]                              │
│                                                                             │
│                                        [← Back]  [Save Draft]  [Next →]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Adjustment Action Types (Dropdown):**

```
┌─────────────────────────────────────┐
│ Select Action                       │
├─────────────────────────────────────┤
│ 📤 Exit Entire Strategy             │
│ 📤 Exit Partial (select legs)       │
│ 🔄 Roll Position (next expiry)      │
│ ↔️ Shift Strikes                     │
│ 🛡️ Add Hedge                         │
│ 📈 Scale Up (add lots)              │
│ 📉 Scale Down (reduce lots)         │
│ 🔀 Convert Strategy                 │
│ 🔔 Alert Only (no action)           │
└─────────────────────────────────────┘
```

#### Step 4: Order Execution Settings

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Create AutoPilot Strategy                                    Step 4 of 7   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ○───────○───────○───────●───────○───────○───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│                          ●                                                  │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ORDER EXECUTION SETTINGS                                               │ │
│ │  Configure how orders should be placed                                  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ORDER TYPE                                                             │ │
│ │                                                                         │ │
│ │  Entry Orders:      [▼ LIMIT                     ]                      │ │
│ │  Adjustment Orders: [▼ MARKET                    ]                      │ │
│ │  Exit Orders:       [▼ MARKET                    ]                      │ │
│ │                                                                         │ │
│ │  ┌─ Limit Order Settings ──────────────────────────────────────────┐   │ │
│ │  │ Price offset from LTP: [▼ +0.5%  ] (will place 0.5% above LTP)  │   │ │
│ │  │ Wait for fill:         [ 30      ] seconds                       │   │ │
│ │  │ If not filled:         [▼ Convert to Market ]                    │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  EXECUTION STYLE                                                        │ │
│ │                                                                         │ │
│ │  ○ Simultaneous (all legs at once)                                      │ │
│ │  ● Sequential (one leg after another)                                   │ │
│ │  ○ With Delay (specify gap between legs)                                │ │
│ │                                                                         │ │
│ │  ┌─ Sequential Settings ───────────────────────────────────────────┐   │ │
│ │  │                                                                  │   │ │
│ │  │  LEG EXECUTION ORDER (drag to reorder)                          │   │ │
│ │  │                                                                  │   │ │
│ │  │  ☰ 1. SELL PE 25800  ──────────────────────────  [Execute first]│   │ │
│ │  │  ☰ 2. SELL CE 26200  ──────────────────────────  [Then this]    │   │ │
│ │  │  ☰ 3. BUY PE 25600   ──────────────────────────  [Then this]    │   │ │
│ │  │  ☰ 4. BUY CE 26400   ──────────────────────────  [Execute last] │   │ │
│ │  │                                                                  │   │ │
│ │  │  Wait between legs: [ 2 ] seconds                                │   │ │
│ │  │                                                                  │   │ │
│ │  │  If any leg fails:                                               │   │ │
│ │  │  ○ Continue with remaining legs                                  │   │ │
│ │  │  ● Stop and alert (partial position)                             │   │ │
│ │  │  ○ Reverse already executed legs                                 │   │ │
│ │  │                                                                  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  SLIPPAGE PROTECTION                                                    │ │
│ │                                                                         │ │
│ │  ☑️ Enable slippage protection                                           │ │
│ │                                                                         │ │
│ │  Max slippage per leg:  [ 2.0 ] %                                       │ │
│ │                                                                         │ │
│ │  If slippage exceeds limit:                                             │ │
│ │  ○ Skip this leg and alert                                              │ │
│ │  ● Wait and retry (max [ 3 ] times)                                     │ │
│ │  ○ Execute anyway (override protection)                                 │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  SPEED VS CONFIRMATION                                                  │ │
│ │                                                                         │ │
│ │  Execution Priority:                                                    │ │
│ │  ○ Speed (execute immediately when condition triggers)                  │ │
│ │  ● Confirmation (verify conditions still valid before execution)        │ │
│ │                                                                         │ │
│ │  Confirmation window: [ 5 ] seconds (re-check conditions before order)  │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                        [← Back]  [Save Draft]  [Next →]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 5: Risk Management

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Create AutoPilot Strategy                                    Step 5 of 7   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ○───────○───────○───────○───────●───────○───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│                                  ●                                          │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  RISK MANAGEMENT                                                        │ │
│ │  Set safety limits for this strategy                                    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  LOSS LIMITS                                                            │ │
│ │                                                                         │ │
│ │  ☑️ Per-Strategy Loss Limit                                              │ │
│ │     Max loss: ₹ [ 8,000      ]                                          │ │
│ │     Action when hit: [▼ Exit strategy and pause AutoPilot ]             │ │
│ │                                                                         │ │
│ │  ☑️ Trailing Stop Loss                                                   │ │
│ │     Trail from peak profit: [ 30 ] %                                    │ │
│ │     (If profit was ₹10K, exit if it drops to ₹7K)                       │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  CAPITAL LIMITS                                                         │ │
│ │                                                                         │ │
│ │  ☑️ Maximum margin for this strategy                                     │ │
│ │     Max margin: ₹ [ 1,50,000  ]                                         │ │
│ │     (Include adjustments in this limit)                                 │ │
│ │                                                                         │ │
│ │  ☑️ Check margin before each order                                       │ │
│ │     Buffer required: [ 20 ] % above calculated margin                   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  TIME RESTRICTIONS                                                      │ │
│ │                                                                         │ │
│ │  ☑️ No execution in first [ 5 ] minutes of market                        │ │
│ │  ☑️ No execution in last [ 15 ] minutes of market                        │ │
│ │  ☐ No execution during lunch hours (12:30 - 13:30)                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  COOLDOWN & RECOVERY                                                    │ │
│ │                                                                         │ │
│ │  ☑️ Cooldown after strategy exit                                         │ │
│ │     Wait [ 30 ] minutes before re-entry allowed                         │ │
│ │                                                                         │ │
│ │  ☐ Cooldown after loss only                                             │ │
│ │     Wait [ 60 ] minutes after loss before re-entry                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  NETWORK/SYSTEM FAILURE HANDLING                                        │ │
│ │                                                                         │ │
│ │  If connection lost during active strategy:                             │ │
│ │  ○ Queue orders and execute when restored                               │ │
│ │  ● Cancel pending and alert (manual intervention required)              │ │
│ │  ○ Retry [ 5 ] times, then alert                                        │ │
│ │                                                                         │ │
│ │  If AlgoChanakya server restarts:                                       │ │
│ │  ● Resume monitoring (strategy continues)                               │ │
│ │  ○ Pause strategy (manual restart required)                             │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                        [← Back]  [Save Draft]  [Next →]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 6: Schedule & Activation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Create AutoPilot Strategy                                    Step 6 of 7   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ○───────○───────○───────○───────○───────●───────○                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│                                          ●                                  │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  SCHEDULE & ACTIVATION                                                  │ │
│ │  When should this strategy run?                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ACTIVATION MODE                                                        │ │
│ │                                                                         │ │
│ │  ● Always Active (every trading day until manually stopped)             │ │
│ │  ○ Date Range (from ___ to ___)                                         │ │
│ │  ○ Specific Days Only                                                   │ │
│ │  ○ Expiry Days Only                                                     │ │
│ │  ○ One-Time Only (run once then deactivate)                             │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  DAY SELECTION (if Specific Days chosen)                                │ │
│ │                                                                         │ │
│ │  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐                            │ │
│ │  │ Mon │ Tue │ Wed │ Thu │ Fri │ Sat │ Sun │                            │ │
│ │  │ [✓] │ [✓] │ [ ] │ [✓] │ [ ] │ [ ] │ [ ] │                            │ │
│ │  └─────┴─────┴─────┴─────┴─────┴─────┴─────┘                            │ │
│ │                                                                         │ │
│ │  ☐ Only on weekly expiry days (Thursday)                                │ │
│ │  ☐ Only on monthly expiry days (last Thursday)                          │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  MARKET HOURS                                                           │ │
│ │                                                                         │ │
│ │  ● Full Market Hours (09:15 - 15:30)                                    │ │
│ │  ○ Custom Window                                                        │ │
│ │                                                                         │ │
│ │  ┌─ Custom Window Settings ────────────────────────────────────────┐   │ │
│ │  │  Start Time: [ 09:20 ]     End Time: [ 15:15 ]                  │   │ │
│ │  │                                                                  │   │ │
│ │  │  ☐ Exclude period: [ 14:00 ] to [ 14:30 ] (optional)            │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  POSITION LIFECYCLE                                                     │ │
│ │                                                                         │ │
│ │  Position Type:                                                         │ │
│ │  ○ Intraday Only (must exit by 15:15)                                   │ │
│ │  ● Positional (can carry forward overnight)                             │ │
│ │                                                                         │ │
│ │  ┌─ Intraday Settings ─────────────────────────────────────────────┐   │ │
│ │  │  Auto square-off time: [ 15:15 ]                                 │   │ │
│ │  │  Square-off order type: [▼ MARKET ]                              │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  If entry conditions not met today:                                     │ │
│ │  ● Try again next trading day                                           │ │
│ │  ○ Expire if not triggered within [ 5 ] days                            │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  PRIORITY (if multiple AutoPilot strategies)                            │ │
│ │                                                                         │ │
│ │  Priority Level: [▼ 1 - Highest ]                                       │ │
│ │                                                                         │ │
│ │  If this strategy conflicts with another:                               │ │
│ │  ● This strategy takes precedence                                       │ │
│ │  ○ Skip this strategy                                                   │ │
│ │  ○ Execute both (if margin allows)                                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                        [← Back]  [Save Draft]  [Next →]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 7: Review & Activate

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Create AutoPilot Strategy                                    Step 7 of 7   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ○───────○───────○───────○───────○───────○───────●                          │
│  Base    Entry   Adjust  Orders  Risk    Schedule Review                    │
│                                                  ●                          │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  REVIEW YOUR AUTOPILOT STRATEGY                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  📋 STRATEGY SUMMARY                                          [Edit ✏️] │ │
│ │                                                                         │ │
│ │  Name:        Iron Condor Weekly - Auto                                 │ │
│ │  Underlying:  NIFTY                                                     │ │
│ │  Expiry:      Current Week (auto-roll)                                  │ │
│ │  Lots:        1                                                         │ │
│ │  Position:    Positional (carry forward allowed)                        │ │
│ │                                                                         │ │
│ │  Legs:                                                                  │ │
│ │  ┌────────────────────────────────────────────────────────────────┐    │ │
│ │  │ 1. SELL PE ATM-200  │ 2. BUY PE ATM-400                       │    │ │
│ │  │ 3. SELL CE ATM+200  │ 4. BUY CE ATM+400                       │    │ │
│ │  └────────────────────────────────────────────────────────────────┘    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  📍 ENTRY CONDITIONS                                          [Edit ✏️] │ │
│ │                                                                         │ │
│ │  Deploy when ALL of these are true:                                     │ │
│ │  ✓ Time is after 09:20                                                  │ │
│ │  ✓ India VIX is between 13 and 18                                       │ │
│ │  ✓ PCR is greater than 0.8                                              │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  🔄 ADJUSTMENT RULES (3 rules)                                [Edit ✏️] │ │
│ │                                                                         │ │
│ │  Rule 1: If P&L loss > ₹5,000 → Add Hedge (Semi-Auto)                   │ │
│ │  Rule 2: If Spot breaches sold CE → Shift strikes +100 (Auto)           │ │
│ │  Rule 3: If P&L profit > ₹8,000 OR Time = 15:15 → Exit All (Auto)       │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ⚙️ EXECUTION SETTINGS                                        [Edit ✏️] │ │
│ │                                                                         │ │
│ │  Entry: LIMIT (+0.5%, 30s wait, convert to MARKET)                      │ │
│ │  Adjustments: MARKET                                                    │ │
│ │  Exit: MARKET                                                           │ │
│ │  Style: Sequential (SELL PE → SELL CE → BUY PE → BUY CE)                │ │
│ │  Slippage Protection: 2% max per leg                                    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  🛡️ RISK LIMITS                                               [Edit ✏️] │ │
│ │                                                                         │ │
│ │  Max Loss: ₹8,000          Max Margin: ₹1,50,000                        │ │
│ │  Trailing SL: 30%          Cooldown: 30 mins after exit                 │ │
│ │  No trades: First 5 mins, Last 15 mins                                  │ │
│ │  Network failure: Cancel pending & alert                                │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  📅 SCHEDULE                                                  [Edit ✏️] │ │
│ │                                                                         │ │
│ │  Activation: Always Active (every trading day)                          │ │
│ │  Hours: 09:20 - 15:15                                                   │ │
│ │  Priority: 1 (Highest)                                                  │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ⚠️ PRE-ACTIVATION CHECKLIST                                            │ │
│ │                                                                         │ │
│ │  ☑️ Zerodha account connected and authenticated                          │ │
│ │  ☑️ Sufficient margin available (₹1,50,000 required, ₹2,80,000 avail)    │ │
│ │  ☑️ Active strategy slots available (2/3 used)                           │ │
│ │  ☑️ Daily loss limit not breached                                        │ │
│ │  ☐ I understand this will place real orders with real money             │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  [📊 Run Backtest]    [📝 Save as Draft]    [🧪 Paper Trade First] │   │
│  │                                                                     │   │
│  │                    [🚀 ACTIVATE STRATEGY]                          │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│                                                       [← Back to Edit]      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.3 Strategy Monitoring (Active Strategy Detail View)

**URL:** `/autopilot/strategies/:id`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back to AutoPilot                                                        │
│                                                                             │
│  Iron Condor Weekly - Auto                                                  │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ STATUS      │ │ P&L         │ │ MARGIN      │ │ ACTIONS                 ││
│  │ 🟢 ACTIVE   │ │ +₹8,200     │ │ ₹1,24,000   │ │ [⏸ Pause] [✕ Exit All] ││
│  │ 2 adjusts   │ │   ↑ 6.6%    │ │ of ₹1.5L    │ │                         ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────────────────┤
│ │  TABS: [Positions] [Conditions] [Activity Log] [Settings]                 │
│ └───────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  CURRENT POSITIONS (6 legs)                                             │ │
│ │                                                                         │ │
│ │  ┌────────────────────────────────────────────────────────────────────┐ │ │
│ │  │ Instrument          │ Qty   │ Avg    │ LTP    │ P&L     │ Status   │ │ │
│ │  ├────────────────────────────────────────────────────────────────────┤ │ │
│ │  │ NIFTY 25800 PE SELL │ -75   │ 45.20  │ 32.10  │ +₹982   │ Original │ │ │
│ │  │ NIFTY 25600 PE BUY  │ +75   │ 28.50  │ 18.20  │ -₹772   │ Original │ │ │
│ │  │ NIFTY 26200 CE SELL │ -75   │ 52.30  │ 41.00  │ +₹847   │ Original │ │ │
│ │  │ NIFTY 26400 CE BUY  │ +75   │ 31.80  │ 22.50  │ -₹697   │ Original │ │ │
│ │  │ NIFTY 25500 PE BUY  │ +75   │ 15.00  │ 12.30  │ -₹202   │ Hedge    │ │ │
│ │  │ NIFTY 26500 CE BUY  │ +75   │ 18.20  │ 14.10  │ -₹307   │ Hedge    │ │ │
│ │  ├────────────────────────────────────────────────────────────────────┤ │ │
│ │  │                              TOTAL P&L               │ +₹8,200    │ │ │
│ │  └────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  💡 2 hedge legs added via Adjustment Rule 1 at 10:45                   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  PAYOFF CHART                                                           │ │
│ │                                                                         │ │
│ │        +₹12K ┤                    ╭────────╮                            │ │
│ │              │                   ╱          ╲                           │ │
│ │              │                  ╱            ╲                          │ │
│ │          0  ─┼─────────────────╱──────────────╲─────────────────       │ │
│ │              │                ╱                ╲                        │ │
│ │        -₹8K ┤───────────────╱                  ╲───────────────        │ │
│ │              │                                                          │ │
│ │              └──────┴──────┴──────┴──────┴──────┴──────┴──────          │ │
│ │               25400  25600  25800  26000  26200  26400  26600           │ │
│ │                               ▲                                         │ │
│ │                          NIFTY: 25,950                                  │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  CONDITION MONITORS                                                     │ │
│ │                                                                         │ │
│ │  ┌── Adjustment Rule 1 (Semi-Auto) ─────────────────────────────────┐  │ │
│ │  │ Trigger: P&L loss > ₹5,000                                        │  │ │
│ │  │ Status: ✅ ALREADY TRIGGERED at 10:45                              │  │ │
│ │  │ Action Taken: Added hedge (PE 25500 + CE 26500)                   │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ │  ┌── Adjustment Rule 2 (Auto) ──────────────────────────────────────┐  │ │
│ │  │ Trigger: Spot breaches sold CE (26200)                            │  │ │
│ │  │ Current: NIFTY = 25,950                                           │  │ │
│ │  │ Progress: ████████████████░░░░░░░░░░░░░░░░  250 pts away (62%)    │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ │  ┌── Adjustment Rule 3 - Exit (Auto) ───────────────────────────────┐  │ │
│ │  │ Trigger: P&L profit > ₹8,000 OR Time = 15:15                      │  │ │
│ │  │ Current: P&L = ₹8,200 ✅ | Time = 11:23                           │  │ │
│ │  │ Status: 🔔 CONDITION MET - Executing exit...                      │  │ │
│ │  └───────────────────────────────────────────────────────────────────┘  │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  RECENT ACTIVITY                                         [View All →]   │ │
│ │                                                                         │ │
│ │  🟢 11:23:45  Exit condition met: P&L > ₹8,000 (current: ₹8,200)        │ │
│ │  🟢 10:45:32  Hedge added: BUY PE 25500 @ ₹15.00 (75 qty)               │ │
│ │  🟢 10:45:31  Hedge added: BUY CE 26500 @ ₹18.20 (75 qty)               │ │
│ │  🔔 10:45:30  Adjustment Rule 1 triggered: P&L = -₹5,120                │ │
│ │  🟢 09:20:08  Entry complete: 4 legs executed, net credit ₹4,200        │ │
│ │  🟢 09:20:05  Entry triggered: All conditions met                       │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.4 Logs & History Screen

**URL:** `/autopilot/logs`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AutoPilot Logs & History                                                   │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  FILTERS                                                                │ │
│ │                                                                         │ │
│ │  Strategy: [▼ All Strategies    ]  Date: [▼ Today        ]              │ │
│ │  Event:    [▼ All Events        ]  Status: [▼ All         ]             │ │
│ │                                                                         │ │
│ │  [🔍 Search logs...]                              [Export CSV 📥]       │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  LOG ENTRIES                                                            │ │
│ │                                                                         │ │
│ │  ┌────────────────────────────────────────────────────────────────────┐ │ │
│ │  │ 🟢 11:23:48 │ ORDER EXECUTED                                       │ │ │
│ │  │ ───────────────────────────────────────────────────────────────── │ │ │
│ │  │ Strategy: Iron Condor Weekly - Auto                                │ │ │
│ │  │ Action: Exit All (Adjustment Rule 3)                               │ │ │
│ │  │ Legs: 6 orders placed, 6 filled                                    │ │ │
│ │  │ Execution time: 2.3 seconds                                        │ │ │
│ │  │ Slippage: ₹45 (0.18%)                                              │ │ │
│ │  │                                                                    │ │ │
│ │  │ Order Details:                                                     │ │ │
│ │  │ ┌────────────────────────────────────────────────────────────┐    │ │ │
│ │  │ │ NIFTY 25800 PE │ BUY  │ 75 │ LTP: 32.10 │ Filled: 32.15  │    │ │ │
│ │  │ │ NIFTY 25600 PE │ SELL │ 75 │ LTP: 18.20 │ Filled: 18.15  │    │ │ │
│ │  │ │ NIFTY 26200 CE │ BUY  │ 75 │ LTP: 41.00 │ Filled: 41.10  │    │ │ │
│ │  │ │ NIFTY 26400 CE │ SELL │ 75 │ LTP: 22.50 │ Filled: 22.45  │    │ │ │
│ │  │ │ NIFTY 25500 PE │ SELL │ 75 │ LTP: 12.30 │ Filled: 12.25  │    │ │ │
│ │  │ │ NIFTY 26500 CE │ SELL │ 75 │ LTP: 14.10 │ Filled: 14.05  │    │ │ │
│ │  │ └────────────────────────────────────────────────────────────┘    │ │ │
│ │  │                                                                    │ │ │
│ │  │ Final P&L: +₹8,155 (after slippage)                               │ │ │
│ │  └────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌────────────────────────────────────────────────────────────────────┐ │ │
│ │  │ 🔔 11:23:45 │ CONDITION TRIGGERED                                  │ │ │
│ │  │ ───────────────────────────────────────────────────────────────── │ │ │
│ │  │ Strategy: Iron Condor Weekly - Auto                                │ │ │
│ │  │ Rule: Adjustment Rule 3 (Exit)                                     │ │ │
│ │  │ Condition: P&L profit > ₹8,000                                     │ │ │
│ │  │ Actual Value: ₹8,200                                               │ │ │
│ │  │ Mode: Fully Automatic                                              │ │ │
│ │  │ Action: Proceeding to execute exit...                              │ │ │
│ │  └────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ┌────────────────────────────────────────────────────────────────────┐ │ │
│ │  │ 🔵 11:15:00 │ CONDITION EVALUATED                                  │ │ │
│ │  │ ───────────────────────────────────────────────────────────────── │ │ │
│ │  │ Strategy: Iron Condor Weekly - Auto                                │ │ │
│ │  │ Rule: Adjustment Rule 3                                            │ │ │
│ │  │ Condition: P&L profit > ₹8,000                                     │ │ │
│ │  │ Actual Value: ₹7,850 (98% to trigger)                              │ │ │
│ │  │ Result: Not triggered yet                                          │ │ │
│ │  └────────────────────────────────────────────────────────────────────┘ │ │
│ │                                                                         │ │
│ │  ... more entries ...                                                   │ │
│ │                                                                         │ │
│ │  [Load More]                                                            │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.5 Global Settings Screen

**URL:** `/autopilot/settings`

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AutoPilot Settings                                                         │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  GLOBAL RISK LIMITS                                                     │ │
│ │  These limits apply across ALL AutoPilot strategies                     │ │
│ │                                                                         │ │
│ │  Daily Loss Limit:         ₹ [ 20,000     ]                             │ │
│ │  When hit: [▼ Pause all AutoPilot strategies ]                          │ │
│ │                                                                         │ │
│ │  Maximum Capital Deployed: ₹ [ 5,00,000   ]                             │ │
│ │  Current usage: ₹2,40,000 (48%)                                         │ │
│ │                                                                         │ │
│ │  Maximum Active Strategies: [ 3 ]                                       │ │
│ │  Current: 2 active                                                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  NOTIFICATION PREFERENCES                                               │ │
│ │                                                                         │ │
│ │  ☑️ Entry condition approaching (90% threshold)                          │ │
│ │  ☑️ Entry order placed                                                   │ │
│ │  ☑️ Entry order executed                                                 │ │
│ │  ☑️ Adjustment condition triggered                                       │ │
│ │  ☑️ Adjustment executed                                                  │ │
│ │  ☑️ Strategy exited                                                      │ │
│ │  ☑️ Order failed/rejected                                                │ │
│ │  ☑️ Daily summary (EOD report)                                           │ │
│ │                                                                         │ │
│ │  Notification Frequency:                                                │ │
│ │  ● Real-time (instant)                                                  │ │
│ │  ○ Batched every [ 15 ] minutes                                         │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  DEFAULT EXECUTION SETTINGS                                             │ │
│ │  Applied to new strategies (can override per strategy)                  │ │
│ │                                                                         │ │
│ │  Default Order Type:     [▼ MARKET      ]                               │ │
│ │  Default Execution Mode: [▼ Semi-Automatic ]                            │ │
│ │  Default Slippage Limit: [ 2.0 ] %                                      │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  LOG RETENTION                                                          │ │
│ │                                                                         │ │
│ │  Keep logs for: [ 90 ] days                                             │ │
│ │  Current storage: 12.4 MB                                               │ │
│ │                                                                         │ │
│ │  [Export All Logs]  [Clear Old Logs]                                    │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  🔴 EMERGENCY CONTROLS                                                  │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │                                                                  │   │ │
│ │  │  [🛑 KILL SWITCH - STOP ALL & EXIT POSITIONS]                   │   │ │
│ │  │                                                                  │   │ │
│ │  │  This will:                                                      │   │ │
│ │  │  • Pause all active AutoPilot strategies                        │   │ │
│ │  │  • Cancel all pending orders                                    │   │ │
│ │  │  • Exit all open positions at MARKET price                      │   │ │
│ │  │                                                                  │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ │  ┌─────────────────────────────────────────────────────────────────┐   │ │
│ │  │  [⏸ PAUSE ALL STRATEGIES]                                       │   │ │
│ │  │  Stop new trades, keep existing positions                       │   │ │
│ │  └─────────────────────────────────────────────────────────────────┘   │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                                                    [Save Settings]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.6 Semi-Automatic Confirmation Modal

When a semi-automatic adjustment triggers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ⚠️ ADJUSTMENT CONFIRMATION REQUIRED                                        │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  Strategy: Iron Condor Weekly - Auto                                        │
│  Rule: Adjustment Rule 1 - Add Hedge                                        │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  TRIGGER REASON                                                         │ │
│ │                                                                         │ │
│ │  Condition: P&L loss exceeds ₹5,000                                     │ │
│ │  Current P&L: -₹5,120                                                   │ │
│ │  Triggered at: 10:45:30                                                 │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  PROPOSED ACTION                                                        │ │
│ │                                                                         │ │
│ │  Add Hedge Legs:                                                        │ │
│ │  ┌────────────────────────────────────────────────────────────────┐    │ │
│ │  │ BUY  │ NIFTY 25500 PE │ 75 qty │ LTP: ₹15.00 │ Cost: ₹1,125   │    │ │
│ │  │ BUY  │ NIFTY 26500 CE │ 75 qty │ LTP: ₹18.20 │ Cost: ₹1,365   │    │ │
│ │  └────────────────────────────────────────────────────────────────┘    │ │
│ │                                                                         │ │
│ │  Total Hedge Cost: ₹2,490                                               │ │
│ │  Additional Margin: ₹0 (hedges reduce margin)                           │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │  ⏱️ AUTO-TIMEOUT                                                         │ │
│ │                                                                         │ │
│ │  If no response in: [▼ 60 seconds ]                                     │ │
│ │  Then: [▼ Skip this adjustment ]                                        │ │
│ │                                                                         │ │
│ │  Time remaining: 0:45                                                   │ │
│ │  ████████████████████████████░░░░░░░░░░░░                               │ │
│ │                                                                         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  [Skip This Time]    [Modify Action]    [✅ CONFIRM & EXECUTE]     │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. User Flow Diagrams

### 4.1 Create AutoPilot Strategy Flow

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Select Base Strategy │
│ • Import from Library│
│ • Current Positions  │
│ • Build Custom       │
│ • Clone Existing     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Configure Instrument │
│ • Underlying         │
│ • Expiry             │
│ • Lots               │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Define Entry         │
│ Conditions           │
│ • Price/Time/Vol     │
│ • OI/Indicator       │
│ • AND/OR logic       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Define Adjustment    │
│ Rules                │
│ • Trigger conditions │
│ • Actions to take    │
│ • Auto/Semi-auto     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Configure Order      │
│ Execution            │
│ • Order types        │
│ • Leg sequence       │
│ • Slippage limits    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Set Risk Limits      │
│ • Loss limits        │
│ • Margin limits      │
│ • Time restrictions  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Schedule Activation  │
│ • Days/Dates         │
│ • Market hours       │
│ • Priority           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Review & Validate    │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │           │
     ▼           ▼
┌─────────┐  ┌─────────────┐
│Backtest │  │ Paper Trade │
└────┬────┘  └──────┬──────┘
     │              │
     └──────┬───────┘
            │
            ▼
   ┌────────────────┐
   │ Activate Live  │
   └────────────────┘
```

### 4.2 Strategy Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                          STRATEGY EXECUTION FLOW                            │
│                                                                             │
│  ┌──────────────┐                                                           │
│  │ Market Opens │                                                           │
│  └──────┬───────┘                                                           │
│         │                                                                   │
│         ▼                                                                   │
│  ┌──────────────────┐                                                       │
│  │ Check if strategy │                                                      │
│  │ is scheduled today│                                                      │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│      Yes  │  No → Skip                                                      │
│           ▼                                                                 │
│  ┌──────────────────┐         ┌─────────────────┐                          │
│  │ Monitor Entry     │ ──────▶│ Log: Condition  │                          │
│  │ Conditions        │ Loop   │ evaluated       │                          │
│  └────────┬─────────┘         └─────────────────┘                          │
│           │                                                                 │
│     Condition Met?                                                          │
│           │                                                                 │
│      Yes  │  No → Continue monitoring                                       │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │ Verify margin     │                                                      │
│  │ available         │                                                      │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│      Yes  │  No → Alert & Skip                                              │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │ Execute Entry     │                                                      │
│  │ Orders (per       │                                                      │
│  │ sequence)         │                                                      │
│  └────────┬─────────┘                                                       │
│           │                                                                 │
│     All Filled?                                                             │
│           │                                                                 │
│      Yes  │  Partial → Handle partial fill                                  │
│           ▼                                                                 │
│  ┌──────────────────┐                                                       │
│  │ STRATEGY ACTIVE   │◀──────────────────────┐                             │
│  │ Monitor P&L &     │                        │                             │
│  │ Adjustments       │                        │                             │
│  └────────┬─────────┘                        │                             │
│           │                                   │                             │
│     Adjustment Condition?                     │                             │
│           │                                   │                             │
│      Yes  ▼                                   │                             │
│  ┌──────────────────┐                        │                             │
│  │ Check: Auto or    │                        │                             │
│  │ Semi-Auto?        │                        │                             │
│  └────────┬─────────┘                        │                             │
│           │                                   │                             │
│     ┌─────┴─────┐                            │                             │
│     │           │                            │                             │
│     ▼           ▼                            │                             │
│  ┌──────┐   ┌─────────────┐                  │                             │
│  │ Auto │   │ Show Modal  │                  │                             │
│  └──┬───┘   │ Wait Confirm│                  │                             │
│     │       └──────┬──────┘                  │                             │
│     │              │                          │                             │
│     │         Confirmed?                      │                             │
│     │              │                          │                             │
│     │         Yes  │  No → Skip               │                             │
│     │              │                          │                             │
│     └──────┬───────┘                          │                             │
│            ▼                                  │                             │
│  ┌──────────────────┐                        │                             │
│  │ Execute           │                        │                             │
│  │ Adjustment        │                        │                             │
│  └────────┬─────────┘                        │                             │
│           │                                   │                             │
│     Is Exit?                                  │                             │
│           │                                   │                             │
│      No   │  Yes → End                        │                             │
│           └───────────────────────────────────┘                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Kill Switch Flow

```
┌────────────────────────────────────────────────────────┐
│                                                        │
│                   KILL SWITCH FLOW                     │
│                                                        │
│  ┌─────────────────┐                                   │
│  │ User clicks     │                                   │
│  │ KILL SWITCH     │                                   │
│  └────────┬────────┘                                   │
│           │                                            │
│           ▼                                            │
│  ┌─────────────────┐                                   │
│  │ Confirm Dialog  │                                   │
│  │ "Are you sure?" │                                   │
│  └────────┬────────┘                                   │
│           │                                            │
│     Confirmed?                                         │
│           │                                            │
│      Yes  │  No → Cancel                               │
│           ▼                                            │
│  ┌─────────────────────────────────────────────────┐  │
│  │                                                  │  │
│  │  PARALLEL EXECUTION                             │  │
│  │                                                  │  │
│  │  ┌───────────────┐  ┌───────────────┐           │  │
│  │  │ 1. Pause all  │  │ 2. Cancel all │           │  │
│  │  │ AutoPilot     │  │ pending orders│           │  │
│  │  │ strategies    │  │               │           │  │
│  │  └───────────────┘  └───────────────┘           │  │
│  │                                                  │  │
│  │  ┌───────────────────────────────────────────┐  │  │
│  │  │ 3. For each open position:                │  │  │
│  │  │    - Place MARKET exit order             │  │  │
│  │  │    - Log execution                       │  │  │
│  │  └───────────────────────────────────────────┘  │  │
│  │                                                  │  │
│  └─────────────────────────────────────────────────┘  │
│           │                                            │
│           ▼                                            │
│  ┌─────────────────┐                                   │
│  │ Show Summary    │                                   │
│  │ - Positions     │                                   │
│  │   closed        │                                   │
│  │ - P&L realized  │                                   │
│  │ - Orders        │                                   │
│  │   cancelled     │                                   │
│  └─────────────────┘                                   │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## 5. Component Library

### 5.1 Condition Builder Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONDITION ROW COMPONENT                                                     │
│                                                                             │
│ Props:                                                                      │
│ - conditionType: 'price' | 'time' | 'indicator' | 'volatility' | 'oi'      │
│ - operator: '>' | '<' | '>=' | '<=' | '=' | 'between'                       │
│ - value: number | string | [number, number]                                 │
│ - onDelete: () => void                                                      │
│ - onChange: (condition) => void                                             │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ [▼ Variable    ] [▼ Operator   ] [ Value          ]         [🗑️]   │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ ADJUSTMENT RULE COMPONENT                                                   │
│                                                                             │
│ Props:                                                                      │
│ - trigger: ConditionGroup                                                   │
│ - action: 'exit' | 'hedge' | 'roll' | 'shift' | 'scale' | 'alert'          │
│ - actionConfig: object                                                      │
│ - executionMode: 'auto' | 'semi-auto'                                       │
│ - enabled: boolean                                                          │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ RULE CARD                                                            │    │
│ │ ┌─────────────────────────────────────────────────────────────────┐ │    │
│ │ │ Trigger: [Condition Builder]                                     │ │    │
│ │ │ Action:  [Action Selector + Config]                              │ │    │
│ │ │ Mode:    ○ Auto  ○ Semi-Auto                                     │ │    │
│ │ └─────────────────────────────────────────────────────────────────┘ │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Status Indicators

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STATUS BADGE COMPONENT                                                      │
│                                                                             │
│ Variants:                                                                   │
│ ┌─────────────────┐                                                        │
│ │ 🟢 ACTIVE       │  Green - Strategy running, monitoring                  │
│ └─────────────────┘                                                        │
│ ┌─────────────────┐                                                        │
│ │ 🟡 WAITING      │  Yellow - Waiting for entry conditions                 │
│ └─────────────────┘                                                        │
│ ┌─────────────────┐                                                        │
│ │ 🟠 PENDING      │  Orange - Adjustment pending confirmation              │
│ └─────────────────┘                                                        │
│ ┌─────────────────┐                                                        │
│ │ ⏸️ PAUSED       │  Gray - Manually paused                                │
│ └─────────────────┘                                                        │
│ ┌─────────────────┐                                                        │
│ │ 🔴 ERROR        │  Red - Error state, needs attention                    │
│ └─────────────────┘                                                        │
│ ┌─────────────────┐                                                        │
│ │ ✅ COMPLETED    │  Blue - Strategy completed successfully                │
│ └─────────────────┘                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Progress Indicator

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CONDITION PROGRESS COMPONENT                                                │
│                                                                             │
│ Props:                                                                      │
│ - condition: string (human readable)                                        │
│ - currentValue: number                                                      │
│ - targetValue: number                                                       │
│ - progress: number (0-100)                                                  │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────┐    │
│ │ NIFTY > 26,000                                                      │    │
│ │ Current: 25,850                                                     │    │
│ │ ████████████████████░░░░░░░░░░  85% (150 pts away)                 │    │
│ └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Gaps & Edge Cases

### 6.1 Technical Gaps

| # | Gap | Description | Severity |
|---|-----|-------------|----------|
| G1 | **Kite API Rate Limits** | Zerodha API has rate limits (3 requests/second). Simultaneous leg execution may hit limits | HIGH |
| G2 | **WebSocket Disconnection** | Real-time data feed may disconnect during critical moments | HIGH |
| G3 | **Order Rejection** | Exchange may reject orders due to price bands, circuit limits | HIGH |
| G4 | **Partial Fills** | Some legs may fill while others don't, creating unbalanced positions | HIGH |
| G5 | **Price Gaps** | Market may gap open, conditions may be missed | MEDIUM |
| G6 | **Server Restart** | How to resume monitoring after AlgoChanakya server restarts | MEDIUM |
| G7 | **Condition Evaluation Frequency** | How often to check conditions (latency vs resource usage) | MEDIUM |
| G8 | **Historical Data for Backtesting** | Need minute-level options data for accurate backtests | MEDIUM |
| G9 | **Concurrent Strategy Conflicts** | Two strategies may want opposite positions | LOW |
| G10 | **Expiry Day Handling** | Options expire at specific times, need precise handling | MEDIUM |

### 6.2 User Experience Gaps

| # | Gap | Description | Severity |
|---|-----|-------------|----------|
| G11 | **Complex Condition Validation** | Advanced expressions may have syntax errors | MEDIUM |
| G12 | **Strategy Template Versioning** | User edits template while strategy is running | LOW |
| G13 | **Undo/Redo in Wizard** | No way to undo changes in multi-step wizard | LOW |
| G14 | **Mobile Monitoring** | No mobile app for monitoring (per your requirement) | LOW |
| G15 | **Condition Testing** | No way to test if conditions would have triggered historically | MEDIUM |

### 6.3 Business Logic Gaps

| # | Gap | Description | Severity |
|---|-----|-------------|----------|
| G16 | **Margin Calculation** | Real-time margin may differ from estimated margin | HIGH |
| G17 | **Slippage in Fast Markets** | High volatility may cause significant slippage | HIGH |
| G18 | **Greeks Calculation** | Real-time Greeks needed for Greeks-based adjustments | MEDIUM |
| G19 | **Multi-Expiry Strategies** | Calendar spreads need handling across expiries | MEDIUM |
| G20 | **Corporate Actions** | Stock splits, bonuses may affect position calculations | LOW |

---

## 7. Mitigations & Recommendations

### 7.1 Technical Mitigations

| Gap | Mitigation | Implementation |
|-----|------------|----------------|
| **G1: Rate Limits** | Implement request queue with throttling. Use batched order placement API if available | Backend queue system with 300ms delay between API calls |
| **G2: WebSocket Disconnect** | Auto-reconnect with exponential backoff. Cache last known state. Alert user if disconnected > 30s | WebSocket wrapper class with reconnect logic |
| **G3: Order Rejection** | Retry with adjusted price (if price band issue). Alert user. Log rejection reason | Order state machine with retry logic |
| **G4: Partial Fills** | Define behavior per strategy: continue/reverse/alert. Show partial position clearly | Partial fill handler with configurable behavior |
| **G5: Price Gaps** | Check conditions at market open. Use "crossed" logic instead of exact match | Gap detection in condition evaluator |
| **G6: Server Restart** | Persist strategy state to database. Resume monitoring on startup. Reconcile with broker positions | PostgreSQL state persistence + startup reconciliation |
| **G7: Evaluation Frequency** | Evaluate every 1 second for active strategies. Use efficient caching | Scheduled task with Redis caching |
| **G8: Backtest Data** | Partner with data provider (Global Data Feeds) or build historical data collection | Data pipeline for historical options data |
| **G10: Expiry Handling** | Track expiry times precisely. Auto square-off 15 mins before expiry. Handle weekly vs monthly | Expiry calendar with precise timestamps |

### 7.2 UX Mitigations

| Gap | Mitigation | Implementation |
|-----|------------|----------------|
| **G11: Condition Validation** | Real-time syntax validation. Show preview of what condition means in plain English | Expression parser with validation |
| **G12: Template Versioning** | Lock strategy config while running. Clone to edit | Version locking with clone feature |
| **G13: Undo/Redo** | Save wizard state at each step. Allow back navigation without data loss | Local state management with history |
| **G15: Condition Testing** | "Simulate" button to check if condition would have triggered in last N days | Historical condition replay feature |

### 7.3 Business Logic Mitigations

| Gap | Mitigation | Implementation |
|-----|------------|----------------|
| **G16: Margin Calculation** | Add 20% buffer to margin estimates. Check margin before each order. Use Kite Margin API | Pre-order margin validation with buffer |
| **G17: Slippage** | Set max slippage per order. Skip or retry if exceeded. Alert user | Slippage check before order confirmation |
| **G18: Greeks** | Calculate Greeks using Black-Scholes. Cache with 5-second TTL | Greeks calculation service |
| **G19: Multi-Expiry** | Handle each expiry as separate leg. Track expiry-wise P&L | Multi-expiry position tracker |

### 7.4 Recommended Safety Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SAFETY FEATURES - MUST HAVE                                                 │
│                                                                             │
│ 1. PRE-FLIGHT CHECKS (before any auto-execution)                           │
│    ☑️ Verify Kite session is active                                         │
│    ☑️ Verify sufficient margin (with 20% buffer)                            │
│    ☑️ Verify daily loss limit not breached                                  │
│    ☑️ Verify market is open and in allowed time window                      │
│    ☑️ Verify conditions are still valid (re-check before order)             │
│                                                                             │
│ 2. CIRCUIT BREAKERS                                                        │
│    ☑️ Auto-pause if 3 consecutive order rejections                          │
│    ☑️ Auto-pause if P&L swing > 50% in 5 minutes                            │
│    ☑️ Auto-pause if API errors > 5 in 1 minute                              │
│                                                                             │
│ 3. AUDIT & COMPLIANCE                                                       │
│    ☑️ Log every condition evaluation with timestamp                         │
│    ☑️ Log every order with before/after state                               │
│    ☑️ Log every user action (pause, resume, edit)                           │
│    ☑️ Daily reconciliation with broker positions                            │
│                                                                             │
│ 4. USER PROTECTION                                                          │
│    ☑️ Require checkbox confirmation before activating                       │
│    ☑️ Show estimated max loss before activation                             │
│    ☑️ Mandatory paper trade period for first-time users (suggested)         │
│    ☑️ Daily summary email/notification                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Implementation Priorities

### Phase 1: Foundation (4 weeks)

| Priority | Feature | Effort |
|----------|---------|--------|
| P1.1 | Database schema for AutoPilot strategies | 3 days |
| P1.2 | Basic condition engine (price, time, VIX) | 5 days |
| P1.3 | Order execution service with Kite API | 5 days |
| P1.4 | Strategy state machine (waiting → active → completed) | 3 days |
| P1.5 | Basic UI: Overview dashboard + strategy list | 5 days |
| P1.6 | Kill switch functionality | 2 days |

### Phase 2: Strategy Creation (3 weeks)

| Priority | Feature | Effort |
|----------|---------|--------|
| P2.1 | Strategy creation wizard (7 steps) | 7 days |
| P2.2 | Simple condition builder (dropdowns) | 3 days |
| P2.3 | Adjustment rules builder | 4 days |
| P2.4 | Review and activation flow | 3 days |
| P2.5 | Import from Strategy Library | 2 days |

### Phase 3: Advanced Features (3 weeks)

| Priority | Feature | Effort |
|----------|---------|--------|
| P3.1 | Advanced expression builder | 4 days |
| P3.2 | Visual flowchart builder | 5 days |
| P3.3 | Semi-automatic confirmation modal | 2 days |
| P3.4 | Paper trading mode | 4 days |
| P3.5 | Comprehensive logging & audit | 3 days |

### Phase 4: Testing & Polish (2 weeks)

| Priority | Feature | Effort |
|----------|---------|--------|
| P4.1 | Backtesting integration | 5 days |
| P4.2 | Edge case handling | 3 days |
| P4.3 | Performance optimization | 2 days |
| P4.4 | User testing & bug fixes | 4 days |

---

## Appendix A: Database Schema (Preliminary)

```sql
-- AutoPilot Strategies
CREATE TABLE autopilot_strategies (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- draft, active, paused, completed, error
    
    -- Base Strategy
    underlying VARCHAR(50) NOT NULL,
    expiry_type VARCHAR(50) NOT NULL, -- current_week, next_week, monthly, specific
    lots INTEGER NOT NULL,
    position_type VARCHAR(50) NOT NULL, -- intraday, positional
    legs_config JSONB NOT NULL,
    
    -- Entry Conditions
    entry_conditions JSONB NOT NULL,
    entry_logic VARCHAR(10) DEFAULT 'AND', -- AND, OR, custom
    
    -- Adjustment Rules
    adjustment_rules JSONB NOT NULL,
    
    -- Order Settings
    order_settings JSONB NOT NULL,
    
    -- Risk Settings
    risk_settings JSONB NOT NULL,
    
    -- Schedule
    schedule_config JSONB NOT NULL,
    priority INTEGER DEFAULT 1,
    
    -- Runtime State
    current_state JSONB, -- legs, P&L, adjustments made
    entry_triggered_at TIMESTAMP,
    last_adjustment_at TIMESTAMP,
    exited_at TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    version INTEGER DEFAULT 1
);

-- AutoPilot Logs
CREATE TABLE autopilot_logs (
    id UUID PRIMARY KEY,
    strategy_id UUID REFERENCES autopilot_strategies(id),
    event_type VARCHAR(50) NOT NULL, -- condition_evaluated, condition_triggered, order_placed, order_executed, error
    event_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AutoPilot Orders
CREATE TABLE autopilot_orders (
    id UUID PRIMARY KEY,
    strategy_id UUID REFERENCES autopilot_strategies(id),
    kite_order_id VARCHAR(50),
    leg_index INTEGER,
    order_type VARCHAR(20), -- entry, adjustment, exit
    instrument VARCHAR(100),
    transaction_type VARCHAR(10),
    quantity INTEGER,
    order_price DECIMAL(10,2),
    executed_price DECIMAL(10,2),
    status VARCHAR(50),
    slippage DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP
);

-- Global Settings
CREATE TABLE autopilot_user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    daily_loss_limit DECIMAL(10,2),
    max_capital DECIMAL(12,2),
    max_active_strategies INTEGER DEFAULT 3,
    notification_preferences JSONB,
    default_order_settings JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Appendix B: API Endpoints (Preliminary)

```
AutoPilot API Routes
====================

# Strategies
GET    /api/autopilot/strategies              # List all strategies
POST   /api/autopilot/strategies              # Create new strategy
GET    /api/autopilot/strategies/:id          # Get strategy details
PUT    /api/autopilot/strategies/:id          # Update strategy
DELETE /api/autopilot/strategies/:id          # Delete strategy
POST   /api/autopilot/strategies/:id/activate # Activate strategy
POST   /api/autopilot/strategies/:id/pause    # Pause strategy
POST   /api/autopilot/strategies/:id/resume   # Resume strategy
POST   /api/autopilot/strategies/:id/exit     # Force exit strategy

# Dashboard
GET    /api/autopilot/dashboard               # Overview stats
GET    /api/autopilot/dashboard/activity      # Recent activity feed

# Logs
GET    /api/autopilot/logs                    # Get logs (filterable)
GET    /api/autopilot/logs/export             # Export logs as CSV

# Settings
GET    /api/autopilot/settings                # Get global settings
PUT    /api/autopilot/settings                # Update settings

# Kill Switch
POST   /api/autopilot/kill-switch             # Emergency stop all

# Backtest
POST   /api/autopilot/backtest                # Run backtest
GET    /api/autopilot/backtest/:id            # Get backtest results

# Paper Trade
POST   /api/autopilot/paper-trade/:id/start   # Start paper trading
POST   /api/autopilot/paper-trade/:id/stop    # Stop paper trading
GET    /api/autopilot/paper-trade/:id/status  # Get paper trade status
```

---

**End of Document**

*This document should be reviewed with the development team before implementation begins.*
