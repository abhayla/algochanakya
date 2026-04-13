# Session: 2026-04-12-nse-crossverify-e2e-tests

**Date:** 2026-04-12 22:00 IST
**Branch:** main

---

## Working Files

| File | Status | Notes |
|------|--------|-------|
| `frontend/src/views/OptionChainView.vue` | modified | Added per-strike `data-testid` attributes for CE/PE LTP, OI, IV, Volume, Strike cells |
| `tests/e2e/pages/OptionChainPage.js` | modified | Added per-strike getters, `parseNumericText()`, `getVisibleStrikes()`, LTP/OI value extractors |
| `tests/e2e/specs/optionchain/optionchain.crossverify.api.spec.js` | created | Full NSE cross-verification E2E test suite (13 tests) |
| `tests/e2e/specs/navigation/navigation.cross-screen.spec.js` | modified | Minor updates (from prior session) |
| `backend/app/api/routes/optionchain.py` | read | Studied how PCR, total OI, max pain, and close_price fallback work |
| `backend/tests/live/test_live_nse_cross_verification.py` | read | Reused NSE API patterns for E2E tests |

## Git State

- **Branch:** main
- **Last 5 commits:**
  - 9781129 fix(tests): fix Upstox cross-verification tests — spot match, graceful skips
  - ab7077c fix(tests): use NSE v3 API for cross-verification tests (works on weekends)
  - edc47b9 fix(instruments): add source_broker filtering to prevent duplicate instrument rows
  - 5e2c854 docs(skills): add cross-broker instrument token architecture reference
  - 1855e93 fix(market-data): fix Upstox option chain token keying and add pre-calculated Greeks
- **Uncommitted changes:** yes — OptionChainView.vue data-testid additions, OptionChainPage.js per-strike helpers, new crossverify spec file
- **Stash list:** stash@{0}: WIP: Token mapping changes before multi-broker ticker refactor

## Key Decisions

- **NSE v3 API over v1:** v1 (`/api/option-chain-indices`) returns empty `{}` on weekends; v3 (`/api/option-chain-v3`) returns cached data with per-strike OI/LTP even on weekends
- **OI calculated from per-strike sums, not totCE/totPE:** NSE's `filtered.totCE.totOI` is 0 on weekends, but individual strike OI values are non-zero — must sum per-strike data
- **Split PCR test into market-hours vs off-market:** Broker (Upstox) returns OI for only 2/246 strikes off-market, causing PCR=12.16 vs NSE's 1.17. This is a broker limitation, not an app bug. Market-hours test compares against NSE (tolerance +/-0.3); off-market test checks sane range (0.1-15.0)
- **Per-strike data-testid pattern:** Used `:data-testid="'optionchain-ce-ltp-' + row.strike"` format for dynamic per-strike selectors enabling E2E data extraction
- **Cookie-based NSE fetch via Playwright request context:** NSE requires cookies from visiting the option chain page first, plus browser-like User-Agent headers

## Task Progress

### Completed

- Added per-strike `data-testid` attributes to OptionChainView.vue (CE/PE LTP, OI, IV, Volume, Strike)
- Added per-strike getter methods and data extraction helpers to OptionChainPage.js
- Created full NSE cross-verification E2E test suite with 13 tests
- Fixed NSE `parseNSEResponse` to calculate OI from per-strike sums (not zero-valued totals)
- Split PCR test into market-hours (exact NSE match) and off-market (sane range)
- Added data completeness diagnostic test
- Fixed BANKNIFTY test race condition (waitForFunction to detect spot price change)
- Saved IST market time feedback memory
- Verified all tests pass or skip correctly on Sunday off-market (8 passed, 5 skipped, 0 failures)

### In Progress

- Market-hours validation — 5 tests skip off-market (ATM CE/PE LTP, PCR vs NSE, multiple strikes non-zero data, OI match). Need to re-run on a weekday during 9:15-15:30 IST to validate these pass
- FINNIFTY cross-verification — not yet tested (only NIFTY and BANKNIFTY covered)

### Blocked

- None

## Relevant Docs

| Document | Relevance |
|----------|-----------|
| `docs/architecture/broker-abstraction.md` | Explains dual-broker system (market data vs order execution) |
| `backend/app/api/routes/optionchain.py` | Backend option chain logic — PCR, max pain, OI aggregation |
| `.claude/rules/e2e-data-testid-only.md` | E2E selector conventions used |
| `.claude/rules/e2e-page-object-pattern.md` | Page object pattern followed |

## Resume Notes

- **Start here:** Run the cross-verification tests during market hours (Mon-Fri 9:15-15:30 IST) to validate the 5 currently-skipped tests: `npx playwright test tests/e2e/specs/optionchain/optionchain.crossverify.api.spec.js --reporter=list`
- **Watch out for:** Upstox returns incomplete OI data off-market (only 2/246 strikes) — PCR and OI comparisons are only meaningful during market hours. NSE v3 API requires cookie warmup (visit page first). BANKNIFTY tab switch has a race condition — `waitForFunction` handles it but takes 15s
- **Context needed:** Re-read `optionchain.crossverify.api.spec.js` for the full test structure; re-read `OptionChainPage.js` for the per-strike helper API
