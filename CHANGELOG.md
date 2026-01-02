# Changelog

All notable changes to AlgoChanakya will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **OHLC Endpoint for Market-Closed Fallback** - New `/api/orders/ohlc` and `/api/orders/quote` endpoints for fetching index prices when market is closed. Frontend automatically falls back to OHLC data when quote API fails outside market hours.
- **AI + AutoPilot Integration** (Week 3 - AutoPilot AI)
  - AI Config integration with AutoPilot StrategyMonitor and OrderExecutor
  - Confidence-based position sizing in order execution (tiered multipliers: SKIP 0x, LOW 1.0x, MEDIUM 1.5x, HIGH 2.0x)
  - AI limits enforcement: VIX limit, daily lots limit, max strategies per day, minimum confidence threshold
  - Paper/Live mode validation with graduation status checking
  - AI metadata tracking in strategies and orders (confidence score, regime type, sizing tier, tier multiplier)
  - Database migration 011: Added 5 AI fields to autopilot_strategies, 2 fields to autopilot_orders
  - Automatic trading mode enforcement (forces paper mode when AI configured for paper trading)
  - Real-time AI limit alerts via WebSocket (ai_limit alert type)
  - Comprehensive logging for AI position sizing decisions
  - **Automated testing verification** - Unit test for AIConfigService position sizing (4/4 tests passed, 100% success rate)

- **AI Configuration & Settings** feature (Week 2 - AutoPilot AI)
  - Autonomous AI trading configuration with position sizing, deployment scheduling, and risk limits
  - Paper trading graduation system (25 trades, 55% win rate, 15 days)
  - Confidence-based position sizing with tiered multipliers
  - Deployment schedule with event day and weekly expiry skipping
  - 9 REST API endpoints for configuration management
  - AIConfigService with lot calculation and limit enforcement
  - AI Settings view with 5 configuration panels and auto-save
  - Navigation link with brain icon in KiteHeader
  - Complete documentation in docs/features/ai/
- Documentation reorganization with industry-standard structure
- CHANGELOG.md for version history
- Architecture Decision Records (ADRs)
- Troubleshooting guide

### Changed
- **AutoPilot StrategyMonitor** - Added AI config limits checking before strategy execution (file: backend/app/services/strategy_monitor.py)
- **AutoPilot OrderExecutor** - Integrated AI position sizing with confidence-based lot calculation (file: backend/app/services/order_executor.py)
- **AutoPilot Models** - Added AI metadata fields to AutoPilotStrategy and AutoPilotOrder models (file: backend/app/models/autopilot.py)
- **OrderRequest dataclass** - Added ai_sizing_mode and ai_tier_multiplier fields for tracking (file: backend/app/services/order_executor.py)
- Moved documentation to `docs/` folder
- Flattened screenshot directory structure
- Extended AI router with configuration endpoints (file: backend/app/api/v1/ai/router.py)
- Updated User model with ai_config relationship (file: backend/app/models/users.py)
- Updated feature registry with AI configuration patterns (file: docs/feature-registry.yaml)

### Fixed
- AutoPilot: CMP not displaying for strategy legs created from templates
- AI Configuration: Confidence tier boundary validation gaps (59→60, 74→75, 84→85) (file: backend/app/models/ai.py)
- **AI Position Sizing**: Tier boundary ambiguity at 85% confidence - discovered during testing that 85% matched MEDIUM tier (1.5x) instead of HIGH tier (2.0x) due to overlapping tier ranges; updated test strategy to 86% for unambiguous HIGH classification

## [0.5.0] - 2024-12-07

### Added
- Dashboard-style header on login page
- Redirect to Dashboard after successful login

### Changed
- Redesigned login screen with light theme
- Added broker logos to login page

## [0.4.0] - 2024-12-06

### Added
- **Option Chain** feature with full OI, IV, Greeks display
- Live data integration for option chain
- Strategy integration from option chain (add legs directly)
- Auto-calculation for option chain flow

### Fixed
- Breakeven accuracy in P/L calculations

## [0.3.0] - 2024-12-05

### Added
- **Strategy Builder** with P/L calculator
- Payoff chart visualization
- Basket order placement via Kite
- Breakeven columns in P/L grid
- Live CMP (Current Market Price) display
- Exit P/L calculation per leg

### Changed
- Redesigned Strategy Builder UI with full-width layout
- Enhanced P/L grid with dynamic columns

## [0.2.0] - 2024-12-04

### Added
- **Watchlist** feature with real-time prices
- WebSocket integration for live tick data
- Instrument search functionality
- Multiple watchlist support
- Index headers (NIFTY, BANKNIFTY, FINNIFTY)

### Changed
- Updated CLAUDE.md with WebSocket and watchlist documentation

## [0.1.0] - 2024-12-03

### Added
- Initial project setup
- FastAPI backend with async PostgreSQL
- Vue.js 3 frontend with Vite
- Zerodha Kite Connect OAuth integration
- JWT-based session management
- Redis for session storage
- Basic user and broker connection models
- Health check endpoint
- Playwright E2E testing setup

### Infrastructure
- PostgreSQL database on VPS
- Redis cache on VPS
- Alembic migrations

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.5.0 | 2024-12-07 | Login redesign, Dashboard redirect |
| 0.4.0 | 2024-12-06 | Option Chain with OI, IV, Greeks |
| 0.3.0 | 2024-12-05 | Strategy Builder with P/L calculator |
| 0.2.0 | 2024-12-04 | Watchlist with live prices |
| 0.1.0 | 2024-12-03 | Initial setup with Kite OAuth |

[Unreleased]: https://github.com/abhayla/algochanakya/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/abhayla/algochanakya/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/abhayla/algochanakya/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/abhayla/algochanakya/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/abhayla/algochanakya/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/abhayla/algochanakya/releases/tag/v0.1.0
