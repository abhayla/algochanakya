# AlgoChanakya Documentation

Welcome to the AlgoChanakya documentation. This index provides quick access to all documentation resources.

## Quick Links

| Document | Description |
|----------|-------------|
| [Architecture Overview](architecture/overview.md) | System architecture, tech stack |
| [Getting Started](guides/development.md) | Development environment setup |
| [API Reference](api/README.md) | API endpoints and usage |
| [Testing Guide](testing/README.md) | E2E testing with Playwright |

## Feature Registry

**`feature-registry.yaml`** - Central registry mapping code files to features for automatic documentation maintenance. Used by the `docs-maintainer` Claude Code skill to keep docs in sync with code changes.

## Documentation Structure

```
docs/
├── feature-registry.yaml  # Maps code files to features
├── architecture/       # System design and technical architecture
│   ├── overview.md     # Tech stack, project structure
│   ├── authentication.md  # OAuth flow, session management
│   ├── websocket.md    # Live price streaming
│   └── database.md     # Database models, migrations
│
├── guides/             # How-to guides and tutorials
│   ├── development.md  # Dev environment setup
│   ├── database-setup.md  # Database configuration
│   └── troubleshooting.md  # Common issues and fixes
│
├── features/           # Feature-specific documentation
│   ├── watchlist/      # Watchlist with real-time prices
│   │   ├── README.md   # Feature overview
│   │   ├── REQUIREMENTS.md  # Requirements checklist
│   │   └── CHANGELOG.md     # Feature changelog
│   ├── positions/      # F&O positions management
│   ├── option-chain/   # Option chain with OI, IV, Greeks
│   ├── strategy-builder/  # Options strategy builder
│   ├── strategy-library/  # Pre-built strategies with AI wizard
│   ├── autopilot/      # AutoPilot auto-execution
│   ├── authentication/ # Zerodha OAuth integration
│   ├── websocket/      # Live data streaming service
│   ├── orders/         # Order management
│   ├── user-preferences/  # User settings
│   └── dashboard/      # Main dashboard
│
├── autopilot/          # AutoPilot auto-execution system
│   ├── README.md       # Overview and architecture
│   ├── ui-ux-design.md # Screens, wireframes, user flows
│   ├── component-design.md  # Vue.js 3 component specs
│   ├── database-schema.md   # PostgreSQL tables, triggers
│   └── api-contracts.md     # FastAPI endpoints, Pydantic models
│
├── api/                # API documentation
│   ├── README.md       # API overview
│   └── openapi.yaml    # OpenAPI specification
│
├── testing/            # Testing documentation
│   └── README.md       # Testing architecture (160 tests)
│
├── decisions/          # Architecture Decision Records (ADRs)
│   ├── template.md     # ADR template
│   └── 001-tech-stack.md  # Tech stack decision
│
├── templates/          # Documentation templates
│   ├── feature.md      # Feature doc template
│   ├── guide.md        # Guide template
│   └── adr.md          # ADR template
│
├── plans/              # Implementation plans
│   └── cmp-fallback.md # CMP fallback feature plan
│
└── assets/             # Images and screenshots
    ├── diagrams/       # Architecture diagrams
    └── screenshots/    # UI screenshots
```

## Architecture

- **[Overview](architecture/overview.md)** - Tech stack (Vue 3 + FastAPI + PostgreSQL), project structure
- **[Authentication](architecture/authentication.md)** - Zerodha OAuth flow, JWT sessions, protected routes
- **[WebSocket](architecture/websocket.md)** - Live price streaming via Kite WebSocket
- **[Database](architecture/database.md)** - SQLAlchemy models, Alembic migrations

## Guides

- **[Development Setup](guides/development.md)** - Get your local environment running
- **[Database Setup](guides/database-setup.md)** - PostgreSQL and Redis configuration
- **[Troubleshooting](guides/troubleshooting.md)** - Common issues and solutions

## Features

Each feature has its own folder with README.md, REQUIREMENTS.md, and CHANGELOG.md.

### Core Trading Features
- **[Watchlist](features/watchlist/)** - Real-time watchlist with live prices
- **[Option Chain](features/option-chain/)** - Full option chain with OI, IV, Greeks, strike finder
- **[Strategy Builder](features/strategy-builder/)** - Multi-leg strategy builder with P/L calculator, payoff charts
- **[Strategy Library](features/strategy-library/)** - 20+ pre-built templates with AI wizard
- **[Positions](features/positions/)** - F&O positions with live P&L tracking
- **[AutoPilot](features/autopilot/)** - Automated execution with conditional entry, adjustments, risk management (5 phases)

### Supporting Features
- **[Authentication](features/authentication/)** - Zerodha OAuth integration, JWT sessions
- **[WebSocket](features/websocket/)** - Live market data streaming service
- **[Orders](features/orders/)** - Order placement and basket execution
- **[User Preferences](features/user-preferences/)** - User settings and configuration
- **[Dashboard](features/dashboard/)** - Main navigation dashboard

## API

- **[API Overview](api/README.md)** - Authentication, endpoints, error handling
- **[OpenAPI Spec](api/openapi.yaml)** - Machine-readable API specification

## Testing

- **[Testing Guide](testing/README.md)** - ~310 tests (240 E2E + 70 backend pytest)
- **[Conventions](testing/conventions.md)** - data-testid naming conventions

## Decisions

Architecture Decision Records document why key decisions were made:

- **[ADR-001: Tech Stack](decisions/001-tech-stack.md)** - Vue 3, FastAPI, PostgreSQL

## Contributing

See the main [README](../README.md) for contribution guidelines.

---

*Last updated: December 2024*
