# AI Service Taxonomy — Detailed Reference

Complete inventory of all 35 AI/ML services in `backend/app/services/ai/`.

## Full Service Table

| # | File | Category | Key Public Functions | Description |
|---|------|----------|---------------------|-------------|
| 1 | `market_regime.py` | Market Regime | `classify()`, `get_current_regime()` | Classify market state using OHLC + indicators |
| 2 | `regime_drift_tracker.py` | Market Regime | `check_drift()`, `get_drift_history()` | Detect regime transitions in progress |
| 3 | `regime_quality_scorer.py` | Market Regime | `score()`, `get_confidence()` | Score reliability of regime classification |
| 4 | `capital_risk_meter.py` | Risk & Capital | `get_risk_level()`, `calculate_exposure()` | Portfolio-wide risk assessment |
| 5 | `risk_state_engine.py` | Risk & Capital | `transition()`, `get_state()`, `can_trade()` | State machine for risk levels |
| 6 | `drawdown_tracker.py` | Risk & Capital | `update()`, `get_drawdown()`, `check_limit()` | Track and alert on drawdown |
| 7 | `kelly_calculator.py` | Risk & Capital | `calculate()`, `get_optimal_fraction()` | Kelly criterion position sizing |
| 8 | `strategy_recommender.py` | Strategy Intel | `recommend()`, `get_candidates()` | Recommend strategies for current conditions |
| 9 | `strategy_cooldown.py` | Strategy Intel | `is_cooled_down()`, `set_cooldown()` | Enforce post-exit cooldown periods |
| 10 | `strike_selector.py` | Strategy Intel | `select_strikes()`, `get_atm_strike()` | Optimal strike selection for options |
| 11 | `position_sizing_engine.py` | Position Mgmt | `calculate_size()`, `get_max_lots()` | Risk-adjusted position sizing |
| 12 | `position_sync.py` | Position Mgmt | `sync()`, `reconcile()` | Broker <-> DB position sync |
| 13 | `portfolio_manager.py` | Position Mgmt | `get_portfolio()`, `calculate_pnl()` | Portfolio-level management |
| 14 | `claude_advisor.py` | AI Advisors | `analyze()`, `get_recommendation()` | Claude API market analysis |
| 15 | `ai_adjustment_advisor.py` | AI Advisors | `suggest_adjustment()`, `evaluate_position()` | Position adjustment recommendations |
| 16 | `feedback_scorer.py` | AI Advisors | `score_trade()`, `aggregate_feedback()` | Trade outcome scoring |
| 17 | `historical_data.py` | Data & Indicators | `fetch_ohlc()`, `get_candles()` | Historical OHLC data fetching |
| 18 | `indicators.py` | Data & Indicators | `rsi()`, `macd()`, `bollinger()`, `atr()` | Technical indicator calculations |
| 19 | `backtester.py` | Data & Indicators | `run()`, `get_results()` | Strategy backtesting engine |
| 20 | `stress_greeks_engine.py` | Data & Indicators | `calculate_greeks()`, `stress_test()` | Greeks with stress scenarios |
| 21 | `ml/training_pipeline.py` | ML Pipeline | `train()`, `evaluate()`, `deploy()` | End-to-end ML training |
| 22 | `ml/feature_extractor.py` | ML Pipeline | `extract()`, `get_feature_names()` | Feature engineering for ML |
| 23 | `ml/model_registry.py` | ML Pipeline | `register()`, `load()`, `list_models()` | Model versioning and storage |
| 24 | `ml/model_blender.py` | ML Pipeline | `blend()`, `get_weights()` | Model ensemble predictions |
| 25 | `ml/global_model_trainer.py` | ML Pipeline | `train_global()`, `cross_validate()` | Cross-instrument model training |
| 26 | `ml/retraining_scheduler.py` | ML Pipeline | `schedule()`, `should_retrain()` | Periodic retraining management |
| 27 | `ml/strategy_scorer.py` | ML Pipeline | `score()`, `rank_strategies()` | ML-based strategy evaluation |
| 28 | `config_service.py` | Infrastructure | `get()`, `set()`, `get_all()` | AI configuration management |
| 29 | `ai_monitor.py` | Infrastructure | `check_health()`, `get_metrics()` | AI service monitoring |
| 30 | `autonomy_status.py` | Infrastructure | `get_level()`, `set_level()` | AutoPilot autonomy tracking |
| 31 | `daily_scheduler.py` | Infrastructure | `run_daily()`, `get_schedule()` | Daily task scheduling |
| 32 | `deployment_executor.py` | Infrastructure | `deploy()`, `rollback()` | Strategy deployment execution |
| 33 | `extreme_event_handler.py` | Infrastructure | `handle_event()`, `check_circuit_breaker()` | Market crash handling |
| 34 | `learning_pipeline.py` | Infrastructure | `process_outcome()`, `update_models()` | Trade outcome learning |
| 35 | `websocket_health_monitor.py` | Infrastructure | `check_health()`, `get_stats()` | WebSocket health monitoring |

## Category Summary

| Category | Count | Primary Purpose |
|----------|-------|----------------|
| Market Regime | 3 | Detect and track market conditions |
| Risk & Capital | 4 | Portfolio risk management |
| Strategy Intelligence | 3 | Strategy selection and management |
| Position Management | 3 | Position sizing and syncing |
| AI Advisors | 3 | LLM and rule-based advice |
| Data & Indicators | 4 | Market data and technical analysis |
| ML Pipeline | 7 | Machine learning operations |
| Infrastructure | 8 | Config, monitoring, scheduling |
| **Total** | **35** | |

## File Organization

```
backend/app/services/ai/
├── __init__.py
├── market_regime.py          # Category 1: Market Regime
├── regime_drift_tracker.py
├── regime_quality_scorer.py
├── capital_risk_meter.py     # Category 2: Risk & Capital
├── risk_state_engine.py
├── drawdown_tracker.py
├── kelly_calculator.py
├── strategy_recommender.py   # Category 3: Strategy Intelligence
├── strategy_cooldown.py
├── strike_selector.py
├── position_sizing_engine.py # Category 4: Position Management
├── position_sync.py
├── portfolio_manager.py
├── claude_advisor.py         # Category 5: AI Advisors
├── ai_adjustment_advisor.py
├── feedback_scorer.py
├── historical_data.py        # Category 6: Data & Indicators
├── indicators.py
├── backtester.py
├── stress_greeks_engine.py
├── config_service.py         # Category 8: Infrastructure
├── ai_monitor.py
├── autonomy_status.py
├── daily_scheduler.py
├── deployment_executor.py
├── extreme_event_handler.py
├── learning_pipeline.py
├── websocket_health_monitor.py
└── ml/                       # Category 7: ML Pipeline
    ├── __init__.py
    ├── training_pipeline.py
    ├── feature_extractor.py
    ├── model_registry.py
    ├── model_blender.py
    ├── global_model_trainer.py
    ├── retraining_scheduler.py
    └── strategy_scorer.py
```
