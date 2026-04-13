---
description: >
  5-component WebSocket ticker architecture: TickerPool manages adapter lifecycle,
  TickerRouter fans out ticks, HealthMonitor tracks adapter health, FailoverController
  switches primary/secondary, broker Adapters handle connections.
globs: ["backend/app/services/brokers/market_data/ticker/**/*.py"]
synthesized: true
private: false
---

# WebSocket Ticker Architecture

## 5-Component Pipeline

```
TickerPool → TickerRouter → HealthMonitor → FailoverController → Adapters
   │              │               │                 │                │
   │              │               │                 │                ├─ SmartAPITickerAdapter
   │              │               │                 │                ├─ KiteTickerAdapter
   │              │               │                 │                ├─ DhanTickerAdapter
   │              │               │                 │                ├─ FyersTickerAdapter
   │              │               │                 │                ├─ UpstoxTickerAdapter
   │              │               │                 │                └─ PaytmTickerAdapter
   │              │               │                 │
   │              │               │                 └─ Primary: angelone, Secondary: upstox
   │              │               │                    (configurable via ORG_ACTIVE_BROKERS)
   │              │               │
   │              │               └─ 5s heartbeat, health score 0-100
   │              │
   │              └─ Fan-out: one tick → all subscribed user WebSockets
   │
   └─ Singleton: ref-counted subscriptions, adapter lifecycle
```

## Component Responsibilities

| Component | File | Purpose |
|-----------|------|---------|
| `TickerPool` | `pool.py` | Singleton adapter manager with ref-counted symbol subscriptions |
| `TickerRouter` | `router.py` | Routes tick updates to user WebSocket connections |
| `HealthMonitor` | `health.py` | Tracks adapter health via 5-second heartbeats, scores 0-100 |
| `FailoverController` | `failover.py` | Make-before-break failover with 120s flap prevention |
| Adapters | `adapters/*.py` | Broker-specific WebSocket connection handlers |

## Failover Thresholds

| Threshold | Value | Description |
|-----------|-------|-------------|
| Failover trigger | Health < 30 | Switch to secondary broker |
| Failback trigger | Health ≥ 70 sustained 60s | Switch back to primary |
| Consecutive low scores | 3 (15s) | Required before failover |
| Flap prevention | 120s cooldown | Prevents rapid primary↔secondary switching |

## Health Pipeline Wiring

The health pipeline is fully wired — adapters report errors to TickerPool, which forwards them to HealthMonitor:

```
Adapter._report_error() → Pool._on_adapter_error() → HealthMonitor.record_error()
Adapter ticks            → Pool._on_adapter_tick()  → HealthMonitor.record_ticks()
Pool.get_or_create()     → HealthMonitor.record_connect()
Pool.remove_adapter()    → HealthMonitor.record_disconnect()
```

Auth errors use `HealthMonitor.record_auth_failure()` which classifies via `token_policy.py`:
- **NOT_RETRYABLE / NOT_REFRESHABLE** → instant failover (health=0, callback fires immediately)
- **RETRYABLE** → gradual decay via normal `record_error()` path

## Token Policy & Auto-Refresh

`token_policy.py` classifies broker auth errors into 4 categories. See `.claude/rules/token-auto-refresh.md`.

TickerPool auto-refreshes expired credentials before reconnecting (for SmartAPI and Upstox).
FailoverController verifies primary credentials before failback.

## Adding to Ticker Components

When modifying the ticker system:

1. **New adapter** — implement in `adapters/`, register in `TickerPool`, add error codes to `token_policy.py`
2. **New metric** — add to `HealthMonitor` scoring
3. **New failover rule** — modify `FailoverController` with flap prevention
4. **New subscriber type** — extend `TickerRouter` fan-out

## MUST NOT

- MUST NOT create WebSocket connections outside the TickerPool — it manages all adapter lifecycle
- MUST NOT skip HealthMonitor when adding a new adapter — all adapters need health tracking
- MUST NOT set failover threshold above 50 — high thresholds cause premature switching
- MUST NOT bypass TickerRouter for tick distribution — all subscribers go through the router
- MUST NOT add a broker adapter without classifying its error codes in `token_policy.py`
