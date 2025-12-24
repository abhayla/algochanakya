# AutoPilot AI Automation - Complete Implementation Plan

## Vision
Transform AlgoChanakya AutoPilot into a **100% autonomous AI trading system** that requires **zero human intervention** during market hours (9:15 AM - 3:30 PM IST), making intelligent decisions to maximize profits for Indian options traders.

---

## Executive Summary

| Aspect | Decision |
|--------|----------|
| **Autonomy Level** | Full autonomy with hard limits (AI cannot override safety) |
| **AI Architecture** | Hybrid: Rules + ML (real-time) + Claude API (scheduled analysis) |
| **Position Sync** | WebSocket order updates (real-time) + 60-sec reconciliation |
| **Position Sizing** | Tiered (configurable confidence thresholds) |
| **Strategy Universe** | User-selected subset with conservative defaults |
| **Learning System** | Multi-factor scoring (P&L + Risk + Execution quality) |
| **Validation** | Paper trading: 15 days + 25 trades + 55% win rate |
| **Data Source** | Kite Historical API + NSE Bhavcopy backup |

---

## Implementation Timeline

```
Week 1-4:   MVP Phase (Core Autonomy)
Week 5-8:   Enhancement Phase (ML + Learning)
Week 9-12:  Optimization Phase (Advanced Features)
```

---

# PART 1: MVP PHASE (Weeks 1-4)

Goal: Get AI trading autonomously with basic intelligence in paper mode.

---

## Week 1: Market Intelligence Engine

### 1.1 Historical Data Integration

**Files to Create:**
```
backend/app/services/ai/
├── __init__.py
├── historical_data.py      # Kite Historical API wrapper
└── indicators.py           # RSI, ADX, EMA, ATR calculations
```

**`historical_data.py` - Key Functions:**
```python
class HistoricalDataService:
    async def get_ohlc(underlying: str, interval: str, from_date, to_date) -> List[OHLC]
    async def get_daily_candles(underlying: str, days: int = 50) -> List[OHLC]
    async def get_intraday_candles(underlying: str, interval: str = "5minute") -> List[OHLC]

    # Cache in Redis with 1-minute TTL for intraday, 1-hour for daily
```

**`indicators.py` - Technical Indicators:**
```python
class TechnicalIndicators:
    def calculate_rsi(prices: List[float], period: int = 14) -> float
    def calculate_adx(high: List, low: List, close: List, period: int = 14) -> float
    def calculate_ema(prices: List[float], period: int) -> float
    def calculate_atr(high: List, low: List, close: List, period: int = 14) -> float
    def calculate_bollinger_bands(prices: List, period: int = 20, std_dev: int = 2) -> BBands
```

**Files to Modify:**
- `backend/app/services/market_data.py` - Add historical OHLC fetching via Kite API

### 1.2 Market Regime Classifier

**Files to Create:**
```
backend/app/services/ai/
└── market_regime.py        # Rule-based regime classification
```

**Regime Categories:**
| Regime | Rule |
|--------|------|
| TRENDING_BULLISH | ADX > 25 AND Price > EMA50 AND RSI < 70 |
| TRENDING_BEARISH | ADX > 25 AND Price < EMA50 AND RSI > 30 |
| RANGEBOUND | ADX < 20 AND BB Width < 2% |
| VOLATILE | VIX > 20 OR ATR > 1.5x average |
| PRE_EVENT | 1-2 days before Budget/RBI/Expiry |
| EVENT_DAY | Budget day, RBI policy, major earnings |

**`market_regime.py` - Key Functions:**
```python
class MarketRegimeClassifier:
    async def classify(underlying: str) -> RegimeResult:
        """Returns regime type with confidence score"""

    async def get_indicators_snapshot(underlying: str) -> IndicatorsSnapshot:
        """Returns all calculated indicators"""

    def is_event_day(date: date) -> Tuple[bool, str]:
        """Check if date is a known event day"""
```

**Database Migration - `ai_market_snapshots`:**
```sql
CREATE TABLE ai_market_snapshots (
    id BIGSERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP WITH TIME ZONE NOT NULL,
    underlying VARCHAR(20) NOT NULL,

    -- Regime
    regime_type VARCHAR(30) NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,

    -- Spot & VIX
    spot_price DECIMAL(10,2) NOT NULL,
    vix DECIMAL(6,2),

    -- Indicators
    rsi_14 DECIMAL(6,2),
    adx_14 DECIMAL(6,2),
    ema_9 DECIMAL(10,2),
    ema_21 DECIMAL(10,2),
    ema_50 DECIMAL(10,2),
    atr_14 DECIMAL(10,2),
    bb_upper DECIMAL(10,2),
    bb_lower DECIMAL(10,2),
    bb_width_pct DECIMAL(6,2),

    -- OI Data
    oi_pcr DECIMAL(5,2),
    max_pain DECIMAL(10,2),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ai_market_snapshots_time ON ai_market_snapshots(snapshot_time DESC);
CREATE INDEX idx_ai_market_snapshots_underlying ON ai_market_snapshots(underlying, snapshot_time DESC);
```

