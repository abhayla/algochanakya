# AI Service Dependency Graph

Import analysis showing which AI services depend on which, plus entry points from other parts of the system.

## Dependency Overview

```
                    ┌─────────────────────┐
                    │   External Entry    │
                    │   Points            │
                    └──────┬──────────────┘
                           │
              ┌────────────┼────────────────┐
              │            │                │
         API Routes   AutoPilot        Scheduler
              │        Services            │
              │            │                │
    ┌─────────┴──┐    ┌───┴────┐     ┌────┴─────┐
    │ Claude     │    │Strategy│     │Daily     │
    │ Advisor    │    │Recomm. │     │Scheduler │
    │            │    └───┬────┘     └────┬─────┘
    └────────────┘        │               │
                     ┌────┴────┐    ┌─────┴──────┐
                     │Market   │    │ML Training │
                     │Regime   │    │Pipeline    │
                     └────┬────┘    └─────┬──────┘
                          │               │
                     ┌────┴────┐    ┌─────┴──────┐
                     │Historical│   │Feature     │
                     │Data     │    │Extractor   │
                     └────┬────┘    └─────┬──────┘
                          │               │
                     ┌────┴────┐    ┌─────┴──────┐
                     │Indicators│   │Historical  │
                     │         │    │Data        │
                     └─────────┘    └────────────┘
```

## Detailed Dependencies

### Tier 0: Foundational (no AI dependencies)
- `config_service.py` -- reads from .env and database, no AI imports
- `historical_data.py` -- fetches from broker adapters, no AI imports
- `indicators.py` -- pure math on OHLC arrays

### Tier 1: Depends on Tier 0 only
- `market_regime.py` <- historical_data, indicators
- `stress_greeks_engine.py` <- historical_data
- `ml/feature_extractor.py` <- historical_data, indicators
- `drawdown_tracker.py` <- (reads position P&L from database)
- `websocket_health_monitor.py` <- (reads WebSocket connection state)

### Tier 2: Depends on Tier 0-1
- `regime_drift_tracker.py` <- market_regime
- `regime_quality_scorer.py` <- market_regime
- `risk_state_engine.py` <- capital_risk_meter, drawdown_tracker
- `kelly_calculator.py` <- (strategy performance data from DB)
- `ml/model_registry.py` <- (filesystem/DB operations)
- `backtester.py` <- historical_data, indicators, stress_greeks_engine

### Tier 3: Depends on Tier 0-2
- `capital_risk_meter.py` <- risk_state_engine, drawdown_tracker, portfolio_manager
- `strategy_recommender.py` <- market_regime, risk_state_engine, config_service
- `strike_selector.py` <- stress_greeks_engine, indicators
- `position_sizing_engine.py` <- kelly_calculator, risk_state_engine
- `ml/training_pipeline.py` <- feature_extractor, model_registry
- `ml/model_blender.py` <- model_registry
- `ml/strategy_scorer.py` <- model_registry, feature_extractor

### Tier 4: Depends on Tier 0-3
- `strategy_cooldown.py` <- strategy_recommender (reads strategy metadata)
- `ai_adjustment_advisor.py` <- stress_greeks_engine, strategy_recommender, risk_state_engine
- `feedback_scorer.py` <- strategy_scorer, backtester
- `position_sync.py` <- portfolio_manager (broker adapter integration)
- `portfolio_manager.py` <- position_sizing_engine, risk_state_engine
- `ml/global_model_trainer.py` <- training_pipeline, feature_extractor
- `ml/retraining_scheduler.py` <- model_registry, training_pipeline

### Tier 5: Orchestrators (depend on many services)
- `daily_scheduler.py` <- market_regime, ml/retraining_scheduler, ai_monitor
- `deployment_executor.py` <- strategy_recommender, position_sizing_engine, risk_state_engine
- `extreme_event_handler.py` <- risk_state_engine, capital_risk_meter, drawdown_tracker
- `ai_monitor.py` <- (imports all services for health checks)
- `learning_pipeline.py` <- feedback_scorer, ml/training_pipeline
- `claude_advisor.py` <- market_regime, indicators (standalone, Anthropic API)
- `autonomy_status.py` <- config_service (reads autonomy level from DB)

## Entry Points

### From API Routes
```
backend/app/api/routes/ai.py
  -> claude_advisor.analyze()
  -> market_regime.get_current_regime()
  -> ai_monitor.check_health()
  -> autonomy_status.get_level()
  -> config_service.get_all()
```

### From AutoPilot Services
```
backend/app/services/autopilot/
  suggestion_engine.py -> strategy_recommender.recommend()
  adjustment_engine.py -> ai_adjustment_advisor.suggest_adjustment()
  condition_engine.py  -> market_regime.get_current_regime()
  kill_switch.py       -> risk_state_engine.get_state()
  strategy_monitor.py  -> drawdown_tracker.check_limit()
```

### From Scheduler
```
backend/app/services/ai/daily_scheduler.py
  -> market_regime.classify() (morning regime check)
  -> ml/retraining_scheduler.should_retrain() (check if models need update)
  -> ai_monitor.check_health() (daily health report)
  -> learning_pipeline.process_outcome() (process yesterday's trades)
```

## Circular Dependency Warnings

There are NO circular dependencies in the current architecture. The tier system ensures unidirectional flow. If you introduce a new dependency, verify it doesn't create a cycle by checking the tier of both services.

**Rule:** A service in Tier N should only import from Tier 0 to N-1, never from its own tier or higher.
