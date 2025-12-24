# AlgoChanakya AutoPilot: AI-Driven Autonomous Trading System

## Vision
Transform AutoPilot into a **fully autonomous AI trading system** that requires **zero human intervention** during market hours (9:15 AM - 3:30 PM IST), making intelligent decisions to maximize profits for Indian options traders.

## User Requirements
| Aspect | Choice |
|--------|--------|
| **Core Goal** | Maximize profits through opportunity capture |
| **Automation Level** | Zero intervention ("set and forget") |
| **Decision Making** | AI-driven within user-defined guardrails |
| **Trading Style** | Both intraday (MIS) and positional (NRML) |

## Current State (75-80% Complete)
- 40 backend services (conditions, adjustments, orders, monitoring)
- 17 database tables
- 12 frontend views, 41+ components
- WebSocket real-time updates
- Kill switch, trailing stops, DTE exits, Greeks tracking

## Critical Gaps to Fill
1. **Auto-deployment scheduler** - Manual activation required each day
2. **Position sync with broker** - No reconciliation with Zerodha app
3. **Market regime detection** - No automatic market classification
4. **AI recommendation engine** - No autonomous strategy selection

---

# IMPLEMENTATION PHASES

## Phase 1: Market Intelligence Engine (Weeks 1-2)

### 1.1 Market Regime Classifier
**Goal:** Automatically detect market conditions in real-time

**Regime Categories:**
| Regime | Indicators | Best Strategies |
|--------|------------|-----------------|
| TRENDING_BULLISH | ADX > 25, Price > EMA50, RSI < 70 | Bull Call Spread, Call Butterfly |
| TRENDING_BEARISH | ADX > 25, Price < EMA50, RSI > 30 | Bear Put Spread, Put Butterfly |
| RANGEBOUND | ADX < 20, Tight Bollinger Bands | Iron Condor, Short Strangle |
| VOLATILE | VIX > 20, Wide ATR | Long Straddle, Iron Butterfly |
| PRE_EVENT | 2-3 days before budget/RBI/expiry | Reduce positions, far OTM only |
| EVENT_DAY | Budget, RBI policy, major earnings | No new positions, hedge existing |

**New Files:**
```
backend/app/services/ai/
├── __init__.py
├── market_regime_classifier.py   # Regime detection logic
├── feature_extractor.py          # Extract ML features from market data
└── indicators.py                 # RSI, ADX, EMA, ATR calculations
```

**Database Schema:**
```sql
CREATE TABLE ai_market_regime_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    regime_type VARCHAR(30) NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,

    -- Indicators
    spot_nifty DECIMAL(10,2),
    vix DECIMAL(6,2),
    adx_value DECIMAL(6,2),
    rsi_14 DECIMAL(6,2),
    ema_9 DECIMAL(10,2),
    ema_21 DECIMAL(10,2),
    ema_50 DECIMAL(10,2),
    atr_14 DECIMAL(10,2),
    oi_pcr DECIMAL(5,2),
    iv_rank DECIMAL(5,2),

    feature_vector JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**API Endpoints:**
- `GET /api/v1/ai/regime/current` - Get current regime with confidence
- `GET /api/v1/ai/regime/history` - Historical regime data

**Frontend Component:**
- `MarketRegimeIndicator.vue` - Dashboard widget showing current regime

**Files to Modify:**
- `backend/app/services/market_data.py` - Add historical OHLC fetching
- `backend/app/main.py` - Register AI router
- `frontend/src/views/autopilot/DashboardView.vue` - Add regime indicator

---

## Phase 2: Position Sync with Broker (Week 3)

### 2.1 Real-Time Position Reconciliation
**Goal:** Auto-detect when user trades via Zerodha app and sync state

**Logic:**
```
Every 30 seconds during market hours:
1. Fetch positions from Kite API
2. Compare with AutoPilot tracked positions
3. Detect: new_external, closed_externally, qty_mismatch
4. Generate sync event and notify user
5. Auto-update AutoPilot state (or ask for confirmation)
```

**New Files:**
```
backend/app/services/ai/
└── position_reconciliation.py    # Sync logic
```

**Database Schema:**
```sql
CREATE TABLE ai_position_sync_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    strategy_id BIGINT REFERENCES autopilot_strategies(id),

    event_type VARCHAR(30) NOT NULL, -- new_external, closed_externally, qty_mismatch
    tradingsymbol VARCHAR(50) NOT NULL,

    autopilot_quantity INTEGER,
    broker_quantity INTEGER,

    action_taken VARCHAR(30), -- imported, updated, ignored
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**API Endpoints:**
- `GET /api/v1/ai/positions/sync-status` - Current sync status
- `POST /api/v1/ai/positions/sync` - Trigger manual sync
- `GET /api/v1/ai/positions/discrepancies` - List unresolved issues

