# Frontend Development Guide

> This file provides frontend-specific guidance for Claude Code. It loads automatically when working with `frontend/` files.
> For cross-cutting rules and mandatory behaviors, see the [root CLAUDE.md](../CLAUDE.md).

---

## Development Commands

### Frontend (from `frontend/`)

```bash
npm run dev           # Development server
npm run build         # Production build
npm run test          # Unit tests (watch mode)
npm run test:run      # Unit tests (once)
npm run test:coverage # Unit tests with coverage
npm run lint          # ESLint check
npm run lint:fix      # ESLint auto-fix
npm run format        # Prettier format
npm run format:check  # Prettier check (CI)
```

### E2E Tests (from project root)

```bash
npm test                           # All tests (auto-login via SmartAPI)
npm run test:specs:{screen}        # By screen: login, dashboard, positions, watchlist, optionchain, strategy, strategylibrary, autopilot, navigation, audit, ofo
npm run test:happy                 # All happy path tests
npm run test:edge                  # All edge case tests
npm run test:headed                # With visible browser
npm run test:debug                 # Debug mode
npm run test:ui                    # Interactive UI mode for debugging
npm run test:audit                 # Accessibility audits
npm run test:isolated              # Tests needing fresh context (login, OAuth)
npx playwright test path/to/spec  # Single file
npx playwright test --grep "test name"  # Single test by name

# AutoPilot-specific tests
npm run test:autopilot:fast        # Fast AutoPilot tests (4 workers, 15s timeout)
npm run test:autopilot:phase4      # Phase 4 tests
npm run test:autopilot:phases123   # Phases 1-3 tests

# Allure reporting
npm run test:allure                # Run tests + generate Allure report + open
npm run allure:serve               # Serve existing allure results

# Test generation
npm run generate:test              # Generate new test from template
```

### Debug Commands

```bash
npx playwright test path/to/spec --debug       # Debug E2E test
npx playwright show-trace trace.zip            # View trace
```

```javascript
// Browser console - test WebSocket (dev on port 8001)
const ws = new WebSocket('ws://localhost:8001/ws/ticks?token=YOUR_JWT')
ws.onmessage = (e) => console.log(JSON.parse(e.data))
ws.send(JSON.stringify({action: 'subscribe', tokens: [256265], mode: 'quote'}))
```

---

## Folder Structure Rules (ENFORCED by hooks)

See [.claude/rules.md](../.claude/rules.md) for all enforced folder structure rules (CSS, images, API code, test organization).

---

## E2E Test Rules

E2E conventions auto-load from `.claude/rules/e2e-*.md`. Key docs: [E2E Test Rules](../docs/testing/e2e-test-rules.md) | [Testing README](../docs/testing/README.md)

**Headless mode:** `playwright.config.js` sets `headless: false` by default for debugging.

---

## Environment Variables

- `frontend/.env`: `VITE_API_BASE_URL=http://localhost:8001`, `VITE_WS_URL=ws://localhost:8001`
- `frontend/.env.local`: Overrides `.env` — **MUST** point to `http://localhost:8001` for dev (not 8005/8000). Git-ignored.
- `frontend/.env.production`: Git-tracked, points to `https://algochanakya.com`.

---

## WebSocket

- Dev: `ws://localhost:8001/ws/ticks?token=<jwt>` | Prod: `wss://algochanakya.com/ws/ticks?token=<jwt>`
- Always close subscriptions in `onUnmounted()` to prevent memory leaks
- Trading constants loaded from `/api/constants/trading` on app init (`src/constants/trading.js`)

---

## Frontend-Specific Pitfalls

- **Wrong port in `.env.local`** — must be `http://localhost:8001` (not 8005/8000)
- **AngelOne login timeout** — auto-TOTP takes 20-25s, use `timeout: 35000` in axios POST
- **WebSocket not cleaned up** — close subscriptions in `onUnmounted()`
- E2E pitfalls (testid, fixtures, selectors) auto-load from `.claude/rules/e2e-*.md`
