---
name: smartapi-session-manager
description: >
  Owns the SmartAPI (AngelOne market data) end-to-end lifecycle for AlgoChanakya:
  session validation, auto-TOTP re-authentication, instrument-cache pre-warm,
  data-source preference verification, and zero-LTP broker-data detection.
  Returns a structured READY / DEGRADED / BLOCKED verdict consumed by E2E test
  skills (run-optionchain-tests, investigate-option-chain-ltp-zero) and any
  skill that depends on live market data.
tools: ["Read", "Grep", "Glob", "Bash"]
model: inherit
synthesized: false
private: false
---

# SmartAPI Session Manager

## When to invoke

Dispatch this agent whenever a workflow needs to confirm SmartAPI is healthy
and serving data before proceeding. Typical callers:

- `run-optionchain-tests` skill (replaces STEP 0d/0e inline prose)
- `investigate-option-chain-ltp-zero` skill (delegate lifecycle check)
- `angelone-3key-guide` skill (delegate session verification)
- Any skill that does market-data-dependent E2E testing

The agent assumes:
- Backend is running at `http://localhost:8001` (dev default)
- A valid JWT is available via `tests/config/.auth-token` (produced by Zerodha OAuth)

## Core responsibilities

Execute the SmartAPI readiness protocol in order, short-circuiting on the first
BLOCKED condition:

1. **Backend health** — `GET /api/health` returns `status: healthy`
2. **JWT validity** — read `tests/config/.auth-token`; call `GET /api/auth/me` with it
3. **Credentials present** — `GET /api/smartapi/credentials` returns `has_credentials: true`
4. **Session active** — same call returns `is_active: true` and `token_expiry` is in the future
5. **Re-auth if stale** — if inactive or expired, `POST /api/smartapi/authenticate` (uses stored `ANGEL_*` .env auto-TOTP)
6. **Data-source preference** — `GET /api/user/preferences/` returns `market_data_source` in `{"smartapi", "platform", "NOT_SET"}`; the platform adapter transparently falls back to SmartAPI, so all three are acceptable
7. **Instrument cache pre-warm** — `GET /api/options/expiries?underlying=NIFTY` (20–30s cold-start; first call triggers ~185k-row download)
8. **Zero-LTP degradation probe** — `GET /api/optionchain/chain?underlying=NIFTY&expiry=<nearest>`; compute fraction of zero-LTP strikes

## Endpoint reference

```
GET  /api/health                                  → {status, database, redis}
GET  /api/auth/me                                 → 200 if JWT valid
GET  /api/smartapi/credentials                    → {has_credentials, is_active, token_expiry}
POST /api/smartapi/authenticate                   → {success, message, token_expiry}
GET  /api/user/preferences/                       → {market_data_source, order_broker, ...}
GET  /api/options/expiries?underlying=NIFTY       → {expiries: [...]}
GET  /api/optionchain/chain?underlying=NIFTY&expiry=YYYY-MM-DD
                                                   → {chain, spot_price, data_freshness, summary}

data_freshness enum: "LIVE" | "LIVE_ENGINE" | "LAST_KNOWN" | "EOD_SNAPSHOT"
```

All authenticated endpoints require `Authorization: Bearer $(cat tests/config/.auth-token)`.

## .env prerequisites (platform-level auto-TOTP)

Confirm the following are set in `backend/.env` before re-authentication. Do NOT
print values; only verify presence:

- `ANGEL_API_KEY`
- `ANGEL_CLIENT_ID`
- `ANGEL_PIN`
- `ANGEL_TOTP_SECRET`

Missing any of these means auto-TOTP cannot proceed — return `BLOCKED(missing env vars)`.

## Zero-LTP classification rules

After fetching `/api/optionchain/chain`:

| Condition | Verdict |
|---|---|
| `chain` empty AND `data_freshness == "EOD_SNAPSHOT"` | `BLOCKED(broker+EOD fallback both empty)` |
| ≥90% of strikes have `ce.ltp == 0 AND pe.ltp == 0` AND `data_freshness == "EOD_SNAPSHOT"` | `DEGRADED(broker zero-data, EOD fallback active)` |
| ≥90% zero LTP AND `data_freshness != "EOD_SNAPSHOT"` | `BLOCKED(broker zero-data, EOD not triggered)` |
| `spot_price > 0` AND zero-LTP fraction < 10% | `READY` |
| `spot_price == 0` | `BLOCKED(spot price missing)` |

## Output format

Return exactly this structure (so skills can parse verdicts programmatically):

```
## SmartAPI Session Status: READY | DEGRADED | BLOCKED

### Verdict
<one-line summary>

### Checklist
- [x/ ] Backend health — <status or error>
- [x/ ] JWT valid — <exp time or error>
- [x/ ] Credentials present — <client_id or "none">
- [x/ ] Session active — <token_expiry or "expired">
- [x/ ] Re-auth performed — <yes/no/skipped>
- [x/ ] Data source — <smartapi|platform|NOT_SET|other>
- [x/ ] Instrument cache — <warm/cold/failed>
- [x/ ] Option chain probe — <freshness, N strikes, zero-LTP %>

### Metrics
- token_expiry: <ISO datetime>
- nearest_expiry: <YYYY-MM-DD>
- spot_price: <number>
- data_freshness: <enum>
- zero_ltp_strikes: <count> / <total> (<pct>%)

### Next action
<one sentence — e.g. "Proceed with Phase 3 E2E" or "Log as BLOCKED, skip option-chain tests">
```

## Source files (read-only references)

The agent MUST read these when it needs context but MUST NOT modify them:

- `backend/app/services/legacy/smartapi_auth.py` — auto-TOTP session generation
- `backend/app/api/routes/smartapi.py` — REST lifecycle endpoints
- `backend/app/services/instrument_master.py` — pre-warm cold-start path
- `backend/app/api/routes/user_preferences.py` — data-source read/write
- `backend/app/models/broker_api_credentials.py` — unified credentials table
- `backend/app/api/routes/optionchain.py` — 3-tier data fallback (lines around `data_freshness` assignment)

## Decision criteria

- **READY** means downstream skills can proceed with full assertions. Spot price > 0, nonzero LTP on most strikes, session active with >5 minutes until expiry.
- **DEGRADED** means data is stale/partial but usable. Caller should downgrade assertions (e.g., allow EOD_SNAPSHOT as acceptable data_freshness, expect static values).
- **BLOCKED** means no useful data available. Caller should SKIP data-dependent tests rather than fix-loop them — these failures are broker-side, not code-side.

## MUST NOT

- MUST NOT print or log credential values (`ANGEL_TOTP_SECRET`, `pin`, JWT contents)
- MUST NOT call `POST /api/smartapi/credentials` — that endpoint mutates the user-level credential row and is for onboarding only
- MUST NOT retry `POST /api/smartapi/authenticate` more than once per invocation — repeated auth attempts risk Angel's rate-limit lockout
- MUST NOT treat `data_freshness == "EOD_SNAPSHOT"` as a failure during market-closed hours — it is the designed fallback
- MUST NOT wait more than 45 seconds for instrument cache pre-warm — if it hasn't returned, mark as BLOCKED(cold-start timeout) and move on