**Frontend Components:**
- `PositionSyncStatus.vue` - Sync indicator with warning badge
- `PositionDiscrepancyModal.vue` - Resolve mismatches

**Files to Modify:**
- `backend/app/services/strategy_monitor.py` - Add sync hooks
- `backend/app/websocket/manager.py` - Add POSITION_SYNC_ALERT message type

---

## Phase 3: Auto-Deployment Scheduler (Weeks 4-5)

### 3.1 Scheduled Strategy Deployment
**Goal:** Automatically deploy strategies at configured times based on market conditions

**Daily Flow:**
```
8:45 AM: Pre-market analysis
├── Fetch overnight data (SGX Nifty, global cues)
├── Run regime classifier
├── Select best strategy template for regime
└── Configure legs with optimal strikes

9:15-9:30 AM: Market open window
├── Wait for initial price discovery (5-15 min)
├── Verify conditions still match
└── Deploy strategy OR skip if conditions changed

During Day: Monitor for re-deployment after exits
```

**New Files:**
```
backend/app/services/ai/
├── daily_scheduler.py           # APScheduler-based job management
└── deployment_executor.py       # Execute scheduled deployments
```

**Database Schema:**
```sql
CREATE TABLE ai_scheduled_deployments (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),

    -- Schedule
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL DEFAULT '09:20',

    -- Strategy Selection
    selected_template_id BIGINT REFERENCES autopilot_templates(id),
    underlying VARCHAR(20) NOT NULL,
    lots INTEGER DEFAULT 1,
    legs_config JSONB NOT NULL,

    -- Market Context
    regime_at_schedule VARCHAR(30),
    vix_at_schedule DECIMAL(6,2),
    confidence_score DECIMAL(5,2),

    -- Execution
    status VARCHAR(20) DEFAULT 'pending', -- pending, deployed, skipped, failed
    deployed_strategy_id BIGINT REFERENCES autopilot_strategies(id),
    deployed_at TIMESTAMP WITH TIME ZONE,
    skip_reason TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE ai_user_config (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) UNIQUE,

    -- Auto-Deployment
    auto_deploy_enabled BOOLEAN DEFAULT FALSE,
    deploy_time TIME DEFAULT '09:20',
    deploy_days VARCHAR(20)[] DEFAULT ARRAY['MON','TUE','WED','THU','FRI'],
    skip_event_days BOOLEAN DEFAULT TRUE,

    -- Preferences
    preferred_underlyings VARCHAR(20)[] DEFAULT ARRAY['NIFTY','BANKNIFTY'],
    max_lots INTEGER DEFAULT 1,
    risk_tolerance VARCHAR(20) DEFAULT 'moderate',
    max_daily_loss DECIMAL(12,2) DEFAULT 10000,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**API Endpoints:**
- `GET /api/v1/ai/deployments` - List scheduled deployments
- `POST /api/v1/ai/deployments` - Create new scheduled deployment
- `DELETE /api/v1/ai/deployments/{id}` - Cancel deployment
- `GET /api/v1/ai/config` - Get user AI configuration
- `PUT /api/v1/ai/config` - Update AI configuration

**Frontend Views:**
- `DeploymentSchedulerView.vue` - Manage scheduled deployments
- `AIConfigView.vue` - Configure AI settings

**Frontend Components:**
- `DeploymentCalendar.vue` - Calendar view of deployments
- `DeploymentStatusCard.vue` - Individual deployment status

---

## Phase 4: AI Strategy Recommendation Engine (Weeks 6-7)

### 4.1 Intelligent Strategy Selection
**Goal:** Recommend optimal strategies based on current market conditions

**Recommendation Logic:**
```
Input: Current market snapshot
├── Regime classification
├── VIX level & IV rank
├── OI PCR & buildup patterns
├── Day of week, DTE
└── Historical performance in similar conditions

