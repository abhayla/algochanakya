---
description: >
  Enforces the strict dependency-ordered startup sequence in the FastAPI lifespan function.
  Violating this order causes silent failures: missing instruments, empty ticker subscriptions, or stale token mappings.
globs: ["backend/app/main.py", "backend/app/services/**/*.py"]
synthesized: true
private: false
version: "1.0.0"
---

# Service Initialization Order

The FastAPI `lifespan()` function in `backend/app/main.py` follows a strict dependency chain. Each stage depends on the completion of all prior stages. Reordering, parallelizing, or skipping stages causes silent failures that are difficult to diagnose.

## Required Initialization Order

```
1. init_db()                          # Database connection pool
   ↓
2. refresh_instrument_master_startup() # Instrument master data from broker APIs
   ↓
3. SmartAPI instruments cache          # Pre-warm instrument lookup cache
   ↓
4. populate_broker_token_mappings()    # Map broker instrument tokens for WebSocket
   ↓
5. refresh_platform_tokens()          # Refresh OAuth tokens (Upstox, AngelOne)
   ↓
6. WebSocket health monitor           # Start health monitoring before ticker
   ↓
7. Ticker system                      # TickerPool → TickerRouter → HealthMonitor → FailoverController
```

## Why This Order Matters

- **Stage 2 before 3:** SmartAPI cache reads from instrument master data loaded in stage 2. Without instruments, the cache is empty.
- **Stage 2 before 4:** `populate_broker_token_mappings()` maps instrument tokens from the master data. Without instruments, WebSocket subscribes to nothing.
- **Stage 4 before 7:** The ticker system uses broker token mappings to subscribe to market data feeds. Without mappings, tickers connect but receive no data — a silent failure.
- **Stage 5 before 7:** Platform tokens (Upstox, AngelOne) must be valid before the ticker attempts authenticated WebSocket connections.
- **Stage 6 before 7:** Health monitor MUST be running before ticker connections start so it can detect immediate connection failures.

## MUST Rules

- MUST NOT reorder stages in `lifespan()` without understanding the dependency chain above
- MUST NOT parallelize stages across dependency boundaries (e.g., running stage 4 concurrently with stage 2)
- MUST wrap each stage in try/except with logging — a failed stage MUST log clearly which stage failed and what downstream stages will be affected
- MUST NOT add new startup services without placing them in the correct position relative to their dependencies
- When adding a new startup stage, document its dependencies as a comment: `# Depends on: init_db, refresh_instrument_master`

## Adding New Startup Services

When adding a new service to the startup sequence:

1. Identify which existing stages it depends on (reads data from, calls into)
2. Identify which existing stages depend on it (will use its output)
3. Place it AFTER all dependencies and BEFORE all dependents
4. Wrap in try/except — log the stage name and error, do NOT let it crash the entire startup
5. Add a comment documenting the dependency: `# Depends on: <stage names>`