### 1.3 Week 1 Deliverables Checklist

- [ ] `backend/app/services/ai/__init__.py`
- [ ] `backend/app/services/ai/historical_data.py`
- [ ] `backend/app/services/ai/indicators.py`
- [ ] `backend/app/services/ai/market_regime.py`
- [ ] Migration: `ai_market_snapshots` table
- [ ] Unit tests for indicators (RSI, ADX, EMA, ATR)
- [ ] Unit tests for regime classifier
- [ ] API endpoint: `GET /api/v1/ai/regime/current`
- [ ] API endpoint: `GET /api/v1/ai/regime/indicators`

---

## Week 2: AI Configuration & Settings

### 2.1 AI User Configuration

**Database Migration - `ai_user_config`:**
```sql
CREATE TABLE ai_user_config (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) UNIQUE,

    -- Autonomy Settings
    ai_enabled BOOLEAN DEFAULT FALSE,
    autonomy_mode VARCHAR(20) DEFAULT 'paper',  -- paper, live

    -- Auto-Deployment
    auto_deploy_enabled BOOLEAN DEFAULT FALSE,
    deploy_time TIME DEFAULT '09:20',
    deploy_days VARCHAR(10)[] DEFAULT ARRAY['MON','TUE','WED','THU','FRI'],
    skip_event_days BOOLEAN DEFAULT TRUE,
    skip_weekly_expiry BOOLEAN DEFAULT FALSE,

    -- Strategy Universe (JSONB array of template IDs)
    allowed_strategies JSONB DEFAULT '[]',

    -- Position Sizing
    sizing_mode VARCHAR(20) DEFAULT 'tiered',  -- fixed, tiered, kelly
    base_lots INTEGER DEFAULT 1,
    confidence_tiers JSONB DEFAULT '[
        {"name": "SKIP", "min": 0, "max": 59, "multiplier": 0},
        {"name": "LOW", "min": 60, "max": 74, "multiplier": 1.0},
        {"name": "MEDIUM", "min": 75, "max": 84, "multiplier": 1.5},
        {"name": "HIGH", "min": 85, "max": 100, "multiplier": 2.0}
    ]',

    -- AI-Specific Limits
    max_lots_per_strategy INTEGER DEFAULT 2,
    max_lots_per_day INTEGER DEFAULT 6,
    max_strategies_per_day INTEGER DEFAULT 5,
    min_confidence_to_trade DECIMAL(5,2) DEFAULT 60.00,
    max_vix_to_trade DECIMAL(5,2) DEFAULT 25.00,
    min_dte_to_enter INTEGER DEFAULT 2,
    weekly_loss_limit DECIMAL(12,2) DEFAULT 50000.00,

    -- Preferred Underlyings
    preferred_underlyings VARCHAR(20)[] DEFAULT ARRAY['NIFTY', 'BANKNIFTY'],

    -- Paper Trading Graduation
    paper_start_date DATE,
    paper_trades_completed INTEGER DEFAULT 0,
    paper_win_rate DECIMAL(5,2) DEFAULT 0,
    paper_total_pnl DECIMAL(14,2) DEFAULT 0,
    paper_graduation_approved BOOLEAN DEFAULT FALSE,

    -- Claude API
    claude_api_key_encrypted TEXT,
    enable_ai_explanations BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 2.2 AI Settings UI

**Files to Create:**
```
frontend/src/views/ai/
├── AISettingsView.vue      # Main AI configuration page
└── components/
    ├── AutonomySettings.vue
    ├── StrategySelector.vue
    ├── PositionSizingConfig.vue
    ├── LimitsConfig.vue
    └── PaperTradingStatus.vue
