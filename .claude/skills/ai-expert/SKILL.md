---
name: ai-expert
description: Expert skill for AlgoChanakya's 35 AI/ML services. Provides taxonomy, dependency graph, debugging guides, and testing patterns for all services in backend/app/services/ai/.
metadata:
  author: AlgoChanakya
  version: "1.0"
  category: debugging
  created_by: skill-evolver
---

# AI Services Expert

Expert skill for debugging, understanding, and extending AlgoChanakya's 35 AI/ML services located in `backend/app/services/ai/`.

## When to Use

- Debugging AI service errors or unexpected behavior
- Understanding dependencies between AI services
- Adding new AI services or extending existing ones
- Troubleshooting AutoPilot integration with AI services
- Investigating ML model training/scoring issues
- Understanding the market regime detection pipeline
- Reviewing risk management calculations

## When NOT to Use

- **Broker API issues** → Use broker expert skills (`/zerodha-expert`, `/angelone-expert`, etc.)
- **Frontend component issues** → Use `/vue-component-generator` or check `frontend/CLAUDE.md`
- **E2E test issues** → Use `/test-fixer` or `/e2e-test-generator`
- **AutoPilot strategy configuration** → Use `/autopilot-assistant`
- **General Python debugging** → Standard debugging approach, no skill needed

## Service Taxonomy (8 Categories)

### 1. Market Regime (3 services)

Detect and track market conditions to inform strategy selection.

| Service | File | Purpose |
|---------|------|---------|
| Market Regime Classifier | `market_regime.py` | Classify current market as bullish/bearish/neutral/volatile |
| Regime Drift Tracker | `regime_drift_tracker.py` | Detect when regime is shifting between states |
| Regime Quality Scorer | `regime_quality_scorer.py` | Score reliability/confidence of regime classification |

**Entry point:** Called by AutoPilot's strategy recommender and daily scheduler.
**Key dependency:** Requires historical OHLC data from `historical_data.py`.

### 2. Risk & Capital Management (4 services)

Manage portfolio risk and capital allocation.

| Service | File | Purpose |
|---------|------|---------|
| Capital Risk Meter | `capital_risk_meter.py` | Overall portfolio risk level (green/yellow/red) |
| Risk State Engine | `risk_state_engine.py` | Track risk state transitions and enforce limits |
| Drawdown Tracker | `drawdown_tracker.py` | Monitor drawdown from peak, trigger alerts |
| Kelly Calculator | `kelly_calculator.py` | Kelly criterion for optimal position sizing |

**Entry point:** Risk state engine is queried before every order. Capital risk meter feeds dashboard.
**Key dependency:** Drawdown tracker depends on position P&L data.

### 3. Strategy Intelligence (3 services)

Select and manage trading strategies.

| Service | File | Purpose |
|---------|------|---------|
| Strategy Recommender | `strategy_recommender.py` | Recommend strategies based on regime + risk |
| Strategy Cooldown | `strategy_cooldown.py` | Enforce cooldown periods after strategy exit |
| Strike Selector | `strike_selector.py` | Select optimal strikes for option strategies |

**Entry point:** Strategy recommender is the primary entry, called by AutoPilot.
**Key dependency:** Depends on market regime + risk state + Greeks data.

### 4. Position Management (3 services)

Handle position sizing, syncing, and portfolio-level decisions.

| Service | File | Purpose |
|---------|------|---------|
| Position Sizing Engine | `position_sizing_engine.py` | Calculate lot sizes based on risk + Kelly |
| Position Sync | `position_sync.py` | Sync positions between broker and local DB |
| Portfolio Manager | `portfolio_manager.py` | Portfolio-level P&L, margin, and exposure tracking |

**Entry point:** Position sizing called before order placement. Sync runs periodically.
**Key dependency:** Position sizing depends on Kelly calculator and risk state.

### 5. AI Advisors (3 services)

LLM-powered and rule-based advisory systems.

| Service | File | Purpose |
|---------|------|---------|
| Claude Advisor | `claude_advisor.py` | Claude API integration for market analysis |
| AI Adjustment Advisor | `ai_adjustment_advisor.py` | Recommend position adjustments based on Greeks |
| Feedback Scorer | `feedback_scorer.py` | Score trade outcomes for learning pipeline |

**Entry point:** Claude advisor called on-demand. Adjustment advisor called by AutoPilot.
**Key dependency:** Claude advisor requires Anthropic API key. Adjustment advisor needs Greeks data.

### 6. Data & Indicators (4 services)

Market data fetching, technical indicators, and backtesting.

| Service | File | Purpose |
|---------|------|---------|
| Historical Data | `historical_data.py` | Fetch OHLC candle data from broker APIs |
| Indicators | `indicators.py` | Technical indicators (RSI, MACD, Bollinger, etc.) |
| Backtester | `backtester.py` | Strategy backtesting engine |
| Stress Greeks Engine | `stress_greeks_engine.py` | Greeks calculation with stress scenarios |

**Entry point:** Historical data is foundational -- used by most other services.
**Key dependency:** Historical data fetches from broker adapters (SmartAPI primary).

### 7. ML Pipeline (7 services)

Machine learning model training, scoring, and management.

| Service | File | Purpose |
|---------|------|---------|
| Training Pipeline | `ml/training_pipeline.py` | End-to-end model training orchestration |
| Feature Extractor | `ml/feature_extractor.py` | Extract features from market data for ML |
| Model Registry | `ml/model_registry.py` | Store, version, and retrieve trained models |
| Model Blender | `ml/model_blender.py` | Ensemble multiple models for predictions |
| Global Model Trainer | `ml/global_model_trainer.py` | Train models across all instruments |
| Retraining Scheduler | `ml/retraining_scheduler.py` | Schedule periodic model retraining |
| Strategy Scorer | `ml/strategy_scorer.py` | ML-based strategy performance scoring |

