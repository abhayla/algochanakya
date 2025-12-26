# AutoPilot AI - Architecture Review Document

**Document Version:** 1.0
**Date:** December 2025
**Status:** For External Review
**Confidentiality:** Proprietary - Redacted for External Review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [AI/ML Approach](#3-aiml-approach)
4. [Trading Logic](#4-trading-logic)
5. [Risk Management](#5-risk-management)
6. [Performance & Monitoring](#6-performance--monitoring)
7. [Questions for Reviewers](#7-questions-for-reviewers)

---

## 1. Executive Summary

### 1.1 Project Vision

**AutoPilot AI** is a fully autonomous options trading system designed for the Indian equity derivatives market (NSE F&O). The system operates with **zero human intervention during market hours** (9:15 AM - 3:30 PM IST), making intelligent trading decisions to maximize profits while strictly enforcing risk limits.

### 1.2 Key Differentiators

| Feature | Description |
|---------|-------------|
| **100% Autonomous** | No manual intervention required during market hours |
| **Multi-Regime Adaptation** | Adjusts strategy selection based on 6 distinct market regimes |
| **Self-Learning** | Daily ML model retraining using multi-factor decision quality scoring |
| **Safety-First** | Mandatory paper trading graduation + multiple hard limits |
| **Position Sync** | Real-time detection of external trades via WebSocket + polling |
| **Explainable AI** | Natural language explanations via Claude API integration |

### 1.3 Implementation Status

**Current Status:** Production-Ready (v1.0)

**Development Timeline:**
- Weeks 1-4 (MVP): Market intelligence, auto-deployment, paper trading ✅
- Weeks 5-8 (Enhancement): ML scoring, self-learning, analytics ✅
- Weeks 9-12 (Optimization): Kelly sizing, backtesting, portfolio management ✅

**Components Delivered:**
- 23 Backend AI Services
- 7 REST API Routers
- 3 Frontend Vue Views + 5 Components
- 4 Database Tables (5000+ records in paper trading)
- 15+ API Endpoints

### 1.4 Feedback Areas Requested

We are seeking feedback on:

1. **Architecture Scalability** - Can this design handle 100+ concurrent users with low latency?
2. **ML Model Approach** - Is the feature engineering sound? Should we use ensemble methods?
3. **Risk Management** - Are the safety mechanisms sufficient? Any blind spots?
4. **Trading Logic** - Is the regime classification robust? Alternative approaches?
5. **System Reliability** - Failure modes we haven't considered? Recovery strategies?

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Frontend (Vue 3)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ AI Settings  │  │ Paper Trade  │  │  Analytics   │              │
│  │     View     │  │  Dashboard   │  │   Dashboard  │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                              │ REST API + WebSocket
┌─────────────────────────────────────────────────────────────────────┐
│                       Backend (FastAPI)                              │
│  ┌──────────────────────────────────────────────────────┐           │
│  │              AI Services Layer                        │           │
│  ├──────────────────────────────────────────────────────┤           │
│  │  Market Intelligence                                  │           │
│  │  ├─ Market Regime Classifier (6 regimes)            │           │
│  │  ├─ Technical Indicators (RSI, ADX, EMA, ATR, BB)   │           │
│  │  └─ Historical Data Service (Kite API + Cache)      │           │
│  ├──────────────────────────────────────────────────────┤           │
│  │  Strategy Engine                                      │           │
│  │  ├─ Strategy Recommender (Regime-Strategy Matrix)   │           │
│  │  ├─ Strike Selector (Delta-based + VIX adjust)      │           │
│  │  └─ ML Strategy Scorer (XGBoost/LightGBM)          │           │
│  ├──────────────────────────────────────────────────────┤           │
│  │  Execution & Monitoring                              │           │
│  │  ├─ Daily Scheduler (Pre/Post market + Deploy)     │           │
│  │  ├─ Deployment Executor (Order placement)          │           │
│  │  ├─ Position Sync (WebSocket + 60s poll)           │           │
│  │  └─ AI Monitor (Decision making loop)              │           │
│  ├──────────────────────────────────────────────────────┤           │
│  │  Learning & Optimization                             │           │
│  │  ├─ Feedback Scorer (Multi-factor quality)         │           │
│  │  ├─ Learning Pipeline (Daily retraining)           │           │
│  │  ├─ Kelly Calculator (Optimal position sizing)     │           │
│  │  └─ Backtester (Historical simulation)             │           │
│  └──────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────────┐
│                      External Services                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ Kite Connect │  │  Claude API  │  │   Redis      │              │
│  │ (Zerodha)    │  │  (Anthropic) │  │   Cache      │              │
│  │ - Orders     │  │ - Explanations│  │ - 1m TTL    │              │
│  │ - Historical │  │ - Pre/Post    │  │ - 1h TTL    │              │
│  │ - WebSocket  │  │   Market      │  │             │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

**Backend:**
- **Framework:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL (async via asyncpg)
- **Cache:** Redis (async)
- **ML:** XGBoost, LightGBM, scikit-learn
- **Scheduler:** APScheduler (for daily jobs)
- **Broker API:** Kite Connect (Zerodha)
- **AI:** Anthropic Claude Sonnet 4.5

**Frontend:**
- **Framework:** Vue.js 3 + Vite
- **State:** Pinia stores
- **Charts:** Chart.js
- **Styling:** Tailwind CSS

**Infrastructure:**
- **Deployment:** [REDACTED]
- **Database:** PostgreSQL [REDACTED]
- **Cache:** Redis [REDACTED]

### 2.3 Data Flow

**Trading Day Timeline:**

```
08:45 AM → Pre-Market Analysis (Claude API)
           ├─ Fetch global cues, SGX Nifty
           ├─ Classify expected regime
           └─ Generate market brief

09:15 AM → Market Opens
           └─ Start real-time monitoring

09:20 AM → Auto-Deployment Window
           ├─ Classify current regime (live indicators)
           ├─ Get strategy recommendations
           ├─ Apply ML scoring (if model available)
           ├─ Check user limits & graduation status
           ├─ Execute deployment if criteria met
           └─ Log decision with reasoning

09:20 AM - 03:20 PM → Monitoring Loop (every 5 seconds)
           ├─ Update position P&L via WebSocket
           ├─ Check adjustment triggers
           ├─ Evaluate AI adjustment suggestions
           ├─ Execute adjustments (if full-auto mode)
           └─ Reconcile positions every 60s

03:20 PM → Auto-Exit Intraday Positions
           └─ Close positions marked as intraday

03:30 PM → Market Closes
           └─ Stop monitoring

04:00 PM → Post-Market Learning
           ├─ Extract completed trades
           ├─ Calculate multi-factor decision scores
           ├─ Update ML model if threshold met
           ├─ Generate learning report (Claude API)
           └─ Store insights for next day
```

### 2.4 Component Interactions

**Regime Classification Flow:**
```
Historical Data Service → OHLC (50 days daily, 5min intraday)
                 ↓
Technical Indicators → RSI, ADX, EMA, ATR, Bollinger Bands
                 ↓
Market Regime Classifier → Apply Rule-Based Logic
                 ↓
Regime Result (Type + Confidence + Reasoning)
```

**Strategy Recommendation Flow:**
```
Regime Result + User Config → Strategy Recommender
                 ↓
Filter by allowed_strategies → Apply Regime-Strategy Matrix
                 ↓
[Optional] ML Strategy Scorer → Predict success probability
                 ↓
Top 3 Recommendations (sorted by confidence)
                 ↓
Strike Selector → Delta-based selection + VIX adjustments
                 ↓
Deployment-Ready Strategy
```

---

## 3. AI/ML Approach

### 3.1 Market Regime Classification

**Objective:** Classify current market conditions into 6 distinct regimes to enable regime-appropriate strategy selection.

**Regime Types:**

| Regime | Rules | Confidence Factors |
|--------|-------|-------------------|
| **TRENDING_BULLISH** | ADX > 25 AND Price > EMA50 AND RSI < 70 | ADX strength, EMA distance, RSI level |
| **TRENDING_BEARISH** | ADX > 25 AND Price < EMA50 AND RSI > 30 | ADX strength, EMA distance, RSI level |
| **RANGEBOUND** | ADX < 20 AND BB Width < 2% | Low ADX, tight Bollinger Bands |
| **VOLATILE** | VIX > 20 OR ATR > 1.5× avg | VIX level, ATR percentile |
| **PRE_EVENT** | 1-2 days before Budget/RBI/Expiry | Event calendar proximity |
| **EVENT_DAY** | Budget day, RBI policy, major earnings | Event calendar match |

**Confidence Scoring:**
- Start with base score based on how well indicators match regime definition
- Adjust for: indicator strength, consistency across timeframes, VIX confirmation
- Final score: 0-100 (skip trading if < 70%)

**Implementation:**
- Rule-based (no ML for regime classification - intentional for explainability)
- Event calendar integration (pre-loaded + API sync)
- Multi-timeframe validation (5min, 15min, daily)

### 3.2 Strategy Recommendation Engine

**Strategy Universe:** 15+ option strategies across 5 categories

| Category | Strategies |
|----------|-----------|
| **Income** | Iron Condor, Short Strangle, Short Straddle, Iron Butterfly |
| **Bullish** | Bull Call Spread, Bull Put Spread, Long Call, Short Put |
| **Bearish** | Bear Put Spread, Bear Call Spread, Long Put, Short Call |
| **Volatile** | Long Straddle, Long Strangle |
| **Advanced** | Butterfly Spread, Ratio Spreads, Call/Put Backspreads |

**Regime-Strategy Scoring Matrix:**

```python
REGIME_STRATEGY_SCORES = {
    "RANGEBOUND": {
        "iron_condor": 90,
        "short_strangle": 85,
        "iron_butterfly": 80,
        # ... (redacted exact values)
    },
    "TRENDING_BULLISH": {
        "bull_call_spread": 85,
        "bull_put_spread": 80,
        # ... (redacted)
    },
    # ... (other regimes redacted)
}
```

**Scoring Adjustments:**
- **VIX Adjustment:** [REDACTED - proprietary formula]
- **Trend Strength:** [REDACTED - proprietary formula]
- **User Preferences:** Filter by allowed_strategies in user config

**Output:** Top 3 strategies with confidence scores and natural language reasoning

### 3.3 ML Model Architecture

**Model Type:** XGBoost / LightGBM (user-selectable)

**Training Pipeline:**
1. Extract completed trades from `autopilot_trade_journal`
2. Calculate 30 features across 5 categories
3. Label trades by multi-factor decision quality score (0-100)
4. Train/test split: 80/20 with time-based splitting
5. Hyperparameter tuning via GridSearchCV
6. Early stopping (10 rounds, validation metric: F1 score)
7. Model evaluation: Accuracy, Precision, Recall, F1, ROC-AUC
8. Save to disk with versioning + metadata

**Feature Engineering (30 features):**

| Category | Features | Description |
|----------|----------|-------------|
| **Market State** (6) | regime_encoded, vix_level, vix_percentile_30d, spot_distance_from_ema50_pct, iv_rank, iv_percentile | Current market conditions |
| **Indicators** (8) | rsi_14, adx_14, atr_14_pct, bb_width_pct, ema_9, ema_21, ema_50, macd | Technical indicators |
| **Options Data** (4) | oi_pcr, max_pain_distance_pct, iv_rank, expected_premium | Options-specific metrics |
| **Time Features** (5) | day_of_week, hour_of_day, dte, minutes_since_open, days_to_monthly_expiry | Temporal patterns |
| **Strategy Features** (7) | strategy_type_encoded, delta_target, theta_target, max_loss, max_profit, breakeven_range_pct, capital_required | Strategy characteristics |

**Model Retraining Trigger:**
- Automatic: After every 25 new completed trades (if win rate > 55%)
- Manual: Via API endpoint
- Rollback: If new model performs worse than active model (A/B testing for 10 trades)

**Model Registry:**
- Database-backed versioning (`ai_model_registry` table)
- Stores: version, accuracy, precision, recall, F1, training_date
- Supports activation/rollback

### 3.4 Strike Selection Logic

**Approach:** Delta-based selection with VIX adjustments

**Delta Targets by Regime:**
- **RANGEBOUND:** [REDACTED] (closer to ATM, more premium)
- **TRENDING:** [REDACTED] (further OTM, more room)
- **VOLATILE:** [REDACTED] (far OTM, safety)
- **PRE_EVENT:** [REDACTED] (very far, reduce gamma)

**VIX Adjustments:**
- High VIX (> 20): [REDACTED]
- Low VIX (< 15): [REDACTED]

**Strike Rounding:**
- Round to nearest strike step (NIFTY: 50, BANKNIFTY: 100, FINNIFTY: 50)
- Validate strike exists in available expiry

### 3.5 Claude AI Integration

**Usage:** Natural language explanations for transparency and user education

**Three Daily API Calls:**

1. **Pre-Market Analysis (8:45 AM):**
   - Input: Global indices, SGX Nifty, overnight news
   - Output: Market brief (2-3 paragraphs) with expected regime and risks
   - Model: Claude Sonnet 4.5 (streaming)

2. **Decision Explanation (9:20 AM):**
   - Input: Regime result, recommended strategy, indicators snapshot
   - Output: Why this strategy was selected, risks to watch, exit criteria
   - Model: Claude Sonnet 4.5

3. **Post-Market Review (4:00 PM):**
   - Input: Completed trades, P&L, decision quality scores
   - Output: What went well, what went wrong, lessons learned
   - Model: Claude Sonnet 4.5 (long context)

**Rate Limiting:**
- 3 calls/day/user (pre, decision, post)
- Fallback: Rule-based explanations if API fails or quota exceeded

**API Key Management:**
- User provides their own Anthropic API key
- Stored encrypted in database
- Validated before enabling AI explanations

### 3.6 Self-Learning Pipeline

**Daily Learning Cycle (4:00 PM):**

```
1. Extract Completed Trades
   └─ Query autopilot_trade_journal for today's closed positions

2. Calculate Decision Quality Scores
   ├─ P&L Outcome (40%): Profit/loss relative to max profit
   ├─ Risk Management (25%): Stayed within limits? No violations?
   ├─ Entry Quality (15%): Entry price vs optimal? Slippage?
   ├─ Adjustment Quality (15%): Adjustments improved position?
   └─ Exit Quality (5%): Exit timing vs optimal?

3. Update ML Model (if threshold met)
   ├─ Extract features for new trades
   ├─ Retrain model with updated dataset
   ├─ Evaluate new model on holdout set
   └─ Activate if performance improves

4. Generate Learning Report
   ├─ Total trades, win rate, P&L
   ├─ Average decision quality score
   ├─ Regime accuracy (did regime prediction match reality?)
   ├─ Claude-generated insights
   └─ Store in ai_learning_reports table
```

**Multi-Factor Decision Quality Score:**

```
Quality Score = (P&L × 0.40) + (Risk × 0.25) + (Entry × 0.15) +
                (Adjustment × 0.15) + (Exit × 0.05)

Where each component is scored 0-100 based on:
- P&L: [REDACTED - proprietary formula]
- Risk: No limit violations (100) vs violations (0)
- Entry: [REDACTED]
- Adjustment: [REDACTED]
- Exit: [REDACTED]
```

**Retraining Conditions:**
- Minimum 25 new trades since last training
- Win rate > 55% on new trades
- Average decision quality > 60

---

## 4. Trading Logic

### 4.1 Auto-Deployment Logic

**Deployment Time:** User-configurable (default: 9:20 AM)

**Deployment Checklist:**
```
1. Check if today is enabled day (Mon-Fri by default)
2. Skip if event_day AND user.skip_event_days = true
3. Check max_strategies_per_day limit not reached
4. Check max_lots_per_day limit not reached
5. Classify current market regime
6. Check regime confidence > 70%
7. Get strategy recommendations (filtered by allowed_strategies)
8. Check recommendation confidence > user.min_confidence_to_trade
9. Check VIX < user.max_vix_to_trade
10. Select strikes using Delta-based selector
11. Calculate position size (Fixed/Tiered/Kelly mode)
12. Check capital available
13. Place orders via Kite Connect
14. Log deployment decision with reasoning
```

**Skip Reasons:**
- `EVENT_DAY_SKIP` - Event day and user opted to skip
- `LOW_CONFIDENCE` - Regime or strategy confidence < 70%
- `HIGH_VIX` - VIX exceeds user limit
- `DAILY_LIMIT_REACHED` - Max strategies or lots limit hit
- `INSUFFICIENT_CAPITAL` - Not enough capital for position
- `NOT_GRADUATED` - Paper trading graduation not completed

### 4.2 Position Sizing Modes

**Three Modes:** Fixed, Tiered, Kelly

#### Fixed Mode
- Always deploy `base_lots` (default: 1)
- Simple, predictable, no dynamic adjustment

#### Tiered Mode (Default)
- Adjust lots based on strategy confidence score
- User-configurable tiers (default):

```json
{
  "tiers": [
    {"name": "SKIP", "min": 0, "max": 59, "multiplier": 0},
    {"name": "LOW", "min": 60, "max": 74, "multiplier": 1.0},
    {"name": "MEDIUM", "min": 75, "max": 84, "multiplier": 1.5},
    {"name": "HIGH", "min": 85, "max": 100, "multiplier": 2.0}
  ]
}
```

Example: Confidence = 82% → MEDIUM tier → 1.5× base_lots

#### Kelly Criterion Mode
- Requires 100+ completed trades for reliability
- Formula: `Kelly% = (Win Rate × Avg Win / Avg Loss - (1 - Win Rate)) / (Avg Win / Avg Loss)`
- Half-Kelly for safety: `Lots = (Kelly% × 0.5 × Capital) / Max Loss per Lot`
- Fallback to Tiered if insufficient data

### 4.3 Position Sync Architecture

**Problem:** Detect when user manually opens/closes positions via Kite app or web

**Dual Sync Mechanism:**

1. **WebSocket Order Updates (Real-Time)**
   - Subscribe to Kite order update WebSocket
   - Detect order fills not placed by AutoPilot
   - Flag as `EXTERNAL_ORDER_DETECTED`
   - Latency: < 5 seconds

2. **Position Reconciliation (Every 60 Seconds)**
   - Fetch positions from Kite API
   - Compare with AutoPilot tracked positions
   - Detect: `new_external`, `closed_externally`, `qty_mismatch`
   - Auto-import or alert user
   - Fallback if WebSocket disconnects

**Sync Events Table:**
```sql
CREATE TABLE ai_position_sync_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID,
    event_type VARCHAR(30),  -- new_external, closed_externally, qty_mismatch
    tradingsymbol VARCHAR(50),
    autopilot_quantity INTEGER,
    broker_quantity INTEGER,
    action_taken VARCHAR(30),  -- imported, updated, ignored, user_resolved
    detected_at TIMESTAMP
);
```

**User Actions:**
- Import external position into AutoPilot tracking
- Ignore (don't track)
- Manually resolve mismatch

### 4.4 Adjustment Logic

**Trigger Types:** 7 types (P&L, Greeks, Spot, Premium, Time, VIX, Manual)

**AI Adjustment Advisor:**
- When trigger fires, evaluate all possible adjustments
- Simulate P&L impact of each adjustment (what-if analysis)
- Score adjustments by: Risk/Reward (40%), Cost (20%), Greeks (20%), P&L (20%)
- Categorize: Defensive, Offensive, Neutral
- Execute automatically if in full-auto mode, else suggest to user

**Adjustment Actions:** 7 types
- Roll strikes
- Add/remove legs
- Convert strategy
- Close position
- Add hedge
- Reduce quantity
- Widen spreads

---

## 5. Risk Management

### 5.1 Safety Layers

**Layer 1: Hard Limits (Non-Overridable)**
- `max_lots_per_strategy` (default: 2)
- `max_lots_per_day` (default: 6)
- `max_strategies_per_day` (default: 5)
- `weekly_loss_limit` (default: ₹50,000)
- `max_vix_to_trade` (default: 25)
- `min_dte_to_enter` (default: 2 days)

**Layer 2: Confidence Thresholds**
- Regime classification: min 70% confidence
- Strategy recommendation: min 60% confidence (user-configurable)
- ML model predictions: min 65% confidence

**Layer 3: Paper Trading Graduation**
- Required before live trading enabled
- Criteria: 15 days active + 25 trades + 55% win rate
- Reset if win rate drops below 45% for 5+ consecutive days

**Layer 4: Kill Switch**
- Emergency stop all AI strategies
- Accessible from dashboard (1-click)
- Pauses all monitoring, order placement, adjustments
- Requires manual re-enable

**Layer 5: Semi-Auto Mode**
- High-risk actions require user confirmation
- Examples: Large adjustments, strategy conversions, re-entry
- Confirmation request sent via WebSocket
- Timeout: 60 seconds (auto-cancel if no response)

### 5.2 Paper Trading Graduation

**Objectives:**
1. Validate AI performance in paper mode before risking real capital
2. Ensure AI decision-making is profitable and stable
3. Build user confidence through transparent tracking

**Graduation Criteria:**

| Metric | Requirement | Rationale |
|--------|-------------|-----------|
| **Days Active** | 15 days | Ensure consistency across market conditions |
| **Total Trades** | 25 trades | Sufficient sample size for statistical validity |
| **Win Rate** | 55%+ | Profitable edge validation |
| **No Violations** | 0 hard limit violations | Risk discipline enforcement |

**Auto-Reset Conditions:**
- Win rate drops below 45% for 5 consecutive days
- 3+ hard limit violations in a week
- User manually resets

**Dashboard:**
- Progress bars for each criterion
- Recent trades log with P&L
- Decision quality trend chart

### 5.3 Position Sync Safety

**Sync Lag Alerts:**
- Alert if position sync lag > 30 seconds
- Auto-pause AI if lag > 5 minutes
- Dashboard indicator: Green (< 5s), Yellow (5-30s), Red (> 30s)

**Mismatch Handling:**
- Quantity mismatches: Alert user, suggest reconciliation
- External trades: Option to import or ignore
- Closed positions: Update AutoPilot tracking immediately

### 5.4 Portfolio-Level Risk

**Multi-Strategy Risk Management:**

**Portfolio Greeks Limits:**
- Max Portfolio Delta: [REDACTED]
- Max Portfolio Gamma: [REDACTED]
- Max Portfolio Theta: [REDACTED]

**Risk Score Calculation:**
```
Risk Score = (Delta × 0.30) + (Gamma × 0.30) +
             (Concentration × 0.25) + (Correlation × 0.15)

- Delta Risk: Absolute portfolio delta / capital
- Gamma Risk: Portfolio gamma × spot volatility
- Concentration: % of capital in single strategy
- Correlation: Average pairwise correlation between strategies

Score: 0-100 (pause deployment if > 80)
```

**Rebalancing Triggers:**
- Concentration > 40% in single underlying
- Portfolio delta > [REDACTED]
- Correlation > 0.7 between 2+ strategies

---

## 6. Performance & Monitoring

### 6.1 Latency Targets

| Operation | Target | Measurement Method |
|-----------|--------|-------------------|
| Regime Classification | < 500ms | End-to-end API call |
| Strategy Recommendation | < 1s | Including ML scoring |
| ML Strategy Scoring | < 2s | Batch prediction (3 strategies) |
| Order Placement | < 3s | API call to Kite |
| Position Sync | < 500ms | WebSocket to database update |
| Historical Data Fetch | < 300ms | From Redis cache (hit) |

### 6.2 Success Rate Targets

| Service | Target | Measurement |
|---------|--------|-------------|
| Historical Data Fetch | 99%+ | API calls successful |
| Indicator Calculation | 99.9%+ | Non-null results |
| Order Placement | 95%+ | Kite API dependent |
| WebSocket Connection | 99%+ | Uptime percentage |
| Regime Classification | 75%+ | Accuracy vs manual labeling |
| ML Model Predictions | 70%+ | F1 score on test set |

### 6.3 Key Metrics Monitored

**Real-Time Metrics:**
1. **AI Decision Rate** - Decisions per hour (should match market activity)
2. **Position Sync Lag** - Delay between Kite and local state
3. **WebSocket Connection Status** - Connected/Disconnected
4. **Active Strategies Count** - Per user

**Daily Metrics:**
1. **Win Rate** - Winning trades / Total trades
2. **Average P&L** - Total P&L / Trading days
3. **Decision Quality Score** - Average across all decisions
4. **Paper Trading Progress** - Days, trades, win rate vs targets
5. **ML Model Accuracy** - Current active model performance

**Weekly Metrics:**
1. **Sharpe Ratio** - Annualized return / volatility
2. **Max Drawdown** - Peak to trough decline
3. **Regime Accuracy** - Correct regime classifications
4. **Error Rate** - Errors per 1000 requests

### 6.4 Alert Triggers

**Critical Alerts (Immediate Action):**
- Win rate < 45% for 5+ consecutive days
- Portfolio risk score > 80
- Position sync lag > 5 minutes
- Error rate > 5%
- ML model accuracy < 60%

**Warning Alerts (Review Within 24h):**
- Win rate < 50% for 3 consecutive days
- Position sync lag > 30 seconds
- Error rate > 2%
- ML model accuracy < 65%
- Kite API rate limit approaching

**Info Alerts:**
- Paper trading graduation achieved
- ML model retrained successfully
- Daily learning report generated

### 6.5 Resource Usage

**Per-User Limits:**
- Memory: ~200MB per active session
- CPU: < 10% during normal operation
- Redis cache: ~50MB per user
- Database connections: 5-10 concurrent

**Scaling Considerations:**
- Horizontal scaling: Run multiple FastAPI workers
- Redis cluster for cache distribution
- Database connection pooling (max 100 connections)
- ML model loaded once per worker (shared memory)

---

## 7. Questions for Reviewers

We value your expert feedback on the following areas:

### 7.1 Architecture & Scalability

1. **Concurrent Users:** Can this architecture handle 100+ concurrent users during market hours without performance degradation? What bottlenecks do you foresee?

2. **Database Design:** The current design uses 4 main AI tables. Should we denormalize for performance, or is the current schema optimal?

3. **Caching Strategy:** We use Redis with 1-min TTL for intraday data and 1-hour for daily. Is this appropriate, or should we use a different caching strategy?

4. **WebSocket Scaling:** Position sync uses WebSocket + 60s polling. Alternative approaches you'd recommend?

5. **Async vs Sync:** We use async/await throughout. Any scenarios where sync would be more appropriate?

### 7.2 AI/ML Approach

6. **Regime Classification:** We use rule-based regime classification for explainability. Would an ML-based classifier be more robust? Trade-offs?

7. **Feature Engineering:** Are there critical features we're missing for strategy success prediction? (Current: 30 features)

8. **Model Selection:** XGBoost vs LightGBM vs Ensemble methods (stacking/bagging). What do you recommend for this use case?

9. **Retraining Frequency:** Currently daily if 25+ new trades. Too frequent? Too infrequent?

10. **Cold Start Problem:** New users have no trade history. Should we use a global model initially, then personalize?

### 7.3 Risk Management

11. **Paper Trading Duration:** 15 days + 25 trades. Is this sufficient validation, or should we require 30+ days?

12. **Hard Limits:** Are our default limits conservative enough? (max 2 lots/strategy, 6 lots/day)

13. **Kelly Criterion:** We use half-Kelly for safety. Is this appropriate for options trading, or should we use quarter-Kelly?

14. **Position Sync Failures:** What should happen if position sync fails for > 5 minutes? Auto-exit all positions? Just pause?

15. **Black Swan Events:** How should the system respond to circuit breakers, extreme volatility, or market halts?

### 7.4 Trading Logic

16. **Strike Selection:** Delta-based selection with VIX adjustments. Alternative methods you'd recommend (e.g., probability-based, IV rank-based)?

17. **Strategy Universe:** 15+ strategies. Should we narrow this for beginners, or keep the full universe with risk warnings?

18. **Adjustment Logic:** What-if simulation + multi-factor scoring. Any edge cases we haven't considered?

19. **Deployment Timing:** Fixed time (9:20 AM) vs dynamic based on regime stability. Pros/cons?

20. **Exit Strategy:** Currently time-based (3:20 PM for intraday). Should we use dynamic exits based on regime changes?

### 7.5 System Reliability

21. **Failure Modes:** What critical failure modes have we not addressed? (e.g., Kite API downtime, database failures)

22. **Recovery Strategy:** If the system crashes mid-day, how should it resume? Re-evaluate positions? Skip trading?

23. **Data Quality:** Historical data gaps or errors. How should we validate and handle bad data?

24. **API Rate Limits:** Kite API has rate limits. How should we handle throttling during high-frequency operations?

25. **Monitoring Blind Spots:** Are there critical metrics we're not monitoring that we should be?

### 7.6 Open Questions

26. **Multi-Account Support:** Currently single account per user. Architecture changes needed for managing multiple demat accounts?

27. **Tax Reporting:** Should AI auto-generate tax reports (capital gains, etc.) or leave to user?

28. **Backtesting Realism:** Our backtester uses historical data. How to account for slippage, impact cost, and order rejection?

29. **Strategy Attribution:** In multi-strategy portfolios, how to accurately attribute P&L to individual strategies?

30. **Explainability vs Performance:** We prioritize explainability (rule-based regime). Would you sacrifice explainability for better performance?

---

## Appendix A: Technology Choices Rationale

**Why FastAPI?**
- Async/await support for concurrent operations
- Automatic OpenAPI docs generation
- Type safety with Pydantic
- WebSocket support built-in

**Why XGBoost/LightGBM over Neural Networks?**
- Smaller dataset (< 10K trades per user)
- Faster training (minutes vs hours)
- Better interpretability (feature importance)
- Lower inference latency

**Why Rule-Based Regime Classification?**
- Explainability required for user trust
- Consistent behavior (no model drift)
- Easier to debug and adjust
- Fast execution (no model loading)

**Why Claude API?**
- Best-in-class natural language explanations
- Long context (200K tokens) for post-market analysis
- Streaming support for pre-market briefs
- Lower cost than GPT-4 for analysis tasks

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Regime** | Market condition classification (e.g., TRENDING_BULLISH) |
| **Confidence Score** | AI's certainty about a decision (0-100%) |
| **Paper Trading** | Simulated trading without real capital |
| **Graduation** | Transitioning from paper to live trading |
| **Delta** | Rate of change of option price with respect to spot price |
| **Greeks** | Sensitivity measures (Delta, Gamma, Theta, Vega) |
| **Kill Switch** | Emergency stop for all AI operations |
| **Semi-Auto Mode** | AI suggests, user confirms before execution |
| **Position Sync** | Keeping AutoPilot positions in sync with broker |
| **DTE** | Days to Expiry |
| **VIX** | Volatility Index (India VIX) |
| **ATR** | Average True Range (volatility indicator) |
| **ADX** | Average Directional Index (trend strength) |
| **RSI** | Relative Strength Index (momentum indicator) |
| **EMA** | Exponential Moving Average |

---

## Contact & Feedback

**Submission Guidelines:**
- Please provide feedback organized by section (e.g., "3.2 Strategy Recommendation Engine")
- Rate critical issues (Blocker / Major / Minor / Enhancement)
- Include specific recommendations, not just problem statements
- Feel free to challenge any design decisions with rationale

**Thank You!**

We deeply appreciate your time and expertise in reviewing this architecture. Your feedback will directly shape the production deployment and future enhancements of AutoPilot AI.

---

**Document End**

*Last Updated: December 2025*
*Version: 1.0*
*Confidentiality: Proprietary - For External Review Only*
