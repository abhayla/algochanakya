# Code-Reviewer Agent Memory

**Purpose:** Track review patterns, frequent violations, and false positives
**Agent:** code-reviewer
**Last Updated:** 2026-02-25

---

## Patterns Observed

### Frequent Violations

#### Broker Abstraction Violations
- Direct `from kiteconnect import KiteConnect` in route files (seen during Phase 1-3 migration)
- Direct `SmartConnect` usage in option chain service before Phase 3 refactor
- Hardcoded broker name strings — DB stores `zerodha`/`angelone`, BrokerType enum uses `kite`/`angel`
- Bypassing `get_market_data_adapter()` to call SmartAPI historical directly
- Importing from `app.services.deprecated/` instead of new ticker adapters (post Phase 4)

#### Trading Constants Violations
- Hardcoded `lot_size = 25` for NIFTY in strategy calculations
- Hardcoded `strike_step = 50` in option chain filtering
- Hardcoded index tokens (256265, 260105) in WebSocket subscription code
- Fix: `from app.constants.trading import get_lot_size, get_strike_step, INDEX_TOKENS`

#### Folder Structure Violations
- New services created at `backend/app/services/` root instead of subdirectory
- E2E test specs at `tests/e2e/specs/` root without screen subdirectory
- CSS files in `frontend/src/assets/css/` instead of `styles/`

### False Positives

- `backend/app/services/instruments.py` — allowed at root (legacy exception in ALLOWED_BACKEND_ROOT_SERVICES)
- `backend/app/services/ofo_calculator.py` — allowed at root (legacy exception)
- `backend/app/services/option_chain_service.py` — allowed at root (legacy exception)
- Test files importing from both backend/frontend layers — tests are exempt from cross-layer rules
- `__init__.py` and `conftest.py` at test root — allowed by guard_folder_structure.py

---

## Decisions Made

### Review Precedents

- Broker name mismatch (`zerodha` in DB vs `kite` in enum) is a known mapping, not a violation
- `Decimal` usage in ticker adapters is mandatory (not `float`) for NormalizedTick price precision
- Legacy services in `app/services/legacy/` and `app/services/deprecated/` are acceptable during migration
- `alembic/versions/` migration files should NOT be auto-formatted (skip in auto_format.py)

### Approval Criteria Evolution

- Phase 4+ (Feb 2026): All new broker code MUST use ticker adapter pattern, not legacy singletons
- Phase 6+ (Feb 2026): All routes MUST use `get_broker_adapter()` factory, zero direct imports
- All 6 brokers supported: Zerodha (Kite), AngelOne (SmartAPI), Upstox, Dhan, Fyers, Paytm

---

## Common Issues

### Recurring Code Patterns

- Missing `await` on SQLAlchemy queries (sync vs async confusion)
- Missing model import in `alembic/env.py` causing silent migration failures
- Frontend using `axios` directly instead of `@/services/api` wrapper
- Using `float` instead of `Decimal` for price fields in new ticker code

### Edge Cases

- `UnifiedOrder.status`: Kite uses "COMPLETE", AngelOne uses "complete" — adapter must normalize to uppercase
- Symbol format: canonical includes exchange prefix (`NSE:NIFTY...`), some code strips it incorrectly
- SmartAPI token format differs from Kite token format — use `TokenManager` for conversion

---

## Last Updated

2026-02-14: Agent memory system initialized
2026-02-25: Populated with baseline data from Phases 1-6 development history