```

**AISettingsView.vue Sections:**
1. **Autonomy Mode** - Paper/Live toggle with graduation status
2. **Trading Schedule** - Deploy time, days, event skipping
3. **Strategy Universe** - Checkboxes for allowed strategies
4. **Position Sizing** - Tier configuration with preview
5. **Hard Limits** - Non-overridable safety limits
6. **AI Explanations** - Claude API key, enable/disable

### 2.3 API Endpoints

**Files to Create:**
```
backend/app/api/v1/ai/
├── __init__.py
├── router.py               # Main AI router
├── config.py               # User config endpoints
└── schemas.py              # Pydantic models
```

**Endpoints:**
```
GET  /api/v1/ai/config                    # Get user AI config
PUT  /api/v1/ai/config                    # Update AI config
GET  /api/v1/ai/config/strategies         # Get allowed strategies
PUT  /api/v1/ai/config/strategies         # Update allowed strategies
GET  /api/v1/ai/config/sizing             # Get position sizing config
PUT  /api/v1/ai/config/sizing             # Update position sizing
POST /api/v1/ai/config/validate-claude    # Validate Claude API key
```

### 2.4 Week 2 Deliverables Checklist

- [ ] Migration: `ai_user_config` table
- [ ] `backend/app/api/v1/ai/__init__.py`
- [ ] `backend/app/api/v1/ai/router.py`
- [ ] `backend/app/api/v1/ai/config.py`
- [ ] `backend/app/api/v1/ai/schemas.py`
- [ ] `frontend/src/views/ai/AISettingsView.vue`
- [ ] `frontend/src/views/ai/components/AutonomySettings.vue`
- [ ] `frontend/src/views/ai/components/StrategySelector.vue`
- [ ] `frontend/src/views/ai/components/PositionSizingConfig.vue`
- [ ] `frontend/src/views/ai/components/LimitsConfig.vue`
- [ ] `frontend/src/views/ai/components/PaperTradingStatus.vue`
- [ ] Register AI routes in `frontend/src/router/index.js`
- [ ] Add AI settings link to navigation

---

## Week 3: Auto-Deployment & Position Sync

### 3.1 Strategy Recommendation Engine

**Files to Create:**
```
backend/app/services/ai/
├── strategy_recommender.py    # Strategy selection logic
├── strike_selector.py         # Dynamic strike selection
└── claude_advisor.py          # Claude API integration
```

**`strategy_recommender.py` - Key Functions:**
```python
class StrategyRecommender:
    async def get_recommendations(
        underlying: str,
        regime: RegimeResult,
        user_config: AIUserConfig
    ) -> List[StrategyRecommendation]:
        """
        Returns top 3 strategy recommendations with confidence scores.
        Filters by user's allowed strategies.
        """

    async def score_strategy(
        template: StrategyTemplate,
        regime: RegimeResult,
        market_data: MarketSnapshot
    ) -> float:
        """
        Scores strategy suitability for current conditions.
        Returns 0-100 confidence score.
        """
```

**Strategy-Regime Mapping (Rule-Based):**
```python
REGIME_STRATEGY_SCORES = {
    "RANGEBOUND": {
        "iron_condor": 90,
        "short_strangle": 85,
        "iron_butterfly": 80,
        "short_straddle": 75,
    },
    "TRENDING_BULLISH": {
        "bull_call_spread": 85,
        "bull_put_spread": 80,
        "call_ratio_backspread": 70,
    },
    "TRENDING_BEARISH": {
        "bear_put_spread": 85,
        "bear_call_spread": 80,
    },
    "VOLATILE": {
        "long_straddle": 80,
        "long_strangle": 75,
        "iron_butterfly": 70,  # wide wings
    },
    "PRE_EVENT": {
        "iron_condor": 60,  # far OTM only
    },
    "EVENT_DAY": {}  # No new positions
}
```

**`strike_selector.py` - Dynamic Strike Selection:**
```python
class DynamicStrikeSelector:
    async def select_strikes(
        underlying: str,
        strategy_type: str,
        regime: RegimeResult,
        expiry: date
    ) -> List[StrikeSelection]:
        """
        Selects optimal strikes based on regime.

        Delta targets by regime:
        - RANGEBOUND: 0.12-0.16 (closer, more premium)
        - TRENDING: 0.08-0.12 (further OTM, more room)
        - VOLATILE: 0.06-0.10 (far OTM, safety)
        - PRE_EVENT: 0.05-0.08 (very far, reduce gamma)
        """
```

**`claude_advisor.py` - Claude API Integration:**
```python
class ClaudeAdvisor:
    async def get_premarket_analysis(market_data: dict) -> str:
        """
        8:45 AM - Analyze global cues, SGX Nifty, news.
        Returns natural language market brief.
        """

    async def explain_recommendation(
        recommendation: StrategyRecommendation,
        regime: RegimeResult
    ) -> str:
        """
        Explain why this strategy was chosen.
        Returns user-friendly explanation.
        """

    async def get_postmarket_review(
        trades: List[Trade],
        performance: dict
    ) -> str:
        """
        4:00 PM - Analyze day's trades.
        Returns lessons learned, what went right/wrong.
        """
