# OFO Changelog

All notable changes to the OFO (Options For Options) feature will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Fixed
- Add deduplication of identical P/L profiles to ensure unique results (file: backend/app/services/ofo_calculator.py)
- Add secondary sort by risk-reward ratio for better result ordering (file: backend/app/services/ofo_calculator.py)

### Added
- Comprehensive E2E tests for calculate button functionality (file: tests/e2e/specs/ofo/ofo.calculate.spec.js)
- Tests for all 9 strategy types with screenshot verification
- Tests for different underlyings (NIFTY, BANKNIFTY, FINNIFTY)
- Tests for different lot sizes and strike ranges

## [1.1.0] - 2026-01-02

### Changed
- "Open in Builder" now shows full P/L grid column range from spot to all strikes (related fix in Strategy Builder v1.2.0)

## [1.0.0] - 2025-12-XX

### Added
- Initial OFO implementation
- Support for 9 strategy types: Iron Condor, Iron Butterfly, Short Straddle, Short Strangle, Long Straddle, Long Strangle, Bull Call Spread, Bear Put Spread, Butterfly Spread
- Multi-strategy selection with Select All / Clear All
- Underlying tabs for NIFTY, BANKNIFTY, FINNIFTY
- Expiry selector
- Strike range configuration (±5 to ±20)
- Lot multiplier (1-10)
- Auto-refresh with configurable interval
- Calculation time display
- Result cards with Open in Builder and Place Order buttons
- OFO Page Object for E2E testing (file: tests/e2e/pages/OFOPage.js)
- Happy path E2E tests (file: tests/e2e/specs/ofo/ofo.happy.spec.js)
- Edge case E2E tests (file: tests/e2e/specs/ofo/ofo.edge.spec.js)
- API E2E tests (file: tests/e2e/specs/ofo/ofo.api.spec.js)
