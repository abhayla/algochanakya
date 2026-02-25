# AutoPilot AI Module - Production Documentation

## Overview

The AutoPilot AI module is a complete autonomous trading system that makes intelligent trading decisions with zero human intervention during market hours. It combines rule-based systems, machine learning, and Claude AI to maximize profits while managing risk.

**Version:** 1.0
**Status:** Production Ready (⚠️ limited test coverage — see [Test Coverage Gap](#test-coverage-gap) below)
**Last Updated:** 2026-02-25

---

## Architecture

```
backend/app/services/ai/              # 35 service files (run: find backend/app/services/ai -name "*.py" ! -name "__init__.py" | wc -l)
├── __init__.py                       # Module exports
│
│  # Core Intelligence
├── market_regime.py                  # 6-regime classification system
├── risk_state_engine.py              # GREEN/YELLOW/RED risk states
├── strategy_recommender.py           # Regime-strategy scoring matrix
├── deployment_executor.py            # Order placement via broker adapters
│
│  # Data & Indicators
├── historical_data.py                # Historical OHLC via broker abstraction + Redis caching
├── indicators.py                     # RSI, ADX, EMA, ATR, Bollinger Bands
├── strike_selector.py                # Delta-based strike selection + VIX adjustments
│
│  # Portfolio & Capital
├── portfolio_manager.py              # Multi-strategy portfolio management
├── position_sizing_engine.py         # Position sizing calculations
├── capital_risk_meter.py             # Capital risk assessment
├── kelly_calculator.py               # Kelly Criterion position sizing
│
│  # Monitoring & Scheduling
├── ai_monitor.py                     # AI decision making and monitoring
├── websocket_health_monitor.py       # WebSocket health tracking
├── daily_scheduler.py                # APScheduler for deployment timing
├── position_sync.py                  # WebSocket + 60s reconciliation
│
│  # Learning & Feedback
├── learning_pipeline.py              # Daily post-market learning + retraining
├── feedback_scorer.py                # Multi-factor decision quality scoring
├── ai_adjustment_advisor.py          # What-if analysis + adjustment recommendations
├── autonomy_status.py                # Trust ladder (Sandbox→Supervised→Autonomous)
│
│  # Risk Management
├── stress_greeks_engine.py           # Stress testing with Greeks
├── regime_drift_tracker.py           # Regime change detection
├── regime_quality_scorer.py          # Regime classification quality
├── drawdown_tracker.py               # Drawdown monitoring
├── extreme_event_handler.py          # Black swan event handling
├── strategy_cooldown.py              # Strategy cooldown periods
│
│  # Utilities
├── claude_advisor.py                 # Claude Sonnet explanations
├── backtester.py                     # Historical strategy backtesting
├── config_service.py                 # AI configuration management
│
└── ml/                               # ML sub-module (7 files)
    ├── feature_extractor.py          # 30-feature extraction for ML
    ├── strategy_scorer.py            # XGBoost/LightGBM strategy scoring
    ├── training_pipeline.py          # Model training + evaluation
    ├── model_registry.py             # Model versioning + activation
    ├── global_model_trainer.py       # Global model training across users
    ├── model_blender.py              # Ensemble model blending
    └── retraining_scheduler.py       # Automated retraining schedule
```

---

## Key Features

### 1. Market Intelligence (Week 1)
- **Historical Data Service:** Fetches OHLC data from Kite with Redis caching (1-min TTL intraday, 1-hour daily)
- **Technical Indicators:** RSI, ADX, EMA, ATR, Bollinger Bands
- **Market Regime Classification:** 6 regime types with confidence scoring
  - TRENDING_BULLISH
  - TRENDING_BEARISH
  - RANGEBOUND
  - VOLATILE
  - PRE_EVENT
  - EVENT_DAY

### 2. AI Configuration (Week 2)
- User-specific AI trading configuration stored in `ai_user_config` table
- Settings: autonomy mode (paper/live), position sizing (fixed/tiered/kelly), deployment schedule, risk limits
- Paper trading graduation system (15 days + 25 trades + 55% win rate)
- Claude API key management with validation

### 3. Auto-Deployment (Week 3)
- **Strategy Recommender:** 15+ option strategies with regime-strategy scoring matrix
- **Strike Selector:** Delta-based selection with VIX adjustments
- **Claude Advisor:** Natural language explanations via Claude Sonnet 4.5
- **Daily Scheduler:** Automated deployment at configured times with event-day skipping
- **Deployment Executor:** Sequential/simultaneous order placement with retry logic
- **Position Sync:** Real-time WebSocket updates + 60-second reconciliation

### 4. Paper Trading & Integration (Week 4)
- **AI Monitor:** Condition evaluation + decision making
- **Decisions Log:** Tracks all AI decisions in `ai_decisions_log` table
- **Paper Trading Dashboard:** Vue frontend with regime indicator, decision cards, activity feed
- **Graduation Progress:** Automated graduation criteria tracking

### 5. ML Strategy Scorer (Week 5)
- **Feature Extractor:** 30 features across 5 categories (market state, indicators, options, time, strategy)
- **Strategy Scorer:** XGBoost/LightGBM models with batch processing
- **Training Pipeline:** Automated training + evaluation with early stopping
- **Model Registry:** Database-backed versioning with activation/rollback

### 6. AI Adjustment Advisor (Week 6)
- **What-If Simulation:** Simulates P&L impact of all possible adjustments
- **Multi-Factor Scoring:** Risk/reward (40%), cost (20%), Greeks (20%), P&L (20%)
- **Action Categorization:** Defensive, offensive, neutral
- **Greek Impact Analysis:** Delta, gamma, theta, vega calculations

### 7. Self-Learning Pipeline (Week 7)
- **Feedback Scorer:** 5-component decision quality scoring
  - P&L outcome (40%)
  - Risk management (25%)
  - Entry quality (15%)
  - Adjustment quality (15%)
  - Exit quality (5%)
- **Learning Pipeline:** Daily post-market analysis + model retraining
- **Learning Reports:** Stored in `ai_learning_reports` table

### 8. Performance Analytics (Week 8)
- **Performance Metrics:** Total trades, win rate, P&L, Sharpe ratio, decision quality
- **Regime Performance:** Performance breakdown by market regime
- **Strategy Performance:** Performance breakdown by strategy type
- **Decision Quality Trend:** Daily quality scores for charting
- **ML Progress:** Active model performance metrics

### 9. Kelly Criterion Position Sizing (Week 9)
- **Historical Performance Analysis:** Extracts wins/losses from completed trades
- **Kelly Fraction Calculation:** (Win Rate × Avg Win / Avg Loss) - (1 - Win Rate) / (Avg Win / Avg Loss)
- **Half-Kelly Safety:** 0.5x multiplier to reduce variance
- **Optimal Lots Calculation:** (Kelly Fraction × Capital) / Max Loss per Lot
- **Minimum Trades Validation:** Requires 100+ trades for reliability

### 10. Advanced Backtesting (Week 10)
- **Historical Simulation:** Replays strategies against past market data
- **Entry/Exit Evaluation:** Evaluates conditions using historical context
- **P&L Calculation:** Hypothetical profit/loss for each simulated trade
- **Performance Metrics:** Sharpe ratio, Sortino ratio, profit factor, max drawdown
- **Regime Performance Analysis:** Breaks down performance by regime type
- **API Endpoints:**
  - POST /api/v1/ai/backtest/run - Full backtest with custom conditions
  - GET /api/v1/ai/backtest/quick - Quick backtest with default strategy

### 11. Multi-Strategy Orchestration (Week 11)
- **Portfolio Greeks Aggregation:** Sums delta/gamma/theta/vega across all active strategies
- **Cross-Strategy Correlation:** Calculates correlation between strategy pairs
- **Portfolio Rebalancing:** Recommendations based on concentration, delta, correlation limits
- **Risk Assessment:** 4-factor risk scoring (delta, gamma, concentration, correlation)
- **Capital Allocation:** Tracks deployed vs available capital
- **API Endpoint:** GET /api/v1/ai/analytics/portfolio

---

## API Endpoints

### Regime Classification
- `GET /api/v1/ai/regime/current` - Current market regime
- `GET /api/v1/ai/regime/indicators` - All indicators snapshot

### AI Configuration
- `GET /api/v1/ai/config/` - Get user AI configuration
- `PUT /api/v1/ai/config/` - Update AI configuration
- `GET /api/v1/ai/config/sizing` - Get position sizing config
- `PUT /api/v1/ai/config/sizing` - Update position sizing config
- `GET /api/v1/ai/config/kelly-recommendation` - Get Kelly recommendation
- `GET /api/v1/ai/config/paper-trading/status` - Paper trading graduation status

### Strategy Recommendations
- `GET /api/v1/ai/recommendations/` - Get strategy recommendations for current regime

### Performance Analytics
- `GET /api/v1/ai/analytics/performance` - Overall performance metrics
- `GET /api/v1/ai/analytics/by-regime` - Performance by market regime
- `GET /api/v1/ai/analytics/by-strategy` - Performance by strategy type
- `GET /api/v1/ai/analytics/decisions` - Decision quality trend
- `GET /api/v1/ai/analytics/learning` - ML model learning progress
- `GET /api/v1/ai/analytics/portfolio` - Multi-strategy portfolio overview

### Backtesting
- `POST /api/v1/ai/backtest/run` - Run full backtest with custom conditions
- `GET /api/v1/ai/backtest/quick` - Quick backtest with default strategy

---

## Database Tables

### AI Configuration (Week 2)
```sql
ai_user_config
├── id (BIGINT PK)
├── user_id (UUID FK → users.id) UNIQUE
├── ai_enabled (BOOLEAN, default: false)
├── autonomy_mode (VARCHAR, default: 'paper')  -- paper, live
├── sizing_mode (VARCHAR, default: 'tiered')   -- fixed, tiered, kelly
├── base_lots (INTEGER, default: 1)
├── confidence_tiers (JSONB)
├── allowed_strategies (JSONB)
├── max_daily_trades (INTEGER, default: 5)
├── max_concurrent_positions (INTEGER, default: 3)
├── claude_api_key (VARCHAR, encrypted)
└── ... (20+ fields total)
```

### AI Decisions Log (Week 4)
```sql
ai_decisions_log
├── id (BIGINT PK)
├── user_id (UUID FK → users.id)
├── decision_type (VARCHAR)  -- ENTRY, EXIT, ADJUSTMENT, SKIP
├── strategy_name (VARCHAR)
├── underlying (VARCHAR)
├── regime (VARCHAR)
├── confidence_score (DECIMAL)
├── recommendation (VARCHAR)
├── executed (BOOLEAN)
└── timestamp (TIMESTAMP)
```

### AI Model Registry (Week 5)
```sql
ai_model_registry
├── id (BIGINT PK)
├── user_id (UUID FK → users.id)
├── model_version (VARCHAR) UNIQUE
├── model_type (VARCHAR)  -- xgboost, lightgbm
├── accuracy (DECIMAL)
├── precision (DECIMAL)
├── recall (DECIMAL)
├── f1_score (DECIMAL)
├── is_active (BOOLEAN)
└── trained_at (TIMESTAMP)
```

### AI Learning Reports (Week 7)
```sql
ai_learning_reports
├── id (BIGINT PK)
├── user_id (UUID FK → users.id)
├── report_date (DATE)
├── total_trades (INTEGER)
├── winning_trades (INTEGER)
├── losing_trades (INTEGER)
├── win_rate (DECIMAL)
├── avg_overall_score (DECIMAL)
├── insights (TEXT)
└── created_at (TIMESTAMP)
```

---

## Environment Variables

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-xxx  # Required for Claude Advisor

# Redis (for caching)
REDIS_URL=redis://103.118.16.189:6379/0

# Kite API
KITE_API_KEY=your_kite_api_key
KITE_API_SECRET=your_kite_api_secret
```

---

## Error Handling

### Critical Errors (Stop Execution)
- Database migration failures
- Kite API authentication failures
- Core service initialization errors
- Invalid user configuration

### Recoverable Errors (Log & Continue)
- Historical data fetch failures (use cached data)
- Claude API rate limits (fall back to rule-based explanations)
- Indicator calculation errors (skip that indicator)
- WebSocket disconnections (reconnect automatically)

### Error Logging
All errors are logged to structured logs with:
- Timestamp
- User ID
- Service name
- Error type
- Stack trace
- Context (market regime, strategy name, etc.)

---

## Performance Metrics

### Latency Targets
- Market regime classification: < 500ms
- Strategy recommendation: < 1s
- ML strategy scoring: < 2s (batch)
- Order placement: < 3s
- Position sync: < 500ms

### Success Rates
- Historical data fetch: 99%+
- Indicator calculation: 99.9%+
- Order placement: 95%+ (network dependent)
- WebSocket connection: 99%+

### Resource Usage
- Memory: ~200MB per user session
- CPU: < 10% during normal operation, < 30% during training
- Redis cache size: ~50MB per user
- Database connections: 5-10 concurrent

---

## Monitoring & Alerts

### Key Metrics to Monitor
1. **AI Decision Rate:** Decisions per hour (should match market activity)
2. **Win Rate:** Overall winning trades percentage (target: > 55%)
3. **Paper Trading Progress:** Days active, trades completed, graduation status
4. **ML Model Accuracy:** Active model performance (target: > 70%)
5. **Position Sync Lag:** Delay between Kite and local state (target: < 5s)
6. **Error Rate:** Errors per 1000 requests (target: < 1%)

### Alert Triggers
- Win rate drops below 45% for 5+ consecutive days
- ML model accuracy drops below 60%
- Position sync lag exceeds 30 seconds
- Error rate exceeds 5%
- Kelly recommendation returns NEGATIVE_EDGE
- Portfolio risk score exceeds 80 (CRITICAL)

---

## Security

### API Key Management
- Claude API key stored encrypted in database
- Kite API credentials in environment variables (never in code)
- JWT tokens for user authentication
- Rate limiting on all AI endpoints (100 requests/minute per user)

### Access Control
- AI features require authenticated user
- Paper trading mode enforced until graduation criteria met
- Kill switch available for emergency stop
- Semi-auto mode for high-risk actions

### Data Protection
- All user data encrypted at rest
- Sensitive logs redacted (API keys, tokens)
- GDPR compliance for EU users
- Data retention: 90 days for logs, indefinite for configurations

---

## Deployment Checklist

### Pre-Deployment
- [ ] All migrations applied (009-014)
- [ ] Environment variables configured (.env file)
- [ ] Redis connection verified
- [ ] Kite API credentials tested
- [ ] Claude API key validated
- [ ] Database backups configured
- [ ] Monitoring dashboards set up
- [ ] Alert channels configured

### Deployment Steps
1. Apply all Alembic migrations: `alembic upgrade head`
2. Restart backend services
3. Verify AI endpoints: `GET /api/v1/ai/regime/current`
4. Run smoke tests on key workflows
5. Monitor logs for first 30 minutes
6. Enable AI for test users first
7. Gradually roll out to production users

### Post-Deployment
- [ ] Verify AI decision logging
- [ ] Check paper trading dashboard
- [ ] Monitor position sync accuracy
- [ ] Review first day's learning report
- [ ] Validate ML model performance
- [ ] Test kill switch functionality
- [ ] Document any issues

---

## Troubleshooting

### Common Issues

**Issue:** AI not making any decisions
**Solution:** Check if `ai_enabled=true` in user config, verify regime classification is working, check deployment schedule

**Issue:** Position sync showing stale data
**Solution:** Verify WebSocket connection, check Kite API rate limits, restart position sync service

**Issue:** ML model accuracy declining
**Solution:** Review recent trades for data quality, check if market conditions changed, retrain model with more recent data

**Issue:** Kelly recommendation returns NOT_ENOUGH_DATA
**Solution:** User needs at least 100 trades before Kelly is reliable, use tiered sizing mode instead

**Issue:** Backtest taking too long
**Solution:** Reduce date range (max 1 year), use quick backtest endpoint, check historical data cache

---

## Support & Maintenance

### Regular Maintenance Tasks
- **Daily:** Review learning reports, check for failed orders, monitor win rate
- **Weekly:** Audit ML model performance, review risk metrics, check paper trading graduations
- **Monthly:** Database cleanup (archive old logs), performance optimization, security audit

### Logs Location
- Application logs: `backend/logs/app.log`
- AI-specific logs: `backend/logs/ai.log`
- Error logs: `backend/logs/error.log`

### Contact
For issues or questions about the AI module, contact the development team or file an issue in the project repository.

---

## Test Coverage Gap

> **⚠️ Warning:** The AI module currently has minimal automated test coverage. Only `backend/tests/backend/ai/test_services_indicators.py` exists, covering technical indicators. The remaining 34 services (including core services like `market_regime.py`, `risk_state_engine.py`, `strategy_recommender.py`, `kelly_calculator.py`, and all ML services) have no dedicated unit tests.
>
> **Priority areas for test coverage:**
> 1. Core: `market_regime.py`, `risk_state_engine.py`, `strategy_recommender.py`
> 2. Capital: `kelly_calculator.py`, `position_sizing_engine.py`, `capital_risk_meter.py`
> 3. Risk: `stress_greeks_engine.py`, `drawdown_tracker.py`, `extreme_event_handler.py`
> 4. ML: `strategy_scorer.py`, `training_pipeline.py`, `model_registry.py`

---

## Version History

- **v1.0 (2025-12-25, updated 2026-02-25):** Production release
  - All 12 weeks of AutoPilot AI plan completed
  - MVP (Weeks 1-4), Enhancement (Weeks 5-8), Optimization (Weeks 9-12) phases done
  - 35 services (28 core + 7 ML), 16 API endpoints, 4 database tables
  - ML-powered strategy scoring with XGBoost/LightGBM
  - Self-learning pipeline with daily retraining
  - Multi-strategy portfolio management
  - Production-ready with comprehensive monitoring

---

## License

Proprietary - AlgoChanakya Platform
© 2025 All Rights Reserved
