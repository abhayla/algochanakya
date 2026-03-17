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

## E2E Test Rules (CRITICAL)

**Complete E2E guidelines:** [E2E Test Rules](../docs/testing/e2e-test-rules.md) | [Testing README](../docs/testing/README.md)

**Key rules (quick reference):**
- **Use `data-testid` ONLY** - no CSS classes, tags, or text selectors
- **Import from `auth.fixture.js`** (NOT `@playwright/test`)
- **Use `authenticatedPage` fixture** for authenticated tests
- **data-testid convention:** `[screen]-[component]-[element]` (e.g., `positions-exit-modal`)
- **Headless mode:** `playwright.config.js` sets `headless: false` by default for better debugging.

---

## Environment Variables

**Setup:** Copy `.env.example` to `.env` and update with actual values.

**Frontend (`frontend/.env`):** `VITE_API_BASE_URL=http://localhost:8001` (dev port), `VITE_WS_URL=ws://localhost:8001` (optional, defaults to API URL)

**Frontend Local Override (`frontend/.env.local`):** Overrides `.env` for local development. **CRITICAL:** Must point to `http://localhost:8001` for dev backend. Common mistake: pointing to wrong port (8005, 8000). This file is git-ignored. **Note:** `.env.example` shows port 8000 (production default) - manually change to 8001 for development.

**Production Build:** `frontend/.env.production` is **git-tracked** with `VITE_API_BASE_URL=https://algochanakya.com` and `VITE_WS_URL=algochanakya.com`. No manual creation needed for builds.

---

## Trading Constants (Frontend)

**NEVER hardcode lot sizes, strike steps, or index tokens.** Always use centralized constants:

```javascript
// Frontend - loaded from backend API on app init
// File: frontend/src/constants/trading.js
import { getLotSize, getStrikeStep, useTradingConstants } from '@/constants/trading'

// Direct function calls
const lotSize = getLotSize('NIFTY')  // 75

// Or use the composable for reactive access
const { LOT_SIZES, STRIKE_STEPS, loadTradingConstants } = useTradingConstants()
```

**Note:** Frontend constants are fetched from `/api/constants/trading` on app initialization. The file contains fallback defaults that match backend values.

---

## WebSocket Patterns

**Connection URLs:**
- Dev: `ws://localhost:8001/ws/ticks?token=<jwt>`
- Prod: `wss://algochanakya.com/ws/ticks?token=<jwt>`
- Index tokens: NIFTY=256265, BANKNIFTY=260105, FINNIFTY=257801, SENSEX=265

**Cleanup:** Always close WebSocket subscriptions in `onUnmounted()` to prevent memory leaks.

**Key files:**
- `src/services/api.js` - HTTP interceptor
- `src/stores/auth.js` - Auth state management

---

## Authentication (Frontend)

The axios interceptor in `src/services/api.js` handles 401 responses by:
1. Clearing `access_token` from localStorage
2. Redirecting to `/login`

**Key Files:**
- `src/services/api.js` - HTTP interceptor (lines 27-35)
- `src/stores/auth.js` - Auth state management

---

## Frontend-Specific Pitfalls

- **Missing `data-testid`** - Required for E2E tests; use `[screen]-[component]-[element]`
- **WebSocket not cleaned up** - Close subscriptions in `onUnmounted()`
- **Direct Kite API calls** - All broker operations go through backend
- **Wrong backend port in `.env.local`** - Frontend `.env.local` overrides `.env`. Must point to `http://localhost:8001` for dev, not 8005 or 8000
- **AngelOne login timeout** - AngelOne auth with auto-TOTP takes 20-25 seconds. Default axios timeout (10s) is too short. Use `timeout: 35000` in POST request to `/api/auth/angelone/login`
- **Wrong import in tests** - Use `auth.fixture.js`, NOT `@playwright/test`
- **CSS/text selectors in tests** - Use `data-testid` only
