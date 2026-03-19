# Session: UI Heuristic Review + Login Dropdown Implementation
**Saved:** 2026-03-18T23:45:00+05:30
**Auto-generated:** false

## Summary
Continued the UI heuristic review from a previous session. Reviewed and implemented findings for 6 screens (OFO, Strategy Builder, Strategy Library, Positions, Settings, User Dropdown). Then consolidated the dual Market Data Source UIs into a single unified interface in the Broker Selection section. About to start implementing the login page dropdown redesign.

## Working Files
- `frontend/src/views/LoginView.vue` (read) — current login page with 6 broker buttons, about to be redesigned
- `frontend/src/views/SettingsView.vue` (modified) — removed MarketDataSourceToggle, added sticky save bar, unsaved changes guard
- `frontend/src/components/settings/BrokerSettings.vue` (modified) — upgraded dropdown to rich radio cards with credential status
- `frontend/src/stores/brokerPreferences.js` (modified) — added credentialStatus + fetchCredentialStatus
- `backend/app/api/routes/user_preferences.py` (modified) — added GET /broker-status endpoint
- `docs/ui-review-2026-03-18.md` (modified) — tracking all 9 screen reviews
- `docs/architecture/authentication.md` (read) — 6 broker auth flows reference

## Recent Changes
No uncommitted changes. All 7 commits pushed to main:
- `7dbe15f` feat(ofo): implement 10 heuristic review findings
- `8e619b3` feat(strategy-builder): implement 12 heuristic review findings
- `dff94b8` feat(strategy-library): implement 10 heuristic review findings
- `6827593` feat(positions): implement 10 heuristic review findings
- `61db661` feat(settings,dropdown): implement heuristic review findings
- `b6d07a8` refactor(settings): consolidate dual market data source UIs

## Key Decisions
1. All 9 screens reviewed using Nielsen's 10 Usability Heuristics
2. Market closed banners added to OFO, Strategy Builder, Positions
3. NIFTY lot size bug fixed (was 25, now 75) in OFO store
4. Place Order button disabled with "Coming Soon" instead of alert()
5. Toast notifications replacing alert() in Positions
6. Settings: consolidated dual Market Data Source UIs — removed MarketDataSourceToggle, upgraded BrokerSettings to rich cards with credential status badges
7. Login page: decided to replace 6 broker buttons with single dropdown + Login button (NOT YET IMPLEMENTED)

## Relevant Docs
- [UI Review Tracking](docs/ui-review-2026-03-18.md) — all findings, statuses, commits for 9 screens
- [Authentication Architecture](docs/architecture/authentication.md) — 6 broker auth flows, login vs API credentials
- [Broker Abstraction](docs/architecture/broker-abstraction.md) — dual-path market data architecture

## Where I Left Off
**Completed:**
- All 9 screens heuristic review implemented and committed
- Settings Market Data Source consolidation done
- All pushed to main

**About to start:**
- Login page dropdown redesign (biggest pending UX change)

**Login dropdown decisions (from previous session review):**
- Replace 6 separate broker buttons with single dropdown + Login button
- AngelOne: inline fields (Client ID, PIN, 6-digit TOTP from authenticator) — NOT stored
- Dhan: inline fields (Client ID, Access Token) — NOT stored
- OAuth brokers (Zerodha, Upstox, Fyers, Paytm): redirect as before
- Loading feedback after clicking Login
- Fix "terms and conditions" — needs actual link
- LoginView.vue is the file to modify (574 lines)
- Auth store functions already exist for all 6 brokers

**Also remaining from review (lower priority):**
- Dashboard findings: card grid uneven, marketing copy, welcome text
- Login finding #4: nav links accessible without auth
- Login finding #7: terms and conditions link

## Resume Prompt
```
Implement the login page dropdown redesign from the session at .claude/sessions/2026-03-18-ui-review-and-login-dropdown.md

Current state: LoginView.vue has 6 separate broker buttons. Replace with:
1. Single broker dropdown (Zerodha, Angel One, Upstox, Fyers, Dhan, Paytm Money)
2. Dynamic content below dropdown based on selection:
   - OAuth brokers (Zerodha, Upstox, Fyers, Paytm): show "Login with {broker}" button → redirect
   - AngelOne: show inline fields (Client ID, PIN, 6-digit TOTP) + Login button
   - Dhan: show inline fields (Client ID, Access Token) + Login button
3. Loading spinner after clicking Login
4. Remove "Open Now" referral links, "Or login with" dividers, "More brokers" section

Auth store handlers already exist: handleZerodhaLogin, handleAngelOneLogin, handleUpstoxLogin, handleFyersLogin, handleDhanLogin, handlePaytmLogin

File: frontend/src/views/LoginView.vue
Tracking doc: docs/ui-review-2026-03-18.md
```