```

### 3.2 Auto-Deployment Scheduler

**Files to Create:**
```
backend/app/services/ai/
├── daily_scheduler.py         # APScheduler-based job management
└── deployment_executor.py     # Execute scheduled deployments
```

**`daily_scheduler.py` - Scheduled Jobs:**
```python
class DailyScheduler:
    """
    Scheduled jobs using APScheduler:

    8:45 AM  - Pre-market analysis (Claude API)
    9:15 AM  - Market open, start monitoring
    9:20 AM  - Execute deployment (if conditions met)
    3:20 PM  - Auto-exit intraday positions
    3:30 PM  - Market close, stop monitoring
    4:00 PM  - Post-market review (Claude API)
    """

    async def run_premarket_analysis(user_id: UUID) -> PremarketReport
    async def check_and_deploy(user_id: UUID) -> Optional[DeploymentResult]
    async def run_postmarket_review(user_id: UUID) -> PostmarketReport
```

**Database Migration - `ai_scheduled_deployments`:**
```sql
CREATE TABLE ai_scheduled_deployments (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),

    -- Schedule
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL DEFAULT '09:20',

    -- Strategy Selection
    underlying VARCHAR(20) NOT NULL,
    selected_template_id BIGINT REFERENCES autopilot_templates(id),
    recommended_strikes JSONB NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL,
    lots INTEGER NOT NULL,

    -- Market Context
    regime_at_schedule VARCHAR(30),
    vix_at_schedule DECIMAL(6,2),
    spot_at_schedule DECIMAL(10,2),

    -- Execution
    status VARCHAR(20) DEFAULT 'pending',  -- pending, deployed, skipped, failed
    deployed_strategy_id BIGINT REFERENCES autopilot_strategies(id),
    deployed_at TIMESTAMP WITH TIME ZONE,
    skip_reason TEXT,
    error_message TEXT,

    -- AI Explanation
    recommendation_explanation TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3.3 Real-Time Position Sync

**Files to Create:**
```
backend/app/services/ai/
└── position_sync.py           # WebSocket + polling sync
```

**`position_sync.py` - Position Reconciliation:**
```python
class PositionSyncService:
    """
    Dual sync mechanism:
    1. WebSocket order updates (real-time)
    2. Position reconciliation (every 60 seconds)
    """

    async def handle_order_update(order_data: dict):
        """
        Called when WebSocket receives order update.
        Detects if order was placed externally (Kite app).
        """

    async def reconcile_positions(user_id: UUID) -> SyncResult:
        """
        Compare AutoPilot tracked positions with broker positions.
        Detect: new_external, closed_externally, qty_mismatch
        """

    async def import_external_position(
        position: BrokerPosition,
        strategy_id: Optional[int]
    ) -> AutoPilotPositionLeg:
        """
        Import externally opened position into AutoPilot tracking.
        """
```

**Database Migration - `ai_position_sync_events`:**
```sql
CREATE TABLE ai_position_sync_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    strategy_id BIGINT REFERENCES autopilot_strategies(id),

    event_type VARCHAR(30) NOT NULL,  -- new_external, closed_externally, qty_mismatch
    tradingsymbol VARCHAR(50) NOT NULL,

    autopilot_quantity INTEGER,
    broker_quantity INTEGER,

    action_taken VARCHAR(30),  -- imported, updated, ignored, user_resolved
    resolved_at TIMESTAMP WITH TIME ZONE,

    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Modify Existing Files:**
- `backend/app/services/kite_ticker.py` - Add order update handler
- `backend/app/websocket/manager.py` - Add `POSITION_SYNC_ALERT`, `EXTERNAL_ORDER_DETECTED` message types

### 3.4 Week 3 Deliverables Checklist

- [ ] `backend/app/services/ai/strategy_recommender.py`
- [ ] `backend/app/services/ai/strike_selector.py`
- [ ] `backend/app/services/ai/claude_advisor.py`
- [ ] `backend/app/services/ai/daily_scheduler.py`
- [ ] `backend/app/services/ai/deployment_executor.py`
- [ ] `backend/app/services/ai/position_sync.py`
- [ ] Migration: `ai_scheduled_deployments` table
- [ ] Migration: `ai_position_sync_events` table
- [ ] API: `GET /api/v1/ai/recommendations`
- [ ] API: `POST /api/v1/ai/deploy`
- [ ] API: `GET /api/v1/ai/sync/status`
- [ ] API: `POST /api/v1/ai/sync/reconcile`
- [ ] WebSocket: Order update handler
- [ ] WebSocket: Position sync alerts
- [ ] Unit tests for strategy recommender
- [ ] Unit tests for position sync

---

## Week 4: Integration & Paper Trading

### 4.1 End-to-End Flow Integration

**Modify `backend/app/services/strategy_monitor.py`:**
```python
# Add AI hooks to existing monitor loop

