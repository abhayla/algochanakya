---
description: >
  Nudges Claude to invoke the appropriate broker expert skill when editing broker files.
globs:
  - "backend/app/services/brokers/**/*.py"
  - "backend/app/api/routes/*_auth.py"
  - "backend/app/websocket/**/*.py"
  - "backend/app/services/brokers/market_data/ticker/**/*.py"
---

# Broker Expert Skill Nudge

When editing broker-related files, MUST consult the appropriate broker expert skill before making changes:

| File Pattern | Skill |
|---|---|
| `*upstox*` | `/upstox-expert` |
| `*smartapi*`, `*angelone*`, `*angel*` | `/angelone-expert` |
| `*kite*`, `*zerodha*` | `/zerodha-expert` |
| `*dhan*` | `/dhan-expert` |
| `*fyers*` | `/fyers-expert` |
| `*paytm*` | `/paytm-expert` |
| `ticker/pool.py`, `ticker/health.py`, `ticker/failover.py`, `ticker/router.py` | `/debug-websocket-ticks` |
| `platform_token_refresh.py`, `token_policy.py`, multiple broker files | `/broker-shared` |

For cross-broker changes (touching 2+ brokers), also invoke `/broker-shared`.
