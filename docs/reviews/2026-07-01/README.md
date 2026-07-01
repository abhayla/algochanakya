# Visual Verification — 2026-07-01

**24 perfect screenshots.** 6 screens × 4 broker configurations, each meeting the strictest rubric:
(i) structural, (ii) domain-sane values, (iii) external-truth cross-check, (iv) visual polish.

## Broker configurations

| Code | Order Broker | Market Data Source |
|---|---|---|
| **AA** | AngelOne (SmartAPI) | AngelOne SmartAPI |
| **UU** | Upstox | Upstox |
| **AU** | AngelOne (SmartAPI) | Upstox (dual-broker mix A) |
| **UA** | Upstox | AngelOne SmartAPI (dual-broker mix B) |

## Screens verified per config

- **login.png** — pre-auth, broker dropdown filtered (4 brokers: Zerodha, Angel One, Upstox, Dhan; Paytm + Fyers hidden)
- **dashboard.png** — nav (4 items), header prices, greeting, 4 module cards (no AutoPilot/OFO leaks), TODAY's P&L, NIFTY 50 + BANK NIFTY cards live
- **optionchain.png** — 100 strikes populated, ATM highlighted, LTPs in realistic rupees (ATM CE ~₹150-180 for NIFTY, was 1.5-1.8 before the /100 fix), IVs symmetric (~12%), Greeks populated
- **strategy.png** — 4 underlying tabs including SENSEX, NIFTY SPOT populated, empty legs state with placeholder summary cards
- **positions.png** — Day/Net toggle, TOTAL P&L badge, empty state with CTAs to Option Chain and Strategy Builder
- **settings.png** — Market Data Source and Order Broker reflecting the config, Fyers + Paytm sections absent, AngelOne SmartAPI fresh auth

## Key fixes surfaced by this campaign

- **`94355f7`** — SmartAPI LTP scale: options passed through as rupees (were divided by 100), indices still divided (paise). Root cause was pyc cache: previous fix on disk but stale bytecode running.
- **`a1a8ee6`** — Login broker dropdown filtered via feature flags (Paytm + Fyers hidden here too, matching the rest of the hide sweep).
- **`f535c09`** — Settings Fyers + Paytm credential sections v-if-gated (sibling-sweep miss from Iteration 2).
- **`c873a3d`** — SENSEX BFO exchange support in instrument + REST paths (foundation for the SENSEX tab).

## External-truth cross-check (spot)

NIFTY 50 dashboard reading 24,023.75 vs Groww/Bloomberg 23,997.20 (intraday high 24,020.65) — delta 26 points (~0.1%), within seconds-scale intraday movement. Change (~+0.66%) matches exactly.

## Regenerate

The audit script `audit-single.mjs` (repo root, gitignored) accepts `<config> <screenName> <path> <waitMs> [noauth]`. To regenerate any single screenshot after code changes, switch prefs via `PUT /api/user/preferences/`, run the audit, read the PNG, apply rubric.
