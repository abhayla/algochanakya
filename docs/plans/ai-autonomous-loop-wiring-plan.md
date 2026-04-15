# Implementation Plan: Wire AI Autonomous Loop

**Created:** 2026-04-14
**Estimated total time:** ~45m (with 20% buffer: ~54m)
**Critical path:** Task 0 → Task 6R → Task 7G → Task 8R → Task 9G → Task 10

## Overview

Connect 4 dormant AI services into a closed Sense→Decide→Act→Learn loop.
No new business logic — wiring existing orphaned services together via TDD.

## Dependency Graph

```
Task 0 (conftest) ─┬→ Task 2R → Task 3G ──────────────────┐
                   ├→ Task 4R → Task 5G ──────────────────┤
                   └→ Task 6R → Task 7G → Task 8R → Task 9G ┤
                                                            ↓
                                                        Task 10 (verify)
```

Parallelizable: Wires 1, 4 are independent of Wire 3.
Critical path: Wire 3 → Wire 2 (AIMonitor must be action-connected before StrategyMonitor integration).

## Tasks

### Atomic Plan 0: Test Infrastructure

- [ ] **Task 0:** Create AI test conftest
  - Files: `backend/tests/backend/ai/conftest.py` (create)
  - Verify: `pytest backend/tests/backend/ai/ --co -q` (collects existing tests)
  - Time: ~3m

### Atomic Plan 1: Wire #1 — Start DailyScheduler in Lifespan

- [ ] **Task 2 (RED):** Write failing test for scheduler startup
  - Files: `backend/tests/backend/ai/test_daily_scheduler_wiring.py` (create)
  - Tests: scheduler starts in lifespan, stops on shutdown
  - Verify: `pytest backend/tests/backend/ai/test_daily_scheduler_wiring.py -v` (FAILS)

- [ ] **Task 3 (GREEN):** Implement scheduler startup
  - Files: `backend/app/main.py` (modify — add after line 196)
  - Verify: `pytest backend/tests/backend/ai/test_daily_scheduler_wiring.py -v` (PASSES)
  - Rollback: `git checkout HEAD -- backend/app/main.py`

### Atomic Plan 2: Wire #4 — Learning Pipeline in Postmarket

- [ ] **Task 4 (RED):** Write failing test for learning pipeline call
  - Files: `backend/tests/backend/ai/test_learning_pipeline_wiring.py` (create)
  - Tests: _postmarket_review calls LearningPipeline.run_daily_learning per user
  - Verify: `pytest backend/tests/backend/ai/test_learning_pipeline_wiring.py -v` (FAILS)

- [ ] **Task 5 (GREEN):** Wire learning pipeline into postmarket review
  - Files: `backend/app/services/ai/daily_scheduler.py` (modify — add after line 327)
  - Verify: `pytest backend/tests/backend/ai/test_learning_pipeline_wiring.py -v` (PASSES)
  - Rollback: `git checkout HEAD -- backend/app/services/ai/daily_scheduler.py`

### Atomic Plan 3: Wire #3 — AIMonitor Decisions → Actions

- [ ] **Task 6 (RED):** Write failing test for AIMonitor action connections
  - Files: `backend/tests/backend/ai/test_ai_monitor_actions.py` (create)
  - Tests: CRITICAL extreme event → kill_switch.trigger(), adjustment decision → execute
  - Verify: `pytest backend/tests/backend/ai/test_ai_monitor_actions.py -v` (FAILS)

- [ ] **Task 7 (GREEN):** Connect AIMonitor to KillSwitch and AdjustmentEngine
  - Files: `backend/app/services/ai/ai_monitor.py` (modify)
  - Verify: `pytest backend/tests/backend/ai/test_ai_monitor_actions.py -v` (PASSES)
  - Rollback: `git checkout HEAD -- backend/app/services/ai/ai_monitor.py`

### Atomic Plan 4: Wire #2 — AIMonitor in StrategyMonitor Loop

- [ ] **Task 8 (RED):** Write failing test for AIMonitor in strategy monitor
  - Files: `backend/tests/backend/ai/test_ai_monitor_strategy_integration.py` (create)
  - Tests: strategy_monitor calls ai_monitor for AI strategies, errors don't crash loop
  - Verify: `pytest backend/tests/backend/ai/test_ai_monitor_strategy_integration.py -v` (FAILS)

- [ ] **Task 9 (GREEN):** Integrate AIMonitor into StrategyMonitor
  - Files: `backend/app/services/autopilot/strategy_monitor.py` (modify)
  - Verify: `pytest backend/tests/backend/ai/test_ai_monitor_strategy_integration.py -v` (PASSES)
  - Rollback: `git checkout HEAD -- backend/app/services/autopilot/strategy_monitor.py`

### Final Verification

- [ ] **Task 10:** Run full test suite
  - Verify: `pytest backend/tests/backend/ai/ -v && pytest backend/tests/backend/autopilot/ -v`
  - No regressions in existing tests