async def _process_ai_strategies(self):
    """
    Called every 5 seconds during market hours.

    For AI-managed strategies:
    1. Check if regime changed significantly
    2. Evaluate AI adjustment suggestions
    3. Execute adjustments if in full-auto mode
    4. Update AI decision log
    """
```

**Files to Create:**
```
backend/app/services/ai/
└── ai_monitor.py              # AI-specific monitoring
```

### 4.2 AI Decision Logging

**Database Migration - `ai_decisions_log`:**
```sql
CREATE TABLE ai_decisions_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    strategy_id BIGINT REFERENCES autopilot_strategies(id),

    decision_type VARCHAR(30) NOT NULL,  -- strategy_selection, entry, adjustment, exit

    -- Input Context
    regime_at_decision VARCHAR(30),
    vix_at_decision DECIMAL(6,2),
    spot_at_decision DECIMAL(10,2),
    indicators_snapshot JSONB,

    -- Decision
    action_taken VARCHAR(50) NOT NULL,
    confidence DECIMAL(5,2) NOT NULL,
    reasoning TEXT,

    -- Outcome (filled after trade completes)
    outcome_pnl DECIMAL(14,2),
    outcome_score DECIMAL(5,2),  -- Multi-factor quality score
    was_correct BOOLEAN,

    decision_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    outcome_recorded_at TIMESTAMP WITH TIME ZONE
);
```

### 4.3 Paper Trading Dashboard

**Files to Create:**
```
frontend/src/views/ai/
└── PaperTradingView.vue       # Paper trading progress dashboard
```

**Dashboard Sections:**
1. **Graduation Progress** - Days, trades, win rate vs. targets
2. **Recent AI Decisions** - List of decisions with explanations
3. **Performance Metrics** - P&L chart, win rate, drawdown
4. **Regime History** - Market regime over time
5. **Position Sync Status** - Real-time sync indicator

### 4.4 Frontend Components

**Files to Create:**
```
frontend/src/components/ai/
├── MarketRegimeIndicator.vue   # Shows current regime with confidence
├── AIDecisionCard.vue          # Single AI decision with explanation
├── GraduationProgress.vue      # Paper trading progress bars
├── PositionSyncStatus.vue      # Sync indicator with alerts
└── AIActivityFeed.vue          # Real-time AI activity
```

### 4.5 Week 4 Deliverables Checklist

- [ ] `backend/app/services/ai/ai_monitor.py`
- [ ] Migration: `ai_decisions_log` table
- [ ] Integrate AI hooks into `strategy_monitor.py`
- [ ] `frontend/src/views/ai/PaperTradingView.vue`
- [ ] `frontend/src/components/ai/MarketRegimeIndicator.vue`
- [ ] `frontend/src/components/ai/AIDecisionCard.vue`
- [ ] `frontend/src/components/ai/GraduationProgress.vue`
- [ ] `frontend/src/components/ai/PositionSyncStatus.vue`
- [ ] `frontend/src/components/ai/AIActivityFeed.vue`
- [ ] End-to-end paper trading test
- [ ] Claude API integration test
- [ ] WebSocket position sync test
- [ ] Add `anthropic` to `requirements.txt`

---

## MVP Success Criteria

After Week 4, the system must be able to:

| Criterion | Target |
|-----------|--------|
| Classify market regime | Correctly identify regime with >70% accuracy |
| Recommend strategies | Suggest appropriate strategies for regime |
| Auto-deploy | Deploy strategy at 9:20 AM without user action |
| Monitor positions | Track P&L, Greeks in real-time |
| Sync with broker | Detect external trades within 60 seconds |
| Log decisions | Record all AI decisions with reasoning |
| Generate explanations | Provide Claude-powered explanations |
| Paper trade | Complete trades in paper mode |
| Track graduation | Show progress toward live trading |

---

# PART 2: ENHANCEMENT PHASE (Weeks 5-8)

Goal: Add ML-based scoring and self-learning capabilities.

---

## Week 5: ML Strategy Scorer

### 5.1 Feature Engineering

**Files to Create:**
```
backend/app/services/ai/ml/
├── __init__.py
├── feature_extractor.py       # Extract ML features from market data
└── strategy_scorer.py         # XGBoost/LightGBM scorer
```

**Features for ML Model:**
```python
FEATURES = [
    # Market State
    "regime_encoded",          # One-hot encoded regime
    "vix_level",
    "vix_percentile_30d",
    "spot_distance_from_ema50_pct",

    # Indicators
    "rsi_14",
    "adx_14",
    "atr_14_pct",
    "bb_width_pct",

    # Options Data
    "iv_rank",
    "iv_percentile",
    "oi_pcr",
    "max_pain_distance_pct",

    # Time Features
    "day_of_week",
    "dte",
    "minutes_since_open",

    # Strategy Features
    "strategy_type_encoded",
    "delta_target",
    "expected_premium",
]
```

### 5.2 Model Training Pipeline

**Files to Create:**
```
backend/app/services/ai/ml/
├── training_pipeline.py       # Model training
├── model_registry.py          # Model versioning
└── models/                    # Saved model files
```

**Database Migration - `ai_model_registry`:**
```sql
CREATE TABLE ai_model_registry (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL,  -- strategy_scorer, regime_classifier
    version VARCHAR(20) NOT NULL,

    model_path VARCHAR(500),

    -- Metrics
    accuracy DECIMAL(5,2),
    precision_score DECIMAL(5,2),
    recall DECIMAL(5,2),
    f1_score DECIMAL(5,2),

    -- Training Info
    training_samples INTEGER,
    training_date TIMESTAMP WITH TIME ZONE,

    is_production BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 5.3 Week 5 Deliverables

- [ ] `backend/app/services/ai/ml/feature_extractor.py`
- [ ] `backend/app/services/ai/ml/strategy_scorer.py`
- [ ] `backend/app/services/ai/ml/training_pipeline.py`
- [ ] `backend/app/services/ai/ml/model_registry.py`
- [ ] Migration: `ai_model_registry` table
- [ ] Initial model training script
- [ ] Model evaluation metrics

---

## Week 6: Intelligent Adjustment Engine

### 6.1 AI-Powered Adjustments

**Files to Create:**
```
backend/app/services/ai/
└── ai_adjustment_advisor.py   # Intelligent adjustment selection
```

**Adjustment Decision Logic:**
```python
class AIAdjustmentAdvisor:
    async def evaluate_adjustments(
        strategy: AutoPilotStrategy,
        current_state: PositionState
    ) -> List[AdjustmentSuggestion]:
        """
        When trigger fires:
        1. Evaluate all possible adjustments
        2. Simulate P&L impact (what-if analysis)
        3. Score by: Expected P&L, new Greeks, margin, cost
        4. Select action with best risk-adjusted score
        5. Execute automatically (full auto mode)
        """
```

### 6.2 Week 6 Deliverables

- [ ] `backend/app/services/ai/ai_adjustment_advisor.py`
- [ ] Integrate with existing `adjustment_engine.py`
- [ ] Integrate with existing `suggestion_engine.py`
- [ ] What-if simulation for adjustments
- [ ] Auto-execute adjustments in full-auto mode

---

## Week 7: Self-Learning Pipeline

### 7.1 Learning Pipeline

**Files to Create:**
```
backend/app/services/ai/
├── learning_pipeline.py       # Post-market analysis
└── feedback_scorer.py         # Multi-factor decision scoring
```

**`feedback_scorer.py` - Decision Quality Score:**
```python
class FeedbackScorer:
    """
    Multi-factor decision quality score (0-100):

    - P&L Outcome: 40%
    - Risk Management: 25%
    - Entry Quality: 15%
    - Adjustment Quality: 15%
    - Exit Quality: 5%
    """

    def score_decision(decision: AIDecision, outcome: TradeOutcome) -> float
    def update_decision_outcome(decision_id: int, outcome: TradeOutcome)
    def should_retrain_model(recent_scores: List[float]) -> bool
```

**Daily Learning Cycle (4:00 PM):**
```python
class LearningPipeline:
    async def run_daily_learning(user_id: UUID):
        """
        1. Extract completed trades from trade_journal
        2. Compute features: entry conditions, during-trade events, exit
        3. Score decisions using multi-factor scoring
        4. Update strategy scoring model if enough data
        5. Generate daily insights report
        """
```

### 7.2 Database Migration - `ai_learning_reports`

```sql
CREATE TABLE ai_learning_reports (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    report_date DATE NOT NULL,

    -- Trade Stats
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5,2),
    total_pnl DECIMAL(14,2),

    -- AI Performance
    avg_decision_score DECIMAL(5,2),
    regime_accuracy DECIMAL(5,2),
    strategy_accuracy DECIMAL(5,2),

    -- Insights (Claude-generated)
    insights_text TEXT,
    lessons_learned JSONB,

    -- Model Updates
    model_updated BOOLEAN DEFAULT FALSE,
    model_version VARCHAR(20),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(user_id, report_date)
);
```

### 7.3 Week 7 Deliverables

- [ ] `backend/app/services/ai/learning_pipeline.py`
- [ ] `backend/app/services/ai/feedback_scorer.py`
- [ ] Migration: `ai_learning_reports` table
- [ ] Daily learning job in scheduler
- [ ] Claude-generated insights
- [ ] Model retraining trigger

---

## Week 8: Performance Analytics Dashboard

### 8.1 Analytics API

**Files to Create:**
```
backend/app/api/v1/ai/
└── analytics.py               # Performance analytics endpoints
```

**Endpoints:**
```
GET /api/v1/ai/analytics/performance    # Overall performance metrics
GET /api/v1/ai/analytics/by-regime      # Performance by market regime
GET /api/v1/ai/analytics/by-strategy    # Performance by strategy type
GET /api/v1/ai/analytics/decisions      # Decision quality over time
GET /api/v1/ai/analytics/learning       # Learning progress metrics
```

### 8.2 Analytics Dashboard UI

**Files to Create:**
```
frontend/src/views/ai/
└── AnalyticsView.vue          # AI performance analytics
```

**Dashboard Sections:**
1. **Performance Summary** - Total P&L, win rate, Sharpe ratio
2. **Regime Performance** - Which regimes AI performs best in
3. **Strategy Performance** - Which strategies work best
4. **Decision Quality Trend** - Quality scores over time
5. **Learning Curve** - Model improvement over time
6. **Daily Reports** - Access to Claude-generated reports

### 8.3 Week 8 Deliverables

- [ ] `backend/app/api/v1/ai/analytics.py`
- [ ] `frontend/src/views/ai/AnalyticsView.vue`
- [ ] Performance charts (Chart.js)
- [ ] Regime performance breakdown
- [ ] Strategy performance breakdown
- [ ] Decision quality trend
- [ ] Export reports (PDF/CSV)

---

# PART 3: OPTIMIZATION PHASE (Weeks 9-12)

Goal: Advanced features and production hardening.

---

## Week 9: Kelly Criterion Position Sizing

### 9.1 Kelly Calculator

**Files to Create:**
```
backend/app/services/ai/
└── kelly_calculator.py        # Kelly-optimal position sizing
```

**Kelly Implementation:**
```python
class KellyCalculator:
    def calculate_kelly_fraction(
        win_rate: float,
        avg_win: float,
        avg_loss: float
    ) -> float:
        """
        Kelly Fraction = (Win Rate × Avg Win / Avg Loss) - (1 - Win Rate)
                         ─────────────────────────────────────────────────
                                          Avg Win / Avg Loss

        Returns fraction of capital to risk (0.0 to 1.0)
        Use half-Kelly (0.5x) for safety.
        """

    def calculate_optimal_lots(
        kelly_fraction: float,
        capital: float,
        max_loss_per_lot: float
    ) -> int:
        """
        Optimal Lots = (Kelly Fraction × Capital) / Max Loss per Lot
        """
```

### 9.2 Week 9 Deliverables

- [ ] `backend/app/services/ai/kelly_calculator.py`
- [ ] Integrate Kelly sizing with position sizing service
- [ ] UI option to enable Kelly sizing (after 100+ trades)
- [ ] Half-Kelly safety factor

---

## Week 10: Advanced Backtesting

### 10.1 Historical Backtesting

**Files to Create:**
```
backend/app/services/ai/
└── backtester.py              # Backtest strategies on historical data
```

**Backtest Features:**
- Test strategies against historical market conditions
- Simulate regime classification with past data
- Calculate hypothetical P&L
- Generate backtest reports

### 10.2 Week 10 Deliverables

- [ ] `backend/app/services/ai/backtester.py`
- [ ] Backtest API endpoints
- [ ] Backtest UI view
- [ ] Historical data for past 6 months

---

## Week 11: Multi-Strategy Orchestration

### 11.1 Portfolio-Level Management

**Features:**
- Manage multiple concurrent strategies
- Portfolio-level Greeks tracking
- Cross-strategy risk limits
- Capital allocation across strategies

### 11.2 Week 11 Deliverables

- [ ] Portfolio Greeks aggregation
- [ ] Cross-strategy correlation analysis
- [ ] Portfolio rebalancing suggestions
- [ ] Multi-strategy dashboard view

---

## Week 12: Production Hardening

### 12.1 Reliability & Monitoring

**Features:**
- Error handling and recovery
- Alerting for AI failures
- Performance monitoring
- Audit logging

### 12.2 Security

**Features:**
- Claude API key encryption
- Rate limiting
- Access control for AI features

### 12.3 Week 12 Deliverables

- [ ] Error recovery mechanisms
- [ ] Alerting system (email/push)
- [ ] Performance metrics (latency, success rate)
- [ ] Security audit
- [ ] Documentation
- [ ] Production deployment checklist

---

# APPENDIX

## A. Complete File List

### New Backend Files (AI Module)

```
backend/app/services/ai/
├── __init__.py
├── historical_data.py
├── indicators.py
├── market_regime.py
├── strategy_recommender.py
├── strike_selector.py
├── claude_advisor.py
├── daily_scheduler.py
├── deployment_executor.py
├── position_sync.py
├── ai_monitor.py
├── ai_adjustment_advisor.py
├── learning_pipeline.py
├── feedback_scorer.py
├── kelly_calculator.py
├── backtester.py
└── ml/
    ├── __init__.py
    ├── feature_extractor.py
    ├── strategy_scorer.py
    ├── training_pipeline.py
    └── model_registry.py
```

### New Backend API Files

```
backend/app/api/v1/ai/
├── __init__.py
├── router.py
├── config.py
├── regime.py
├── recommendations.py
├── deployments.py
├── sync.py
├── analytics.py
├── learning.py
└── schemas.py
```

### New Frontend Files

```
frontend/src/views/ai/
├── AISettingsView.vue
├── PaperTradingView.vue
├── AnalyticsView.vue
└── components/
    ├── AutonomySettings.vue
    ├── StrategySelector.vue
    ├── PositionSizingConfig.vue
    ├── LimitsConfig.vue
    ├── PaperTradingStatus.vue
    └── ... (more components)

frontend/src/components/ai/
├── MarketRegimeIndicator.vue
├── AIDecisionCard.vue
├── GraduationProgress.vue
├── PositionSyncStatus.vue
└── AIActivityFeed.vue
```

### Files to Modify

```
backend/app/main.py                    # Register AI router
backend/app/services/strategy_monitor.py   # Add AI hooks
backend/app/services/market_data.py    # Add historical data
backend/app/services/kite_ticker.py    # Add order update handler
backend/app/websocket/manager.py       # Add AI message types
backend/requirements.txt               # Add anthropic, scikit-learn, xgboost
frontend/src/router/index.js           # Add AI routes
frontend/src/stores/autopilot.js       # Add AI state
```

## B. Database Migrations

### Migration 1: AI Core Tables (Week 1-2)
```sql
-- ai_market_snapshots
-- ai_user_config
```

### Migration 2: Deployment & Sync (Week 3)
```sql
-- ai_scheduled_deployments
-- ai_position_sync_events
```

### Migration 3: Decisions & Learning (Week 4-7)
```sql
-- ai_decisions_log
-- ai_learning_reports
```

### Migration 4: ML Models (Week 5)
```sql
-- ai_model_registry
```

## C. Environment Variables

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# AI Feature Flags
AI_ENABLED=true
AI_PREMARKET_TIME=08:45
AI_DEPLOY_TIME=09:20
AI_POSTMARKET_TIME=16:00

# ML Model
ML_MODEL_PATH=/app/models/
ML_RETRAIN_THRESHOLD=0.55
```

## D. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Win Rate | > 55% | Trades won / Total trades |
| Average Daily P&L | > ₹3,000 | Total P&L / Trading days |
| Sharpe Ratio | > 1.0 | Annualized return / Volatility |
| Max Drawdown | < 15% | Peak to trough decline |
| AI Confidence Accuracy | > 70% | High-conf trades win rate |
| User Intervention Rate | < 10% | Manual overrides / Total actions |
| Regime Classification Accuracy | > 75% | Correct regime / Total |
| Position Sync Latency | < 5 sec | Time to detect external trade |

---

## E. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| AI makes catastrophic trade | Kill switch always available, hard limits enforced |
| Model degradation | Performance monitoring, auto-pause if win rate drops |
| Position sync failure | 60-second polling backup, manual sync button |
| Claude API failure | Graceful degradation, fallback to rule-based explanations |
| Regime misclassification | Confidence threshold (70%), don't trade if uncertain |
| Over-trading | Max strategies per day limit |
| Data quality issues | Validate historical data, handle gaps |

---

*Plan created: 2024-12-24*
*Last updated: 2024-12-24*
*Status: Ready for implementation*
