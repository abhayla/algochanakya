# Live Broker Tests

Manual E2E tests that verify real broker data during market hours. These require live credentials and are **never** run in CI.

## Prerequisites

- **Market hours:** 9:15 AM - 3:30 PM IST, Monday-Friday
- **Credentials:** AngelOne + Upstox configured in `.env`
- **Auth state:** Pre-warmed by `global-setup.js` (runs automatically)
- **Dev stack running:** Backend on :8001, Frontend on :5173

## Quick Run

```bash
# All live tests
npx playwright test tests/e2e/specs/live/

# Single file
npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js

# By tag
npx playwright test --grep @live

# Headed (see the browser)
npx playwright test tests/e2e/specs/live/ --headed
```

---

## Test Files

### 1. `live.broker-screens.spec.js` — Per-Broker Screen Verification

**What:** Sets each of the 6 brokers as data source one by one, then verifies 4 screens render real data.

**Brokers tested:** AngelOne (smartapi), Zerodha (kite), Upstox, Dhan, Fyers, Paytm

**Screens tested per broker:**

| Screen | Assertion |
|--------|-----------|
| Watchlist | NIFTY price visible, value > 1000 |
| Option Chain | >=5 strike rows, ATM badge, CE LTP > 0 |
| Positions | Table or empty state (no error) |
| Dashboard | NIFTY card visible, price > 0, badge non-empty |

**Total tests:** 24 (6 brokers x 4 screens)

**When to run:**
- After adding/modifying a broker adapter
- After changing market data fetching logic
- After modifying any screen that displays live prices
- Smoke test to verify all broker credentials are working

**How to run:**
```bash
# All brokers, all screens
npx playwright test tests/e2e/specs/live/live.broker-screens.spec.js

# Single broker
npx playwright test tests/e2e/specs/live/live.broker-screens.spec.js --grep "angelone"
npx playwright test tests/e2e/specs/live/live.broker-screens.spec.js --grep "Upstox"
```

---

### 2. `live.broker-switch-flow.spec.js` — Broker Switch + WebSocket

**What:** Tests the full AngelOne <-> Upstox switch cycle: verifies all 6 screens get live data after each switch, WebSocket badge updates without reload, and edge cases like rapid switching.

**Sections:**

| Section | Tests | What it covers |
|---------|-------|----------------|
| Happy path | 4 | All screens with A1, switch to Upstox, switch back, order broker unchanged |
| WebSocket badge | 2 | Badge updates on Dashboard/Watchlist without page reload (via API switch) |
| Edge cases | 7 | Reload persistence, rapid switch, mid-load switch, platform banner, P&L after double switch, cross-screen nav, settings reflection |

**Total tests:** 13

**When to run:**
- After modifying broker preference save/load logic
- After changing WebSocket reconnection or `source_changed` message handling
- After modifying the data source badge or upgrade banner components
- After changing the Settings broker section UI

**How to run:**
```bash
# Full suite
npx playwright test tests/e2e/specs/live/live.broker-switch-flow.spec.js

# Just happy path
npx playwright test tests/e2e/specs/live/live.broker-switch-flow.spec.js --grep "AngelOne"

# Just edge cases
npx playwright test tests/e2e/specs/live/live.broker-switch-flow.spec.js --grep "Edge"
```

---

### 3. `live.unified-broker-flow.happy.spec.js` — End-to-End Lifecycle

**What:** Single chained flow covering the complete user journey: login page -> settings -> option chain -> switch broker -> verify across all screens. Two serial groups: happy path and edge cases.

**HAPPY PATH (Steps 1-8):**

| Step | Scenario | Key assertions |
|------|----------|----------------|
| 1 | Login page broker dropdown | 6-7 options, includes Zerodha + AngelOne |
| 2 | Settings dropdown counts | 7 market data options, 7 order broker options |
| 3 | AngelOne -> Option Chain | Spot > 10000, >=5 strikes, LTP > 0, ATM badge |
| 4 | Switch to Upstox | Save persists on settings re-visit |
| 5 | Option Chain with Upstox | Strikes, LTP > 0, no error |
| 6 | Cross-screen check | Dashboard, Watchlist, Positions load without error |
| 7 | Badge verification | Badge shows "upstox" on 3 screens |
| 8 | Switch back to AngelOne | Option Chain restores, badge updates |

**EDGE CASES (Steps 9-16):**

| Step | Scenario | Key assertions |
|------|----------|----------------|
| 9 | Reload persistence | Source stays "upstox" after full page reload |
| 10 | Rapid switching | A1->U->A1 fast — no WebSocket crash, OC still loads |
| 11 | Mid-load switch | Switch via API while OC loading — no error, strikes render |
| 12 | Platform banner | Banner shows on platform default, hides on switch back |
| 13 | Order broker isolation | Order broker stays "kite" through all data switches |
| 14 | All 6 screens | Dashboard through AutoPilot — no error state on any |
| 15 | Settings round-trip | Navigate away, come back — still shows correct source |
| 16 | BANKNIFTY after switch | Different underlying also loads with switched broker |

**Total tests:** 16

**When to run:**
- Before release: full regression of broker data flow
- After changes to login page broker selection
- After changes to settings broker dropdowns
- After changes to option chain data loading
- After changes to broker preference API (`/api/user/preferences/`)
- After changes to WebSocket ticker/reconnection logic
- After changes to data source badge or upgrade banner

**How to run:**
```bash
# Full suite (happy + edge)
npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js

# Just happy path
npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js --grep "HAPPY"

# Just edge cases
npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js --grep "EDGE"

# Single step
npx playwright test tests/e2e/specs/live/live.unified-broker-flow.happy.spec.js --grep "Step 3"
```

---

## When to Run Which File

| Scenario | File to run |
|----------|-------------|
| "Does broker X work at all?" | `live.broker-screens.spec.js --grep "brokerX"` |
| "Does switching brokers break anything?" | `live.broker-switch-flow.spec.js` |
| "Full pre-release broker regression" | `live.unified-broker-flow.happy.spec.js` |
| "Quick smoke test during market hours" | `npx playwright test tests/e2e/specs/live/ --grep "Step 3"` |
| "All live tests, everything" | `npx playwright test tests/e2e/specs/live/` |

## Coverage Matrix

| What | broker-screens | broker-switch-flow | unified-flow |
|------|:-:|:-:|:-:|
| Login page broker dropdown | | | x |
| Settings dropdown counts | | | x |
| Per-broker screen verification (all 6) | x | | |
| AngelOne live data | x | x | x |
| Upstox live data | x | x | x |
| Kite/Dhan/Fyers/Paytm live data | x | | |
| Broker switch happy path | | x | x |
| Cross-screen after switch | | x | x |
| WebSocket badge update (no reload) | | x | |
| Rapid switching | | x | x |
| Mid-load switch | | x | x |
| Reload persistence | | x | x |
| Platform banner show/hide | | x | x |
| Order broker isolation | | x | x |
| BANKNIFTY after switch | | | x |
| All 6 screens no-error check | | x | x |
| Settings round-trip | | x | x |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| All tests fail with timeout | Outside market hours | Run between 9:15 AM - 3:30 PM IST |
| Single broker tests fail | Credentials expired | Check `.env`, re-authenticate via Settings |
| "No live price found" | WebSocket not connecting | Check backend logs for ticker errors |
| "Strike rows should appear" timeout | Option chain API slow | Increase timeout or check backend |
| Tests pass locally, fail headed | Browser window too small | Tests auto-maximize; check display settings |
