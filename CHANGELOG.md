# Changelog

All notable changes to AlgoChanakya will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Moved documentation to `docs/` folder
- Flattened screenshot directory structure
- Extended AI router with configuration endpoints (file: backend/app/api/v1/ai/router.py)
- Updated User model with ai_config relationship (file: backend/app/models/users.py)
- Updated feature registry with AI configuration patterns (file: docs/feature-registry.yaml)

### Fixed
- AutoPilot: CMP not displaying for strategy legs created from templates
- AI Configuration: Confidence tier boundary validation gaps (59→60, 74→75, 84→85) (file: backend/app/models/ai.py)

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