Output: Top 3 strategies with confidence scores
├── Strategy template ID
├── Recommended strikes (delta-based)
├── Expected P&L range
├── Risk metrics
└── Explanation (why this strategy now)
```

**New Files:**
```
backend/app/services/ai/
├── strategy_recommendation_engine.py  # Core recommendation logic
├── dynamic_strike_selector.py         # Optimal strike selection
└── explainability.py                  # Decision explanations
```

**Database Schema:**
```sql
CREATE TABLE ai_strategy_performance (
    id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT REFERENCES autopilot_strategies(id),
    template_id BIGINT REFERENCES autopilot_templates(id),
    underlying VARCHAR(20) NOT NULL,

    -- Context at Entry
    trade_date DATE NOT NULL,
    regime_at_entry VARCHAR(30),
    vix_at_entry DECIMAL(6,2),
    iv_rank_at_entry DECIMAL(5,2),
    dte_at_entry INTEGER,

    -- Outcomes
    gross_pnl DECIMAL(14,2),
    net_pnl DECIMAL(14,2),
    win BOOLEAN,
    roi_pct DECIMAL(8,4),
    exit_reason VARCHAR(50),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE ai_decisions_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    strategy_id BIGINT REFERENCES autopilot_strategies(id),

    decision_type VARCHAR(30) NOT NULL, -- strategy_selection, adjustment, exit
    input_features JSONB NOT NULL,
    predictions JSONB,
    selected_action VARCHAR(50),
    confidence DECIMAL(5,2),
    reasoning TEXT,

    was_correct BOOLEAN, -- filled after outcome
    outcome_pnl DECIMAL(14,2),

    decision_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Dynamic Strike Selection:**
```
Base delta varies by regime:
- RANGEBOUND: Delta 0.12-0.16 (closer, more premium)
- TRENDING: Delta 0.08-0.12 (further OTM, more room)
- VOLATILE: Delta 0.06-0.10 (far OTM, safety)
- PRE_EVENT: Delta 0.05-0.08 (very far, reduce gamma)
```

**API Endpoints:**
- `GET /api/v1/ai/recommendations` - Get strategy recommendations
- `GET /api/v1/ai/recommendations/{id}/explain` - Get explanation
- `POST /api/v1/ai/recommendations/{id}/accept` - Accept and deploy
- `POST /api/v1/ai/recommendations/{id}/reject` - Reject with feedback

**Frontend Views:**
- `RecommendationsView.vue` - Browse AI recommendations

**Frontend Components:**
- `RecommendationCard.vue` - Single recommendation display
- `ConfidenceGauge.vue` - Visual confidence indicator
- `AIDecisionExplainer.vue` - Modal with decision explanation

---

## Phase 5: Intelligent Adjustment Engine (Weeks 8-9)

### 5.1 AI-Powered Adjustments
**Goal:** Automatically make smart adjustments without human intervention

**Adjustment Triggers & Actions:**
| Trigger | AI Decision | Actions Considered |
|---------|-------------|-------------------|
| Delta breach | Rebalance needed | Shift leg, add hedge, roll |
| Profit target | Lock profits | Partial exit, tighten stops |
| Loss threshold | Protect capital | Hedge, exit, roll down |
| Time decay | Capture theta | Exit early, let decay |
| IV spike | Opportunity | Adjust strikes, exit |
| Expiry near | Gamma risk | Roll, close, convert |

**AI Adjustment Flow:**
```
When trigger fires:
1. Evaluate all possible adjustments
2. Simulate P&L impact (what-if analysis)
3. Score by: Expected P&L, new Greeks, margin, cost
4. Select action with best risk-adjusted score
5. Execute automatically (full auto mode)
6. Log decision for learning
```

**New Files:**
```
backend/app/services/ai/
└── ai_adjustment_advisor.py     # Intelligent adjustment selection
```

**Files to Modify:**
- `backend/app/services/adjustment_engine.py` - Integrate AI advisor
- `backend/app/services/suggestion_engine.py` - Add AI confidence scoring

**API Endpoints:**
- `GET /api/v1/ai/strategies/{id}/suggested-adjustments` - Get AI suggestions
- `POST /api/v1/ai/strategies/{id}/adjustments/{adj}/execute` - Execute
- `POST /api/v1/ai/strategies/{id}/adjustments/{adj}/feedback` - Feedback

**Frontend Components:**
- `AIAdjustmentSuggestionCard.vue` - Show AI suggestion with confidence

---

## Phase 6: Self-Learning Pipeline (Weeks 10-12)

### 6.1 Continuous Improvement System
**Goal:** Learn from every trade to improve future decisions

**Daily Learning Cycle (4:00 PM):**
```
1. Extract completed trades from trade_journal
2. Compute features: entry conditions, during-trade events, exit
3. Label outcomes: Win/Loss, magnitude, reason
4. Update strategy scoring model
5. Update regime classifier if misclassified
6. Generate daily insights report
```

**New Files:**
```
backend/app/services/ai/
├── learning_pipeline.py         # Post-market analysis
├── model_registry.py            # Model versioning
└── ab_testing.py                # Test new models
```

**Database Schema:**
```sql
CREATE TABLE ai_model_registry (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- regime_classifier, strategy_scorer
    version VARCHAR(20) NOT NULL,

    model_path VARCHAR(500),
    accuracy DECIMAL(5,2),
    f1_score DECIMAL(5,2),

    is_production BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE ai_learning_reports (
    id BIGSERIAL PRIMARY KEY,
    report_date DATE NOT NULL UNIQUE,

    total_trades INTEGER,
    winning_trades INTEGER,
    win_rate DECIMAL(5,2),
    total_pnl DECIMAL(14,2),

    regime_accuracy DECIMAL(5,2),
    strategy_accuracy DECIMAL(5,2),

    insights JSONB,
    model_updates JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**API Endpoints:**
- `GET /api/v1/ai/learning/daily-report` - Daily learning report
- `GET /api/v1/ai/learning/model-performance` - Model metrics

**Frontend Views:**
- `LearningInsightsView.vue` - View AI learning reports

---

## Phase 7: Full Autonomy Mode (Weeks 13-14)

### 7.1 Complete Hands-Off Trading
**Goal:** System handles everything from strategy selection to exit

**Full Auto Mode Flow:**
```
Pre-Market (8:45 AM):
├── Analyze market conditions
├── Classify regime
├── Select optimal strategy
└── Schedule deployment

Market Open (9:20 AM):
├── Verify conditions
├── Deploy strategy with AI-selected strikes
└── Begin monitoring

During Day:
├── Real-time position sync
├── AI-driven adjustments
├── Smart profit booking
└── Dynamic stop management

Market Close:
├── Auto-exit intraday positions
├── Manage positional strategies
└── Log all decisions

Post-Market (4:00 PM):
├── Learning pipeline
├── Performance analysis
└── Model updates
```

**User Guardrails (Configurable):**
- Max daily loss limit
- Max lots per strategy
- Allowed underlyings
- Allowed strategy types
- Excluded days (events)

**Emergency Controls:**
- Kill Switch (always available)
- Pause AI (switch to manual)
- Override any decision

---

# CRITICAL FILES SUMMARY

## New Files to Create

### Backend Services (`backend/app/services/ai/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `market_regime_classifier.py` | Regime detection |
| `feature_extractor.py` | ML feature extraction |
| `indicators.py` | RSI, ADX, EMA, ATR |
| `position_reconciliation.py` | Broker sync |
| `daily_scheduler.py` | Auto-deployment |
| `deployment_executor.py` | Execute deployments |
| `strategy_recommendation_engine.py` | Strategy selection |
| `dynamic_strike_selector.py` | Optimal strikes |
| `ai_adjustment_advisor.py` | Smart adjustments |
| `explainability.py` | Decision explanations |
| `learning_pipeline.py` | Post-market learning |
| `model_registry.py` | Model management |

### Backend API (`backend/app/api/v1/ai/`)
| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `router.py` | Main AI router |
| `regime.py` | Regime endpoints |
| `deployments.py` | Deployment endpoints |
| `recommendations.py` | Recommendation endpoints |
| `config.py` | User config endpoints |
| `learning.py` | Learning endpoints |

### Frontend Views (`frontend/src/views/ai/`)
| File | Purpose |
|------|---------|
| `AIConfigView.vue` | AI settings |
| `DeploymentSchedulerView.vue` | Scheduled deployments |
| `RecommendationsView.vue` | AI recommendations |
| `LearningInsightsView.vue` | Learning reports |

### Frontend Components (`frontend/src/components/ai/`)
| File | Purpose |
|------|---------|
| `MarketRegimeIndicator.vue` | Regime display |
| `PositionSyncStatus.vue` | Sync indicator |
| `DeploymentCalendar.vue` | Calendar view |
| `RecommendationCard.vue` | Strategy recommendation |
| `ConfidenceGauge.vue` | Confidence display |
| `AIDecisionExplainer.vue` | Explanation modal |
| `LearningReportCard.vue` | Daily insights |

## Existing Files to Modify

| File | Modification |
|------|--------------|
| `backend/app/main.py` | Register AI router, initialize scheduler |
| `backend/app/services/strategy_monitor.py` | Add AI hooks (regime, sync, adjustments) |
| `backend/app/services/market_data.py` | Add historical OHLC, bulk quotes |
| `backend/app/services/adjustment_engine.py` | Integrate AI advisor |
| `backend/app/services/suggestion_engine.py` | Add AI confidence scoring |
| `backend/app/models/autopilot.py` | Add AI columns (ai_selected, regime_at_entry) |
| `backend/app/websocket/manager.py` | Add AI message types |
| `frontend/src/stores/autopilot.js` | Add AI state management |
| `frontend/src/views/autopilot/DashboardView.vue` | Add regime indicator, recommendations |
| `frontend/src/router/index.js` | Add AI routes |

---

# DATABASE MIGRATIONS

## Migration 1: AI Core Tables
```sql
-- ai_market_regime_snapshots
-- ai_user_config
-- ai_scheduled_deployments
```

## Migration 2: Performance Tracking
```sql
-- ai_strategy_performance
-- ai_decisions_log
```

## Migration 3: Position Sync
```sql
-- ai_position_sync_events
```

## Migration 4: Learning System
```sql
-- ai_model_registry
-- ai_learning_reports
```

## Migration 5: Strategy Table Updates
```sql
ALTER TABLE autopilot_strategies ADD COLUMN ai_selected BOOLEAN DEFAULT FALSE;
ALTER TABLE autopilot_strategies ADD COLUMN regime_at_entry VARCHAR(30);
ALTER TABLE autopilot_strategies ADD COLUMN ai_confidence DECIMAL(5,2);
```

---

# SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Win Rate | > 65% |
| Average Daily P&L | > INR 5,000 |
| Sharpe Ratio | > 1.5 |
| Max Drawdown | < 15% |
| AI Confidence Accuracy | > 75% |
| User Intervention Rate | < 10% |

---

# RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| AI makes bad trade | Kill switch always available, max loss limits |
| Position sync delay | 30-second polling, manual sync button |
| Model degradation | Performance monitoring, auto-rollback |
| Regime misclassification | Confidence threshold (70%), fallback rules |
| Over-trading | Max strategies per day limit |

---

# IMPLEMENTATION ORDER

| Phase | Duration | Features |
|-------|----------|----------|
| **Phase 1** | Weeks 1-2 | Market Regime Classifier |
| **Phase 2** | Week 3 | Position Sync with Broker |
| **Phase 3** | Weeks 4-5 | Auto-Deployment Scheduler |
| **Phase 4** | Weeks 6-7 | AI Strategy Recommendations |
| **Phase 5** | Weeks 8-9 | Intelligent Adjustments |
| **Phase 6** | Weeks 10-12 | Self-Learning Pipeline |
| **Phase 7** | Weeks 13-14 | Full Autonomy Mode |

**Total Duration: 14 weeks**
