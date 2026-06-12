---
name: ai-autonomous-loop
description: >
  Sense→Decide→Act→Learn closed loop for AI trading with a FIXED safety-gate
  order in ai_monitor.py: circuit breaker → extreme events → risk state, only
  then position sync, regime checks, and adjustment execution.
globs: ["backend/app/services/ai/**/*.py", "backend/app/api/v1/ai/**/*.py"]
synthesized: true
version: "1.0.0"
private: false
---

# AI Autonomous Loop — Gate Order Is Fixed

`AIMonitor.process_ai_strategies()` (`backend/app/services/ai/ai_monitor.py`,
called every 5 seconds) runs a closed Sense→Decide→Act→Learn loop. The three
safety gates run BEFORE any sensing or acting, in this exact order:

```
Step -2  Circuit breaker  (lines 121-153)   OPEN → halt ALL AI processing
Step -1  Extreme events   (lines 161-235)   CRITICAL → kill_switch + early return
Step  0  Risk state       (lines 237-313)   PAUSED → block deployments + early return
─────────────────────────────────────────────────────────────────────────────
Step  1  Sense   position_sync.sync_positions          (line 316)
Step  2  Sense   regime change check                   (lines 318-321)
Step  3  Decide  position health evaluation            (lines 323-329)
Step  4  Act     adjustment_engine.execute_adjustment  (lines 331-353)
Step  5  Log     decisions persisted                   (lines 355-357)
```

## Gate semantics (verified against the code)

- **Step -2 — circuit breaker** (lines 121-153): `get_health_monitor()` →
  `get_circuit_state()`. `OPEN` logs a `circuit_breaker` decision and
  `return decisions` — nothing else runs. `HALF_OPEN` sets
  `self._block_new_deployments = True` but allows monitoring.
- **Step -1 — extreme events** (lines 161-235): `market_data.get_vix()` →
  `extreme_event_handler.detect_extreme_events()`. `CRITICAL` severity triggers
  `self.kill_switch.trigger(...)` immediately (lines 174-181), blocks new
  deployments, and returns early. `ELEVATED` blocks deployments without
  returning. The detection block itself is fail-open: an exception in the check
  logs and continues (lines 233-235) — keep it that way; the circuit breaker is
  the fail-closed layer.
- **Step 0 — risk state** (lines 237-313): `risk_state_engine.evaluate_state()`
  vs `get_current_state()`; transitions are persisted via `transition_state()`
  with sharpe/drawdown/consecutive-loss metrics. `PAUSED` logs a
  `deployment_blocked` decision and returns early (lines 292-313). `DEGRADED`
  continues with conservative adjustments.

## State machine thresholds — `risk_state_engine.py`

Docstring at lines 22-44, constants at lines 46-60:

| Transition | Condition | Constant |
|---|---|---|
| NORMAL → DEGRADED | Sharpe < 0.5 over 20 trades OR drawdown > 10% | `SHARPE_DEGRADED_THRESHOLD`, `DRAWDOWN_DEGRADED_THRESHOLD` |
| DEGRADED → PAUSED | drawdown > 20% OR Sharpe < 0 | `DRAWDOWN_PAUSED_THRESHOLD`, `SHARPE_PAUSED_THRESHOLD` |
| → NORMAL (recovery) | manual, or Sharpe > 0.7 AND drawdown < 5% | `SHARPE_RECOVERY_THRESHOLD`, `DRAWDOWN_RECOVERY_THRESHOLD` |

DEGRADED behavior: `min_confidence_to_trade` +15%
(`DEGRADED_CONFIDENCE_INCREASE`), lot multiplier ×0.5
(`DEGRADED_LOT_MULTIPLIER`), offensive adjustments disabled.
`MIN_TRADES_FOR_EVALUATION = 20` — do not evaluate Sharpe on fewer trades.

## Learn — DailyScheduler

Started in the lifespan (`backend/app/main.py` lines 220-227,
`start_scheduler()` from `app.services.ai.daily_scheduler`; stopped at
lines 232-234). Cron slots: premarket 8:45, deploy 9:20, **postmarket 4:00 PM —
runs the LearningPipeline** (extract completed trades, score decisions, retrain
models). Scheduler startup failure is logged but MUST NOT block app startup
(the try/except at lines 222-227 is intentional).

## Reviews

Changes under these globs go to the existing **autopilot-safety-reviewer** and
**risk-state-reviewer** agents — do not merge gate-order or threshold changes
on self-review alone.

## CRITICAL RULES

- MUST NOT reorder or bypass the gate sequence: circuit breaker (Step -2) → extreme events (Step -1) → risk state (Step 0) → Sense → Decide → Act.
- MUST NOT add an Act path (adjustment, deployment, order placement) that skips risk-state evaluation — every action flows through `process_ai_strategies()` after Step 0, or replicates all three gates.
- MUST keep `CircuitBreakerState.OPEN` as a hard early return — no "monitoring only" carve-outs on OPEN.
- MUST keep CRITICAL extreme events wired to `kill_switch.trigger()`; a failed kill-switch call is logged, never swallowed silently into a normal cycle.
- MUST NOT change thresholds in `risk_state_engine.py` (lines 46-60) without updating the class docstring (lines 22-44) and routing the change through risk-state-reviewer.
- Adjustments MUST execute via `adjustment_engine.execute_adjustment()` (ai_monitor.py lines 341-353) — never call broker order APIs directly from AI decision code.
- MUST keep DailyScheduler start non-fatal in the lifespan; the trading API serves without the Learn loop, not vice versa.