**Entry point:** Training pipeline orchestrates all ML operations. Retraining scheduler triggers periodically.
**Key dependency:** Feature extractor depends on historical data + indicators.

### 8. Infrastructure (8 services)

Configuration, monitoring, scheduling, and system management.

| Service | File | Purpose |
|---------|------|---------|
| Config Service | `config_service.py` | AI service configuration management |
| AI Monitor | `ai_monitor.py` | Monitor AI service health and performance |
| Autonomy Status | `autonomy_status.py` | Track AutoPilot autonomy level |
| Daily Scheduler | `daily_scheduler.py` | Schedule daily AI tasks (retraining, regime check) |
| Deployment Executor | `deployment_executor.py` | Execute strategy deployments |
| Extreme Event Handler | `extreme_event_handler.py` | Handle market crashes, circuit breakers |
| Learning Pipeline | `learning_pipeline.py` | Process trade outcomes for model improvement |
| WebSocket Health Monitor | `websocket_health_monitor.py` | Monitor WebSocket connection health |

**Entry point:** Daily scheduler is the main cron-like entry. Config service used everywhere.
**Key dependency:** AI monitor depends on all other services for health checks.

## Debugging Guide

### Common Error Patterns

| Error | Likely Service | Fix |
|-------|---------------|-----|
| `No regime data available` | market_regime.py | Check historical data fetch. Ensure OHLC data exists for the instrument. |
| `Risk state transition blocked` | risk_state_engine.py | Check current risk state. May need manual reset via admin API. |
| `Model not found in registry` | ml/model_registry.py | Run training pipeline first. Check model storage path. |
| `Feature extraction failed` | ml/feature_extractor.py | Verify historical data is available. Check for NaN values. |
| `Kelly calculator: negative edge` | kelly_calculator.py | Win rate too low. Check strategy performance data. |
| `Anthropic API error` | claude_advisor.py | Check API key in `.env`. Verify rate limits. |
| `Position sync mismatch` | position_sync.py | Broker positions differ from local DB. Run manual sync. |
| `Drawdown limit breached` | drawdown_tracker.py | Portfolio drawdown exceeded threshold. Check kill switch. |

### Debugging Workflow

1. **Identify the category** -- Which of the 8 categories does the error fall into?
2. **Check the dependency graph** -- See `references/dependency-graph.md` for upstream dependencies
3. **Verify data inputs** -- Most AI service failures are caused by missing/stale input data
4. **Check configuration** -- `config_service.py` manages all AI config. Verify values.
5. **Review logs** -- AI services log to `backend/logs/ai/`. Check for warnings before errors.
6. **Test in isolation** -- Use pytest markers: `@pytest.mark.ai` for AI service tests

### Testing AI Services

**Test location:** `backend/tests/backend/ai/`

**Naming convention:** `test_{service_name}.py`

**Example test structure:**
```python
import pytest
from app.services.ai.market_regime import RegimeClassifier

@pytest.mark.ai
class TestRegimeClassifier:
    def test_bullish_regime(self, sample_ohlc_data):
        classifier = RegimeClassifier()
        result = classifier.classify(sample_ohlc_data)
        assert result.regime in ['bullish', 'bearish', 'neutral', 'volatile']
        assert 0.0 <= result.confidence <= 1.0

    def test_insufficient_data(self):
        classifier = RegimeClassifier()
        with pytest.raises(ValueError, match="Insufficient data"):
            classifier.classify([])
```

**Running AI tests:**
```bash
cd backend
pytest tests/backend/ai/ -v                                    # All AI tests
pytest tests/backend/ai/test_market_regime.py -v               # Single file
pytest -m ai -v                                                # By marker
pytest tests/backend/ai/ -k "test_bullish" -v                  # By name
```

## Configuration Reference

AI services are configured via `config_service.py` which reads from:
1. `backend/.env` -- API keys, model paths
2. Database `ai_config` table -- Runtime parameters
3. Default values in each service

**Key environment variables:**
```bash
# Claude Advisor
ANTHROPIC_API_KEY=sk-ant-...

# ML Pipeline
ML_MODEL_PATH=backend/models/
ML_TRAINING_DATA_PATH=backend/data/training/

# Risk Management
MAX_PORTFOLIO_DRAWDOWN=0.05      # 5% max drawdown
RISK_FREE_RATE=0.065             # 6.5% (Indian Govt bond rate)
MAX_POSITION_SIZE_PCT=0.10       # 10% max per position

# Market Regime
REGIME_LOOKBACK_DAYS=30
REGIME_CONFIDENCE_THRESHOLD=0.6
```

## Adding a New AI Service

1. Create file in `backend/app/services/ai/` (or `ai/ml/` for ML services)
2. Follow existing patterns: class-based, async where needed, proper logging
3. Register in `config_service.py` if it needs configuration
4. Add test file in `backend/tests/backend/ai/`
5. Update `references/service-taxonomy.md` and `references/dependency-graph.md`
6. If it integrates with AutoPilot, update `/autopilot-assistant` skill

## Cross-References

- **Service Taxonomy (detailed):** `references/service-taxonomy.md`
- **Dependency Graph:** `references/dependency-graph.md`
- **AutoPilot Integration:** `/autopilot-assistant` skill
- **Backend CLAUDE.md:** `backend/CLAUDE.md` -- AI/ML section
- **AI Test Directory:** `backend/tests/backend/ai/`
